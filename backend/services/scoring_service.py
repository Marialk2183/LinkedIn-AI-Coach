"""Computes the six dashboard scores from a parsed profile.

Every score is a transparent, weighted blend of named components (returned in
the breakdown) so the dashboard can explain *why* a score is what it is. The
overall score optionally blends in the ML prediction when the model is loaded.
"""

from __future__ import annotations

from ml.features import extract_features
from ml.predictor import ProfileScorePredictor
from models.domain import ParsedProfile, ScoreResult
from utils import text as T
from utils.constants import (
    LEADERSHIP_SKILLS,
    LEADERSHIP_TERMS,
    ROLE_KEYWORDS,
    SENIORITY_KEYWORDS,
    TECHNICAL_SKILLS,
)


def _clamp(v: float) -> int:
    return int(max(0, min(100, round(v))))


def _ratio(value: float, target: float) -> float:
    """0..100 saturating ratio."""
    return min(1.0, value / target) * 100 if target else 0.0


class ScoringService:
    def __init__(self, predictor: ProfileScorePredictor | None = None) -> None:
        self._predictor = predictor

    def score(self, p: ParsedProfile) -> ScoreResult:
        completeness, c_comp = self._completeness(p)
        technical, t_comp = self._technical(p)
        recruiter, r_comp = self._recruiter(p)
        networking, n_comp = self._networking(p)
        readiness, ready_comp = self._career_readiness(p, technical, completeness)
        ats, ats_comp = self._ats(p, completeness)
        leadership, lead_comp = self._leadership(p)

        # Overall keeps its original 5-dimension rule blend (and ML blend) so the
        # calibrated bands stay stable; ATS/Leadership are reported, not folded in.
        rule_overall = (
            completeness * 0.20
            + technical * 0.25
            + recruiter * 0.25
            + networking * 0.15
            + readiness * 0.15
        )

        ml_used = False
        overall = rule_overall
        if self._predictor and self._predictor.available:
            ml_pred = self._predictor.predict(extract_features(p))
            if ml_pred is not None:
                overall = 0.5 * rule_overall + 0.5 * ml_pred
                ml_used = True

        breakdown = {
            "completeness": {"score": completeness, **c_comp},
            "technical": {"score": technical, **t_comp},
            "recruiter": {"score": recruiter, **r_comp},
            "networking": {"score": networking, **n_comp},
            "career_readiness": {"score": readiness, **ready_comp},
            "ats": {"score": ats, **ats_comp},
            "leadership": {"score": leadership, **lead_comp},
        }
        return ScoreResult(
            overall=_clamp(overall),
            completeness=completeness,
            technical=technical,
            recruiter=recruiter,
            networking=networking,
            career_readiness=readiness,
            ats=ats,
            leadership=leadership,
            breakdown=breakdown,
            ml_used=ml_used,
        )

    # ------------------------------------------------------------------ #
    def _completeness(self, p: ParsedProfile) -> tuple[int, dict]:
        comp = {
            "headline": 100.0 if p.headline.strip() else 0.0,
            "about": _ratio(p.about_length, 120),
            "experience": _ratio(p.experience_count, 3),
            "education": 100.0 if p.education_count else 0.0,
            "certifications": _ratio(p.certifications_count, 3),
            "projects": _ratio(p.projects_count, 3),
            "skills": _ratio(p.skills_count, 10),
        }
        weights = {
            "headline": 0.15, "about": 0.22, "experience": 0.20, "education": 0.10,
            "certifications": 0.11, "projects": 0.12, "skills": 0.10,
        }
        score = sum(comp[k] * weights[k] for k in comp)
        return _clamp(score), comp

    def _technical(self, p: ParsedProfile) -> tuple[int, dict]:
        comp = {
            "technical_skills": _ratio(len(p.technical_skills), 6),
            "projects": _ratio(p.projects_count, 3),
            "certifications": _ratio(p.certifications_count, 3),
            "experience": _ratio(p.experience_years, 5),
        }
        weights = {"technical_skills": 0.45, "projects": 0.25, "certifications": 0.10, "experience": 0.20}
        score = sum(comp[k] * weights[k] for k in comp)
        return _clamp(score), comp

    def _recruiter(self, p: ParsedProfile) -> tuple[int, dict]:
        headline_q = min(1.0, p.headline_length / 10) * 100
        # bonus if headline contains a role/skill keyword
        if any(s in p.headline.lower() for s in TECHNICAL_SKILLS):
            headline_q = min(100.0, headline_q + 15)
        comp = {
            "headline_quality": headline_q,
            "about_quality": _ratio(p.about_length, 150),
            "skill_relevance": _ratio(len(p.technical_skills), 8),
            "experience_quality": _ratio(p.experience_count, 3) * 0.6 + _ratio(p.experience_years, 5) * 0.4,
        }
        weights = {"headline_quality": 0.30, "about_quality": 0.25, "skill_relevance": 0.25, "experience_quality": 0.20}
        score = sum(comp[k] * weights[k] for k in comp)
        return _clamp(score), comp

    def _networking(self, p: ParsedProfile) -> tuple[int, dict]:
        # Activity is a smooth, always-available proxy; explicit connection /
        # follower counts (when present in the pasted text) add real reach on top.
        activity = (
            _ratio(p.about_length, 150) * 0.40
            + _ratio(p.experience_count, 3) * 0.30
            + _ratio(p.skills_count, 8) * 0.30
        )
        conn = _ratio(p.connections or 0, 500) if p.connections is not None else None
        foll = _ratio(p.followers or 0, 1500) if p.followers is not None else None
        if conn is None and foll is None:
            comp = {"connections": 0.0, "followers": 0.0, "activity_indicators": activity}
            score = activity * 0.70  # inferred-only networking is capped
        else:
            comp = {
                "connections": conn or 0.0,
                "followers": foll or 0.0,
                "activity_indicators": activity,
            }
            score = comp["connections"] * 0.45 + comp["followers"] * 0.15 + activity * 0.40
        return _clamp(score), comp

    def _career_readiness(self, p: ParsedProfile, technical: int, completeness: int) -> tuple[int, dict]:
        comp = {
            "technical_depth": float(technical),
            "experience": _ratio(p.experience_years, 4),
            "credentials": _ratio(p.certifications_count + p.projects_count, 5),
            "profile_completeness": float(completeness),
        }
        weights = {"technical_depth": 0.35, "experience": 0.25, "credentials": 0.20, "profile_completeness": 0.20}
        score = sum(comp[k] * weights[k] for k in comp)
        return _clamp(score), comp

    def _ats(self, p: ParsedProfile, completeness: int) -> tuple[int, dict]:
        """Applicant-Tracking-System readiness: parseable structure + keywords.

        An ATS ranks profiles on recognizable sections and role-relevant
        keywords, so this rewards a complete structure, breadth of searchable
        skills, a role-keyworded headline, and quantified, parseable impact.
        """
        achievement_text = " ".join([p.about, *p.experiences, *p.projects])
        role_kw = 100.0 if T.count_keyword_hits(p.headline, ROLE_KEYWORDS) else 0.0
        comp = {
            "section_structure": float(completeness),
            "keyword_coverage": _ratio(p.skills_count, 12),
            "technical_keywords": _ratio(len(p.technical_skills), 8),
            "headline_role_keyword": role_kw,
            "quantified_impact": _ratio(T.count_quantified_metrics(achievement_text), 4),
        }
        weights = {
            "section_structure": 0.30, "keyword_coverage": 0.25,
            "technical_keywords": 0.20, "headline_role_keyword": 0.15,
            "quantified_impact": 0.10,
        }
        score = sum(comp[k] * weights[k] for k in comp)
        return _clamp(score), comp

    def _leadership(self, p: ParsedProfile) -> tuple[int, dict]:
        """Leadership/seniority signal from tenure, language, title, and skills."""
        text = " ".join([p.headline, p.about, *p.experiences, *p.projects])
        owned = {s.lower() for s in p.skills}
        seniority = 100.0 if T.count_keyword_hits(p.headline, SENIORITY_KEYWORDS) else 0.0
        comp = {
            "experience_seniority": _ratio(p.experience_years, 8),
            "leadership_language": _ratio(T.count_keyword_hits(text, LEADERSHIP_TERMS), 4),
            "seniority_title": seniority,
            "leadership_skills": _ratio(len(owned & LEADERSHIP_SKILLS), 2),
        }
        weights = {
            "experience_seniority": 0.35, "leadership_language": 0.30,
            "seniority_title": 0.20, "leadership_skills": 0.15,
        }
        score = sum(comp[k] * weights[k] for k in comp)
        return _clamp(score), comp
