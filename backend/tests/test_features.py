"""Feature extraction: shape, determinism, and signal correctness."""

from ml.features import FEATURE_ORDER, extract_features, features_vector
from ml.synthesize import archetype_profiles
from utils.parser import parse_profile


def test_feature_vector_shape_and_order():
    p = parse_profile("Jordan Taylor\nData Scientist | Python")
    feats = extract_features(p)
    assert set(feats) == set(FEATURE_ORDER)
    assert len(features_vector(feats)) == len(FEATURE_ORDER) == 16


def test_extraction_is_deterministic():
    text = archetype_profiles()["strong"].raw_text
    a = features_vector(extract_features(parse_profile(text)))
    b = features_vector(extract_features(parse_profile(text)))
    assert a == b


def test_quantified_and_action_signals_detected():
    p = parse_profile(
        "Jordan Taylor\nEngineer\n\nExperience\nEngineer 2020 - Present\n"
        "- Led work that improved revenue by 20% and saved $1.2M"
    )
    f = extract_features(p)
    assert f["quantified_metrics_count"] >= 2  # 20% and $1.2M
    assert f["action_verb_count"] >= 1          # "led"


def test_role_keyword_and_alignment():
    p = parse_profile(
        "Jordan Taylor\nData Scientist | ML\n\nSkills\n"
        "python, machine learning, statistics, pandas, scikit-learn, sql"
    )
    f = extract_features(p)
    assert f["headline_has_role_keyword"] == 1.0
    assert f["role_skill_alignment"] >= 0.8  # matches Data Scientist core well
