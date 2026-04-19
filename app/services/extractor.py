import json
from typing import List

from app.models.extraction import ExtractedPost, NormalizedPost
from app.services.llm import call_llm_validated


EXTRACT_SYSTEM_PROMPT = """
You are an information extraction system for a travel-planning application.

Your task is to extract travel-relevant structured data from social media posts.

Rules:
- Return only valid JSON.
- Do not include markdown.
- Be conservative. If something is unclear, lower confidence instead of guessing.
- Separate destination-level references from specific place-level references.
- Only mark a post as travel-relevant if it contains useful travel inspiration, destination cues, places, activities, neighborhoods, or itinerary ideas.
- Vibe tags should be short and travel-relevant, such as:
  trendy, romantic, luxury, budget, local, scenic, foodie, nightlife, aesthetic, relaxing, adventurous, photogenic.
- best_time_of_day values must come from:
  morning, afternoon, evening, night, flexible
- budget_signal must be one of:
  budget, medium, luxury, unknown
- pace_signal must be one of:
  relaxed, moderate, packed, unknown
- Confidence scores must be numbers between 0 and 1.
"""


def build_extract_prompt(post: NormalizedPost) -> str:
    return f"""
Extract structured travel signals from this social media post.

Post:
{json.dumps(post.model_dump(), indent=2)}

Return JSON in exactly this shape:
{{
  "post_id": "string",
  "is_travel_relevant": true,
  "destination_candidates": [
    {{
      "name": "string",
      "confidence": 0.0
    }}
  ],
  "place_candidates": [
    {{
      "name": "string",
      "type": "string",
      "confidence": 0.0,
      "reason": "string"
    }}
  ],
  "activities": ["string"],
  "vibe_tags": ["string"],
  "best_time_of_day": ["morning"],
  "budget_signal": "budget",
  "pace_signal": "moderate",
  "notes": "string"
}}
"""


def extract_post(post: NormalizedPost) -> ExtractedPost:
    prompt = f"""{EXTRACT_SYSTEM_PROMPT.strip()}

Return ONLY valid JSON matching the requested shape. No explanation.

{build_extract_prompt(post).strip()}
"""
    return call_llm_validated(prompt, ExtractedPost)


def extract_posts(posts: List[NormalizedPost]) -> List[ExtractedPost]:
    return [extract_post(post) for post in posts]