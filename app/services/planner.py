import json

from app.models.schemas import GenerateTripRequest, TripPlan
from app.services.llm import call_llm_validated


PLAN_SYSTEM_PROMPT = """
You are a travel itinerary planner.

Your task is to create a realistic, geographically coherent trip itinerary from structured place data and user preferences.

Rules:
- Return only valid JSON.
- Use only the candidate places provided.
- Prefer high-scoring places.
- Group each day geographically to reduce travel time.
- Respect time-of-day fit when possible.
- Do not overload the itinerary.
- Each day should have a clear area or neighborhood focus.
- Each itinerary item must include a short why_included explanation.
- Avoid repeating the same place.
- If there are not enough places, create a lighter itinerary rather than inventing new places.
"""


def build_generate_trip_prompt(request: GenerateTripRequest) -> str:
    return f"""
Create a trip itinerary from this input:

{json.dumps(request.model_dump(), indent=2)}

Return JSON in exactly this shape:
{{
  "destination": "string",
  "summary": "string",
  "days": [
    {{
      "day": 1,
      "area": "string",
      "theme": "string",
      "items": [
        {{
          "time": "HH:MM",
          "place_id": "string",
          "name": "string",
          "activity_type": "string",
          "duration_minutes": 0,
          "why_included": "string"
        }}
      ],
      "backup_options": ["string"]
    }}
  ],
  "planning_notes": ["string"]
}}
"""


def generate_trip(request: GenerateTripRequest) -> TripPlan:
    prompt = f"""{PLAN_SYSTEM_PROMPT.strip()}

Return ONLY valid JSON matching the requested shape. No explanation.

{build_generate_trip_prompt(request).strip()}
"""
    return call_llm_validated(prompt, TripPlan)