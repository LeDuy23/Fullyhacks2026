"""Public TikTok metadata via official oEmbed (no TikTok login; no video bytes)."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


def fetch_tiktok_oembed_data(url: str) -> dict[str, Any]:
    """
    https://developers.tiktok.com/doc/embed-videos/
    Returns title, author_name, thumbnail_url, html embed snippet, etc.
    """
    u = (url or "").strip()
    if not u or "tiktok.com" not in u.lower():
        raise ValueError("Expected a tiktok.com (or vm.tiktok.com) video URL")
    q = urllib.parse.urlencode({"url": u})
    api = f"https://www.tiktok.com/oembed?{q}"
    req = urllib.request.Request(
        api,
        headers={"User-Agent": "DeepDiveTravelBot/1.0 (+travel-planner)"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=18) as resp:
            if resp.getcode() != 200:
                raise RuntimeError(f"TikTok oEmbed HTTP {resp.getcode()}")
            raw = resp.read().decode("utf-8", errors="replace")
            data = json.loads(raw)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"TikTok oEmbed failed: {e.code}") from e
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
        raise RuntimeError(f"TikTok oEmbed error: {e}") from e
    if not isinstance(data, dict):
        raise RuntimeError("TikTok oEmbed returned non-object JSON")
    return data
