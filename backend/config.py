"""Application configuration (env-driven, single source of truth)."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "LinkedIn AI Coach API"
    app_version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    debug: bool = False

    # AI (Gemini)
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-flash-latest", alias="GEMINI_MODEL")

    # Database
    database_url: str = Field(
        default="sqlite:///./linkedin_coach.db", alias="DATABASE_URL"
    )

    # ML
    ml_model_path: str = Field(default="ml/model.pkl", alias="ML_MODEL_PATH")

    # CORS — NoDecode so a comma-separated env value isn't JSON-parsed; the
    # validator below splits it into a list.
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
        alias="CORS_ORIGINS",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split(cls, v: object) -> object:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @property
    def ai_enabled(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def model_abs_path(self) -> Path:
        p = Path(self.ml_model_path)
        return p if p.is_absolute() else BASE_DIR / p


@lru_cache
def get_settings() -> Settings:
    return Settings()
