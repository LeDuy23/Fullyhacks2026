"""
Load repo-root `.env` before tests run.

Uses override=True so values from `.env` replace empty placeholders in the environment.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


def load_project_env() -> None:
    """Load `.env` from the project root; fall back to default dotenv search."""
    if ENV_FILE.is_file():
        load_dotenv(ENV_FILE, override=True)
    else:
        load_dotenv(override=True)


load_project_env()


def pytest_configure(config) -> None:
    load_project_env()


def has_gemini_api_key() -> bool:
    return bool(
        (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip()
    )
