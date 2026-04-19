from fastapi import APIRouter, HTTPException

from app.http_exceptions import llm_runtime_http_exception
from app.models.schemas import ExtractRequest, ExtractResponse
from app.services.extractor import extract_posts

router = APIRouter()


@router.post("/extract", response_model=ExtractResponse)
def extract_route(request: ExtractRequest):
    try:
        results = extract_posts(request.posts)
        return ExtractResponse(results=results)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except RuntimeError as e:
        raise llm_runtime_http_exception(e) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"extract failed: {e}") from e