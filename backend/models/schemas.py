"""Pydantic API request/response schemas (the wire contract)."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

SourceType = Literal["url", "text", "export"]


# ----------------------------- requests -----------------------------
class AnalyzeRequest(BaseModel):
    source_type: SourceType = "text"
    profile_url: str | None = Field(default=None, examples=["https://linkedin.com/in/jane"])
    profile_text: str | None = Field(default=None, description="Pasted profile content.")

    @model_validator(mode="after")
    def _require_payload(self) -> "AnalyzeRequest":
        if self.source_type == "url" and not (self.profile_url or "").strip():
            raise ValueError("profile_url is required when source_type='url'")
        if self.source_type in ("text", "export") and not (self.profile_text or "").strip():
            raise ValueError("profile_text is required when source_type='text'")
        return self


class HeadlineRequest(BaseModel):
    headline: str = Field(..., examples=["MCA Student"])
    skills: list[str] = Field(default_factory=list)
    target_role: str | None = None


class AboutRequest(BaseModel):
    name: str | None = None
    headline: str | None = None
    skills: list[str] = Field(default_factory=list)
    experience_years: float = 0.0
    target_role: str | None = None
    current_about: str | None = None


class CareerPredictRequest(BaseModel):
    profile_text: str = Field(..., description="Pasted profile content.")


FetchKind = Literal["github", "web"]


class FetchRequest(BaseModel):
    """Pull text from a compliant public source (never LinkedIn)."""

    url: str = Field(..., examples=["https://github.com/torvalds"])
    kind: FetchKind | None = Field(
        default=None, description="Force a source kind; otherwise auto-detected."
    )


# ----------------------------- responses -----------------------------
class MetricBreakdown(BaseModel):
    score: int
    components: dict[str, float] = Field(default_factory=dict)


class ScoresSchema(BaseModel):
    overall: int
    completeness: int
    technical: int
    recruiter: int
    networking: int
    career_readiness: int
    ats: int = 0
    leadership: int = 0


class RecommendationSchema(BaseModel):
    category: str
    content: str
    impact_points: int | None = None
    example: str | None = None


class CareerMatchSchema(BaseModel):
    role: str
    match_pct: float
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)


class AIWritingSchema(BaseModel):
    headline: str | None = None
    about: str | None = None
    ai_generated: bool = False


class ParsedSummary(BaseModel):
    name: str | None = None
    headline: str = ""
    skills_count: int = 0
    certifications_count: int = 0
    projects_count: int = 0
    experience_years: float = 0.0
    connections: int | None = None
    followers: int | None = None


class AnalysisResponse(BaseModel):
    analysis_id: int | None = None
    source_type: SourceType
    scores: ScoresSchema
    breakdown: dict[str, MetricBreakdown] = Field(default_factory=dict)
    ml_used: bool = False
    parsed: ParsedSummary
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommendations: list[RecommendationSchema] = Field(default_factory=list)
    career_predictions: list[CareerMatchSchema] = Field(default_factory=list)
    ai_writing: AIWritingSchema = Field(default_factory=AIWritingSchema)


class HeadlineResponse(BaseModel):
    headline: str
    ai_generated: bool = False


class AboutResponse(BaseModel):
    about: str
    ai_generated: bool = False


class FetchResponse(BaseModel):
    """Normalized text from a compliant source, ready to paste into /analyze."""

    url: str
    kind: FetchKind
    title: str
    text: str
    char_count: int
    metadata: dict[str, str | int | float] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str
    version: str
    ai_enabled: bool
    ai_provider: str = "fallback"  # gemini | azure | fallback
    artifact_store: str = "local"  # local | azure_blob
    ml_loaded: bool
    model_version: int | None = None
    model_metrics: dict[str, float] = Field(default_factory=dict)
