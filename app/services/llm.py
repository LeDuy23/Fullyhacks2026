import json
import os
import re
import time
from typing import Any, Type, TypeVar

import google.generativeai as genai
from google.api_core import exceptions as google_exc
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
    """429 / quota / transient overload from Gemini or google-api-core."""
    if isinstance(exc, google_exc.ResourceExhausted):
        return True
    if isinstance(exc, google_exc.ServiceUnavailable):
        return True
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
    genai.configure(api_key=api_key)

    # Dict form works across google-generativeai versions.
    generation_config = {
        "temperature": 0.2,
        "response_mime_type": "application/json",
    }

    model = genai.GenerativeModel(
        model_name,
        system_instruction=JSON_SYSTEM_MESSAGE,
    )

    response = None
    last_quota_error: Exception | None = None
    for attempt in range(_MAX_COMPLETION_ATTEMPTS):
        try:
            response = model.generate_content(
                prompt,
                generation_config=generation_config,
            )
            break
        except (google_exc.GoogleAPIError, OSError, TimeoutError) as e:
            if isinstance(e, google_exc.NotFound):
                raise RuntimeError(
                    f"Gemini model {model_name!r} was not found or is not available for your account. "
                    "Older IDs (e.g. gemini-2.0-flash) may return 404 for new users. "
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

    try:
        content = response.text
    except ValueError as e:
        raise RuntimeError(
            "Gemini returned no text (safety block or empty parts). "
            f"finish_reason={getattr(response.candidates[0], 'finish_reason', None)}"
        ) from e

    if not content or not content.strip():
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
