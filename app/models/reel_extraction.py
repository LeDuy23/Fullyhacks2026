"""Pydantic models for reel video location extraction (Gemini + Places)."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class ReelEvidence(BaseModel):
    source: str = "visual"
    detail: str = ""


class ReelLocationItem(BaseModel):
    name: str
    type: str = "other"
    city_hint: Optional[str] = None
    address_hint: Optional[str] = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence: List[ReelEvidence] = Field(default_factory=list)


class ReelVideoLocations(BaseModel):
    locations: List[ReelLocationItem] = Field(default_factory=list)


class ResolvedPlacePin(BaseModel):
    """A candidate matched via Places searchText (for map / clients)."""

    query: str
    google_place_id: Optional[str] = None
    name: str
    formatted_address: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    types: List[str] = Field(default_factory=list)
    rating: Optional[float] = None
    user_rating_count: Optional[int] = None
    match_score: float = 0.0
