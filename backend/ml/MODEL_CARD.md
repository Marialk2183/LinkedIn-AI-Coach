# Model Card — Profile Score Model

## Overview
A `RandomForestRegressor` that predicts a LinkedIn profile's **overall score
(0–100)** from 16 engineered features. At serving time its prediction is blended
50/50 with the transparent rule-based overall (`services/scoring_service.py`).

- **Version:** 2
- **Algorithm:** scikit-learn `RandomForestRegressor` (300 trees, max_depth 14)
- **Artifact:** `ml/model.pkl` (bundles model + `feature_order` + metrics + `trained_at`)
- **Retrain:** `python -m ml.train` (from `backend/`)

## Intended use
Give users directional, explainable feedback on profile strength and the
highest-impact improvements. **Not** an authoritative or official LinkedIn score.

## Training data
Synthetic. LinkedIn's Terms of Service prohibit scraping, so there is no corpus
of real, human-rated profiles. We generate realistic profile **text** across the
quality spectrum (`ml/synthesize.py`), each with a latent quality `q` plus
independent per-section noise so features are correlated but not degenerate. Every
sample is run through the **real parser and feature extractor**, so the model is
trained on exactly the inputs it sees in production.

- Samples: 6,000
- Labels: the rubric in `ml/rubric.py` (LinkedIn All-Star completeness + recruiter
  heuristics), plus small gaussian jitter to model rater noise.

## Features (16)
headline_length, about_length, skills_count, technical_skills_count,
soft_skills_count, certifications_count, projects_count, experience_count,
education_count, experience_years, connections, followers,
quantified_metrics_count, action_verb_count, headline_has_role_keyword,
role_skill_alignment.

## Metrics (5-fold cross-validated)
- CV MAE ≈ 2.3 points · CV R² ≈ 0.98 · Holdout MAE ≈ 2.4

Archetype calibration (rubric label vs prediction), recruiter-realistic bands:

| tier | label | pred |
|---|---|---|
| empty | 14 | 14 |
| weak | 36 | 38 |
| average | 57 | 60 |
| strong | 76 | 75 |
| elite | 91 | 89 |

## Limitations
- The model learns a **defined rubric**, not real recruiter outcomes; "accuracy"
  means faithful, well-calibrated alignment to that rubric, not to hiring success.
- Quality is bounded by the rubric's assumptions and by the text parser (analysis
  runs only on pasted text — no scraping).
- To incorporate real signal later, replace the synthetic labels in
  `ml/train.py` with a labeled dataset (or LLM-as-judge labels) and retrain; the
  feature pipeline and serving path stay unchanged.
