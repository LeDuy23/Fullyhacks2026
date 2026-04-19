from fastapi import HTTPException


def llm_runtime_http_exception(exc: RuntimeError) -> HTTPException:
    """Map LLM configuration failures (missing API key, etc.) to HTTP errors."""
    msg = str(exc)
    if "GEMINI_API_KEY" in msg or "GOOGLE_API_KEY" in msg:
        return HTTPException(status_code=503, detail=msg)
    return HTTPException(status_code=502, detail=msg)
