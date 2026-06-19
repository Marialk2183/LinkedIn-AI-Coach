"""Heuristic parser: raw LinkedIn profile text -> ParsedProfile.

LinkedIn forbids scraping, so this operates on text the user pastes. It splits
the text into recognized sections, then extracts structured signals. Robust to
missing sections and messy formatting; never raises on bad input.
"""

import re

from models.domain import ParsedProfile
from utils import text as T
from utils.constants import ALL_SKILLS, SECTION_ALIASES, TECHNICAL_SKILLS

# Build a header -> canonical-section lookup.
_HEADER_LOOKUP: dict[str, str] = {
    alias.lower(): section
    for section, aliases in SECTION_ALIASES.items()
    for alias in aliases
}
_ALL_HEADERS = sorted(_HEADER_LOOKUP, key=len, reverse=True)


def _split_sections(body: str) -> dict[str, str]:
    """Split text into {canonical_section: block} by scanning header-only lines."""
    sections: dict[str, list[str]] = {}
    current = "_intro"
    sections[current] = []
    for line in body.splitlines():
        stripped = line.strip().lower().rstrip(":")
        if stripped in _HEADER_LOOKUP:
            current = _HEADER_LOOKUP[stripped]
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items()}


def _extract_skills(*blocks: str) -> tuple[list[str], list[str]]:
    """Match canonical skills anywhere in the given blocks."""
    haystack = " \n ".join(blocks).lower()
    found: list[str] = []
    for skill in ALL_SKILLS:
        # word-ish boundary match (handles 'c++', 'node.js', 'ci/cd')
        pattern = r"(?<![\w])" + re.escape(skill) + r"(?![\w])"
        if re.search(pattern, haystack):
            found.append(skill)
    found = sorted(set(found))
    technical = sorted(s for s in found if s in TECHNICAL_SKILLS)
    return found, technical


def _bullet_entries(block: str) -> list[str]:
    """Split a section block into entries (bullets or non-empty lines)."""
    if not block:
        return []
    lines = T.nonempty_lines(block)
    bullets = [re.sub(r"^[\-\*•·]\s*", "", ln) for ln in lines]
    return [b for b in bullets if len(b) > 1]


def parse_profile(raw_text: str, source_type: str = "text") -> ParsedProfile:
    raw = T.normalize(raw_text or "")
    sections = _split_sections(raw)

    intro = sections.get("_intro", "")
    intro_lines = T.nonempty_lines(intro)

    # Name = first short, title-cased line without digits; headline = next line.
    name: str | None = None
    headline = ""
    if intro_lines:
        first = intro_lines[0]
        if len(first) <= 60 and not any(c.isdigit() for c in first):
            name = first
            headline = intro_lines[1] if len(intro_lines) > 1 else ""
        else:
            headline = first

    about = sections.get("about", "")
    skills_block = sections.get("skills", "")
    experience_block = sections.get("experience", "")
    projects_block = sections.get("projects", "")
    certs_block = sections.get("certifications", "")
    education_block = sections.get("education", "")

    skills, technical_skills = _extract_skills(
        skills_block, headline, about, experience_block, projects_block, raw
    )

    profile = ParsedProfile(
        name=name,
        headline=headline,
        about=about,
        experiences=_bullet_entries(experience_block),
        education=_bullet_entries(education_block),
        certifications=_bullet_entries(certs_block),
        projects=_bullet_entries(projects_block),
        skills=skills,
        technical_skills=technical_skills,
        experience_years=T.estimate_experience_years(raw),
        connections=T.find_int_near(raw, "connections", "connection"),
        followers=T.find_int_near(raw, "followers", "follower"),
        raw_text=raw,
    )
    return profile
