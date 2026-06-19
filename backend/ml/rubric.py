"""The scoring rubric — the ML model's *teacher*.

Because LinkedIn's ToS forbids scraping, there is no corpus of real, human-rated
profiles to learn from. Instead we encode a transparent, defensible rubric drawn
from LinkedIn's own "All-Star" completeness pillars plus well-known recruiter
heuristics (role-keyword searchability, quantified achievements, skill relevance).

`rubric_overall` produces the ground-truth label; `ml/train.py` fits a
RandomForest to approximate it over the richer feature set, so the served model
generalizes the rubric smoothly rather than reciting a brittle formula.

Calibration target (recruiter-realistic):
    empty ~15-25 · weak ~30-40 · average ~55-65 · strong ~75-85 · elite ~88-95

Every component is a saturating ratio in [0, 1] and contributes with a positive
weight, so the rubric is monotonic: improving any signal never lowers the score.
"""

from __future__ import annotations

from ml.features import extract_features
from models.domain import ParsedProfile

# --- calibration: maps raw weighted score (0..100) onto realistic bands ---
_FLOOR = 14.0
_SCALE = 0.80


def _sat(value: float, target: float) -> float:
    """Saturating ratio in [0, 1]; reaches 1.0 at `target`."""
    if target <= 0:
        return 0.0
    return min(1.0, max(0.0, value) / target)


def rubric_components(profile: ParsedProfile) -> dict[str, float]:
    """The named [0,1] components behind the rubric score (useful for tests/debug)."""
    f = extract_features(profile)

    headline = 0.0
    if profile.headline.strip():
        headline = 0.6 + (0.4 if f["headline_has_role_keyword"] else 0.0)

    experience = 0.5 * _sat(f["experience_count"], 3) + 0.5 * _sat(f["experience_years"], 8)
    skill_depth = 0.6 * f["role_skill_alignment"] + 0.4 * _sat(f["technical_skills_count"], 8)

    return {
        "headline": headline,
        "about": _sat(f["about_length"], 180),
        "experience": experience,
        "education": 1.0 if f["education_count"] else 0.0,
        "skills": _sat(f["skills_count"], 11),
        "skill_depth": skill_depth,
        "certifications": _sat(f["certifications_count"], 3),
        "projects": _sat(f["projects_count"], 3),
        "quantified": _sat(f["quantified_metrics_count"], 6),
        "writing": _sat(f["action_verb_count"], 6),
        "networking": _sat(f["connections"], 600),
    }


_WEIGHTS: dict[str, float] = {
    "headline": 0.10,
    "about": 0.14,
    "experience": 0.16,
    "education": 0.06,
    "skills": 0.10,
    "skill_depth": 0.12,
    "certifications": 0.07,
    "projects": 0.09,
    "quantified": 0.07,
    "writing": 0.04,
    "networking": 0.05,
}


def rubric_overall(profile: ParsedProfile) -> float:
    """Ground-truth overall profile score in [0, 100]."""
    comp = rubric_components(profile)
    raw = 100.0 * sum(comp[k] * _WEIGHTS[k] for k in _WEIGHTS)
    score = _FLOOR + _SCALE * raw
    return float(max(0.0, min(100.0, score)))
