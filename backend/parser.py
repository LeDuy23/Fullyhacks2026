"""
Instagram post parser.

Accepts Instagram post/reel URLs, scrapes the page for captions and metadata,
and returns NormalizedPost-compatible dicts ready for the AI extraction pipeline.

Scraping strategy (in priority order):
1. RapidAPI Real-Time Instagram Scraper (best data, requires subscription).
2. Fetch the public oembed endpoint (no auth needed, gives title/author).
3. Fetch the HTML page and pull JSON-LD or <meta> og:description tags for
   the caption, thumbnail, and creator name.
4. Fall back gracefully — if nothing is parseable, return a skeleton with
   the URL so downstream extraction can still flag it as low-confidence.
"""

import os
import re
import json
import uuid
import logging
from typing import Optional
from urllib.parse import urlparse
from dataclasses import dataclass, field, asdict

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_INSTAGRAM_URL_RE = re.compile(
    r"https?://(?:www\.)?instagram\.com/"
    r"(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)"
)

_TIKTOK_URL_RE = re.compile(
    r"https?://(?:www\.|vm\.)?tiktok\.com/"
    r"(?:@[\w.]+/video/(\d+)|(\w+))"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

OEMBED_URL = "https://api.instagram.com/oembed"
REQUEST_TIMEOUT = 15

RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "")
RAPIDAPI_HOST = os.environ.get("RAPIDAPI_HOST", "real-time-instagram-scraper-api1.p.rapidapi.com")
RAPIDAPI_MEDIA_URL = f"https://{RAPIDAPI_HOST}/v1/media_info"


# ---- Data classes -----------------------------------------------------------

@dataclass
class ParsedPost:
    url: str
    platform: str
    caption: str = ""
    transcript: str = ""
    ocr_text: str = ""
    thumbnail_url: str = ""
    creator: str = ""
    detected_text: str = ""
    raw_text: str = ""
    post_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_normalized(self) -> dict:
        """Return a dict matching the NormalizedPost schema."""
        return {
            "post_id": self.post_id,
            "url": self.url,
            "platform": self.platform,
            "caption": self.caption,
            "transcript": self.transcript,
            "ocr_text": self.ocr_text,
            "thumbnail_text": self.detected_text,
            "raw_text": self.raw_text,
        }


# ---- URL helpers ------------------------------------------------------------

def detect_platform(url: str) -> Optional[str]:
    if _INSTAGRAM_URL_RE.search(url):
        return "instagram"
    if _TIKTOK_URL_RE.search(url):
        return "tiktok"
    return None


def validate_url(url: str) -> str:
    """Normalise and validate the URL. Returns cleaned URL or raises."""
    url = url.strip()
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Invalid URL scheme: {url}")
    platform = detect_platform(url)
    if platform is None:
        raise ValueError(
            f"URL does not look like an Instagram or TikTok post: {url}"
        )
    return url


def extract_shortcode(url: str) -> Optional[str]:
    m = _INSTAGRAM_URL_RE.search(url)
    return m.group(1) if m else None


# ---- Instagram scraping -----------------------------------------------------

def _fetch_rapidapi(shortcode: str) -> dict:
    """
    Hit the RapidAPI Real-Time Instagram Scraper /v1/media_info endpoint.

    Response shape:
        { "data": { "items": [ { "caption": { "text": "..." }, "user": { ... }, ... } ] } }

    Returns a dict with caption / creator / thumbnail_url keys,
    or an empty dict on any failure (missing key, network error, etc.).
    """
    if not RAPIDAPI_KEY:
        return {}

    try:
        resp = requests.get(
            RAPIDAPI_MEDIA_URL,
            params={"code_or_id_or_url": shortcode},
            headers={
                "x-rapidapi-key": RAPIDAPI_KEY,
                "x-rapidapi-host": RAPIDAPI_HOST,
            },
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.debug("RapidAPI failed for %s: %s", shortcode, exc)
        return {}

    items = data.get("data", {}).get("items")
    if not items:
        return {}
    item = items[0]

    result: dict = {}

    caption_obj = item.get("caption")
    if isinstance(caption_obj, dict):
        result["caption"] = caption_obj.get("text", "")
    elif isinstance(caption_obj, str):
        result["caption"] = caption_obj
    else:
        result["caption"] = ""

    user = item.get("user") or item.get("owner") or {}
    if isinstance(user, dict):
        result["creator"] = user.get("username", "") or user.get("full_name", "")
    else:
        result["creator"] = ""

    result["thumbnail_url"] = (
        item.get("thumbnail_url")
        or item.get("display_url")
        or item.get("image_versions2", {}).get("candidates", [{}])[0].get("url", "")
    )

    return result


def _fetch_oembed(url: str) -> dict:
    """Use Instagram's public oembed endpoint (no API key required)."""
    try:
        resp = requests.get(
            OEMBED_URL,
            params={"url": url, "omitscript": "true"},
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.debug("oembed failed for %s: %s", url, exc)
        return {}


def _fetch_html_meta(url: str) -> dict:
    """Scrape the HTML page for og: meta tags and JSON-LD."""
    result: dict = {
        "caption": "",
        "thumbnail_url": "",
        "creator": "",
    }
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except Exception as exc:
        logger.debug("HTML fetch failed for %s: %s", url, exc)
        return result

    soup = BeautifulSoup(resp.text, "html.parser")

    og_desc = soup.find("meta", attrs={"property": "og:description"})
    if og_desc and og_desc.get("content"):
        result["caption"] = og_desc["content"]

    og_title = soup.find("meta", attrs={"property": "og:title"})
    if og_title and og_title.get("content"):
        title = og_title["content"]
        if not result["caption"]:
            result["caption"] = title
        creator_match = re.search(r"@([\w.]+)", title)
        if creator_match:
            result["creator"] = creator_match.group(0)

    og_image = soup.find("meta", attrs={"property": "og:image"})
    if og_image and og_image.get("content"):
        result["thumbnail_url"] = og_image["content"]

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            ld = json.loads(script.string or "")
            if isinstance(ld, dict):
                result["caption"] = result["caption"] or ld.get("caption", "")
                result["caption"] = result["caption"] or ld.get("articleBody", "")
                author = ld.get("author", {})
                if isinstance(author, dict):
                    result["creator"] = result["creator"] or author.get("name", "")
        except (json.JSONDecodeError, TypeError):
            continue

    return result


def scrape_instagram(url: str) -> ParsedPost:
    """
    Scrape a single Instagram post URL and return a ParsedPost.

    Priority: RapidAPI -> oembed -> HTML meta -> empty skeleton.
    """
    post = ParsedPost(url=url, platform="instagram")
    shortcode = extract_shortcode(url)
    post.post_id = shortcode or post.post_id

    if shortcode:
        rapid = _fetch_rapidapi(shortcode)
        if rapid:
            post.caption = rapid.get("caption", "")
            post.creator = rapid.get("creator", "")
            post.thumbnail_url = rapid.get("thumbnail_url", "")

    if not post.caption:
        oembed = _fetch_oembed(url)
        if oembed:
            post.caption = post.caption or oembed.get("title", "")
            post.creator = post.creator or oembed.get("author_name", "")
            post.thumbnail_url = post.thumbnail_url or oembed.get("thumbnail_url", "")

    if not post.caption:
        meta = _fetch_html_meta(url)
        post.caption = post.caption or meta.get("caption", "")
        post.creator = post.creator or meta.get("creator", "")
        post.thumbnail_url = post.thumbnail_url or meta.get("thumbnail_url", "")

    post.raw_text = _build_raw_text(post)
    return post


# ---- TikTok scraping --------------------------------------------------------

def scrape_tiktok(url: str) -> ParsedPost:
    """Scrape a TikTok post URL via HTML meta tags."""
    post = ParsedPost(url=url, platform="tiktok")

    meta = _fetch_html_meta(url)
    post.caption = meta.get("caption", "")
    post.creator = meta.get("creator", "")
    post.thumbnail_url = meta.get("thumbnail_url", "")
    post.raw_text = _build_raw_text(post)
    return post


# ---- Shared helpers ---------------------------------------------------------

def _build_raw_text(post: ParsedPost) -> str:
    """Combine all text fields into a single blob for downstream AI."""
    parts = [
        post.caption,
        post.transcript,
        post.ocr_text,
        post.detected_text,
    ]
    return "\n".join(p for p in parts if p).strip()


# ---- Public API -------------------------------------------------------------

def parse_url(url: str) -> ParsedPost:
    """Parse a single URL (Instagram or TikTok) into a ParsedPost."""
    url = validate_url(url)
    platform = detect_platform(url)

    if platform == "instagram":
        return scrape_instagram(url)
    if platform == "tiktok":
        return scrape_tiktok(url)

    raise ValueError(f"Unsupported platform for URL: {url}")


def parse_urls(urls: list[str]) -> list[ParsedPost]:
    """Parse a batch of URLs. Invalid URLs are logged and skipped."""
    results: list[ParsedPost] = []
    for url in urls:
        try:
            results.append(parse_url(url))
        except ValueError as exc:
            logger.warning("Skipping invalid URL %s: %s", url, exc)
    return results


def parse_urls_to_normalized(urls: list[str]) -> list[dict]:
    """Parse URLs and return NormalizedPost-compatible dicts."""
    return [post.to_normalized() for post in parse_urls(urls)]
