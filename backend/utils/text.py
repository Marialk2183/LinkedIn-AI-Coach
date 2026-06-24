"""Small, dependency-free text helpers used by the parser and scorers."""

import re

from utils.constants import ACTION_VERBS

# Quantified-impact tokens: %, currency, k/m/b magnitudes, and multipliers.
# Deliberately excludes bare integers (e.g. years like "2019") to avoid counting
# dates and noise as achievements.
_METRIC_PATTERN = re.compile(
    r"(\$\s?\d[\d,]*\.?\d*[kmb]?)"          # $1.2M, $500k
    r"|(\d[\d,]*\.?\d*\s?%)"                # 20%, 12.5 %
    r"|(\b\d[\d,]*\.?\d*\s?[kmb]\b)"        # 10k, 2m
    r"|(\b\d+\s?x\b)",                       # 3x
    re.IGNORECASE,
)


def normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # collapse 3+ blank lines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def nonempty_lines(block: str) -> list[str]:
    return [ln.strip() for ln in block.splitlines() if ln.strip()]


def word_count(text: str) -> int:
    return len(text.split())


def find_int_near(text: str, *keywords: str) -> int | None:
    """Find a number adjacent to any keyword, e.g. '500+ connections' -> 500.

    Handles 'k'/'m' suffixes (1.2k -> 1200).
    """
    for kw in keywords:
        # number before keyword: '500+ connections'
        m = re.search(rf"([\d.,]+)\s*([km])?\+?\s*{re.escape(kw)}", text, re.IGNORECASE)
        if not m:
            # number after keyword: 'connections: 500'
            m = re.search(rf"{re.escape(kw)}\s*[:\-]?\s*([\d.,]+)\s*([km])?", text, re.IGNORECASE)
        if m:
            return _to_int(m.group(1), m.group(2))
    return None


def _to_int(num: str, suffix: str | None) -> int | None:
    try:
        value = float(num.replace(",", ""))
    except ValueError:
        return None
    if suffix:
        value *= {"k": 1_000, "m": 1_000_000}[suffix.lower()]
    return int(value)


def estimate_experience_years(text: str) -> float:
    """Estimate total years of experience from explicit phrases or date ranges."""
    # explicit: '5 years', '5+ yrs'
    explicit = [
        float(m) for m in re.findall(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years|yrs|year)", text, re.IGNORECASE)
    ]
    if explicit:
        return max(explicit)

    # date ranges: '2019 - 2023', '2020 - Present'
    total = 0.0
    for start, end in re.findall(
        r"(\b(?:19|20)\d{2})\s*[-–to]+\s*((?:19|20)\d{2}|present|current)",
        text,
        re.IGNORECASE,
    ):
        start_y = int(start)
        end_y = 2025 if end.lower() in ("present", "current") else int(end)
        if end_y >= start_y:
            total += end_y - start_y
    return float(total)


def count_quantified_metrics(text: str) -> int:
    """Count quantified-impact tokens (%, $, 10k, 3x, large numbers) in text.

    Achievement quantification is a strong recruiter signal ("increased revenue 20%"
    beats "responsible for revenue").
    """
    if not text:
        return 0
    return len(_METRIC_PATTERN.findall(text))


def count_action_verbs(text: str) -> int:
    """Count distinct strong action verbs (led, built, optimized, …) in text."""
    if not text:
        return 0
    words = set(re.findall(r"[a-zA-Z]+", text.lower()))
    return len(words & ACTION_VERBS)


def count_keyword_hits(text: str, keywords: set[str]) -> int:
    """Count how many distinct keywords appear in text.

    Single-word keywords match on word boundaries (so "lead" hits "Lead" but not
    "leadership"); multi-word phrases match as substrings. Generic helper reused
    by the ATS and Leadership scorers.
    """
    if not text:
        return 0
    lowered = text.lower()
    words = set(re.findall(r"[a-z]+", lowered))
    hits = 0
    for kw in keywords:
        if " " in kw:
            if kw in lowered:
                hits += 1
        elif kw in words:
            hits += 1
    return hits
