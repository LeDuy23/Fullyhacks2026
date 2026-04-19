from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

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
    persist: bool = False
    user_id: Optional[UUID] = None

    @model_validator(mode="after")
    def _user_when_persist(self):
        if self.persist and self.user_id is None:
            raise ValueError("user_id is required when persist is true")
        return self


class ExtractResponse(BaseModel):
    results: List[ExtractedPost]


# Alias for tests and callers that refer to "extraction output" by name.
ExtractionOutput = ExtractedPost
