"""Unit tests for Instagram / TikTok URL detection and post enrichment (no network)."""

import pytest

from app.models.extraction import NormalizedPost
from app.services.social_link import (
    detect_platform,
    enrich_normalized_post,
    first_url_in_text,
)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("check https://www.instagram.com/reel/AbCdEfGhIj/ cool", "https://www.instagram.com/reel/AbCdEfGhIj/"),
        (
            "https://www.instagram.com/reel/DIuiMVhTQlt/?igsh=NTc4MTIwNjQ2YQ==",
            "https://www.instagram.com/reel/DIuiMVhTQlt/?igsh=NTc4MTIwNjQ2YQ==",
        ),
        (
            "see https://www.instagram.com/reel/DIuiMVhTQlt/?igsh=NTc4MTIwNjQ2YQ== ok",
            "https://www.instagram.com/reel/DIuiMVhTQlt/?igsh=NTc4MTIwNjQ2YQ==",
        ),
        ("https://vm.tiktok.com/ZMxxxxxxx/", "https://vm.tiktok.com/ZMxxxxxxx/"),
        ("no link here", ""),
    ],
)
def test_first_url_in_text(text, expected):
    assert first_url_in_text(text) == expected


@pytest.mark.parametrize(
    "url,plat",
    [
        ("https://www.instagram.com/reel/ABC123/", "instagram"),
        ("https://instagram.com/p/xyz/", "instagram"),
        ("https://www.tiktok.com/@user/video/1234567890", "tiktok"),
        ("https://vm.tiktok.com/ZMfoo/", "tiktok"),
        ("https://example.com/page", "other"),
    ],
)
def test_detect_platform(url, plat):
    assert detect_platform(url) == plat


def test_enrich_tiktok_merges_oembed(monkeypatch):
    from app.services import social_link

    def fake_tt(u):
        return {"title": "Best ramen in Osaka", "author_name": "tokyo_eats"}

    monkeypatch.setattr(social_link, "fetch_tiktok_oembed", fake_tt)
    monkeypatch.setattr(social_link, "fetch_instagram_oembed", lambda u: None)

    post = NormalizedPost(
        post_id="t1",
        url="https://deepdive.app/import",
        platform="other",
        caption="",
        transcript="",
        ocr_text="",
        thumbnail_text="",
        raw_text="https://www.tiktok.com/@tokyo_eats/video/1",
    )
    out = enrich_normalized_post(post)
    assert out.platform == "tiktok"
    assert "tokyo_eats" in out.raw_text or "Osaka" in out.raw_text
    assert "tiktok.com" in out.url


def test_enrich_instagram_no_oembed_adds_hint_for_short_paste(monkeypatch):
    from app.services import social_link

    monkeypatch.setattr(social_link, "fetch_instagram_caption_rapidapi", lambda u: None)
    monkeypatch.setattr(social_link, "fetch_instagram_oembed", lambda u: None)

    post = NormalizedPost(
        post_id="i1",
        url="https://deepdive.app/import",
        platform="other",
        caption="",
        transcript="",
        ocr_text="",
        thumbnail_text="",
        raw_text="https://www.instagram.com/reel/ABC123/",
    )
    out = enrich_normalized_post(post)
    assert out.platform == "instagram"
    assert "Could not load caption" in out.raw_text or "RapidAPI" in out.raw_text
