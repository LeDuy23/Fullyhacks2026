from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI

# Load project-root `.env` so GEMINI_API_KEY is available without exporting in the shell.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
from app.routes.extract import router as extract_router
from app.routes.generate_trip import router as generate_trip_router
from app.routes.revise_trip import router as revise_trip_router
from app.routes.plan_from_posts import router as plan_from_posts_router

app = FastAPI(title="Travel Planner AI Backend")

app.include_router(extract_router)
app.include_router(generate_trip_router)
app.include_router(revise_trip_router)
app.include_router(plan_from_posts_router)


@app.get("/")
def root():
    return {"ok": True, "message": "Travel planner backend is running"}