"""Persist TikTok oEmbed + Gemini insight into Supabase `posts` + `extractions` (schema-aligned)."""

from __future__ import annotations

import hashlib
import re
from typing import Any
from uuid import UUID

from postgrest.exceptions import APIError

from app.services.supabase_client import get_supabase_client
from app.services.tiktok_gemini import TikTokTravelInsight


class InvalidSupabaseUserError(ValueError):
    """Raised when `user_id` is not a valid `public.users.id` (FK)."""


class SupabaseNotConfiguredError(RuntimeError):
    """Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY."""


class SupabasePersistError(RuntimeError):
    """PostgREST or unexpected failure while writing to Supabase."""


_VIDEO_ID = re.compile(r"/video/(\d+)", re.I)


def client_post_id_from_tiktok_url(url: str) -> str:
    m = _VIDEO_ID.search(url)
    if m:
        return m.group(1)
    h = hashlib.sha256(url.strip().encode("utf-8")).hexdigest()
    return f"tt_{h[:24]}"


def tiktok_insight_to_extraction_row(insight: TikTokTravelInsight) -> dict[str, Any]:
    travel = bool(
        insight.inferred_destinations or insight.place_mentions or insight.activities or insight.vibe_tags
    )
    dest = [{"name": n, "confidence": 0.65} for n in insight.inferred_destinations]
    places = [
        {
            "name": n,
            "type": "unknown",
            "confidence": 0.55,
            "reason": "TikTok oEmbed / Gemini metadata",
        }
        for n in insight.place_mentions
    ]
    notes = insight.summary.strip()
    if insight.limitations:
        notes = f"{notes}\n\n{insight.limitations}".strip()
    return {
        "is_travel_relevant": travel,
        "destination_candidates": dest,
        "place_candidates": places,
        "activities": insight.activities,
        "vibe_tags": insight.vibe_tags,
        "best_time_of_day": ["flexible"],
        "budget_signal": "unknown",
        "pace_signal": "unknown",
        "notes": notes[:20000],
        "aggregate_confidence": 0.55,
        "model_version": "tiktok_gemini_oembed",
    }


def persist_tiktok_gemini_insight(
    *,
    user_id: UUID,
    url: str,
    oembed: dict[str, Any],
    insight: TikTokTravelInsight,
) -> tuple[str, str]:
    """
    Upsert `posts` (unique user_id+url) and `extractions` (unique post_id).
    Returns (post_id, extraction_id) as UUID strings.
    """
    sb = get_supabase_client()
    if sb is None:
        raise SupabaseNotConfiguredError(
            "Supabase is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in `.env`."
        )

    uid = str(user_id)
    raw_text = (oembed.get("title") or "").strip()
    author = (oembed.get("author_name") or "").strip()
    if author:
        raw_text = f"{raw_text}\n@{author}".strip() if raw_text else f"@{author}"

    meta: dict[str, Any] = {
        "source": "tiktok_gemini_oembed",
        "oembed": oembed,
        "tiktok_gemini": insight.model_dump(),
    }

    post_row = {
        "user_id": uid,
        "url": url.strip(),
        "platform": "tiktok",
        "client_post_id": client_post_id_from_tiktok_url(url),
        "raw_text": raw_text or None,
        "metadata_json": meta,
    }

    try:
        pr = (
            sb.table("posts")
            .upsert(post_row, on_conflict="user_id,url", returning="representation")
            .execute()
        )
    except APIError as e:
        msg = (e.message or "") + (e.details or "")
        if "23503" in msg or "foreign key" in msg.lower():
            raise InvalidSupabaseUserError(
                "Invalid user_id: no matching row in public.users (create the user first, or use an existing UUID)."
            ) from e
        raise SupabasePersistError(e.message or str(e)) from e

    rows = pr.data or []
    if not rows:
        raise SupabasePersistError("Supabase upsert returned no post row")
    post_id = rows[0]["id"]
    if not post_id:
        raise SupabasePersistError("Supabase post row missing id")

    ext_payload = {"post_id": post_id, **tiktok_insight_to_extraction_row(insight)}
    try:
        er = (
            sb.table("extractions")
            .upsert(ext_payload, on_conflict="post_id", returning="representation")
            .execute()
        )
    except APIError as e:
        raise SupabasePersistError(e.message or str(e)) from e

    erows = er.data or []
    if not erows:
        raise SupabasePersistError("Supabase upsert returned no extraction row")
    ext_id = erows[0]["id"]
    if not ext_id:
        raise SupabasePersistError("Supabase extraction row missing id")

    return str(post_id), str(ext_id)
