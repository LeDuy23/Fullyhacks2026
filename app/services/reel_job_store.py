"""Thread-safe job store for reel extraction; mirrors to Supabase when configured."""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

_lock = threading.Lock()
_jobs: dict[str, dict[str, Any]] = {}


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_job(source_url: str) -> str:
    jid = str(uuid.uuid4())
    row = {
        "id": jid,
        "source_url": source_url.strip(),
        "status": "queued",
        "result": None,
        "error": None,
        "created_at": _utcnow_iso(),
        "completed_at": None,
    }
    with _lock:
        _jobs[jid] = row
    _sync_supabase_upsert(row)
    return jid


def get_job(job_id: str) -> Optional[dict[str, Any]]:
    with _lock:
        row = _jobs.get(job_id)
        return json.loads(json.dumps(row)) if row else None


def update_job(job_id: str, **fields: Any) -> None:
    with _lock:
        if job_id not in _jobs:
            return
        _jobs[job_id].update(fields)
        row = dict(_jobs[job_id])
    _sync_supabase_upsert(row)


def _sync_supabase_upsert(row: dict[str, Any]) -> None:
    try:
        from app.services.supabase_client import get_supabase_client

        cli = get_supabase_client()
        if cli is None:
            return
        payload = {
            "id": row["id"],
            "source_url": row["source_url"],
            "status": row["status"],
            "result": row.get("result"),
            "error": row.get("error"),
            "created_at": row.get("created_at"),
            "completed_at": row.get("completed_at"),
        }
        cli.table("reel_extraction_jobs").upsert(payload).execute()
    except Exception:
        pass


def clear_all_for_tests() -> None:
    with _lock:
        _jobs.clear()
