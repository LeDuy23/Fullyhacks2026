from fastapi import APIRouter, HTTPException

from app.http_exceptions import llm_runtime_http_exception
from app.models.schemas import ExtractRequest, ExtractResponse
from app.services.extractor import extract_posts
from app.services.persistence import persist_extractions
from app.services.tiktok_supabase import (
    InvalidSupabaseUserError,
    SupabaseNotConfiguredError,
    SupabasePersistError,
)

router = APIRouter()


@router.post("/extract", response_model=ExtractResponse)
def extract_route(request: ExtractRequest):
    try:
        results = extract_posts(request.posts)
        if request.persist:
            if request.user_id is None:
                raise HTTPException(status_code=422, detail="user_id is required when persist is true")
            persist_extractions(request.user_id, request.posts, results)
        return ExtractResponse(results=results)
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
        raise HTTPException(status_code=500, detail=f"extract failed: {e}") from e