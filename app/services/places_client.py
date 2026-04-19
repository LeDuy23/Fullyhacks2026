"""Google Places API (New) — places:searchText."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from difflib import SequenceMatcher
from typing import Any, Optional

from app.models.reel_extraction import ResolvedPlacePin

_PLACES_URL = "https://places.googleapis.com/v1/places:searchText"
_FIELD_MASK = (
    "places.id,places.displayName,places.formattedAddress,"
    "places.location,places.types,places.rating,places.userRatingCount"
)


def _api_key() -> str:
    return (os.environ.get("GOOGLE_MAPS_API_KEY") or "").strip()


def places_available() -> bool:
    return bool(_api_key())


def search_text(text_query: str, *, timeout: float = 15.0) -> list[dict[str, Any]]:
    key = _api_key()
    if not key:
        return []
    body = json.dumps({"textQuery": text_query}).encode("utf-8")
    req = urllib.request.Request(
        _PLACES_URL,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": key,
            "X-Goog-FieldMask": _FIELD_MASK,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.getcode() != 200:
                return []
            raw = resp.read().decode("utf-8", errors="replace")
            data = json.loads(raw)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, OSError):
        return []
    places = data.get("places") or []
    return places if isinstance(places, list) else []


def _name_similarity(a: str, b: str) -> float:
    a = (a or "").strip().lower()
    b = (b or "").strip().lower()
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def resolve_candidate(
    candidate_name: str,
    city_hint: Optional[str] = None,
    *,
    min_score: float = 0.45,
) -> Optional[ResolvedPlacePin]:
    q_parts = [candidate_name]
    if city_hint:
        q_parts.append(city_hint)
    text_query = " ".join(q_parts).strip()
    places = search_text(text_query)
    if not places:
        return None
    best: Optional[tuple[float, dict[str, Any]]] = None
    for p in places:
        disp = (p.get("displayName") or {})
        pname = disp.get("text") if isinstance(disp, dict) else ""
        loc = p.get("location") or {}
        lat = loc.get("latitude")
        lng = loc.get("longitude")
        types = p.get("types") or []
        if not isinstance(types, list):
            types = []
        rating = p.get("rating")
        urc = p.get("userRatingCount")
        name_sim = _name_similarity(candidate_name, pname or "")
        pop = 0.0
        if isinstance(rating, (int, float)) and isinstance(urc, int) and urc > 0:
            pop = min(1.0, (float(rating) / 5.0) * min(1.0, urc / 500.0))
        score = 0.55 * name_sim + 0.35 * pop + 0.1 * (1.0 if lat is not None else 0.0)
        if best is None or score > best[0]:
            best = (score, p)
    if best is None:
        return None
    sc, p = best
    if sc < min_score:
        return None
    disp = (p.get("displayName") or {})
    pname = disp.get("text") if isinstance(disp, dict) else candidate_name
    loc = p.get("location") or {}
    lat = loc.get("latitude")
    lng = loc.get("longitude")
    return ResolvedPlacePin(
        query=text_query,
        google_place_id=p.get("id"),
        name=pname or candidate_name,
        formatted_address=p.get("formattedAddress"),
        lat=float(lat) if lat is not None else None,
        lng=float(lng) if lng is not None else None,
        types=list(p.get("types") or []) if isinstance(p.get("types"), list) else [],
        rating=float(p["rating"]) if isinstance(p.get("rating"), (int, float)) else None,
        user_rating_count=int(p["userRatingCount"]) if isinstance(p.get("userRatingCount"), int) else None,
        match_score=sc,
    )
