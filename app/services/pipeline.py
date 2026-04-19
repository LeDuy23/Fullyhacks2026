from app.models.schemas import ExtractedPost, PreferenceProfile, CandidatePlace
from app.services.scoring import (
    build_preference_profile,
    aggregate_places,
    score_places,
)


def build_trip_inputs(extracted_posts: list[ExtractedPost]) -> dict:
    profile: PreferenceProfile = build_preference_profile(extracted_posts)
    aggregated_places: list[CandidatePlace] = aggregate_places(extracted_posts)
    scored_places: list[CandidatePlace] = score_places(aggregated_places, profile)

    return {
        "destination": profile.dominant_destination or "Unknown",
        "preference_profile": profile,
        "candidate_places": scored_places,
    }