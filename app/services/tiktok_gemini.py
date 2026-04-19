"""Gemini reads TikTok *metadata* (oEmbed JSON) — not the video file — for travel signals."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from app.services.llm import call_llm_validated
from app.services.tiktok_reader import fetch_tiktok_oembed_data


class TikTokTravelInsight(BaseModel):
    summary: str = ""
    inferred_destinations: list[str] = Field(default_factory=list)
    place_mentions: list[str] = Field(default_factory=list)
    activities: list[str] = Field(default_factory=list)
    vibe_tags: list[str] = Field(default_factory=list)
    limitations: str = (
        "Based on public oEmbed text only (title/author/HTML snippet). "
        "Video, audio, and comments were not accessed."
    )


def _build_tiktok_gemini_prompt(url: str, oembed: dict[str, Any]) -> str:
    schema_hint = """
Return JSON in exactly this shape:
{
  "summary": "string",
  "inferred_destinations": ["string"],
  "place_mentions": ["string"],
  "activities": ["string"],
  "vibe_tags": ["string"],
  "limitations": "string"
}
"""
    return f"""You are a travel assistant. The input is TikTok **oEmbed JSON** for a public video.
You do **not** have transcripts or comments—only title, author_name, thumbnail_url, and embed HTML.
Infer travel-relevant signals conservatively; use "unknown" confidence by preferring empty lists over guesses.

TikTok URL: {url}

oEmbed JSON:
{json.dumps(oembed, indent=2)}

{schema_hint.strip()}

Set "limitations" to remind the user that only public metadata was used if the caption is thin.
"""


def _analyze_tiktok_from_oembed(url: str, oembed: dict[str, Any]) -> TikTokTravelInsight:
    return call_llm_validated(_build_tiktok_gemini_prompt(url, oembed), TikTokTravelInsight)


def analyze_tiktok_with_gemini(url: str) -> TikTokTravelInsight:
    oembed = fetch_tiktok_oembed_data(url)
    return _analyze_tiktok_from_oembed(url, oembed)


def analyze_tiktok_with_gemini_and_oembed(url: str) -> tuple[TikTokTravelInsight, dict[str, Any]]:
    """Single oEmbed fetch + Gemini pass; use when persisting to Supabase (needs raw oEmbed)."""
    oembed = fetch_tiktok_oembed_data(url)
    return _analyze_tiktok_from_oembed(url, oembed), oembed
