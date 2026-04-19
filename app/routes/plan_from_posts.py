from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, model_validator
from uuid import UUID

from app.http_exceptions import llm_runtime_http_exception
from app.models.schemas import GenerateTripRequest, NormalizedPost, TripConstraints
from app.services.extractor import extract_posts
from app.services.persistence import persist_extractions, persist_generated_trip
from app.services.pipeline import build_trip_inputs
from app.services.planner import generate_trip
from app.services.tiktok_supabase import (
    InvalidSupabaseUserError,
    SupabaseNotConfiguredError,
    SupabasePersistError,
)

router = APIRouter()


class PlanFromPostsRequest(BaseModel):
    posts: list[NormalizedPost]
    trip_constraints: TripConstraints
    persist: bool = False
    user_id: UUID | None = None

    @model_validator(mode="after")
    def _user_when_persist(self):
        if self.persist and self.user_id is None:
            raise ValueError("user_id is required when persist is true")
        return self


@router.post("/plan-from-posts")
def plan_from_posts(request: PlanFromPostsRequest):
    try:
        extracted = extract_posts(request.posts)
        if request.persist:
            if request.user_id is None:
                raise HTTPException(status_code=422, detail="user_id is required when persist is true")
            persist_extractions(request.user_id, request.posts, extracted)
        trip_inputs = build_trip_inputs(extracted)

        trip_request = GenerateTripRequest(
            destination=trip_inputs["destination"],
            trip_constraints=request.trip_constraints,
            preference_profile=trip_inputs["preference_profile"],
            candidate_places=trip_inputs["candidate_places"],
            persist=request.persist,
            user_id=request.user_id,
        )

        trip = generate_trip(trip_request)
        trip_id: str | None = None
        if request.persist:
            if request.user_id is None:
                raise HTTPException(status_code=422, detail="user_id is required when persist is true")
            trip_id = persist_generated_trip(request.user_id, trip_request, trip)

        return {
            "extracted_results": extracted,
            "preference_profile": trip_inputs["preference_profile"],
            "candidate_places": trip_inputs["candidate_places"],
            "trip": trip,
            "persisted_trip_id": trip_id,
        }
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except InvalidSupabaseUserError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except SupabaseNotConfiguredError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except SupabasePersistError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except RuntimeError as e:
        raise llm_runtime_http_exception(e) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"plan-from-posts failed: {e}") from e