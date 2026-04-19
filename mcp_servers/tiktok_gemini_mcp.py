#!/usr/bin/env python3
"""
MCP server: TikTok public oEmbed + Gemini travel insights (metadata only; no video download).

Run from the repository root (needs `mcp` and `.env` with GEMINI_API_KEY):

  python mcp_servers/tiktok_gemini_mcp.py

Add to Cursor (example): Settings → MCP → stdio command:
  python /absolute/path/to/Fullyhacks2026/mcp_servers/tiktok_gemini_mcp.py
  cwd: /absolute/path/to/Fullyhacks2026
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "deepdive-tiktok-gemini",
    instructions=(
        "Expose TikTok oEmbed (public metadata) and optional Gemini analysis for travel cues. "
        "Does not access private videos, DMs, or raw video bytes."
    ),
)


@mcp.tool()
def tiktok_get_oembed(url: str) -> str:
    """Fetch public TikTok video metadata via TikTok's oEmbed API (title, author, thumbnail)."""
    from app.services.tiktok_reader import fetch_tiktok_oembed_data

    return json.dumps(fetch_tiktok_oembed_data(url), indent=2)


@mcp.tool()
def tiktok_gemini_travel_insights(
    url: str,
    persist_to_supabase: bool = False,
    supabase_user_id: str | None = None,
) -> str:
    """Use Google Gemini on oEmbed metadata only. Optionally upsert into Supabase posts+extractions (needs service role in .env)."""
    from app.services.tiktok_gemini import (
        analyze_tiktok_with_gemini,
        analyze_tiktok_with_gemini_and_oembed,
    )
    from app.services.tiktok_supabase import (
        InvalidSupabaseUserError,
        SupabaseNotConfiguredError,
        SupabasePersistError,
        persist_tiktok_gemini_insight,
    )

    if persist_to_supabase:
        if not supabase_user_id or not supabase_user_id.strip():
            return json.dumps(
                {"error": "supabase_user_id is required when persist_to_supabase is true"},
                indent=2,
            )
        try:
            uid = UUID(supabase_user_id.strip())
        except ValueError:
            return json.dumps({"error": "supabase_user_id must be a valid UUID"}, indent=2)

        try:
            insight, oembed = analyze_tiktok_with_gemini_and_oembed(url)
            post_id, ext_id = persist_tiktok_gemini_insight(
                user_id=uid, url=url, oembed=oembed, insight=insight
            )
        except SupabaseNotConfiguredError as e:
            return json.dumps({"error": str(e)}, indent=2)
        except InvalidSupabaseUserError as e:
            return json.dumps({"error": str(e)}, indent=2)
        except SupabasePersistError as e:
            return json.dumps({"error": str(e)}, indent=2)
        except RuntimeError as e:
            return json.dumps({"error": str(e)}, indent=2)
        payload = {
            **insight.model_dump(),
            "supabase_post_id": post_id,
            "supabase_extraction_id": ext_id,
        }
        return json.dumps(payload, indent=2, ensure_ascii=False)

    return analyze_tiktok_with_gemini(url).model_dump_json(indent=2)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
