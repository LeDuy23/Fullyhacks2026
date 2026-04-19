from fastapi import APIRouter, HTTPException

from app.http_exceptions import llm_runtime_http_exception
from app.models.extraction import ExtractedPost
from app.models.schemas import ExtractRequest, ExtractResponse
from app.services.maps_url_resolve import is_google_maps_url
from app.services.extractor import extract_posts
from app.services.reel_job_store import create_job, get_job
from app.services.reel_pipeline import run_reel_extraction_job
from app.services.social_link import detect_platform, first_url_in_text

router = APIRouter()


def _should_use_reel_pipeline(request: ExtractRequest) -> bool:
    if len(request.posts) != 1:
        return False
    p = request.posts[0]
    if (p.image_base64 or "").strip():
        return False
    raw = (p.raw_text or "").strip()
    url = first_url_in_text(raw) or (p.url or "").strip()
    if not url:
        return False
    platform = detect_platform(url)
    return platform in {"instagram", "tiktok"} or is_google_maps_url(url)


@router.post("/extract", response_model=ExtractResponse)
def extract_route(request: ExtractRequest):
    try:
        if _should_use_reel_pipeline(request):
            p = request.posts[0]
            raw = (p.raw_text or "").strip()
            source_url = first_url_in_text(raw) or (p.url or "").strip()
            job_id = create_job(source_url)
            run_reel_extraction_job(job_id)
            row = get_job(job_id) or {}
            if row.get("status") == "done":
                payload = (((row.get("result") or {}).get("extract") or {}).get("results") or [])
                if payload:
                    first = payload[0]
                    return ExtractResponse(results=[ExtractedPost.model_validate(first)])
            msg = (row.get("error") if isinstance(row, dict) else None) or "URL extraction failed"
            raise RuntimeError(msg)
        results = extract_posts(request.posts)
        return ExtractResponse(results=results)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except RuntimeError as e:
        raise llm_runtime_http_exception(e) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"extract failed: {e}") from e