"""Recommendations must be impact-ranked and quantified."""

from services.career_service import CareerService
from services.recommendation_service import RecommendationService
from services.scoring_service import ScoringService
from ml.synthesize import archetype_profiles


def _build(tier: str):
    p = archetype_profiles()[tier]
    scoring = ScoringService(predictor=None)
    scores = scoring.score(p)
    career = CareerService().predict(p)
    return RecommendationService().build(p, scores, career)


def test_recommendations_sorted_by_impact_desc():
    _, _, recs = _build("weak")
    impacts = [r.impact_points or 0 for r in recs]
    assert impacts == sorted(impacts, reverse=True)


def test_recommendations_have_quantified_impact_in_text():
    _, _, recs = _build("weak")
    top = recs[0]
    assert top.impact_points and top.impact_points > 0
    assert "pts" in top.content


def test_weak_profile_gets_actionable_recommendations():
    strengths, weaknesses, recs = _build("weak")
    assert recs and strengths and weaknesses


def test_elite_profile_has_little_to_improve():
    _, _, recs = _build("elite")
    # An elite profile should have small or no high-impact gaps.
    assert max((r.impact_points or 0) for r in recs) <= 8


def test_recommendations_carry_concrete_examples():
    _, _, recs = _build("weak")
    # The top recommendations should be precise — each with a worked example.
    assert any(r.example for r in recs)


def test_weak_profile_flags_unquantified_writing():
    _, _, recs = _build("weak")
    # A weak profile with little quantified impact should be told to add metrics.
    assert any("Quantify" in r.content for r in recs)
