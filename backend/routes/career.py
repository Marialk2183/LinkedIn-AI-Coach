"""Standalone career-prediction endpoint."""

from fastapi import APIRouter, Depends, HTTPException, status

from models.schemas import CareerMatchSchema, CareerPredictRequest
from routes.deps import get_career_service
from services.career_service import CareerService
from utils.parser import parse_profile

router = APIRouter(prefix="/career", tags=["career"])


@router.post("/predict", response_model=list[CareerMatchSchema])
def predict(
    payload: CareerPredictRequest, career: CareerService = Depends(get_career_service)
) -> list[CareerMatchSchema]:
    if not payload.profile_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="profile_text is required",
        )
    parsed = parse_profile(payload.profile_text)
    matches = career.predict(parsed)
    return [
        CareerMatchSchema(
            role=m.role, match_pct=m.match_pct,
            matched_skills=m.matched_skills, missing_skills=m.missing_skills,
        )
        for m in matches
    ]
