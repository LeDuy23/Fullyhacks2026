import json
from app.models.schemas import ReviseTripRequest, TripPlan
from app.services.ai_client import generate_json


REVISE_SYSTEM_PROMPT = """
You are a travel itinerary editor.

You revise an existing itinerary based on a user's request.

Rules:
- Return only valid JSON.
- Preserve the overall trip structure when possible.
- Only use candidate places provided.
- Respect the user's requested changes.
- Keep the itinerary realistic and not overloaded.
- Avoid inventing new places.
- Keep day numbering stable unless the request clearly requires bigger changes.
"""


def build_revise_trip_prompt(request: ReviseTripRequest) -> str:
    return f"""
Revise this itinerary.

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


def revise_trip(request: ReviseTripRequest) -> TripPlan:
    raw = generate_json(REVISE_SYSTEM_PROMPT, build_revise_trip_prompt(request))
    return TripPlan(**raw)