from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.http_exceptions import llm_runtime_http_exception
from app.models.schemas import GenerateTripRequest, NormalizedPost, TripConstraints
from app.services.extractor import extract_posts
from app.services.pipeline import build_trip_inputs
from app.services.planner import generate_trip

router = APIRouter()


class PlanFromPostsRequest(BaseModel):
    posts: list[NormalizedPost]
    trip_constraints: TripConstraints


@router.post("/plan-from-posts")
def plan_from_posts(request: PlanFromPostsRequest):
    try:
        extracted = extract_posts(request.posts)
        trip_inputs = build_trip_inputs(extracted)

        trip_request = GenerateTripRequest(
            destination=trip_inputs["destination"],
            trip_constraints=request.trip_constraints,
            preference_profile=trip_inputs["preference_profile"],
            candidate_places=trip_inputs["candidate_places"],
        )

        trip = generate_trip(trip_request)

        return {
            "extracted_results": extracted,
            "preference_profile": trip_inputs["preference_profile"],
            "candidate_places": trip_inputs["candidate_places"],
            "trip": trip,
        }
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except RuntimeError as e:
        raise llm_runtime_http_exception(e) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"plan-from-posts failed: {e}") from e