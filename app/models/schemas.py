from typing import List, Literal, Optional
from pydantic import BaseModel, Field


TimeOfDay = Literal["morning", "afternoon", "evening", "night", "flexible"]
BudgetSignal = Literal["budget", "medium", "luxury", "unknown"]
PaceSignal = Literal["relaxed", "moderate", "packed", "unknown"]


class NormalizedPost(BaseModel):
    post_id: str
    url: str
    platform: Literal["tiktok", "instagram", "other"]
    caption: Optional[str] = ""
    transcript: Optional[str] = ""
    ocr_text: Optional[str] = ""
    thumbnail_text: Optional[str] = ""
    raw_text: str


class DestinationCandidate(BaseModel):
    name: str
    confidence: float = Field(ge=0.0, le=1.0)


class PlaceCandidate(BaseModel):
    name: str
    type: str
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


class ExtractedPost(BaseModel):
    post_id: str
    is_travel_relevant: bool
    destination_candidates: List[DestinationCandidate]
    place_candidates: List[PlaceCandidate]
    activities: List[str]
    vibe_tags: List[str]
    best_time_of_day: List[TimeOfDay]
    budget_signal: BudgetSignal
    pace_signal: PaceSignal
    notes: str


class ExtractRequest(BaseModel):
    posts: List[NormalizedPost]


class ExtractResponse(BaseModel):
    results: List[ExtractedPost]


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


# ---- Link import schemas ----------------------------------------------------

class ImportLinksRequest(BaseModel):
    urls: List[str] = Field(..., min_length=1)


class ImportedPost(BaseModel):
    post_id: str
    url: str
    platform: Literal["tiktok", "instagram", "other"]
    caption: str = ""
    transcript: str = ""
    ocr_text: str = ""
    thumbnail_text: str = ""
    raw_text: str
    creator: str = ""
    thumbnail_url: str = ""


class ImportLinksResponse(BaseModel):
    imported: List[ImportedPost]
    skipped: List[str] = []