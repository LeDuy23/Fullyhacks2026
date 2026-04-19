"""
Re-exports from backend.parser so the FastAPI app can import
the parser without path hacks.

All scraping logic lives in backend/parser.py.
"""

from backend.parser import (  # noqa: F401
    ParsedPost,
    detect_platform,
    validate_url,
    extract_shortcode,
    scrape_instagram,
    scrape_tiktok,
    parse_url,
    parse_urls,
    parse_urls_to_normalized,
)
