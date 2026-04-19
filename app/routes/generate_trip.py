from fastapi import APIRouter, HTTPException

from app.http_exceptions import llm_runtime_http_exception
from app.models.schemas import GenerateTripRequest, TripPlan
from app.services.planner import generate_trip

router = APIRouter()


@router.post("/generate-trip", response_model=TripPlan)
def generate_trip_route(request: GenerateTripRequest):
    try:
        return generate_trip(request)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except RuntimeError as e:
        raise llm_runtime_http_exception(e) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"generate-trip failed: {e}") from e