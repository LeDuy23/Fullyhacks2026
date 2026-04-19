from fastapi import APIRouter, HTTPException
from app.models.schemas import ExtractRequest, ExtractResponse
from app.services.extractor import extract_posts

router = APIRouter()


@router.post("/extract", response_model=ExtractResponse)
def extract_route(request: ExtractRequest):
    try:
        results = extract_posts(request.posts)
        return ExtractResponse(results=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"extract failed: {str(e)}")