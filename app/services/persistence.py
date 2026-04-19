from __future__ import annotations

from typing import Any
from uuid import UUID

from postgrest.exceptions import APIError

from app.models.extraction import ExtractedPost, NormalizedPost
from app.models.schemas import GenerateTripRequest, ReviseTripRequest, TripPlan
from app.services.supabase_client import get_supabase_client
from app.services.tiktok_supabase import InvalidSupabaseUserError, SupabaseNotConfiguredError, SupabasePersistError


def _ensure_client():
    sb = get_supabase_client()
    if sb is None:
        raise SupabaseNotConfiguredError(
            "Supabase is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in `.env`."
        )
    return sb


def _aggregate_confidence(extracted: ExtractedPost) -> float:
    values = [d.confidence for d in extracted.destination_candidates] + [
        p.confidence for p in extracted.place_candidates
    ]
    if not values:
        return 0.0
    return round(sum(values) / len(values), 3)


def persist_extractions(user_id: UUID, posts: list[NormalizedPost], results: list[ExtractedPost]) -> None:
    sb = _ensure_client()
    uid = str(user_id)
    post_by_external_id = {p.post_id: p for p in posts}

    for extracted in results:
        source_post = post_by_external_id.get(extracted.post_id)
        if source_post is None:
            raise SupabasePersistError(f"missing source post for extracted post_id={extracted.post_id}")

        post_row: dict[str, Any] = {
            "user_id": uid,
            "url": source_post.url.strip(),
            "platform": source_post.platform,
            "client_post_id": source_post.post_id,
            "raw_text": source_post.raw_text,
            "metadata_json": {
                "caption": source_post.caption,
                "transcript": source_post.transcript,
                "ocr_text": source_post.ocr_text,
                "thumbnail_text": source_post.thumbnail_text,
                "image_mime_type": source_post.image_mime_type,
                "has_image_base64": bool(source_post.image_base64),
            },
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
                    "Invalid user_id: no matching row in public.users."
                ) from e
            raise SupabasePersistError(e.message or str(e)) from e

        rows = pr.data or []
        if not rows or not rows[0].get("id"):
            raise SupabasePersistError("failed to resolve post id while persisting extraction")
        post_id = rows[0]["id"]

        extraction_row = {
            "post_id": post_id,
            "is_travel_relevant": extracted.is_travel_relevant,
            "destination_candidates": [d.model_dump() for d in extracted.destination_candidates],
            "place_candidates": [p.model_dump() for p in extracted.place_candidates],
            "activities": extracted.activities,
            "vibe_tags": extracted.vibe_tags,
            "best_time_of_day": extracted.best_time_of_day,
            "budget_signal": extracted.budget_signal,
            "pace_signal": extracted.pace_signal,
            "notes": extracted.notes,
            "aggregate_confidence": _aggregate_confidence(extracted),
            "model_version": "extract_endpoint_v1",
        }
        try:
            sb.table("extractions").upsert(extraction_row, on_conflict="post_id").execute()
        except APIError as e:
            raise SupabasePersistError(e.message or str(e)) from e


def persist_generated_trip(user_id: UUID, request: GenerateTripRequest, trip: TripPlan) -> str:
    sb = _ensure_client()
    row = {
        "user_id": str(user_id),
        "destination": request.destination,
        "constraints_json": request.trip_constraints.model_dump(),
        "itinerary_json": trip.model_dump(),
        "preference_profile_json": request.preference_profile.model_dump(),
        "candidate_places_json": [p.model_dump() for p in request.candidate_places],
    }
    try:
        res = sb.table("trips").insert(row, returning="representation").execute()
    except APIError as e:
        msg = (e.message or "") + (e.details or "")
        if "23503" in msg or "foreign key" in msg.lower():
            raise InvalidSupabaseUserError("Invalid user_id: no matching row in public.users.") from e
        raise SupabasePersistError(e.message or str(e)) from e
    rows = res.data or []
    if not rows or not rows[0].get("id"):
        raise SupabasePersistError("trip insert succeeded without returned id")
    return str(rows[0]["id"])


def persist_revised_trip(request: ReviseTripRequest, revised_trip: TripPlan) -> None:
    sb = _ensure_client()
    trip_id = str(request.trip_id)

    try:
        old_res = sb.table("trips").select("itinerary_json").eq("id", trip_id).limit(1).execute()
    except APIError as e:
        raise SupabasePersistError(e.message or str(e)) from e

    old_trip_json = {}
    old_rows = old_res.data or []
    if old_rows:
        old_trip_json = old_rows[0].get("itinerary_json") or {}

    try:
        sb.table("trips").update({"itinerary_json": revised_trip.model_dump()}).eq("id", trip_id).execute()
        sb.table("trip_edits").insert(
            {
                "trip_id": trip_id,
                "user_prompt": request.revision_request,
                "previous_itinerary_json": old_trip_json,
                "new_itinerary_json": revised_trip.model_dump(),
            }
        ).execute()
    except APIError as e:
        raise SupabasePersistError(e.message or str(e)) from e
