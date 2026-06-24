from fastapi import APIRouter

from . import analyze, assistant, career, health, sources


def build_api_router(prefix: str) -> APIRouter:
    """Aggregate all versioned routers under the API prefix."""
    api = APIRouter(prefix=prefix)
    api.include_router(analyze.router)
    api.include_router(assistant.router)
    api.include_router(career.router)
    api.include_router(sources.router)
    return api


__all__ = ["build_api_router", "health"]
