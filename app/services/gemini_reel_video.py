"""Gemini native video: upload MP4, extract structured locations, delete file."""

from __future__ import annotations

import os
import time
from pathlib import Path

from google import genai
from google.genai import errors as google_exc
from pydantic import ValidationError

from app.models.reel_extraction import ReelVideoLocations
from app.services.llm import (
    DEFAULT_MODEL,
    JSON_SYSTEM_MESSAGE,
    _MAX_COMPLETION_ATTEMPTS,
    _backoff_seconds,
    _gemini_api_key,
    _is_quota_retryable,
    extract_json_object,
)

_VIDEO_PROMPT = """
Watch this short-form travel/social video. Identify every distinct real-world location
(business, landmark, street, neighborhood venue) that is clearly shown or mentioned.
If you cannot identify a specific named location, do NOT guess — return an empty "locations" array.
Multiple shots of the same location count as ONE entry.
Generic shots (sky, anonymous food close-ups, people with no identifying venue) are NOT locations.

Return JSON only with this exact shape:
{
  "locations": [
    {
      "name": "official or commonly known name",
      "type": "restaurant | cafe | bar | landmark | shop | hotel | beach | dive_site | other",
      "city_hint": "city or neighborhood if inferable, else null",
      "address_hint": "street or address fragment if visible, else null",
      "confidence": 0.0,
      "evidence": [{"source": "visual|audio|text", "detail": "short quote or description"}]
    }
  ]
}
"""


def extract_locations_from_video_file(video_path: str) -> ReelVideoLocations:
    path = Path(video_path)
    if not path.is_file():
        raise FileNotFoundError(video_path)
    api_key = _gemini_api_key()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    model_name = (os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL).strip() or DEFAULT_MODEL
    client = genai.Client(api_key=api_key)

    from google.genai import types as genai_types

    uploaded = None
    try:
        uploaded = client.files.upload(
            file=str(path),
            config=genai_types.UploadFileConfig(mime_type="video/mp4"),
        )
        if not uploaded or not uploaded.name:
            raise RuntimeError("Gemini file upload returned no file name")

        deadline = time.time() + 300
        got = uploaded
        while time.time() < deadline:
            got = client.files.get(name=uploaded.name)
            st = getattr(got, "state", None)
            st_name = str(st) if st is not None else ""
            if "ACTIVE" in st_name.upper():
                break
            if "FAIL" in st_name.upper():
                raise RuntimeError(f"Gemini file processing failed: state={st_name}")
            time.sleep(2.0)
        else:
            raise RuntimeError("Timeout waiting for uploaded video to become ACTIVE")

        uri = getattr(got, "uri", None) or getattr(uploaded, "uri", None)
        mime = getattr(got, "mime_type", None) or getattr(uploaded, "mime_type", None) or "video/mp4"
        if not uri:
            raise RuntimeError("Uploaded file has no uri")

        config = genai_types.GenerateContentConfig(
            temperature=0.15,
            response_mime_type="application/json",
            system_instruction=JSON_SYSTEM_MESSAGE + " " + _VIDEO_PROMPT,
        )

        response = None
        last_quota_error: Exception | None = None
        for attempt in range(_MAX_COMPLETION_ATTEMPTS):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[
                        genai_types.Part.from_uri(file_uri=uri, mime_type=mime),
                        "Extract locations per instructions. Return JSON only.",
                    ],
                    config=config,
                )
                break
            except (google_exc.ClientError, OSError, TimeoutError) as e:
                if _is_quota_retryable(e):
                    last_quota_error = e
                    if attempt == _MAX_COMPLETION_ATTEMPTS - 1:
                        raise RuntimeError("Gemini quota exhausted for video") from e
                    time.sleep(_backoff_seconds(attempt))
                    continue
                raise RuntimeError(f"Gemini video error: {e}") from e

        if response is None:
            raise RuntimeError("Gemini video request failed") from last_quota_error

        content = (response.text or "").strip()
        if not content:
            raise ValueError("Gemini returned empty content for video")
        data = extract_json_object(content)
        try:
            return ReelVideoLocations.model_validate(data)
        except ValidationError as e:
            raise ValueError(f"Video extraction JSON invalid: {e}") from e
    finally:
        if uploaded and getattr(uploaded, "name", None):
            try:
                client.files.delete(name=uploaded.name)
            except Exception:
                pass
