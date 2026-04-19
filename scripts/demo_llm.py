"""
Demo: mock social caption → Gemini → extraction JSON → trip plan JSON.

No video file is read; you pass text as if it were caption/transcript from a post.
From project root:  python scripts/demo_llm.py
Writes the same text to `llm-output.txt` in the project root.
Requires GEMINI_API_KEY in `.env`.
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

from app.models.extraction import NormalizedPost
from app.models.schemas import GenerateTripRequest, TripConstraints
from app.services.extractor import extract_post
from app.services.pipeline import build_trip_inputs
from app.services.planner import generate_trip

OUTPUT_FILE = _ROOT / "llm-output.txt"

MOCK_CAPTION = """
Tokyo day 🇯🇵 Shibuya Sky at sunset, sushi in Shinjuku, last stop Golden Gai.
"""

post = NormalizedPost(
    post_id="demo_1",
    url="https://example.com/reel/1",
    platform="instagram",
    raw_text=MOCK_CAPTION.strip(),
    caption=MOCK_CAPTION.strip(),
)

lines: list[str] = []


def emit(text: str) -> None:
    lines.append(text)
    print(text)


emit("--- INPUT (text standing in for caption / transcript) ---")
emit("")
emit(MOCK_CAPTION.strip())
emit("")

extracted = extract_post(post)
emit("--- STEP 1: EXTRACTION (places, vibes, destinations) ---")
emit(extracted.model_dump_json(indent=2))
emit("")

inputs = build_trip_inputs([extracted])
trip_req = GenerateTripRequest(
    destination=inputs["destination"],
    trip_constraints=TripConstraints(days=2),
    preference_profile=inputs["preference_profile"],
    candidate_places=inputs["candidate_places"],
)
plan = generate_trip(trip_req)
emit("--- STEP 2: TRIP PLAN (itinerary JSON) ---")
emit(plan.model_dump_json(indent=2))

OUTPUT_FILE.write_text("\n".join(lines), encoding="utf-8")
print(f"\nWrote {OUTPUT_FILE}")
