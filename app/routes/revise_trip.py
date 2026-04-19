from fastapi import APIRouter, HTTPException

from app.http_exceptions import llm_runtime_http_exception
from app.models.schemas import ReviseTripRequest, TripPlan
from app.services.persistence import persist_revised_trip
from app.services.reviser import revise_trip
from app.services.tiktok_supabase import SupabaseNotConfiguredError, SupabasePersistError

router = APIRouter()


@router.post("/revise-trip", response_model=TripPlan)
def revise_trip_route(request: ReviseTripRequest):
    try:
        revised = revise_trip(request)
        if request.persist:
            if request.user_id is None or request.trip_id is None:
                raise HTTPException(
                    status_code=422, detail="user_id and trip_id are required when persist is true"
                )
            persist_revised_trip(request, revised)
        return revised
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except SupabaseNotConfiguredError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except SupabasePersistError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except RuntimeError as e:
        raise llm_runtime_http_exception(e) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"revise-trip failed: {e}") from e