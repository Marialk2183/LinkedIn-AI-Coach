"""Application entry point — assembles the FastAPI app."""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config import get_settings
from database import Base, engine
from models import orm  # noqa: F401  (register ORM models on Base before create_all)
from routes import build_api_router, health

logging.basicConfig(level=logging.INFO)

# Built React app (frontend/dist) — present in a production build, absent in dev.
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


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

    # In production the API also serves the built frontend (single deployable
    # service). In dev (no dist/) the root returns a small JSON info payload.
    if FRONTEND_DIST.is_dir():
        _mount_frontend(app)
    else:
        @app.get("/", include_in_schema=False)
        def root() -> dict:
            return {
                "name": settings.app_name,
                "version": settings.app_version,
                "docs": "/docs",
                "analyze": f"POST {settings.api_prefix}/analyze",
            }

    return app


def _mount_frontend(app: FastAPI) -> None:
    """Serve the built SPA, falling back to index.html for client-side routes."""
    index = FRONTEND_DIST / "index.html"
    assets = FRONTEND_DIST / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    # Registered last, so real API/docs/health routes always match first; anything
    # else returns a static file if it exists, otherwise the SPA entry point.
    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str) -> FileResponse:
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index)


app = create_app()
