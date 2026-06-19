"""Feature extraction for the profile-score model.

This is the single source of truth for the model's inputs: both training
(`ml/train.py`) and serving (`services/scoring_service.py`) call `extract_features`,
so the trained model and the runtime extractor can never drift.

Features go beyond raw section sizes to capture *quality* signals a recruiter
cares about — quantified achievements, action-verb density, role-keyword presence,
and how well the skill set aligns with a known target role.
"""

from models.domain import ParsedProfile
from utils import text as T
from utils.constants import ROLE_DEFINITIONS, ROLE_KEYWORDS

FEATURE_ORDER: list[str] = [
    "headline_length",
    "about_length",
    "skills_count",
    "technical_skills_count",
    "soft_skills_count",
    "certifications_count",
    "projects_count",
    "experience_count",
    "education_count",
    "experience_years",
    "connections",
    "followers",
    "quantified_metrics_count",
    "action_verb_count",
    "headline_has_role_keyword",
    "role_skill_alignment",
]


def _role_skill_alignment(profile: ParsedProfile) -> float:
    """Best core-skill coverage across all known roles, in [0, 1].

    Mirrors the core-coverage term in CareerService so the feature reflects the
    same notion of "fit for a real role" the career predictor reports.
    """
    owned = {s.lower() for s in profile.skills}
    best = 0.0
    for spec in ROLE_DEFINITIONS.values():
        core = spec["core"]
        if not core:
            continue
        cov = len([s for s in core if s in owned]) / len(core)
        best = max(best, cov)
    return best


def _headline_has_role_keyword(headline: str) -> float:
    h = headline.lower()
    return 1.0 if any(kw in h for kw in ROLE_KEYWORDS) else 0.0


def extract_features(profile: ParsedProfile) -> dict[str, float]:
    achievement_text = " ".join([profile.about, *profile.experiences, *profile.projects])
    return {
        "headline_length": float(profile.headline_length),
        "about_length": float(profile.about_length),
        "skills_count": float(profile.skills_count),
        "technical_skills_count": float(len(profile.technical_skills)),
        "soft_skills_count": float(profile.skills_count - len(profile.technical_skills)),
        "certifications_count": float(profile.certifications_count),
        "projects_count": float(profile.projects_count),
        "experience_count": float(profile.experience_count),
        "education_count": float(profile.education_count),
        "experience_years": float(profile.experience_years),
        "connections": float(profile.connections or 0),
        "followers": float(profile.followers or 0),
        "quantified_metrics_count": float(T.count_quantified_metrics(achievement_text)),
        "action_verb_count": float(T.count_action_verbs(achievement_text)),
        "headline_has_role_keyword": _headline_has_role_keyword(profile.headline),
        "role_skill_alignment": _role_skill_alignment(profile),
    }


def features_vector(features: dict[str, float]) -> list[float]:
    """Order a feature dict into the model's expected input vector."""
    return [features[name] for name in FEATURE_ORDER]
