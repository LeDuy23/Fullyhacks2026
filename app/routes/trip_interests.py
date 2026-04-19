"""Trip interest catalog for plan UI (labels sent to planner as free text)."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter

router = APIRouter()

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_INTERESTS_FILE = _PROJECT_ROOT / "trip-interests.json"


@router.get("/trip-interests")
def get_trip_interests() -> dict:
    data = json.loads(_INTERESTS_FILE.read_text(encoding="utf-8"))
    interests = data.get("interests") or []
    cats = sorted({str(x.get("category") or "Other") for x in interests})
    return {"interests": interests, "categories": cats}
