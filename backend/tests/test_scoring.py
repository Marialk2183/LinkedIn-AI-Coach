"""Dimension scores must order tiers correctly and stay monotonic."""

from ml.synthesize import archetype_profiles
from services.scoring_service import ScoringService

TIERS = ["empty", "weak", "average", "strong", "elite"]
DIMENSIONS = ["overall", "completeness", "technical", "recruiter",
              "networking", "career_readiness"]


def _scores_by_tier():
    svc = ScoringService(predictor=None)  # rule-only -> deterministic
    profiles = archetype_profiles()
    return {t: svc.score(profiles[t]) for t in TIERS}


def test_overall_increases_across_tiers():
    by = _scores_by_tier()
    overalls = [by[t].overall for t in TIERS]
    assert all(b > a for a, b in zip(overalls, overalls[1:])), overalls


def test_every_dimension_non_decreasing_across_tiers():
    by = _scores_by_tier()
    for dim in DIMENSIONS:
        seq = [getattr(by[t], dim) for t in TIERS]
        assert all(b >= a for a, b in zip(seq, seq[1:])), f"{dim}: {seq}"


def test_scores_are_bounded():
    by = _scores_by_tier()
    for t in TIERS:
        for dim in DIMENSIONS:
            v = getattr(by[t], dim)
            assert 0 <= v <= 100


def test_strong_and_elite_are_high_average_is_mid():
    by = _scores_by_tier()
    assert by["average"].overall >= 50
    assert by["strong"].overall >= 70
    assert by["elite"].overall >= 85
