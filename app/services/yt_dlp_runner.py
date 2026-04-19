"""Download video metadata (and optional media path) via yt-dlp subprocess."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import sys
from pathlib import Path
from typing import Any


def _yt_dlp_cmd() -> list[str]:
    exe = shutil.which("yt-dlp")
    if exe:
        return [exe]
    return [sys.executable, "-m", "yt_dlp"]


def yt_dlp_available() -> bool:
    exe = shutil.which("yt-dlp")
    if exe:
        return True
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "yt_dlp", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return proc.returncode == 0
    except Exception:
        return False


def fetch_metadata_json(url: str, timeout_sec: int = 120) -> dict[str, Any]:
    if not yt_dlp_available():
        raise RuntimeError("yt-dlp is not installed or not on PATH")
    proc = subprocess.run(
        [*_yt_dlp_cmd(), "-j", "--no-warnings", "--no-playlist", url],
        capture_output=True,
        text=True,
        timeout=timeout_sec,
        env={**os.environ},
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()[:2000]
        raise RuntimeError(f"yt-dlp failed ({proc.returncode}): {err}")
    line = proc.stdout.strip().split("\n", 1)[0]
    return json.loads(line)


def download_best_mp4(url: str, timeout_sec: int = 120) -> dict[str, Any]:
    if not yt_dlp_available():
        raise RuntimeError("yt-dlp is not installed or not on PATH")
    tmp = tempfile.mkdtemp(prefix="reel_")
    out_tpl = str(Path(tmp) / "video.%(ext)s")
    proc = subprocess.run(
        [
            *_yt_dlp_cmd(),
            "-f",
            "mp4/bestvideo+bestaudio/best",
            "--merge-output-format",
            "mp4",
            "-o",
            out_tpl,
            "--no-warnings",
            "--no-playlist",
            url,
        ],
        capture_output=True,
        text=True,
        timeout=timeout_sec,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()[:2000]
        raise RuntimeError(f"yt-dlp download failed ({proc.returncode}): {err}")
    mp4s = list(Path(tmp).glob("*.mp4"))
    if not mp4s:
        raise RuntimeError("yt-dlp did not produce an mp4 file")
    meta = fetch_metadata_json(url, timeout_sec=timeout_sec)
    return {"temp_dir": tmp, "video_path": str(mp4s[0]), "metadata": meta}
