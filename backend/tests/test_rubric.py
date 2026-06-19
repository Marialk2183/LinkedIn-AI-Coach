"""The rubric must be monotonic and land archetypes in recruiter-realistic bands."""

from dataclasses import replace

import pytest

from ml.rubric import rubric_overall
from ml.synthesize import archetype_profiles
from utils.parser import parse_profile

# (tier, low, high) recruiter-realistic bands. `empty` is allowed to sit at the
# rubric floor since a name-only profile genuinely carries no signal.
BANDS = [
    ("empty", 10, 25),
    ("weak", 30, 45),
    ("average", 52, 68),
    ("strong", 72, 85),
    ("elite", 86, 96),
]


@pytest.mark.parametrize("tier,low,high", BANDS)
def test_archetypes_in_band(tier, low, high):
    score = rubric_overall(archetype_profiles()[tier])
    assert low <= score <= high, f"{tier}={score} outside [{low},{high}]"


def test_archetypes_strictly_increasing():
    profiles = archetype_profiles()
    scores = [rubric_overall(profiles[t]) for t, _, _ in BANDS]
    assert scores == sorted(scores)
    assert all(b > a for a, b in zip(scores, scores[1:]))


def test_adding_skills_never_lowers_score():
    p = parse_profile("Jordan Taylor\nData Analyst\n\nSkills\nsql, excel")
    before = rubric_overall(p)
    after = rubric_overall(replace(p, skills=p.skills + ["python", "tableau", "pandas"]))
    assert after >= before


def test_expanding_about_never_lowers_score():
    p = parse_profile("Jordan Taylor\nEngineer\n\nAbout\nShort bio.")
    before = rubric_overall(p)
    after = rubric_overall(replace(p, about="word " * 150))
    assert after >= before
