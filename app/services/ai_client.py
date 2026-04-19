def generate_json(system_prompt: str, user_prompt: str) -> dict:
    if '"destination_candidates"' in user_prompt and '"place_candidates"' in user_prompt:
        return {
            "post_id": "post_1",
            "is_travel_relevant": True,
            "destination_candidates": [
                {"name": "Tokyo", "confidence": 0.95}
            ],
            "place_candidates": [
                {
                    "name": "Shibuya Sky",
                    "type": "viewpoint",
                    "confidence": 0.93,
                    "reason": "Explicitly mentioned in the post"
                }
            ],
            "activities": ["viewpoint", "food"],
            "vibe_tags": ["trendy", "photogenic"],
            "best_time_of_day": ["evening"],
            "budget_signal": "medium",
            "pace_signal": "moderate",
            "notes": "Travel-focused Tokyo post"
        }

    if '"current_trip"' in user_prompt and '"revision_request"' in user_prompt:
        return {
            "destination": "Tokyo",
            "summary": "A revised Tokyo trip with a more relaxed pace.",
            "days": [
                {
                    "day": 1,
                    "area": "Shibuya",
                    "theme": "Views and food",
                    "items": [
                        {
                            "time": "18:00",
                            "place_id": "shibuya_sky",
                            "name": "Shibuya Sky",
                            "activity_type": "viewpoint",
                            "duration_minutes": 90,
                            "why_included": "Popular sunset spot that matches the saved content."
                        }
                    ],
                    "backup_options": ["ramen_street"]
                }
            ],
            "planning_notes": ["Mock revised output for testing"]
        }

    if '"trip_constraints"' in user_prompt and '"candidate_places"' in user_prompt:
        return {
            "destination": "Tokyo",
            "summary": "A sample 3-day Tokyo trip focused on views and food.",
            "days": [
                {
                    "day": 1,
                    "area": "Shibuya",
                    "theme": "Views and food",
                    "items": [
                        {
                            "time": "17:30",
                            "place_id": "shibuya_sky",
                            "name": "Shibuya Sky",
                            "activity_type": "viewpoint",
                            "duration_minutes": 90,
                            "why_included": "Highly relevant and a great evening activity."
                        }
                    ],
                    "backup_options": ["ramen_street"]
                }
            ],
            "planning_notes": ["Mock output for testing"]
        }

    raise ValueError("No mock configured for this prompt")