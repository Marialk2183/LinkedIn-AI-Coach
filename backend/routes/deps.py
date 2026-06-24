"""Service graph construction (composition root for the API layer)."""

from functools import lru_cache

from config import Settings, get_settings
from ml.predictor import get_predictor
from services.ai_service import AIService
from services.analysis_service import AnalysisService
from services.career_service import CareerService
from services.recommendation_service import RecommendationService
from services.scoring_service import ScoringService
from services.scrape_service import ScrapeService
from services.storage import ArtifactStore, build_store


@lru_cache
def _ai_service() -> AIService:
    return AIService(get_settings())


@lru_cache
def _career_service() -> CareerService:
    return CareerService()


@lru_cache
def _scoring_service() -> ScoringService:
    return ScoringService(predictor=get_predictor())


@lru_cache
def _scrape_service() -> ScrapeService:
    return ScrapeService(get_settings())


@lru_cache
def _artifact_store() -> ArtifactStore:
    return build_store(get_settings())


@lru_cache
def _analysis_service() -> AnalysisService:
    return AnalysisService(
        scoring=_scoring_service(),
        recommender=RecommendationService(),
        career=_career_service(),
        ai=_ai_service(),
    )


# FastAPI dependency callables ---------------------------------------------
def get_ai_service() -> AIService:
    return _ai_service()


def get_career_service() -> CareerService:
    return _career_service()


def get_analysis_service() -> AnalysisService:
    return _analysis_service()


def get_scrape_service() -> ScrapeService:
    return _scrape_service()


def get_artifact_store() -> ArtifactStore:
    return _artifact_store()


def settings_dep() -> Settings:
    return get_settings()
