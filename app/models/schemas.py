from typing import List, Literal, Optional

from pydantic import BaseModel

from app.models.extraction import (
    BudgetSignal,
    ExtractRequest,
    ExtractResponse,
    ExtractedPost,
    NormalizedPost,
    PaceSignal,
)


class CandidatePlace(BaseModel):
    place_id: str
    name: str
    category: str
    neighborhood: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    opening_hours: Optional[str] = None
    estimated_visit_minutes: Optional[int] = 60
    best_time_of_day: List[str] = []
    mention_count: int
    avg_confidence: float
    score: Optional[float] = None


class PreferenceProfile(BaseModel):
    dominant_destination: Optional[str] = None
    top_vibes: List[str]
    top_activities: List[str]
    budget_signal: BudgetSignal
    pace_signal: PaceSignal


class TripConstraints(BaseModel):
    days: int
    budget: Optional[Literal["budget", "medium", "luxury"]] = "medium"
    pace: Optional[Literal["relaxed", "moderate", "packed"]] = "moderate"
    group_type: Optional[str] = "friends"
    must_include: List[str] = []
    avoid: List[str] = []
    transport_mode: Optional[str] = "public_transit"


class ItineraryItem(BaseModel):
    time: str
    place_id: str
    name: str
    activity_type: str
    duration_minutes: int
    why_included: str


class ItineraryDay(BaseModel):
    day: int
    area: str
    theme: str
    items: List[ItineraryItem]
    backup_options: List[str]


class TripPlan(BaseModel):
    destination: str
    summary: str
    days: List[ItineraryDay]
    planning_notes: List[str]


class GenerateTripRequest(BaseModel):
    destination: str
    trip_constraints: TripConstraints
    preference_profile: PreferenceProfile
    candidate_places: List[CandidatePlace]


class ReviseTripRequest(BaseModel):
    current_trip: TripPlan
    revision_request: str
    trip_constraints: Optional[TripConstraints] = None
    candidate_places: List[CandidatePlace]


__all__ = [
    "BudgetSignal",
    "PaceSignal",
    "NormalizedPost",
    "ExtractedPost",
    "ExtractRequest",
    "ExtractResponse",
    "CandidatePlace",
    "PreferenceProfile",
    "TripConstraints",
    "ItineraryItem",
    "ItineraryDay",
    "TripPlan",
    "GenerateTripRequest",
    "ReviseTripRequest",
]
