from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    ImportLinksRequest,
    ImportLinksResponse,
    ImportedPost,
)
from app.services.instagram_parser import parse_urls, ParsedPost

router = APIRouter()


def _to_imported_post(p: ParsedPost) -> ImportedPost:
    return ImportedPost(
        post_id=p.post_id,
        url=p.url,
        platform=p.platform,
        caption=p.caption,
        transcript=p.transcript,
        ocr_text=p.ocr_text,
        thumbnail_text=p.detected_text,
        raw_text=p.raw_text,
        creator=p.creator,
        thumbnail_url=p.thumbnail_url,
    )


@router.post("/import-links", response_model=ImportLinksResponse)
def import_links(request: ImportLinksRequest):
    """
    Accept a list of Instagram/TikTok URLs, scrape them,
    and return structured post data ready for extraction.
    """
    try:
        parsed = parse_urls(request.urls)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parsing failed: {e}")

    parsed_urls = {p.url for p in parsed}
    skipped = [u for u in request.urls if u.strip() not in parsed_urls]

    return ImportLinksResponse(
        imported=[_to_imported_post(p) for p in parsed],
        skipped=skipped,
    )
