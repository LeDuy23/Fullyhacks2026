from collections import Counter
from typing import List
from app.models.schemas import ExtractedPost, CandidatePlace, PreferenceProfile


def normalize_key(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def estimate_duration(category: str) -> int:
    c = category.lower()
    if "cafe" in c:
        return 60
    if "restaurant" in c or "food" in c:
        return 90
    if "view" in c or "viewpoint" in c:
        return 90
    if "museum" in c:
        return 120
    if "shopping" in c:
        return 90
    return 60


def build_preference_profile(extracted_posts: List[ExtractedPost]) -> PreferenceProfile:
    vibe_counts = Counter()
    activity_counts = Counter()
    destination_counts = Counter()
    budget_counts = Counter()
    pace_counts = Counter()

    for post in extracted_posts:
        if not post.is_travel_relevant:
            continue

        vibe_counts.update(post.vibe_tags)
        activity_counts.update(post.activities)
        destination_counts.update([d.name for d in post.destination_candidates])
        budget_counts.update([post.budget_signal])
        pace_counts.update([post.pace_signal])

    dominant_destination = destination_counts.most_common(1)[0][0] if destination_counts else None
    budget_signal = budget_counts.most_common(1)[0][0] if budget_counts else "unknown"
    pace_signal = pace_counts.most_common(1)[0][0] if pace_counts else "unknown"

    return PreferenceProfile(
        dominant_destination=dominant_destination,
        top_vibes=[k for k, _ in vibe_counts.most_common(5)],
        top_activities=[k for k, _ in activity_counts.most_common(5)],
        budget_signal=budget_signal,
        pace_signal=pace_signal,
    )


def aggregate_places(extracted_posts: List[ExtractedPost]) -> List[CandidatePlace]:
    merged = {}

    for post in extracted_posts:
        if not post.is_travel_relevant:
            continue

        for place in post.place_candidates:
            key = normalize_key(place.name)

            if key not in merged:
                merged[key] = {
                    "place_id": key,
                    "name": place.name,
                    "category": place.type,
                    "mention_count": 1,
                    "avg_confidence": place.confidence,
                    "best_time_of_day": list(post.best_time_of_day),
                    "estimated_visit_minutes": estimate_duration(place.type),
                    "lat": place.lat,
                    "lng": place.lng,
                    "google_place_id": place.google_place_id,
                }
            else:
                existing = merged[key]
                old_count = existing["mention_count"]
                existing["mention_count"] += 1
                existing["avg_confidence"] = (
                    existing["avg_confidence"] * old_count + place.confidence
                ) / existing["mention_count"]

                for tod in post.best_time_of_day:
                    if tod not in existing["best_time_of_day"]:
                        existing["best_time_of_day"].append(tod)
                if place.lat is not None and place.lng is not None:
                    prev_conf = existing.get("_merge_best_conf", -1.0)
                    if existing.get("lat") is None or place.confidence >= prev_conf:
                        existing["lat"] = place.lat
                        existing["lng"] = place.lng
                        existing["_merge_best_conf"] = place.confidence
                if place.google_place_id and not existing.get("google_place_id"):
                    existing["google_place_id"] = place.google_place_id

    out: List[CandidatePlace] = []
    for value in merged.values():
        value.pop("_merge_best_conf", None)
        out.append(CandidatePlace(**value))
    return out


def compute_preference_match(place: CandidatePlace, profile: PreferenceProfile) -> float:
    score = 0.0
    category = place.category.lower()

    if place.category in profile.top_activities:
        score += 5

    if "cafe" in category and "aesthetic" in profile.top_vibes:
        score += 2

    if ("view" in category or "viewpoint" in category) and "photogenic" in profile.top_vibes:
        score += 2

    if ("bar" in category or "nightlife" in category) and "nightlife" in profile.top_vibes:
        score += 2

    if "food" in category and "foodie" in profile.top_vibes:
        score += 2

    return score


def score_places(places: List[CandidatePlace], profile: PreferenceProfile) -> List[CandidatePlace]:
    scored = []

    for place in places:
        mention_weight = min(place.mention_count * 2, 10)
        confidence_weight = place.avg_confidence * 10
        preference_match_weight = compute_preference_match(place, profile)
        feasibility_weight = 4
        uniqueness_weight = 2

        total = (
            mention_weight
            + confidence_weight
            + preference_match_weight
            + feasibility_weight
            + uniqueness_weight
        )

        scored_place = place.model_copy(update={"score": round(total, 2)})
        scored.append(scored_place)

    scored.sort(key=lambda p: p.score or 0, reverse=True)
    return scored