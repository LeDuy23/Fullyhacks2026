"""HTTP smoke tests for the FastAPI app (no live Gemini calls)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_ok() -> None:
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is True


def test_trip_interests_ok() -> None:
    r = client.get("/trip-interests")
    assert r.status_code == 200
    body = r.json()
    interests = body.get("interests")
    assert isinstance(interests, list)
    assert len(interests) >= 10
    assert all("label" in x and "category" in x for x in interests[:5])
    cats = body.get("categories")
    assert isinstance(cats, list)
    assert len(cats) >= 3


def test_extract_validation_empty_body() -> None:
    r = client.post("/extract", json={})
    assert r.status_code == 422


def test_plan_from_posts_validation() -> None:
    r = client.post("/plan-from-posts", json={})
    assert r.status_code == 422


def test_cors_preflight_get() -> None:
    r = client.options(
        "/",
        headers={
            "Origin": "http://127.0.0.1:4321",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert r.status_code == 200


def test_tiktok_oembed_rejects_non_tiktok_url() -> None:
    r = client.post("/tiktok/oembed", json={"url": "https://example.com/video"})
    assert r.status_code == 422


def test_tiktok_gemini_read_validation_short_url() -> None:
    r = client.post("/tiktok/gemini-read", json={"url": "short"})
    assert r.status_code == 422


def test_tiktok_gemini_read_persist_requires_user_id() -> None:
    r = client.post(
        "/tiktok/gemini-read",
        json={
            "url": "https://www.tiktok.com/@someone/video/7123456789012345678",
            "persist": True,
        },
    )
    assert r.status_code == 422
