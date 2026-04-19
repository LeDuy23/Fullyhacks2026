from fastapi import APIRouter, HTTPException

from app.http_exceptions import llm_runtime_http_exception
from app.models.schemas import ReviseTripRequest, TripPlan
from app.services.reviser import revise_trip

router = APIRouter()


@router.post("/revise-trip", response_model=TripPlan)
def revise_trip_route(request: ReviseTripRequest):
    try:
        return revise_trip(request)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except RuntimeError as e:
        raise llm_runtime_http_exception(e) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"revise-trip failed: {e}") from e