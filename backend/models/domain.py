"""Internal domain models (dataclasses) passed between services.

Decoupled from both the ORM and the API schemas so business logic never imports
the framework or the persistence layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ParsedProfile:
    """Normalized profile extracted from raw text."""

    name: str | None = None
    headline: str = ""
    about: str = ""
    experiences: list[str] = field(default_factory=list)
    education: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    projects: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    technical_skills: list[str] = field(default_factory=list)
    experience_years: float = 0.0
    connections: int | None = None
    followers: int | None = None
    raw_text: str = ""

    # --- convenience metrics used by scoring + ML ---
    @property
    def headline_length(self) -> int:
        return len(self.headline.split())

    @property
    def about_length(self) -> int:
        return len(self.about.split())

    @property
    def skills_count(self) -> int:
        return len(self.skills)

    @property
    def certifications_count(self) -> int:
        return len(self.certifications)

    @property
    def projects_count(self) -> int:
        return len(self.projects)

    @property
    def experience_count(self) -> int:
        return len(self.experiences)

    @property
    def education_count(self) -> int:
        return len(self.education)


@dataclass
class ScoreResult:
    """The six headline scores plus a transparent per-metric breakdown."""

    overall: int
    completeness: int
    technical: int
    recruiter: int
    networking: int
    career_readiness: int
    breakdown: dict[str, dict[str, float]] = field(default_factory=dict)
    ml_used: bool = False


@dataclass
class RecommendationItem:
    category: str  # strength | weakness | missing_skill | missing_certification | ...
    content: str
    impact_points: int | None = None  # estimated gain to the overall score
    example: str | None = None  # a concrete, copy-pasteable illustration of the fix


@dataclass
class CareerMatch:
    role: str
    match_pct: float
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
