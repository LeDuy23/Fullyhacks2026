from fastapi import APIRouter, HTTPException

from app.http_exceptions import llm_runtime_http_exception
from app.models.schemas import GenerateTripRequest, TripPlan
from app.services.planner import generate_trip
from app.services.persistence import persist_generated_trip
from app.services.tiktok_supabase import (
    InvalidSupabaseUserError,
    SupabaseNotConfiguredError,
    SupabasePersistError,
)

router = APIRouter()


@router.post("/generate-trip", response_model=TripPlan)
def generate_trip_route(request: GenerateTripRequest):
    try:
        trip = generate_trip(request)
        if request.persist:
            if request.user_id is None:
                raise HTTPException(status_code=422, detail="user_id is required when persist is true")
            persist_generated_trip(request.user_id, request, trip)
        return trip
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
        raise HTTPException(status_code=500, detail=f"generate-trip failed: {e}") from e