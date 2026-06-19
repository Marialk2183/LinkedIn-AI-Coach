"""Train the profile-score model.

Pipeline (no real LinkedIn data needed — see ml/rubric.py for why):

    synthesize realistic profile text  (ml/synthesize.py)
        -> parse_profile               (the real runtime parser)
        -> extract_features            (the real runtime extractor, 16 features)
        -> rubric_overall label        (ml/rubric.py, the "teacher")
        -> RandomForestRegressor

Training on the real parser + extractor guarantees the served model sees exactly
the features it was trained on. The RF generalizes the rubric smoothly over the
rich feature space, so at serving time it contributes signal the simple
rule-based blend lacks (quantified achievements, action verbs, role alignment).

Run:  python -m ml.train      (from the backend/ directory)
"""

from __future__ import annotations

import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import KFold, cross_val_predict, train_test_split

# Allow running as a script (python ml/train.py) or module (python -m ml.train).
sys.path.append(str(Path(__file__).resolve().parent.parent))

from config import get_settings  # noqa: E402
from ml.features import FEATURE_ORDER, extract_features, features_vector  # noqa: E402
from ml.rubric import rubric_overall  # noqa: E402
from ml.synthesize import TIERS, archetype_profiles, generate_profiles  # noqa: E402

MODEL_VERSION = 2
RNG = np.random.default_rng(42)


def build_dataset(n: int) -> tuple[np.ndarray, np.ndarray]:
    """Return (X, y): features and jittered rubric labels for n synthetic profiles."""
    samples = generate_profiles(n)
    X = np.array([features_vector(extract_features(s.profile)) for s in samples], dtype=float)
    y_true = np.array([rubric_overall(s.profile) for s in samples], dtype=float)
    # Small human-rating jitter so the model learns the trend, not the exact formula.
    y = np.clip(y_true + RNG.normal(0, 2.0, len(y_true)), 0, 100)
    return X, y


def _archetype_calibration(model: RandomForestRegressor) -> dict:
    """Score the fixed per-tier archetypes: rubric label vs model prediction."""
    out: dict[str, dict] = {}
    for tier, profile in archetype_profiles().items():
        vec = features_vector(extract_features(profile))
        out[tier] = {
            "label": round(rubric_overall(profile), 1),
            "pred": round(float(model.predict([vec])[0]), 1),
        }
    return out


def train_and_save(n: int = 6000) -> Path:
    settings = get_settings()
    X, y = build_dataset(n)

    model = RandomForestRegressor(
        n_estimators=300, max_depth=14, min_samples_leaf=3, random_state=42, n_jobs=-1
    )

    # Honest generalization estimate: 5-fold cross-validated predictions.
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    cv_pred = cross_val_predict(model, X, y, cv=kf, n_jobs=-1)
    cv_mae = mean_absolute_error(y, cv_pred)
    cv_r2 = r2_score(y, cv_pred)

    # Held-out check, then fit the final model on everything.
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)
    model.fit(X_tr, y_tr)
    holdout_mae = mean_absolute_error(y_te, model.predict(X_te))
    model.fit(X, y)

    calib = _archetype_calibration(model)

    print(f"Trained RandomForestRegressor on {len(X)} synthetic profiles "
          f"({len(FEATURE_ORDER)} features)")
    print(f"  CV MAE      : {cv_mae:.2f}")
    print(f"  CV R^2      : {cv_r2:.3f}")
    print(f"  Holdout MAE : {holdout_mae:.2f}")
    print("  Archetype calibration (rubric label vs model prediction):")
    print(f"    {'tier':8} {'label':>7} {'pred':>7}")
    for t in TIERS:
        if t in calib:
            c = calib[t]
            print(f"    {t:8} {c['label']:7.1f} {c['pred']:7.1f}")
    print("  Top feature importances:")
    order = np.argsort(model.feature_importances_)[::-1]
    for i in order[:8]:
        print(f"    {FEATURE_ORDER[i]:26} {model.feature_importances_[i]:.3f}")

    bundle = {
        "model": model,
        "feature_order": FEATURE_ORDER,
        "version": MODEL_VERSION,
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_samples": len(X),
        "metrics": {
            "cv_mae": round(float(cv_mae), 3),
            "cv_r2": round(float(cv_r2), 3),
            "holdout_mae": round(float(holdout_mae), 3),
        },
        "calibration": calib,
    }
    out = settings.model_abs_path
    out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, out)
    print(f"Saved model v{MODEL_VERSION} -> {out}")
    return out


if __name__ == "__main__":
    train_and_save()
