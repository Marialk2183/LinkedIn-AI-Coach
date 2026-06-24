"""Orchestrates the full analysis pipeline and persistence.

parse -> score -> recommend -> predict careers -> AI writing -> persist -> map
to the API response. This is the only service the routes talk to for /analyze.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from models import orm
from models.domain import ScoreResult
from models.schemas import (
    AIWritingSchema,
    AnalysisResponse,
    CareerMatchSchema,
    MetricBreakdown,
    ParsedSummary,
    RecommendationSchema,
    ScoresSchema,
)
from services.ai_service import AIService
from services.career_service import CareerService
from services.recommendation_service import RecommendationService
from services.scoring_service import ScoringService
from utils.parser import parse_profile


class AnalysisService:
    def __init__(
        self,
        scoring: ScoringService,
        recommender: RecommendationService,
        career: CareerService,
        ai: AIService,
    ) -> None:
        self._scoring = scoring
        self._recommender = recommender
        self._career = career
        self._ai = ai

    def analyze(
        self, db: Session, *, source_type: str, profile_text: str | None
    ) -> AnalysisResponse:
        text = (profile_text or "").strip()
        if not text:
            raise ValueError(
                "Profile text is required. Direct URL analysis is not available "
                "(LinkedIn prohibits scraping) — paste your profile content instead."
            )

        # --- pipeline (pure) ---
        parsed = parse_profile(text, source_type)
        scores = self._scoring.score(parsed)
        career = self._career.predict(parsed)
        strengths, weaknesses, recs = self._recommender.build(parsed, scores, career)

        top_role = career[0].role if career else None
        headline, h_ai = self._ai.improve_headline(
            parsed.headline, parsed.technical_skills or parsed.skills, top_role
        )
        about, a_ai = self._ai.improve_about(
            parsed.name, parsed.headline, parsed.technical_skills or parsed.skills,
            parsed.experience_years, top_role, parsed.about,
        )

        # --- persist ---
        profile_row = orm.Profile(
            source_type=source_type,
            raw_text=text,
            name=parsed.name,
            headline=parsed.headline,
            parsed_json=self._parsed_summary(parsed).model_dump(),
        )
        analysis_row = orm.Analysis(
            overall=scores.overall,
            completeness=scores.completeness,
            technical=scores.technical,
            recruiter=scores.recruiter,
            networking=scores.networking,
            career_readiness=scores.career_readiness,
            breakdown_json=scores.breakdown,
            ml_used=scores.ml_used,
        )
        analysis_row.profile = profile_row
        analysis_row.recommendations = (
            [orm.Recommendation(category="strength", content=s) for s in strengths]
            + [orm.Recommendation(category="weakness", content=w) for w in weaknesses]
            + [orm.Recommendation(category=r.category, content=r.content) for r in recs]
        )
        analysis_row.career_predictions = [
            orm.CareerPrediction(role=m.role, match_pct=m.match_pct) for m in career
        ]
        analysis_row.ai_outputs = [
            orm.AiOutput(kind="headline", content=headline),
            orm.AiOutput(kind="about", content=about),
        ]
        db.add(analysis_row)
        db.commit()
        db.refresh(analysis_row)

        # --- map to response ---
        return AnalysisResponse(
            analysis_id=analysis_row.id,
            source_type=source_type,  # type: ignore[arg-type]
            scores=ScoresSchema(
                overall=scores.overall,
                completeness=scores.completeness,
                technical=scores.technical,
                recruiter=scores.recruiter,
                networking=scores.networking,
                career_readiness=scores.career_readiness,
                ats=scores.ats,
                leadership=scores.leadership,
            ),
            breakdown=self._breakdown(scores),
            ml_used=scores.ml_used,
            parsed=self._parsed_summary(parsed),
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=[
                RecommendationSchema(
                    category=r.category, content=r.content,
                    impact_points=r.impact_points, example=r.example,
                )
                for r in recs
            ],
            career_predictions=[
                CareerMatchSchema(
                    role=m.role, match_pct=m.match_pct,
                    matched_skills=m.matched_skills, missing_skills=m.missing_skills,
                )
                for m in career
            ],
            ai_writing=AIWritingSchema(
                headline=headline, about=about, ai_generated=bool(h_ai or a_ai)
            ),
        )

    # ------------------------------------------------------------------ #
    @staticmethod
    def _breakdown(scores: ScoreResult) -> dict[str, MetricBreakdown]:
        out: dict[str, MetricBreakdown] = {}
        for metric, data in scores.breakdown.items():
            comps = {k: round(float(v), 1) for k, v in data.items() if k != "score"}
            out[metric] = MetricBreakdown(score=int(data["score"]), components=comps)
        return out

    @staticmethod
    def _parsed_summary(parsed) -> ParsedSummary:
        return ParsedSummary(
            name=parsed.name,
            headline=parsed.headline,
            skills_count=parsed.skills_count,
            certifications_count=parsed.certifications_count,
            projects_count=parsed.projects_count,
            experience_years=round(parsed.experience_years, 1),
            connections=parsed.connections,
            followers=parsed.followers,
        )
