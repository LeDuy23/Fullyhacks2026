"""Resolve Google Maps share URLs to a text query for Places / geocoding."""

from __future__ import annotations

import re
from typing import Optional
from urllib.parse import unquote, urlparse

_MAPS_HOST = re.compile(r"(^|\.)google\.|maps\.app\.goo\.gl|goo\.gl/maps", re.I)


def is_google_maps_url(url: str) -> bool:
    u = (url or "").strip().lower()
    if not u:
        return False
    return bool(_MAPS_HOST.search(u)) or ("maps.google.com" in u or "google.com/maps" in u)


def maps_url_to_query_text(url: str) -> Optional[str]:
    cands = maps_url_query_candidates(url)
    return cands[0] if cands else None


def maps_url_query_candidates(url: str) -> list[str]:
    if not url or not is_google_maps_url(url):
        return []
    out: list[str] = []
    try:
        p = urlparse(url.strip())
        q = unquote(p.query or "")
        m = re.search(r"/place/([^/@?]+)", p.path or "", re.I)
        if m:
            val = m.group(1).replace("+", " ").strip()
            if val:
                out.append(val)
        for part in q.split("&"):
            if part.startswith("q="):
                val = unquote(part[2:]).strip()
                if val:
                    out.append(val)
            if part.startswith("query="):
                val = unquote(part[6:]).strip()
                if val:
                    out.append(val)
        latlng = re.search(r"/@(-?\d+\.\d+),(-?\d+\.\d+)", p.path or "")
        if latlng:
            out.append(f"{latlng.group(1)},{latlng.group(2)}")
        frag = unquote(p.fragment or "")
        if frag and len(frag) < 200:
            out.append(frag.strip())
    except Exception:
        pass
    seen: set[str] = set()
    uniq: list[str] = []
    for s in out:
        k = s.strip().lower()
        if not k or k in seen:
            continue
        seen.add(k)
        uniq.append(s.strip())
    return uniq
