"""Smoke tests for POST/GET /api/jobs (no live yt-dlp or Gemini)."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_post_job_returns_job_id() -> None:
    with patch("app.routes.reel_jobs.run_reel_extraction_job"):
        r = client.post(
            "/api/jobs",
            json={"url": "https://www.tiktok.com/@someone/video/7123456789012345678"},
        )
    assert r.status_code == 200
    body = r.json()
    assert "job_id" in body
    assert len(body["job_id"]) == 36


def test_get_job_not_found() -> None:
    r = client.get("/api/jobs/00000000-0000-4000-8000-000000000000")
    assert r.status_code == 404


def test_post_job_rejects_short_body() -> None:
    r = client.post("/api/jobs", json={"url": "ab"})
    assert r.status_code == 422
