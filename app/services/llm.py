import base64
import binascii
import json
import os
import re
import time
from typing import Any, Type, TypeVar

from google import genai
from google.genai import errors as google_exc
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

# Default: current Flash model (2.0 IDs are often 404 for new API users). Override with GEMINI_MODEL.
DEFAULT_MODEL = "gemini-2.5-flash"
_MAX_COMPLETION_ATTEMPTS = max(1, int(os.environ.get("GEMINI_MAX_RETRIES") or "8"))

JSON_SYSTEM_MESSAGE = (
    "You are a JSON-only API. Respond with a single valid JSON object. "
    "No markdown fences, no commentary, no text before or after the JSON."
)


def _backoff_seconds(attempt: int) -> float:
    """Exponential backoff capped at 90s; attempt is 0-based."""
    return min(2.0**attempt + 0.25, 90.0)


def _is_quota_retryable(exc: BaseException) -> bool:
    """429 / quota / transient overload from Gemini."""
    if isinstance(exc, google_exc.ClientError):
        msg = str(exc).lower()
        if "429" in msg or "resource exhausted" in msg or "quota" in msg:
            return True
        if "503" in msg or "overloaded" in msg or "unavailable" in msg:
            return True
        return False
    msg = str(exc).lower()
    if "429" in msg or "resource exhausted" in msg or "quota" in msg:
        return True
    if "503" in msg or "overloaded" in msg or "unavailable" in msg:
        return True
    return False


def extract_json_object(text: str) -> dict[str, Any]:
    """
    Find and parse the first valid JSON object in text.
    Handles markdown code fences and leading/trailing prose.
    """
    if not text or not text.strip():
        raise ValueError("Empty model response; no JSON to parse")

    cleaned = _strip_markdown_fences(text.strip())

    decoder = json.JSONDecoder()
    start = 0
    while True:
        brace = cleaned.find("{", start)
        if brace == -1:
            break
        try:
            obj, _ = decoder.raw_decode(cleaned, brace)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
        start = brace + 1

    match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", cleaned, re.DOTALL)
    if match:
        try:
            obj = json.loads(match.group(0))
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass

    try:
        obj = json.loads(cleaned)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    raise ValueError("No valid JSON object found in model response")


def _strip_markdown_fences(text: str) -> str:
    t = text.strip()
    if not t.startswith("```"):
        return t
    lines = t.split("\n")
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _gemini_api_key() -> str:
    return (
        (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "")
        .strip()
    )


def call_llm(prompt: str) -> dict[str, Any]:
    """
    Send a prompt to Google Gemini and return the first JSON object from the reply.

    API key: ``GEMINI_API_KEY`` (or ``GOOGLE_API_KEY``).
    Model: ``GEMINI_MODEL`` or ``gemini-2.5-flash``.
    """
    api_key = _gemini_api_key()
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it to the project `.env` file "
            "(or set GOOGLE_API_KEY). Get a key at https://aistudio.google.com/apikey"
        )

    model_name = (os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL).strip() or DEFAULT_MODEL
    client = genai.Client(api_key=api_key)

    from google.genai import types as genai_types
    config = genai_types.GenerateContentConfig(
        temperature=0.2,
        response_mime_type="application/json",
        system_instruction=JSON_SYSTEM_MESSAGE,
    )

    response = None
    last_quota_error: Exception | None = None
    for attempt in range(_MAX_COMPLETION_ATTEMPTS):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )
            break
        except (google_exc.ClientError, OSError, TimeoutError) as e:
            if "404" in str(e) or "not found" in str(e).lower():
                raise RuntimeError(
                    f"Gemini model {model_name!r} was not found or is not available for your account. "
                    "Set GEMINI_MODEL=gemini-2.5-flash (or gemini-1.5-flash) in `.env`. "
                    "See https://ai.google.dev/gemini-api/docs/models"
                ) from e
            if _is_quota_retryable(e):
                last_quota_error = e
                if attempt == _MAX_COMPLETION_ATTEMPTS - 1:
                    raise RuntimeError(
                        "Gemini quota / rate limit: still failing after "
                        f"{_MAX_COMPLETION_ATTEMPTS} attempts. "
                        "Wait a few minutes or check API usage in Google AI Studio."
                    ) from e
                time.sleep(_backoff_seconds(attempt))
                continue
            raise RuntimeError(f"Gemini API error: {e}") from e

    if response is None:
        raise RuntimeError("Gemini request failed after retries.") from last_quota_error

    if not response.candidates:
        fb = getattr(response, "prompt_feedback", None)
        raise RuntimeError(f"Gemini returned no candidates (blocked or empty). feedback={fb}")

    content = (response.text or "").strip()
    if not content:
        raise ValueError("Gemini returned empty message content")

    try:
        parsed = extract_json_object(content)
    except ValueError as e:
        raise ValueError(f"Could not parse JSON from model output: {e}") from e

    return parsed


def call_llm_validated(prompt: str, model: Type[T]) -> T:
    """Run call_llm and validate against a Pydantic model."""
    data = call_llm(prompt)
    try:
        return model.model_validate(data)
    except ValidationError as e:
        raise ValueError(f"LLM output failed schema validation: {e}") from e


_MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MiB raw image


def call_llm_validated_with_image(
    prompt: str,
    image_bytes: bytes,
    mime_type: str,
    model: Type[T],
) -> T:
    """
    Multimodal Gemini: one image + text prompt → JSON validated as ``model``.
    """
    if len(image_bytes) > _MAX_IMAGE_BYTES:
        raise ValueError(f"Image too large (max {_MAX_IMAGE_BYTES} bytes)")
    api_key = _gemini_api_key()
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it to the project `.env` file "
            "(or set GOOGLE_API_KEY). Get a key at https://aistudio.google.com/apikey"
        )

    model_name = (os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL).strip() or DEFAULT_MODEL
    client = genai.Client(api_key=api_key)

    from google.genai import types as genai_types
    mt = (mime_type or "image/png").split(";")[0].strip().lower()
    if mt not in ("image/png", "image/jpeg", "image/webp", "image/gif"):
        mt = "image/png"

    config = genai_types.GenerateContentConfig(
        temperature=0.2,
        response_mime_type="application/json",
        system_instruction=JSON_SYSTEM_MESSAGE,
    )

    response = None
    last_quota_error: Exception | None = None
    for attempt in range(_MAX_COMPLETION_ATTEMPTS):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[
                    genai_types.Part.from_bytes(data=image_bytes, mime_type=mt),
                    prompt,
                ],
                config=config,
            )
            break
        except (google_exc.ClientError, OSError, TimeoutError) as e:
            if "404" in str(e) or "not found" in str(e).lower():
                raise RuntimeError(
                    f"Gemini model {model_name!r} was not found or is not available for your account. "
                    "Set GEMINI_MODEL=gemini-2.5-flash (or gemini-1.5-flash) in `.env`."
                ) from e
            if _is_quota_retryable(e):
                last_quota_error = e
                if attempt == _MAX_COMPLETION_ATTEMPTS - 1:
                    raise RuntimeError(
                        "Gemini quota / rate limit: still failing after "
                        f"{_MAX_COMPLETION_ATTEMPTS} attempts."
                    ) from e
                time.sleep(_backoff_seconds(attempt))
                continue
            raise RuntimeError(f"Gemini API error: {e}") from e

    if response is None:
        raise RuntimeError("Gemini request failed after retries.") from last_quota_error

    if not response.candidates:
        fb = getattr(response, "prompt_feedback", None)
        raise RuntimeError(f"Gemini returned no candidates (blocked or empty). feedback={fb}")

    content = (response.text or "").strip()
    if not content:
        raise ValueError("Gemini returned empty message content")

    try:
        parsed = extract_json_object(content)
    except ValueError as e:
        raise ValueError(f"Could not parse JSON from model output: {e}") from e

    try:
        return model.model_validate(parsed)
    except ValidationError as e:
        raise ValueError(f"LLM output failed schema validation: {e}") from e


def decode_image_base64_field(b64: str) -> tuple[bytes, str]:
    """Decode NormalizedPost.image_base64; accepts optional data URL prefix."""
    raw = (b64 or "").strip()
    if not raw:
        raise ValueError("Empty image_base64")
    mime = "image/png"
    if raw.startswith("data:"):
        head, _, rest = raw.partition(",")
        if ";" in head:
            mime = head[5:].split(";")[0].strip() or mime
        raw = rest
    try:
        data = base64.b64decode(raw, validate=True)
    except binascii.Error:
        data = base64.b64decode(raw)
    if len(data) > _MAX_IMAGE_BYTES:
        raise ValueError(f"Image too large (max {_MAX_IMAGE_BYTES} bytes)")
    return data, mime
