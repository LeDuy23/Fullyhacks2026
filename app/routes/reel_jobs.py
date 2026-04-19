"""Async reel / Maps URL extraction — POST /api/jobs, GET /api/jobs/:id."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from app.services.reel_job_store import create_job, get_job
from app.services.reel_pipeline import run_reel_extraction_job
from app.services.social_link import first_url_in_text

router = APIRouter(prefix="/api", tags=["jobs"])


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
