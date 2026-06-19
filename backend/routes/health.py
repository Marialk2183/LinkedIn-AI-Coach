"""Health / readiness probe."""

from fastapi import APIRouter, Depends

from config import Settings, get_settings
from ml.predictor import get_predictor
from models.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    predictor = get_predictor()
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        ai_enabled=settings.ai_enabled,
        ml_loaded=predictor.available,
        model_version=predictor.version,
        model_metrics=predictor.metrics,
    )
