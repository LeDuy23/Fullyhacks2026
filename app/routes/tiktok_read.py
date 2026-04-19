from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from app.http_exceptions import llm_runtime_http_exception
from app.services.tiktok_gemini import (
    TikTokTravelInsight,
    analyze_tiktok_with_gemini,
    analyze_tiktok_with_gemini_and_oembed,
)
from app.services.tiktok_reader import fetch_tiktok_oembed_data
from app.services.tiktok_supabase import (
    InvalidSupabaseUserError,
    SupabaseNotConfiguredError,
    SupabasePersistError,
    persist_tiktok_gemini_insight,
)

router = APIRouter(prefix="/tiktok", tags=["tiktok"])


class TikTokUrlBody(BaseModel):
    url: str = Field(..., min_length=8, description="Full TikTok video URL")


class TikTokGeminiReadBody(BaseModel):
    url: str = Field(..., min_length=8, description="Full TikTok video URL")
    persist: bool = False
    """When true, upsert into Supabase `posts` + `extractions` (needs service role env + valid user_id)."""
    user_id: UUID | None = None

    @model_validator(mode="after")
    def _user_when_persist(self):
        if self.persist and self.user_id is None:
            raise ValueError("user_id is required when persist is true")
        return self


class TikTokGeminiReadResponse(TikTokTravelInsight):
    supabase_post_id: str | None = None
    supabase_extraction_id: str | None = None


@router.post("/oembed", response_model=dict)
def tiktok_oembed(body: TikTokUrlBody):
    try:
        return fetch_tiktok_oembed_data(body.url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.post("/gemini-read", response_model=TikTokGeminiReadResponse)
def tiktok_gemini_read(body: TikTokGeminiReadBody):
    try:
        if body.persist:
            insight, oembed = analyze_tiktok_with_gemini_and_oembed(body.url)
            post_id, ext_id = persist_tiktok_gemini_insight(
                user_id=body.user_id,  # validated: present when persist
                url=body.url,
                oembed=oembed,
                insight=insight,
            )
            return TikTokGeminiReadResponse(
                **insight.model_dump(),
                supabase_post_id=post_id,
                supabase_extraction_id=ext_id,
            )
        insight = analyze_tiktok_with_gemini(body.url)
        return TikTokGeminiReadResponse(**insight.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except InvalidSupabaseUserError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except SupabaseNotConfiguredError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except SupabasePersistError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except RuntimeError as e:
        raise llm_runtime_http_exception(e) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"tiktok gemini-read failed: {e}") from e
