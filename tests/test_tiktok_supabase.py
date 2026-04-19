"""Unit tests for TikTok → Supabase mapping (no DB or network)."""

from __future__ import annotations

from app.services.tiktok_gemini import TikTokTravelInsight
from app.services.tiktok_supabase import client_post_id_from_tiktok_url, tiktok_insight_to_extraction_row


def test_client_post_id_prefers_video_id() -> None:
    u = "https://www.tiktok.com/@travel/video/7123456789012345678"
    assert client_post_id_from_tiktok_url(u) == "7123456789012345678"


def test_client_post_id_hash_fallback() -> None:
    u = "https://vm.tiktok.com/ZMxyz/"
    cid = client_post_id_from_tiktok_url(u)
    assert cid.startswith("tt_")


def test_tiktok_insight_to_extraction_row_shape() -> None:
    ins = TikTokTravelInsight(
        summary="Nice beach",
        inferred_destinations=["Bali"],
        place_mentions=["Canggu"],
        activities=["surf"],
        vibe_tags=["chill"],
        limitations="meta only",
    )
    row = tiktok_insight_to_extraction_row(ins)
    assert row["is_travel_relevant"] is True
    assert row["budget_signal"] == "unknown"
    assert row["best_time_of_day"] == ["flexible"]
    assert len(row["destination_candidates"]) == 1
    assert row["destination_candidates"][0]["name"] == "Bali"
    assert len(row["place_candidates"]) == 1
    assert "Bali" in row["notes"] or "Nice beach" in row["notes"]
