from fastapi import APIRouter, HTTPException
from app.models.schemas import GenerateTripRequest, TripPlan
from app.services.planner import generate_trip

router = APIRouter()


@router.post("/generate-trip", response_model=TripPlan)
def generate_trip_route(request: GenerateTripRequest):
    try:
        return generate_trip(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"generate-trip failed: {str(e)}")