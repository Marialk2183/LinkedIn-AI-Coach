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

    # AI provider selection: "auto" (Azure if configured, else Gemini), "gemini",
    # or "azure". Gemini stays the default and the universal fallback.
    ai_provider: str = Field(default="auto", alias="AI_PROVIDER")

    # AI (Gemini)
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-flash-latest", alias="GEMINI_MODEL")

    # AI (Azure OpenAI) — lights up only when endpoint + key + deployment are set.
    azure_openai_endpoint: str | None = Field(
        default=None, alias="AZURE_OPENAI_ENDPOINT"
    )
    azure_openai_api_key: str | None = Field(
        default=None, alias="AZURE_OPENAI_API_KEY"
    )
    azure_openai_deployment: str | None = Field(
        default=None, alias="AZURE_OPENAI_DEPLOYMENT"
    )
    azure_openai_api_version: str = Field(
        default="2024-10-21", alias="AZURE_OPENAI_API_VERSION"
    )

    # Artifact storage (generated PDF reports): "auto" (Azure Blob if configured,
    # else local filesystem), "local", or "azure_blob".
    artifact_store: str = Field(default="auto", alias="ARTIFACT_STORE")
    artifacts_dir: str = Field(default="var/artifacts", alias="ARTIFACTS_DIR")
    azure_blob_connection_string: str | None = Field(
        default=None, alias="AZURE_BLOB_CONNECTION_STRING"
    )
    azure_blob_container: str = Field(
        default="reports", alias="AZURE_BLOB_CONTAINER"
    )

    # Database
    database_url: str = Field(
        default="sqlite:///./linkedin_coach.db", alias="DATABASE_URL"
    )

    # ML
    ml_model_path: str = Field(default="ml/model.pkl", alias="ML_MODEL_PATH")

    # Compliant source fetching (GitHub API, portfolio sites, job postings).
    # No LinkedIn scraping — that path stays on the export-.zip / PDF upload.
    github_token: str | None = Field(default=None, alias="GITHUB_TOKEN")
    fetch_timeout_seconds: float = Field(default=10.0, alias="FETCH_TIMEOUT_SECONDS")
    fetch_max_bytes: int = Field(default=3 * 1024 * 1024, alias="FETCH_MAX_BYTES")
    fetch_user_agent: str = Field(
        default="LinkedInAICoach/1.0 (+compliant-fetch)", alias="FETCH_USER_AGENT"
    )

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
    def gemini_enabled(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def azure_openai_enabled(self) -> bool:
        return bool(
            self.azure_openai_endpoint
            and self.azure_openai_api_key
            and self.azure_openai_deployment
        )

    @property
    def ai_enabled(self) -> bool:
        return self.gemini_enabled or self.azure_openai_enabled

    @property
    def azure_blob_enabled(self) -> bool:
        return bool(self.azure_blob_connection_string)

    @property
    def model_abs_path(self) -> Path:
        p = Path(self.ml_model_path)
        return p if p.is_absolute() else BASE_DIR / p

    @property
    def artifacts_abs_dir(self) -> Path:
        p = Path(self.artifacts_dir)
        return p if p.is_absolute() else BASE_DIR / p


@lru_cache
def get_settings() -> Settings:
    return Settings()
