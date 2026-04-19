from fastapi import APIRouter, HTTPException
from app.models.schemas import ReviseTripRequest, TripPlan
from app.services.reviser import revise_trip

router = APIRouter()


@router.post("/revise-trip", response_model=TripPlan)
def revise_trip_route(request: ReviseTripRequest):
    try:
        return revise_trip(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"revise-trip failed: {str(e)}")