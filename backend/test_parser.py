"""
Tests for backend/parser.py

Covers:
  - URL validation & platform detection
  - Shortcode extraction
  - HTML meta-tag parsing (mocked, no network)
  - oembed parsing (mocked)
  - Full scrape_instagram pipeline (mocked)
  - Batch parse_urls with invalid URLs skipped
  - to_normalized() output shape
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from parser import (
    detect_platform,
    validate_url,
    extract_shortcode,
    _fetch_rapidapi,
    _fetch_html_meta,
    _fetch_oembed,
    _build_raw_text,
    scrape_instagram,
    scrape_tiktok,
    parse_url,
    parse_urls,
    parse_urls_to_normalized,
    ParsedPost,
)


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------

class TestDetectPlatform:
    def test_instagram_post(self):
        assert detect_platform("https://www.instagram.com/p/ABC123/") == "instagram"

    def test_instagram_reel(self):
        assert detect_platform("https://instagram.com/reel/XYZ789/") == "instagram"

    def test_instagram_reels(self):
        assert detect_platform("https://www.instagram.com/reels/DEF456/") == "instagram"

    def test_instagram_tv(self):
        assert detect_platform("https://www.instagram.com/tv/GHI012/") == "instagram"

    def test_tiktok_video(self):
        url = "https://www.tiktok.com/@user/video/1234567890"
        assert detect_platform(url) == "tiktok"

    def test_tiktok_vm(self):
        assert detect_platform("https://vm.tiktok.com/ZMx1234/") == "tiktok"

    def test_unknown_url(self):
        assert detect_platform("https://youtube.com/watch?v=abc") is None

    def test_plain_text(self):
        assert detect_platform("not a url at all") is None


class TestValidateUrl:
    def test_valid_instagram(self):
        url = "https://www.instagram.com/p/ABC123/"
        assert validate_url(url) == url

    def test_strips_whitespace(self):
        url = "  https://www.instagram.com/p/ABC123/  "
        assert validate_url(url) == url.strip()

    def test_rejects_bad_scheme(self):
        with pytest.raises(ValueError, match="Invalid URL scheme"):
            validate_url("ftp://instagram.com/p/ABC123/")

    def test_rejects_non_social_url(self):
        with pytest.raises(ValueError, match="does not look like"):
            validate_url("https://google.com/search?q=travel")


class TestExtractShortcode:
    def test_post_shortcode(self):
        assert extract_shortcode("https://www.instagram.com/p/CxYz123_Ab/") == "CxYz123_Ab"

    def test_reel_shortcode(self):
        assert extract_shortcode("https://instagram.com/reel/DAx-99/") == "DAx-99"

    def test_no_match(self):
        assert extract_shortcode("https://instagram.com/explore/") is None


# ---------------------------------------------------------------------------
# HTML meta scraping (mocked network)
# ---------------------------------------------------------------------------

SAMPLE_HTML = """
<html>
<head>
  <meta property="og:description" content="Best ramen in Shibuya 🍜 #tokyo #travel" />
  <meta property="og:title" content="@foodie_adventures on Instagram" />
  <meta property="og:image" content="https://img.example.com/thumb.jpg" />
  <script type="application/ld+json">
  {
    "author": {"name": "foodie_adventures"},
    "caption": "Best ramen in Shibuya"
  }
  </script>
</head>
<body></body>
</html>
"""

SAMPLE_HTML_MINIMAL = """
<html><head>
  <meta property="og:description" content="Just vibes" />
</head><body></body></html>
"""

SAMPLE_HTML_EMPTY = "<html><head></head><body></body></html>"


def _mock_response(text, status=200):
    resp = MagicMock()
    resp.text = text
    resp.status_code = status
    resp.raise_for_status = MagicMock()
    if status >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status}")
    return resp


class TestFetchHtmlMeta:
    @patch("parser.requests.get")
    def test_extracts_og_tags(self, mock_get):
        mock_get.return_value = _mock_response(SAMPLE_HTML)

        result = _fetch_html_meta("https://www.instagram.com/p/ABC123/")

        assert result["caption"] == "Best ramen in Shibuya 🍜 #tokyo #travel"
        assert result["creator"] == "@foodie_adventures"
        assert result["thumbnail_url"] == "https://img.example.com/thumb.jpg"

    @patch("parser.requests.get")
    def test_minimal_html(self, mock_get):
        mock_get.return_value = _mock_response(SAMPLE_HTML_MINIMAL)

        result = _fetch_html_meta("https://www.instagram.com/p/ABC123/")

        assert result["caption"] == "Just vibes"
        assert result["creator"] == ""
        assert result["thumbnail_url"] == ""

    @patch("parser.requests.get")
    def test_empty_html_returns_defaults(self, mock_get):
        mock_get.return_value = _mock_response(SAMPLE_HTML_EMPTY)

        result = _fetch_html_meta("https://www.instagram.com/p/ABC123/")

        assert result["caption"] == ""
        assert result["creator"] == ""
        assert result["thumbnail_url"] == ""

    @patch("parser.requests.get")
    def test_network_failure_returns_defaults(self, mock_get):
        mock_get.return_value = _mock_response("", status=500)

        result = _fetch_html_meta("https://www.instagram.com/p/ABC123/")

        assert result == {"caption": "", "thumbnail_url": "", "creator": ""}


# ---------------------------------------------------------------------------
# oembed (mocked)
# ---------------------------------------------------------------------------

class TestFetchOembed:
    @patch("parser.requests.get")
    def test_successful_oembed(self, mock_get):
        oembed_data = {
            "title": "Amazing sunset at Santorini",
            "author_name": "travel_gram",
            "thumbnail_url": "https://img.example.com/oembed.jpg",
        }
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = oembed_data
        mock_get.return_value = resp

        result = _fetch_oembed("https://www.instagram.com/p/ABC123/")

        assert result["title"] == "Amazing sunset at Santorini"
        assert result["author_name"] == "travel_gram"

    @patch("parser.requests.get")
    def test_oembed_failure_returns_empty(self, mock_get):
        mock_get.side_effect = Exception("timeout")

        result = _fetch_oembed("https://www.instagram.com/p/ABC123/")

        assert result == {}


# ---------------------------------------------------------------------------
# RapidAPI (mocked)
# ---------------------------------------------------------------------------

RAPIDAPI_RESPONSE_FULL = {
    "data": {
        "items": [{
            "caption": {"text": "Best hidden café in Kyoto #japan #travel"},
            "user": {"username": "kyoto_foodie", "full_name": "Kyoto Foodie"},
            "thumbnail_url": "https://img.example.com/rapid_thumb.jpg",
        }]
    }
}

RAPIDAPI_RESPONSE_STRING_CAPTION = {
    "data": {
        "items": [{
            "caption": "Street food in Bangkok",
            "user": {"username": "bkk_eats"},
            "display_url": "https://img.example.com/bkk.jpg",
        }]
    }
}

RAPIDAPI_RESPONSE_NO_CAPTION = {
    "data": {
        "items": [{
            "user": {"username": "silent_poster"},
        }]
    }
}

RAPIDAPI_RESPONSE_EMPTY_ITEMS = {
    "data": {
        "items": []
    }
}


class TestFetchRapidapi:
    @patch("parser.RAPIDAPI_KEY", "test-key")
    @patch("parser.requests.get")
    def test_extracts_caption_from_dict(self, mock_get):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = RAPIDAPI_RESPONSE_FULL
        mock_get.return_value = resp

        result = _fetch_rapidapi("ABC123")

        assert result["caption"] == "Best hidden café in Kyoto #japan #travel"
        assert result["creator"] == "kyoto_foodie"
        assert result["thumbnail_url"] == "https://img.example.com/rapid_thumb.jpg"

    @patch("parser.RAPIDAPI_KEY", "test-key")
    @patch("parser.requests.get")
    def test_extracts_string_caption(self, mock_get):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = RAPIDAPI_RESPONSE_STRING_CAPTION
        mock_get.return_value = resp

        result = _fetch_rapidapi("DEF456")

        assert result["caption"] == "Street food in Bangkok"
        assert result["creator"] == "bkk_eats"
        assert result["thumbnail_url"] == "https://img.example.com/bkk.jpg"

    @patch("parser.RAPIDAPI_KEY", "test-key")
    @patch("parser.requests.get")
    def test_handles_missing_caption(self, mock_get):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = RAPIDAPI_RESPONSE_NO_CAPTION
        mock_get.return_value = resp

        result = _fetch_rapidapi("GHI789")

        assert result["caption"] == ""
        assert result["creator"] == "silent_poster"

    @patch("parser.RAPIDAPI_KEY", "test-key")
    @patch("parser.requests.get")
    def test_empty_items_returns_empty(self, mock_get):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = RAPIDAPI_RESPONSE_EMPTY_ITEMS
        mock_get.return_value = resp

        result = _fetch_rapidapi("EMPTY1")

        assert result == {}

    @patch("parser.RAPIDAPI_KEY", "test-key")
    @patch("parser.requests.get")
    def test_network_failure_returns_empty(self, mock_get):
        mock_get.side_effect = Exception("connection refused")

        result = _fetch_rapidapi("FAIL00")

        assert result == {}

    @patch("parser.RAPIDAPI_KEY", "test-key")
    @patch("parser.requests.get")
    def test_http_error_returns_empty(self, mock_get):
        resp = MagicMock()
        resp.raise_for_status.side_effect = Exception("HTTP 403")
        mock_get.return_value = resp

        result = _fetch_rapidapi("FORBID")

        assert result == {}

    def test_no_api_key_returns_empty(self):
        with patch("parser.RAPIDAPI_KEY", ""):
            result = _fetch_rapidapi("ANY123")
            assert result == {}


# ---------------------------------------------------------------------------
# Full scrape pipeline (mocked)
# ---------------------------------------------------------------------------

class TestScrapeInstagram:
    @patch("parser._fetch_html_meta")
    @patch("parser._fetch_oembed")
    @patch("parser._fetch_rapidapi")
    def test_rapidapi_first_priority(self, mock_rapid, mock_oembed, mock_html):
        mock_rapid.return_value = {
            "caption": "RapidAPI caption wins",
            "creator": "rapid_user",
            "thumbnail_url": "https://img.example.com/rapid.jpg",
        }

        post = scrape_instagram("https://www.instagram.com/p/RAP123/")

        assert post.caption == "RapidAPI caption wins"
        assert post.creator == "rapid_user"
        assert post.thumbnail_url == "https://img.example.com/rapid.jpg"
        mock_oembed.assert_not_called()
        mock_html.assert_not_called()

    @patch("parser._fetch_html_meta")
    @patch("parser._fetch_oembed")
    @patch("parser._fetch_rapidapi")
    def test_falls_back_to_oembed_when_rapidapi_empty(self, mock_rapid, mock_oembed, mock_html):
        mock_rapid.return_value = {}
        mock_oembed.return_value = {
            "title": "Tokyo street food tour",
            "author_name": "nomad_eats",
            "thumbnail_url": "https://img.example.com/oembed.jpg",
        }

        post = scrape_instagram("https://www.instagram.com/p/XYZ789/")

        assert post.platform == "instagram"
        assert post.post_id == "XYZ789"
        assert post.caption == "Tokyo street food tour"
        assert post.creator == "nomad_eats"
        assert post.thumbnail_url == "https://img.example.com/oembed.jpg"
        assert "Tokyo street food tour" in post.raw_text
        mock_html.assert_not_called()

    @patch("parser._fetch_html_meta")
    @patch("parser._fetch_oembed")
    @patch("parser._fetch_rapidapi")
    def test_falls_back_to_html_when_both_empty(self, mock_rapid, mock_oembed, mock_html):
        mock_rapid.return_value = {}
        mock_oembed.return_value = {}
        mock_html.return_value = {
            "caption": "Fallback caption from HTML",
            "creator": "@html_creator",
            "thumbnail_url": "https://img.example.com/html.jpg",
        }

        post = scrape_instagram("https://www.instagram.com/p/FALL123/")

        assert post.caption == "Fallback caption from HTML"
        assert post.creator == "@html_creator"
        assert post.thumbnail_url == "https://img.example.com/html.jpg"

    @patch("parser._fetch_html_meta")
    @patch("parser._fetch_oembed")
    @patch("parser._fetch_rapidapi")
    def test_empty_scrape_still_returns_skeleton(self, mock_rapid, mock_oembed, mock_html):
        mock_rapid.return_value = {}
        mock_oembed.return_value = {}
        mock_html.return_value = {"caption": "", "creator": "", "thumbnail_url": ""}

        post = scrape_instagram("https://www.instagram.com/p/EMPTY00/")

        assert post.platform == "instagram"
        assert post.post_id == "EMPTY00"
        assert post.caption == ""
        assert post.raw_text == ""

    @patch("parser._fetch_html_meta")
    @patch("parser._fetch_oembed")
    @patch("parser._fetch_rapidapi")
    def test_rapidapi_no_caption_falls_through(self, mock_rapid, mock_oembed, mock_html):
        """RapidAPI returns creator but no caption — should fall to oembed."""
        mock_rapid.return_value = {
            "caption": "",
            "creator": "rapid_user",
            "thumbnail_url": "",
        }
        mock_oembed.return_value = {
            "title": "Oembed fills the gap",
            "author_name": "oembed_user",
            "thumbnail_url": "https://img.example.com/oembed.jpg",
        }

        post = scrape_instagram("https://www.instagram.com/p/PARTIAL/")

        assert post.caption == "Oembed fills the gap"
        assert post.creator == "rapid_user"  # kept from RapidAPI
        mock_html.assert_not_called()


class TestScrapeTiktok:
    @patch("parser._fetch_html_meta")
    def test_tiktok_scrape(self, mock_html):
        mock_html.return_value = {
            "caption": "Hidden gems in Bali #travel",
            "creator": "@bali_vibes",
            "thumbnail_url": "https://img.example.com/tt.jpg",
        }

        post = scrape_tiktok("https://www.tiktok.com/@bali_vibes/video/999")

        assert post.platform == "tiktok"
        assert post.caption == "Hidden gems in Bali #travel"
        assert post.creator == "@bali_vibes"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class TestParseUrl:
    @patch("parser.scrape_instagram")
    def test_dispatches_instagram(self, mock_scrape):
        mock_scrape.return_value = ParsedPost(
            url="https://www.instagram.com/p/TEST01/",
            platform="instagram",
            caption="test",
            raw_text="test",
        )

        post = parse_url("https://www.instagram.com/p/TEST01/")

        assert post.platform == "instagram"
        mock_scrape.assert_called_once()

    @patch("parser.scrape_tiktok")
    def test_dispatches_tiktok(self, mock_scrape):
        mock_scrape.return_value = ParsedPost(
            url="https://www.tiktok.com/@u/video/123",
            platform="tiktok",
            caption="test",
            raw_text="test",
        )

        post = parse_url("https://www.tiktok.com/@u/video/123")

        assert post.platform == "tiktok"
        mock_scrape.assert_called_once()

    def test_rejects_invalid_url(self):
        with pytest.raises(ValueError):
            parse_url("https://youtube.com/watch?v=abc")


class TestParseUrls:
    @patch("parser.scrape_instagram")
    def test_skips_invalid_urls(self, mock_scrape):
        mock_scrape.return_value = ParsedPost(
            url="https://www.instagram.com/p/OK123/",
            platform="instagram",
            raw_text="ok",
        )

        results = parse_urls([
            "https://www.instagram.com/p/OK123/",
            "https://badurl.com/nope",
            "not even a url",
        ])

        assert len(results) == 1
        assert results[0].platform == "instagram"

    @patch("parser.scrape_instagram")
    def test_handles_empty_list(self, mock_scrape):
        assert parse_urls([]) == []


# ---------------------------------------------------------------------------
# Normalized output shape
# ---------------------------------------------------------------------------

class TestToNormalized:
    def test_output_keys(self):
        post = ParsedPost(
            url="https://www.instagram.com/p/ABC/",
            platform="instagram",
            caption="hello",
            raw_text="hello",
            post_id="ABC",
        )

        norm = post.to_normalized()

        assert set(norm.keys()) == {
            "post_id", "url", "platform", "caption",
            "transcript", "ocr_text", "thumbnail_text", "raw_text",
        }
        assert norm["post_id"] == "ABC"
        assert norm["platform"] == "instagram"
        assert norm["caption"] == "hello"
        assert norm["raw_text"] == "hello"


class TestParseUrlsToNormalized:
    @patch("parser.scrape_instagram")
    def test_returns_list_of_dicts(self, mock_scrape):
        mock_scrape.return_value = ParsedPost(
            url="https://www.instagram.com/p/N1/",
            platform="instagram",
            caption="normalized test",
            raw_text="normalized test",
            post_id="N1",
        )

        results = parse_urls_to_normalized([
            "https://www.instagram.com/p/N1/",
        ])

        assert len(results) == 1
        assert isinstance(results[0], dict)
        assert results[0]["post_id"] == "N1"
        assert results[0]["platform"] == "instagram"


# ---------------------------------------------------------------------------
# _build_raw_text
# ---------------------------------------------------------------------------

class TestBuildRawText:
    def test_combines_fields(self):
        post = ParsedPost(
            url="x", platform="instagram",
            caption="line1", transcript="line2",
            ocr_text="line3", detected_text="line4",
        )
        assert _build_raw_text(post) == "line1\nline2\nline3\nline4"

    def test_skips_empty_fields(self):
        post = ParsedPost(
            url="x", platform="instagram",
            caption="only caption",
        )
        assert _build_raw_text(post) == "only caption"

    def test_all_empty(self):
        post = ParsedPost(url="x", platform="instagram")
        assert _build_raw_text(post) == ""


# ---------------------------------------------------------------------------
# Live integration test (hits the real network — run explicitly with -k live)
# ---------------------------------------------------------------------------

LIVE_INSTAGRAM_URL = (
    "https://www.instagram.com/reel/DVqnjpBDxZp/"
    "?utm_source=ig_web_copy_link&igsh=MzRlODBiNWFlZA=="
)


class TestLiveInstagram:
    """
    These tests make real HTTP requests to Instagram.
    Run them explicitly:  python3 -m pytest test_parser.py -v -k live
    """

    def test_live_detect_platform(self):
        assert detect_platform(LIVE_INSTAGRAM_URL) == "instagram"

    def test_live_validate_url(self):
        cleaned = validate_url(LIVE_INSTAGRAM_URL)
        assert "instagram.com" in cleaned

    def test_live_extract_shortcode(self):
        code = extract_shortcode(LIVE_INSTAGRAM_URL)
        assert code == "DVqnjpBDxZp"

    def test_live_scrape(self):
        post = scrape_instagram(LIVE_INSTAGRAM_URL)

        print(f"\n{'='*60}")
        print(f"  POST ID:       {post.post_id}")
        print(f"  URL:           {post.url}")
        print(f"  PLATFORM:      {post.platform}")
        print(f"  CREATOR:       {post.creator}")
        print(f"  CAPTION:       {post.caption[:200]}{'...' if len(post.caption) > 200 else ''}")
        print(f"  THUMBNAIL:     {post.thumbnail_url[:100] if post.thumbnail_url else '(none)'}")
        print(f"  RAW TEXT:      {post.raw_text[:200]}{'...' if len(post.raw_text) > 200 else ''}")
        print(f"{'='*60}\n")

        assert post.platform == "instagram"
        assert post.post_id == "DVqnjpBDxZp"
        assert isinstance(post.caption, str)
        assert isinstance(post.raw_text, str)

    def test_live_to_normalized(self):
        post = scrape_instagram(LIVE_INSTAGRAM_URL)
        norm = post.to_normalized()

        assert norm["post_id"] == "DVqnjpBDxZp"
        assert norm["platform"] == "instagram"
        assert "url" in norm
        assert "raw_text" in norm

    def test_live_parse_url(self):
        post = parse_url(LIVE_INSTAGRAM_URL)
        assert post.platform == "instagram"
        assert post.post_id == "DVqnjpBDxZp"
