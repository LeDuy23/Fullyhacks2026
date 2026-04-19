"""Orchestrate reel URL → yt-dlp → Gemini video → Places → ExtractResponse-shaped result."""

from __future__ import annotations

import shutil
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.models.extraction import DestinationCandidate, ExtractedPost, NormalizedPost, PlaceCandidate
from app.models.reel_extraction import ReelLocationItem, ResolvedPlacePin
from app.services.extractor import extract_post
from app.services.gemini_reel_video import extract_locations_from_video_file
from app.services.maps_url_resolve import is_google_maps_url, maps_url_query_candidates, maps_url_to_query_text
from app.services.places_client import places_available, resolve_candidate, search_text
from app.services.reel_job_store import update_job
from app.services.social_link import detect_platform, enrich_normalized_post, first_url_in_text
from app.services.yt_dlp_runner import download_best_mp4, yt_dlp_available


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_extracted_post(
    *,
    post_id: str,
    source_url: str,
    items: list[ReelLocationItem],
    resolved: list[Optional[ResolvedPlacePin]],
) -> ExtractedPost:
    dest_scores: dict[str, float] = {}
    for loc in items:
        if loc.city_hint:
            ch = loc.city_hint.strip()
            if ch:
                dest_scores[ch] = max(dest_scores.get(ch, 0.0), loc.confidence)
    dest_candidates = [
        DestinationCandidate(name=k, confidence=min(1.0, v + 0.05)) for k, v in sorted(dest_scores.items(), key=lambda x: -x[1])
    ][:8]

    place_candidates: list[PlaceCandidate] = []
    for loc, pin in zip(items, resolved):
        if pin:
            conf = min(loc.confidence, max(0.0, min(1.0, pin.match_score + 0.1)))
            reason_parts = []
            if pin.formatted_address:
                reason_parts.append(pin.formatted_address)
            if loc.evidence:
                reason_parts.append(loc.evidence[0].detail[:200])
            place_candidates.append(
                PlaceCandidate(
                    name=pin.name,
                    type=(pin.types[0] if pin.types else loc.type) or "place",
                    confidence=conf,
                    reason=" · ".join(reason_parts) or f"Matched via Google Places (score {pin.match_score:.2f})",
                )
            )
        else:
            place_candidates.append(
                PlaceCandidate(
                    name=loc.name,
                    type=loc.type,
                    confidence=loc.confidence * 0.55,
                    reason="Model suggestion; no confident Google Places match — verify before saving.",
                )
            )

    notes = f"Reel-to-map pipeline for {source_url[:120]}"
    return ExtractedPost(
        post_id=post_id,
        is_travel_relevant=len(place_candidates) > 0,
        destination_candidates=dest_candidates,
        place_candidates=place_candidates[:24],
        activities=[],
        vibe_tags=["reel_import"],
        best_time_of_day=["flexible"],
        budget_signal="unknown",
        pace_signal="unknown",
        notes=notes,
    )


def _fallback_caption_only(url: str) -> ExtractedPost:
    uid = str(uuid.uuid4())[:12]
    post = NormalizedPost(
        post_id=f"reel-{uid}",
        url=url,
        platform=detect_platform(url),
        raw_text=url,
    )
    return extract_post(enrich_normalized_post(post))


def run_reel_extraction_job(job_id: str) -> None:
    from app.services import reel_job_store

    row = reel_job_store.get_job(job_id)
    if not row:
        return
    source_url = (row.get("source_url") or "").strip()
    update_job(job_id, status="processing")

    temp_dir: Optional[str] = None
    debug: dict[str, Any] = {"source_url": source_url}
    try:
        post_id = f"job-{job_id[:8]}"

        if is_google_maps_url(source_url):
            q = maps_url_to_query_text(source_url) or source_url
            queries = maps_url_query_candidates(source_url) or [q, source_url]
            debug["maps_queries"] = queries
            if not places_available():
                raise RuntimeError(
                    "GOOGLE_MAPS_API_KEY is not set — cannot resolve Google Maps links server-side."
                )
            places: list[dict[str, Any]] = []
            used_query = q
            for query in queries:
                places = search_text(query)
                if places:
                    used_query = query
                    break
            if not places:
                raise RuntimeError("No place found for that Maps URL query candidates.")
            p0 = places[0]
            disp = (p0.get("displayName") or {})
            pname = disp.get("text") if isinstance(disp, dict) else q
            loc = p0.get("location") or {}
            lat = loc.get("latitude")
            lng = loc.get("longitude")
            pin = ResolvedPlacePin(
                query=used_query,
                google_place_id=p0.get("id"),
                name=pname or q,
                formatted_address=p0.get("formattedAddress"),
                lat=float(lat) if lat is not None else None,
                lng=float(lng) if lng is not None else None,
                types=list(p0.get("types") or []),
                rating=float(p0["rating"]) if isinstance(p0.get("rating"), (int, float)) else None,
                user_rating_count=int(p0["userRatingCount"]) if isinstance(p0.get("userRatingCount"), int) else None,
                match_score=0.95,
            )
            synthetic = ReelLocationItem(
                name=pin.name,
                type="landmark",
                city_hint=None,
                address_hint=pin.formatted_address,
                confidence=0.95,
                evidence=[],
            )
            extracted = _build_extracted_post(
                post_id=post_id,
                source_url=source_url,
                items=[synthetic],
                resolved=[pin],
            )
            result: dict[str, Any] = {
                "extract": {"results": [extracted.model_dump()]},
                "resolved_places": [pin.model_dump()],
                "mode": "google_maps_direct",
                "debug": debug,
            }
            update_job(
                job_id,
                status="done",
                result=result,
                error=None,
                completed_at=_utcnow_iso(),
            )
            return

        canonical = first_url_in_text(source_url) or source_url
        debug["canonical_url"] = canonical
        used_video = False
        reel_locs: list[ReelLocationItem] = []

        if yt_dlp_available():
            try:
                pack = download_best_mp4(canonical)
                temp_dir = pack["temp_dir"]
                video_path = pack["video_path"]
                used_video = True
                reel_locs = extract_locations_from_video_file(video_path).locations
                debug["yt_dlp"] = "ok"
                debug["video_extract"] = "ok"
            except Exception as e:
                used_video = False
                reel_locs = []
                debug["video_error"] = str(e)[:500]
        else:
            debug["video_error"] = "yt-dlp not available on PATH"

        resolved_pins: list[Optional[ResolvedPlacePin]] = []

        if used_video and reel_locs:
            for loc in reel_locs:
                pin: Optional[ResolvedPlacePin] = None
                if places_available():
                    pin = resolve_candidate(loc.name, loc.city_hint)
                resolved_pins.append(pin)
            extracted = _build_extracted_post(
                post_id=post_id,
                source_url=canonical,
                items=reel_locs,
                resolved=resolved_pins,
            )
            result = {
                "extract": {"results": [extracted.model_dump()]},
                "resolved_places": [p.model_dump() if p else None for p in resolved_pins],
                "mode": "gemini_video",
                "debug": debug,
            }
        else:
            extracted = _fallback_caption_only(canonical)
            result = {
                "extract": {"results": [extracted.model_dump()]},
                "resolved_places": [],
                "mode": "caption_oembed_fallback",
                "debug": debug,
            }

        update_job(
            job_id,
            status="done",
            result=result,
            error=None,
            completed_at=_utcnow_iso(),
        )
    except Exception as e:
        update_job(
            job_id,
            status="failed",
            result=None,
            error=str(e)[:4000],
            completed_at=_utcnow_iso(),
        )
    finally:
        if temp_dir:
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
