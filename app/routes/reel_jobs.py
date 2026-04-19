"""Async reel / Maps URL extraction — POST /api/jobs, GET /api/jobs/:id, GET /api/proxy-image."""

from __future__ import annotations

from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.services.reel_job_store import create_job, get_job
from app.services.reel_pipeline import run_reel_extraction_job
from app.services.social_link import first_url_in_text

router = APIRouter(prefix="/api", tags=["jobs"])

_MAX_PROXY_IMAGE_BYTES = 5 * 1024 * 1024
_PROXY_SUFFIXES: tuple[str, ...] = (
    ".cdninstagram.com",
    ".fbcdn.net",
    ".tiktokcdn.com",
    ".tiktokcdn-us.com",
    ".tiktokv.com",
    ".tiktokw.eu",
    ".googleusercontent.com",
    ".ytimg.com",
    ".ggpht.com",
)
_PROXY_EXACT: frozenset[str] = frozenset({"i.ytimg.com", "img.youtube.com"})


def _proxy_host_allowed(host: str) -> bool:
    h = (host or "").lower()
    if not h or h.startswith("127.") or h.startswith("192.168.") or h.startswith("10."):
        return False
    if h in _PROXY_EXACT:
        return True
    return any(h.endswith(suf) for suf in _PROXY_SUFFIXES)


def _proxy_url_allowed(url: str) -> bool:
    raw = (url or "").strip()
    if len(raw) > 2048 or len(raw) < 12:
        return False
    try:
        p = urlparse(raw)
    except ValueError:
        return False
    if p.scheme != "https":
        return False
    return _proxy_host_allowed(p.hostname or "")


def _fetch_proxy_image(url: str) -> tuple[bytes, str]:
    req = Request(
        url,
        headers={
            "User-Agent": "DeepDive-ThumbnailProxy/1.0",
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        },
        method="GET",
    )
    try:
        with urlopen(req, timeout=20) as resp:  # noqa: S310 — URL allowlisted above
            ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            data = resp.read(_MAX_PROXY_IMAGE_BYTES + 1)
    except HTTPError as e:
        raise ValueError(f"upstream http {e.code}") from e
    except URLError as e:
        raise ValueError(f"upstream error: {e.reason!s}") from e
    if len(data) > _MAX_PROXY_IMAGE_BYTES:
        raise ValueError("image too large")
    if ctype and not ctype.startswith("image/"):
        raise ValueError("response is not an image")
    if not ctype:
        ctype = "image/jpeg"
    return data, ctype


class CreateJobBody(BaseModel):
    url: str = Field(..., min_length=4)


@router.post("/jobs")
def post_job(body: CreateJobBody, background_tasks: BackgroundTasks):
    raw = body.url.strip()
    canonical = first_url_in_text(raw) or raw
    if len(canonical) < 12:
        raise HTTPException(status_code=422, detail="Could not find a valid URL in the request")
    job_id = create_job(canonical)
    background_tasks.add_task(run_reel_extraction_job, job_id)
    return {"job_id": job_id}


@router.get("/jobs/{job_id}")
def get_job_route(job_id: str):
    row = get_job(job_id)
    if not row:
        raise HTTPException(status_code=404, detail="job not found")
    return row


@router.get("/proxy-image")
def proxy_image(url: str = Query(..., min_length=12, max_length=2048)):
    """Fetch allowed social/video CDN thumbnails server-side for the DeepDive UI."""
    if not _proxy_url_allowed(url):
        raise HTTPException(status_code=403, detail="URL host is not allowed for proxy")
    try:
        body, ctype = _fetch_proxy_image(url)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    return Response(
        content=body,
        media_type=ctype,
        headers={"Cache-Control": "public, max-age=86400"},
    )
