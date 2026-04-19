import json
from typing import List

from app.models.extraction import ExtractedPost, NormalizedPost
from app.services.llm import call_llm_validated, call_llm_validated_with_image, decode_image_base64_field
from app.services.social_link import enrich_normalized_post


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


def _extract_from_image_post(post: NormalizedPost) -> ExtractedPost:
    raw_b64 = (post.image_base64 or "").strip()
    if not raw_b64:
        raise ValueError("image_base64 is empty")
    image_bytes, mime = decode_image_base64_field(raw_b64)
    mime = (post.image_mime_type or mime or "image/png").split(";")[0].strip()
    notes = (post.raw_text or "").strip() or "No extra notes; infer only from the image."
    prompt = f"""{EXTRACT_SYSTEM_PROMPT.strip()}

You are given a travel-related screenshot or photo. Read visible text (signs, captions, maps, UI).
User notes (may be empty): {notes}

Return ONLY valid JSON matching the requested shape. No explanation.
post_id must be exactly: {json.dumps(post.post_id)}

{build_extract_prompt(post).strip()}
"""
    return call_llm_validated_with_image(prompt, image_bytes, mime, ExtractedPost)


def extract_post(post: NormalizedPost) -> ExtractedPost:
    if (post.image_base64 or "").strip():
        return _extract_from_image_post(post)
    prompt = f"""{EXTRACT_SYSTEM_PROMPT.strip()}

Return ONLY valid JSON matching the requested shape. No explanation.

{build_extract_prompt(post).strip()}
"""
    return call_llm_validated(prompt, ExtractedPost)


def extract_posts(posts: List[NormalizedPost]) -> List[ExtractedPost]:
    return [extract_post(enrich_normalized_post(post)) for post in posts]