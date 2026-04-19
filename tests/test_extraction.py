"""
Integration tests: raw social text → prompt → call_llm → JSON dict → ExtractionOutput (Pydantic).

Requires GEMINI_API_KEY (or GOOGLE_API_KEY) in `.env` or the environment.
Run from project root:  python -m pytest tests/test_extraction.py -v

Live tests are consolidated to avoid duplicate API calls (rate limits). `call_llm` retries on 429.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_PROJECT_ENV = _PROJECT_ROOT / ".env"
if _PROJECT_ENV.is_file():
    load_dotenv(_PROJECT_ENV, override=True)
else:
    load_dotenv(override=True)

import pytest
from pydantic import ValidationError

from app.models.extraction import ExtractionOutput, NormalizedPost
from app.services.extractor import EXTRACT_SYSTEM_PROMPT, build_extract_prompt
from app.services.llm import call_llm

LIVE_TESTS_ENABLED = bool(
    (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip()
)

# Small pause between calls to reduce burst (backoff in `call_llm` handles 429).
_LIVE_CASE_DELAY_SEC = float(os.environ.get("GEMINI_TEST_DELAY_SEC") or "0.35")

text_1 = """
Best day in Tokyo 🇯🇵
Started at Shibuya Sky for sunset, then sushi at Uobei 🍣
Ended the night in Shinjuku nightlife district 🔥
"""

text_2 = """
POV: you finally visit Paris 😍
croissants at a random cafe, walked along the Seine, Eiffel Tower at night!!
literally felt like a movie
"""

text_3 = """
morning routine, gym, protein shake, answering emails
nothing crazy today
"""

text_4 = """
This rooftop view was insane. Best sunset spot ever.
Food was also crazy good.
"""

MAIN_CASES: list[tuple[str, str]] = [
    ("clear_travel_tokyo", text_1),
    ("messy_influencer_paris", text_2),
    ("weak_non_travel", text_3),
    ("ambiguous_location", text_4),
]


def _build_extraction_prompt(
    raw_text: str,
    *,
    post_id: str = "test_post",
    platform: str = "instagram",
) -> str:
    post = NormalizedPost(
        post_id=post_id,
        url=f"https://example.com/{post_id}",
        platform=platform,
        raw_text=raw_text,
        caption=raw_text.strip(),
    )
    return f"""{EXTRACT_SYSTEM_PROMPT.strip()}

Return ONLY valid JSON matching the requested shape. No explanation.

{build_extract_prompt(post).strip()}
"""


def run_extraction_pipeline(raw_text: str, post_id: str = "test_post") -> ExtractionOutput:
    prompt = _build_extraction_prompt(raw_text, post_id=post_id)
    result: dict[str, Any] = call_llm(prompt)
    try:
        return ExtractionOutput.model_validate(result)
    except ValidationError as exc:
        print("\n--- VALIDATION FAILED ---")
        print("RAW LLM PARSED JSON (dict):")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("PYDANTIC ERRORS:", exc)
        raise


def assert_destination_and_place_confidences(parsed: ExtractionOutput) -> None:
    assert isinstance(parsed.destination_candidates, list)
    assert isinstance(parsed.place_candidates, list)
    for d in parsed.destination_candidates:
        assert isinstance(d.confidence, float)
        assert 0.0 <= d.confidence <= 1.0
    for p in parsed.place_candidates:
        assert isinstance(p.confidence, float)
        assert 0.0 <= p.confidence <= 1.0


def test_confidence_bounds_unit() -> None:
    bad = {
        "post_id": "x",
        "is_travel_relevant": True,
        "destination_candidates": [{"name": "X", "confidence": 2.0}],
        "place_candidates": [],
        "activities": [],
        "vibe_tags": [],
        "best_time_of_day": ["flexible"],
        "budget_signal": "unknown",
        "pace_signal": "unknown",
        "notes": "",
    }
    with pytest.raises(ValidationError):
        ExtractionOutput.model_validate(bad)


@pytest.mark.skipif(
    not LIVE_TESTS_ENABLED,
    reason="GEMINI_API_KEY / GOOGLE_API_KEY missing or empty; skipping live LLM tests",
)
class TestExtractionLive:
    def test_main_cases_single_loop(self) -> None:
        """One API batch: all four captions + assertions (avoids duplicate calls)."""
        for i, (name, text) in enumerate(MAIN_CASES):
            if i > 0:
                time.sleep(_LIVE_CASE_DELAY_SEC)
            print(f"\n--- CASE {i + 1}: {name} ---")
            print("INPUT:", repr(text.strip()[:200] + ("..." if len(text) > 200 else "")))
            parsed = run_extraction_pipeline(text, post_id=f"case_{i + 1}")
            assert_destination_and_place_confidences(parsed)
            print("OUTPUT:", parsed.model_dump_json(indent=2))

            if name == "clear_travel_tokyo":
                assert parsed.is_travel_relevant is True
                dest_blob = " ".join(d.name.lower() for d in parsed.destination_candidates)
                place_blob = " ".join(p.name.lower() for p in parsed.place_candidates)
                assert (
                    "tokyo" in dest_blob
                    or "japan" in dest_blob
                    or "tokyo" in place_blob
                    or "shibuya" in place_blob
                )
            elif name == "messy_influencer_paris":
                assert parsed.is_travel_relevant is True
            elif name == "weak_non_travel":
                dest_max = max((d.confidence for d in parsed.destination_candidates), default=0.0)
                assert not parsed.is_travel_relevant or dest_max < 0.85
            elif name == "ambiguous_location":
                pass

    def test_edge_empty_string_no_crash(self) -> None:
        time.sleep(_LIVE_CASE_DELAY_SEC)
        parsed = run_extraction_pipeline("", post_id="empty_1")
        assert_destination_and_place_confidences(parsed)

    def test_edge_extremely_long_string_handled(self) -> None:
        time.sleep(_LIVE_CASE_DELAY_SEC)
        long_text = ("Checked out this amazing alley in Lisbon! " * 2000)[:120_000]
        try:
            parsed = run_extraction_pipeline(long_text, post_id="long_1")
            assert_destination_and_place_confidences(parsed)
        except RuntimeError as e:
            assert (
                "gemini" in str(e).lower()
                or "google" in str(e).lower()
                or "token" in str(e).lower()
                or "rate" in str(e).lower()
                or "quota" in str(e).lower()
            )
        except ValueError as e:
            assert "parse" in str(e).lower() or "validation" in str(e).lower() or "JSON" in str(e)

    def test_edge_malformed_text_no_unhandled_exception(self) -> None:
        time.sleep(_LIVE_CASE_DELAY_SEC)
        malformed = "Paris \x00 cafe \xff\xfe mixed bytes " + "emoji🔥" * 500
        parsed = run_extraction_pipeline(malformed, post_id="badbytes_1")
        assert_destination_and_place_confidences(parsed)
