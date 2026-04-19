"""
Detect Instagram / TikTok URLs in pasted text and enrich posts for extraction.

- Platform + canonical URL are inferred from the link (reels, /p/, TikTok video URLs, short links).
- TikTok: public oEmbed often returns title + author (no API key).
- Instagram: legacy oEmbed may work for some public posts; Meta often blocks server-side
  fetches without an app token — we still tag the platform and may append a short hint.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Literal, Optional

from app.models.extraction import NormalizedPost

# Query strings may include "=" (e.g. ?igsh=…==); strip bidi/format chars apps append after copy.
_BIDI_OR_ZW = re.compile(r"[\u200b-\u200f\u202a-\u202e\ufeff]+")


def _normalize_pasted_url_text(text: str) -> str:
    t = (text or "").replace("\ufeff", "")
    t = _BIDI_OR_ZW.sub("", t)
    return " ".join(t.split())


_URL_RE = re.compile(r"https?://[^\s<>\"']+", re.I)

# Instagram: /reel/, /reels/, /p/, /tv/
# TikTok: www.tiktok.com, vm.tiktok.com, vt.tiktok.com, tiktok.com/t/
_PLATFORMS: tuple[tuple[re.Pattern[str], Literal["instagram", "tiktok"]], ...] = (
    (re.compile(r"https?://(?:www\.)?(?:vm\.|vt\.)?tiktok\.com/", re.I), "tiktok"),
    (re.compile(r"https?://(?:www\.)?tiktok\.com/@[^/\s]+/video/\d+", re.I), "tiktok"),
    (re.compile(r"https?://(?:www\.)?tiktok\.com/t/\S+", re.I), "tiktok"),
    (re.compile(r"https?://(?:www\.)?instagram\.com/(?:reel|reels|p|tv)/", re.I), "instagram"),
    (re.compile(r"https?://(?:www\.)?instagr\.am/(?:reel|reels|p|tv)/", re.I), "instagram"),
)


def first_url_in_text(text: str) -> str:
    t = _normalize_pasted_url_text(text)
    if not t:
        return ""
    # Prefer full https URL up to first whitespace (keeps ?igsh=…== intact).
    start = re.search(r"\bhttps?://", t, re.I)
    if start:
        rest = t[start.start() :]
        end = re.search(r"\s", rest)
        chunk = rest if not end else rest[: end.start()]
        chunk = chunk.rstrip(".,);]'\"").strip()
        if re.match(r"https?://", chunk, re.I):
            return chunk
    m = _URL_RE.search(t)
    if not m:
        return ""
    return m.group(0).rstrip(".,);]'\"")


def detect_platform(url: str) -> Literal["tiktok", "instagram", "other"]:
    if not url:
        return "other"
    for pattern, plat in _PLATFORMS:
        if pattern.search(url):
            return plat
    u = url.lower()
    if "tiktok.com" in u or "vm.tiktok.com" in u or "vt.tiktok.com" in u:
        return "tiktok"
    if "instagram.com" in u or "instagr.am" in u:
        return "instagram"
    return "other"


def _http_get_json(url: str, *, timeout: float = 12.0) -> Optional[dict]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "DeepDiveTravelBot/1.0 (+https://github.com)"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.getcode() != 200:
                return None
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, OSError):
        return None


def fetch_tiktok_oembed(page_url: str) -> Optional[dict]:
    q = urllib.parse.urlencode({"url": page_url})
    return _http_get_json(f"https://www.tiktok.com/oembed?{q}")


def fetch_instagram_oembed(page_url: str) -> Optional[dict]:
    """May return None when Meta blocks anonymous oEmbed (common for reels)."""
    q = urllib.parse.urlencode({"url": page_url})
    return _http_get_json(f"https://api.instagram.com/oembed/?{q}")


def _rapidapi_host_header() -> str:
    h = (os.environ.get("RAPIDAPI_HOST") or "").strip()
    if not h:
        return ""
    h = h.replace("https://", "").replace("http://", "")
    return h.split("/")[0].strip()


def _dig_caption_text(obj: object, depth: int = 0) -> str:
    """Find a usable caption/title string in nested RapidAPI JSON."""
    if depth > 16:
        return ""
    if isinstance(obj, dict):
        for k, v in obj.items():
            lk = str(k).lower()
            if any(x in lk for x in ("caption", "title", "description", "text")) and isinstance(v, str):
                t = v.strip()
                if len(t) > 5:
                    return t
        for v in obj.values():
            got = _dig_caption_text(v, depth + 1)
            if got:
                return got
    elif isinstance(obj, list):
        for it in obj:
            got = _dig_caption_text(it, depth + 1)
            if got:
                return got
    return ""


def fetch_instagram_caption_rapidapi(page_url: str) -> Optional[str]:
    """
    Optional RapidAPI Instagram scraper (see RAPIDAPI_KEY / RAPIDAPI_HOST in `.env`).
    Tries POST paths in order; set RAPIDAPI_IG_PATH to your provider's route if needed.
    """
    key = (os.environ.get("RAPIDAPI_KEY") or "").strip()
    host = _rapidapi_host_header()
    if not key or not host:
        return None
    custom = (os.environ.get("RAPIDAPI_IG_PATH") or "").strip()
    paths = ([custom] if custom else []) + [
        "v1/media/info",
        "media/info",
        "get_media_info",
    ]
    for path in paths:
        api_url = f"https://{host}/{path.lstrip('/')}"
        payload = json.dumps({"url": page_url, "link": page_url}).encode("utf-8")
        req = urllib.request.Request(
            api_url,
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-RapidAPI-Key": key,
                "X-RapidAPI-Host": host,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                if resp.getcode() != 200:
                    continue
                raw = resp.read().decode("utf-8", errors="replace")
                data = json.loads(raw)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
            continue
        cap = _dig_caption_text(data)
        if cap and len(cap) > 10:
            return cap[:8000]
    return None


def _oembed_caption_line(platform: str, meta: dict) -> str:
    title = (meta.get("title") or "").strip()
    author = (meta.get("author_name") or "").strip()
    if author and title:
        return f"[{platform} oEmbed] {author}: {title}"
    if title:
        return f"[{platform} oEmbed] {title}"
    if author:
        return f"[{platform} oEmbed] {author}"
    return ""


def enrich_normalized_post(post: NormalizedPost) -> NormalizedPost:
    """
    Fill url/platform from pasted links; append oEmbed text when available so the LLM
    can extract travel signals without scraping the social app.
    """
    if post.image_base64 and str(post.image_base64).strip():
        return post

    text = (post.raw_text or "").strip()
    url = (post.url or "").strip()

    if (not url or url == "https://deepdive.app/import") and text:
        url = first_url_in_text(text)

    if not url:
        return post

    platform = detect_platform(url)
    additions: list[str] = []

    if platform == "tiktok":
        meta = fetch_tiktok_oembed(url)
        if meta:
            line = _oembed_caption_line("TikTok", meta)
            if line:
                additions.append(line)
    elif platform == "instagram":
        rapid_caption = fetch_instagram_caption_rapidapi(url)
        if rapid_caption:
            additions.append(f"[Instagram import]\n{rapid_caption}")
        else:
            meta = fetch_instagram_oembed(url)
            if meta:
                line = _oembed_caption_line("Instagram", meta)
                if line:
                    additions.append(line)
            else:
                # Likely reel / login wall — nudge user only when paste looks URL-only.
                short = len(text) < 400 and (not text or first_url_in_text(text) == text.strip())
                if short:
                    additions.append(
                        "[Instagram] Could not load caption via oEmbed or RapidAPI. "
                        "Paste the caption or location notes above/below the link for best results."
                    )

    new_raw = text
    for line in additions:
        if line and line not in new_raw:
            new_raw = f"{new_raw}\n{line}" if new_raw else line

    return post.model_copy(
        update={
            "url": url,
            "platform": platform,
            "raw_text": new_raw,
        }
    )
