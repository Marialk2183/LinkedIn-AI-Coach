"""AI writing assistant endpoints (headline + About)."""

from fastapi import APIRouter, Depends

from models.schemas import (
    AboutRequest,
    AboutResponse,
    HeadlineRequest,
    HeadlineResponse,
)
from routes.deps import get_ai_service
from services.ai_service import AIService

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/headline", response_model=HeadlineResponse)
def improve_headline(
    payload: HeadlineRequest, ai: AIService = Depends(get_ai_service)
) -> HeadlineResponse:
    headline, ai_generated = ai.improve_headline(
        payload.headline, payload.skills, payload.target_role
    )
    return HeadlineResponse(headline=headline, ai_generated=ai_generated)


@router.post("/about", response_model=AboutResponse)
def improve_about(
    payload: AboutRequest, ai: AIService = Depends(get_ai_service)
) -> AboutResponse:
    about, ai_generated = ai.improve_about(
        payload.name,
        payload.headline,
        payload.skills,
        payload.experience_years,
        payload.target_role,
        payload.current_about,
    )
    return AboutResponse(about=about, ai_generated=ai_generated)
