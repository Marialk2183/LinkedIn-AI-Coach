"""Health / readiness probe."""

from fastapi import APIRouter, Depends

from config import Settings, get_settings
from ml.predictor import get_predictor
from models.schemas import HealthResponse
from routes.deps import get_ai_service, get_artifact_store
from services.ai_service import AIService
from services.storage import ArtifactStore

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(
    settings: Settings = Depends(get_settings),
    ai: AIService = Depends(get_ai_service),
    store: ArtifactStore = Depends(get_artifact_store),
) -> HealthResponse:
    predictor = get_predictor()
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        ai_enabled=settings.ai_enabled,
        ai_provider=ai.provider_name,
        artifact_store=store.name,
        ml_loaded=predictor.available,
        model_version=predictor.version,
        model_metrics=predictor.metrics,
    )
