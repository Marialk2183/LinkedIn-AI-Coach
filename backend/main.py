"""Application entry point — assembles the FastAPI app."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from database import Base, engine
from models import orm  # noqa: F401  (register ORM models on Base before create_all)
from routes import build_api_router, health

logging.basicConfig(level=logging.INFO)


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="AI-powered LinkedIn profile analysis, scoring, and coaching.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Create tables (dev convenience; use Alembic migrations in production).
    Base.metadata.create_all(bind=engine)

    app.include_router(health.router)
    app.include_router(build_api_router(settings.api_prefix))

    @app.get("/", include_in_schema=False)
    def root() -> dict:
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "analyze": f"POST {settings.api_prefix}/analyze",
        }

    return app


app = create_app()
