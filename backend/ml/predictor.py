"""Loads model.pkl and predicts the overall profile score.

Degrades gracefully: if the model file is missing or fails to load, `available`
is False and the scoring service falls back to the rule-based overall.
"""

from __future__ import annotations

import logging
from functools import lru_cache

import joblib

from config import get_settings
from ml.features import FEATURE_ORDER, features_vector

logger = logging.getLogger(__name__)


class ProfileScorePredictor:
    def __init__(self) -> None:
        self._model = None
        self._feature_order: list[str] = FEATURE_ORDER
        self.version: int | None = None
        self.metrics: dict = {}
        self.trained_at: str | None = None
        self._load()

    def _load(self) -> None:
        path = get_settings().model_abs_path
        if not path.exists():
            logger.warning("ML model not found at %s — using rule-based overall.", path)
            return
        try:
            bundle = joblib.load(path)
            self._model = bundle["model"]
            self._feature_order = bundle.get("feature_order", FEATURE_ORDER)
            self.version = bundle.get("version")
            self.metrics = bundle.get("metrics", {})
            self.trained_at = bundle.get("trained_at")
            # A model trained on a different feature set must not be trusted.
            if self._feature_order != FEATURE_ORDER:
                logger.error(
                    "Model feature order mismatch (expected %d features, got %d) — "
                    "ignoring stale model; retrain with `python -m ml.train`.",
                    len(FEATURE_ORDER), len(self._feature_order),
                )
                self._model = None
                return
            logger.info("Loaded ML model v%s from %s", self.version, path)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to load ML model; using rule-based overall.")
            self._model = None

    @property
    def available(self) -> bool:
        return self._model is not None

    def predict(self, features: dict[str, float]) -> float | None:
        if self._model is None:
            return None
        try:
            vector = [features[name] for name in self._feature_order]
            pred = float(self._model.predict([vector])[0])
            return max(0.0, min(100.0, pred))
        except Exception:  # noqa: BLE001
            logger.exception("ML prediction failed; falling back.")
            return None


@lru_cache
def get_predictor() -> ProfileScorePredictor:
    return ProfileScorePredictor()
