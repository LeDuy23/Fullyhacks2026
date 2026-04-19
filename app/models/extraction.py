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
    # Optional screenshot / photo (Gemini vision). Raw base64 only; no data: URL prefix.
    image_base64: Optional[str] = None
    image_mime_type: Optional[str] = None


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


# Alias for tests and callers that refer to "extraction output" by name.
ExtractionOutput = ExtractedPost
