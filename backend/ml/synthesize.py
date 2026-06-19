"""Synthetic profile generator for training the score model.

Generates realistic LinkedIn profile *text* across five quality tiers and a set
of personas, then runs each through the real `parse_profile` so the training set
exercises the exact parser + feature extractor used at serving time (no drift).

Tiers control how much of each section is filled and how achievement-oriented the
writing is, producing a spread that maps onto the recruiter-realistic bands the
rubric is calibrated to.

Run nothing here directly — `ml/train.py` imports `generate_profiles`.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from models.domain import ParsedProfile
from utils.parser import parse_profile

TIERS = ["empty", "weak", "average", "strong", "elite"]

# A persona supplies role-coherent vocabulary so generated skills actually align
# with a known role (drives role_skill_alignment / skill_depth realistically).
PERSONAS: dict[str, dict[str, list[str]]] = {
    "Data Scientist": {
        "titles": ["Data Scientist", "Senior Data Scientist", "Lead Data Scientist"],
        "skills": ["python", "machine learning", "statistics", "pandas", "scikit-learn",
                   "sql", "deep learning", "nlp", "tensorflow", "pytorch",
                   "data visualization", "numpy"],
        "certs": ["AWS Certified Machine Learning", "TensorFlow Developer Certificate",
                  "Google Advanced Data Analytics"],
        "projects": ["Customer churn prediction model", "Product recommendation engine",
                     "NLP sentiment classifier", "Demand forecasting pipeline"],
    },
    "Data Analyst": {
        "titles": ["Data Analyst", "Senior Data Analyst", "Business Data Analyst"],
        "skills": ["sql", "excel", "data analysis", "data visualization", "statistics",
                   "python", "tableau", "power bi", "pandas"],
        "certs": ["Google Data Analytics", "Microsoft Power BI Data Analyst",
                  "Tableau Desktop Specialist"],
        "projects": ["Sales performance dashboard", "Marketing funnel analysis",
                     "KPI reporting automation"],
    },
    "AI Engineer": {
        "titles": ["AI Engineer", "Machine Learning Engineer", "Senior AI Engineer"],
        "skills": ["python", "deep learning", "tensorflow", "pytorch", "machine learning",
                   "nlp", "computer vision", "transformers", "llm", "docker"],
        "certs": ["AWS Certified Machine Learning", "DeepLearning.AI Specialization",
                  "NVIDIA Deep Learning Institute"],
        "projects": ["LLM-powered chatbot", "Image classification service",
                     "Real-time object detection system"],
    },
    "Software Developer": {
        "titles": ["Software Developer", "Software Engineer", "Senior Software Engineer"],
        "skills": ["java", "python", "javascript", "git", "rest api", "react",
                   "node.js", "docker", "sql", "typescript"],
        "certs": ["AWS Certified Developer", "Oracle Certified Professional Java",
                  "Microsoft Azure Developer Associate"],
        "projects": ["E-commerce checkout service", "Real-time chat application",
                     "Internal developer tooling platform"],
    },
    "Business Analyst": {
        "titles": ["Business Analyst", "Senior Business Analyst", "Product Analyst"],
        "skills": ["data analysis", "excel", "sql", "communication", "stakeholder management",
                   "power bi", "tableau", "agile", "project management"],
        "certs": ["CBAP", "PMI Professional in Business Analysis", "Scrum Master"],
        "projects": ["Requirements gathering for ERP rollout", "Process optimization study",
                     "Stakeholder reporting framework"],
    },
    "ML Engineer": {
        "titles": ["ML Engineer", "Machine Learning Engineer", "MLOps Engineer"],
        "skills": ["python", "machine learning", "docker", "sql", "scikit-learn",
                   "kubernetes", "aws", "airflow", "pytorch", "tensorflow", "ci/cd"],
        "certs": ["AWS Certified Machine Learning", "Kubernetes Administrator (CKA)",
                  "Google Cloud ML Engineer"],
        "projects": ["Model serving platform", "Feature store implementation",
                     "Automated retraining pipeline"],
    },
    "Student": {
        "titles": ["Computer Science Student", "Aspiring Data Scientist", "MCA Student"],
        "skills": ["python", "java", "sql", "git", "html", "css", "machine learning"],
        "certs": ["Coursera Machine Learning", "freeCodeCamp Responsive Web Design"],
        "projects": ["College capstone project", "Personal portfolio website",
                     "Kaggle competition entry"],
    },
}

_ACTION_VERBS = ["Led", "Built", "Designed", "Developed", "Implemented", "Optimized",
                 "Automated", "Delivered", "Scaled", "Improved", "Launched", "Drove"]
_OUTCOMES = ["accuracy", "revenue", "engagement", "throughput", "conversion",
             "latency", "retention", "efficiency", "cost savings"]
_SOFT = ["leadership", "communication", "teamwork", "problem solving", "agile"]

# Per-section maxima (value reached when that section's level == 1.0). Each
# section's level is the profile's latent quality `q` plus independent noise, so
# sections are correlated (coherent profiles) but not identical — no single
# feature can perfectly predict the rubric, which keeps the model robust.
_MAX = dict(about=240, skills=12, soft=4, exp=4, years=15, bullets=4, certs=3, projects=3)
_SECTION_NOISE = 0.24  # std-dev of independent per-section jitter on `q`

_ABOUT_SENTENCES = [
    "I am a results-driven professional passionate about building data products.",
    "I specialize in turning messy data into decisions that move the business.",
    "My focus is shipping reliable systems that scale with the organization.",
    "I enjoy collaborating across teams to deliver measurable outcomes.",
    "I have a track record of mentoring engineers and driving best practices.",
    "I care deeply about clean code, reproducibility, and clear communication.",
    "I thrive in fast-paced environments where I can own problems end to end.",
    "I combine strong technical depth with a pragmatic, product-minded approach.",
]


@dataclass
class Sample:
    profile: ParsedProfile
    tier: str
    persona: str


def _level(rng: np.random.Generator, q: float) -> float:
    """A section richness in [0, 1]: latent quality plus independent jitter."""
    return float(np.clip(q + rng.normal(0, _SECTION_NOISE), 0.0, 1.0))


def _count(rng: np.random.Generator, q: float, maximum: int) -> int:
    """Map an independent section level onto a 0..maximum integer count."""
    return int(round(_level(rng, q) * maximum))


def _tier_of(q: float) -> str:
    """Coarse tier label from latent quality (for reporting / calibration)."""
    return TIERS[min(4, int(q * 5))]


def _make_about(rng: np.random.Generator, words: int, title: str) -> str:
    if words <= 0:
        return ""
    parts = [f"{title} with a passion for impact."]
    while len(" ".join(parts).split()) < words:
        parts.append(_ABOUT_SENTENCES[int(rng.integers(0, len(_ABOUT_SENTENCES)))])
    return " ".join(parts)


def _make_bullet(rng: np.random.Generator, quantified: bool) -> str:
    verb = _ACTION_VERBS[int(rng.integers(0, len(_ACTION_VERBS)))]
    outcome = _OUTCOMES[int(rng.integers(0, len(_OUTCOMES)))]
    if quantified:
        pct = int(rng.integers(10, 60))
        return f"- {verb} initiatives that improved {outcome} by {pct}%"
    return f"- {verb} cross-functional work on {outcome}"


def _build_text(rng: np.random.Generator, q: float, persona: str) -> str:
    spec = PERSONAS[persona]
    title = spec["titles"][int(rng.integers(0, len(spec["titles"])))]
    quant_rate = _level(rng, q)  # how achievement-quantified this person writes

    lines: list[str] = ["Jordan Taylor"]  # name line

    # Headline — present above a low bar; gains a role keyword as quality rises.
    if _level(rng, q) > 0.12:
        if _level(rng, q) > 0.4:
            lines.append(f"{title} | {', '.join(spec['skills'][:3])}")
        else:
            lines.append("Open to opportunities")

    # About
    about_words = _count(rng, q, _MAX["about"])
    if about_words >= 5:
        lines += ["", "About", _make_about(rng, about_words, title)]

    # Experience
    n_exp = _count(rng, q, _MAX["exp"])
    if n_exp > 0:
        lines += ["", "Experience"]
        base_year = 2025 - max(1, _count(rng, q, _MAX["years"]))
        for i in range(n_exp):
            start = base_year + i
            end = "Present" if i == n_exp - 1 else str(start + 1)
            lines.append(f"{title} {start} - {end}")
            for _ in range(_count(rng, q, _MAX["bullets"])):
                lines.append(_make_bullet(rng, quantified=rng.random() < quant_rate))

    # Skills (role-coherent technical + a few soft)
    skills = spec["skills"][:_count(rng, q, _MAX["skills"])] + _SOFT[:_count(rng, q, _MAX["soft"])]
    if skills:
        lines += ["", "Skills", ", ".join(skills)]

    # Projects
    n_proj = _count(rng, q, _MAX["projects"])
    if n_proj > 0:
        lines += ["", "Projects"] + [f"- {p}" for p in spec["projects"][:n_proj]]

    # Certifications
    n_certs = _count(rng, q, _MAX["certs"])
    if n_certs > 0:
        lines += ["", "Certifications"] + [f"- {c}" for c in spec["certs"][:n_certs]]

    # Education
    if _level(rng, q) > 0.25:
        lines += ["", "Education", "B.S. Computer Science, State University"]

    # Connections / followers (reach grows with quality)
    if _level(rng, q) > 0.35:
        conns = int(rng.integers(200, 900))
        lines += ["", f"{conns}+ connections"]
        if _level(rng, q) > 0.8:
            lines.append(f"{int(rng.integers(1, 30))}00 followers")

    return "\n".join(lines)


# Canonical, hand-written profiles — one per tier — used as *stable* anchors for
# calibration reporting and tests. Unlike the noisy training set, these are fixed
# representatives whose scores should land in the recruiter-realistic bands.
ARCHETYPES: dict[str, str] = {
    "empty": "Jordan Taylor",
    "weak": (
        "Jordan Taylor\n"
        "Open to opportunities\n\n"
        "About\n"
        "Recent computer science graduate looking for a first role in tech. "
        "Eager to learn and contribute.\n\n"
        "Experience\n"
        "Intern 2023 - 2023\n"
        "- Helped the team with data entry\n\n"
        "Skills\n"
        "python, sql, excel, git\n\n"
        "Education\n"
        "B.S. Computer Science, State University"
    ),
    "average": (
        "Jordan Taylor\n"
        "Data Analyst | SQL, Excel, Python\n\n"
        "About\n"
        "Data analyst who enjoys turning data into clear decisions. I work with "
        "stakeholders to build dashboards and reports that drive action. "
        "Comfortable across SQL, Excel and Python and always learning.\n\n"
        "Experience\n"
        "Data Analyst 2022 - Present\n"
        "- Built reporting that improved decision speed by 20%\n"
        "- Analyzed funnels to support marketing\n\n"
        "Skills\n"
        "sql, excel, python, data analysis, data visualization, tableau\n\n"
        "Education\n"
        "B.S. Statistics, State University\n\n"
        "350+ connections"
    ),
    "strong": (
        "Jordan Taylor\n"
        "Senior Data Scientist | Machine Learning, Python, NLP\n\n"
        "About\n"
        + " ".join(["Senior data scientist with a track record of shipping ML "
                    "products that move business metrics."] * 6) + "\n\n"
        "Experience\n"
        "Senior Data Scientist 2020 - Present\n"
        "- Led models that improved retention by 18%\n"
        "- Built pipelines that cut latency 30%\n"
        "Data Scientist 2018 - 2020\n"
        "- Designed forecasting that saved $1.2M\n\n"
        "Skills\n"
        "python, machine learning, statistics, pandas, scikit-learn, sql, deep learning, nlp, tensorflow\n\n"
        "Projects\n"
        "- Churn prediction model\n- Recommendation engine\n\n"
        "Certifications\n"
        "- AWS Certified Machine Learning\n\n"
        "Education\n"
        "M.S. Computer Science, State University\n\n"
        "500+ connections"
    ),
    "elite": (
        "Jordan Taylor\n"
        "Lead Machine Learning Engineer | LLMs, MLOps, Python, AWS\n\n"
        "About\n"
        + " ".join(["Lead ML engineer who builds and scales production AI "
                    "systems and mentors high-performing teams."] * 10) + "\n\n"
        "Experience\n"
        "Lead ML Engineer 2019 - Present\n"
        "- Led platform serving 10k requests/sec, improved accuracy 22%\n"
        "- Scaled training that reduced costs by 35%\n"
        "- Mentored 8 engineers and drove MLOps best practices\n"
        "Machine Learning Engineer 2016 - 2019\n"
        "- Automated retraining that boosted conversion 15%\n"
        "- Delivered models generating $3M revenue\n\n"
        "Skills\n"
        "python, machine learning, docker, sql, scikit-learn, kubernetes, aws, "
        "airflow, pytorch, tensorflow, ci/cd, deep learning\n\n"
        "Projects\n"
        "- Model serving platform\n- Feature store\n- Automated retraining pipeline\n\n"
        "Certifications\n"
        "- AWS Certified Machine Learning\n- Kubernetes Administrator (CKA)\n- Google Cloud ML Engineer\n\n"
        "Education\n"
        "M.S. Computer Science, State University\n\n"
        "800+ connections\n2500 followers"
    ),
}


def archetype_profiles() -> dict[str, ParsedProfile]:
    """Parsed canonical profiles, one per tier (stable calibration anchors)."""
    return {tier: parse_profile(text) for tier, text in ARCHETYPES.items()}


def generate_profiles(n: int = 5000, seed: int = 42) -> list[Sample]:
    """Generate `n` parsed synthetic profiles spanning the quality spectrum.

    Each profile has a latent quality `q ~ U(0,1)`; section richness is `q` plus
    independent noise, producing realistic, decorrelated feature combinations.
    """
    rng = np.random.default_rng(seed)
    personas = list(PERSONAS.keys())
    samples: list[Sample] = []
    for _ in range(n):
        q = float(rng.random())
        persona = personas[int(rng.integers(0, len(personas)))]
        text = _build_text(rng, q, persona)
        samples.append(Sample(profile=parse_profile(text), tier=_tier_of(q), persona=persona))
    return samples
