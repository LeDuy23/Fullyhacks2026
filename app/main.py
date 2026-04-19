import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load project-root `.env` so GEMINI_API_KEY is available without exporting in the shell.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
from app.routes.extract import router as extract_router
from app.routes.generate_trip import router as generate_trip_router
from app.routes.revise_trip import router as revise_trip_router
from app.routes.plan_from_posts import router as plan_from_posts_router
from app.routes.tiktok_read import router as tiktok_read_router
from app.routes.trip_interests import router as trip_interests_router
from app.routes.reel_jobs import router as reel_jobs_router

app = FastAPI(title="Travel Planner AI Backend")

_cors = os.getenv(
    "CORS_ORIGINS",
    "http://127.0.0.1:4321,http://localhost:4321,"
    "http://127.0.0.1:3000,http://localhost:3000,"
    "http://127.0.0.1:5173,http://localhost:5173",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(extract_router)
app.include_router(generate_trip_router)
app.include_router(revise_trip_router)
app.include_router(plan_from_posts_router)
app.include_router(tiktok_read_router)
app.include_router(trip_interests_router)
app.include_router(reel_jobs_router)


@app.get("/")
def root():
    return {"ok": True, "message": "Travel planner backend is running"}