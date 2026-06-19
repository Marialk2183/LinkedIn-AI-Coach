"""Phase 3 — AI writing assistant via Gemini, with a heuristic fallback.

Gemini is wrapped behind this single interface. If no API key is configured (or
a call fails), every method degrades to a deterministic template so endpoints
never hard-fail. Swap the provider here without touching routes/services.
"""

from __future__ import annotations

import logging

from config import Settings
from models.domain import ParsedProfile

logger = logging.getLogger(__name__)


class AIService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model = None
        if settings.ai_enabled:
            try:
                import google.generativeai as genai

                genai.configure(api_key=settings.gemini_api_key)
                self._model = genai.GenerativeModel(settings.gemini_model)
                logger.info("Gemini initialized (%s)", settings.gemini_model)
            except Exception:  # noqa: BLE001
                logger.exception("Gemini init failed; using fallback writer.")
                self._model = None

    @property
    def enabled(self) -> bool:
        return self._model is not None

    def _generate(self, prompt: str) -> str | None:
        if self._model is None:
            return None
        try:
            resp = self._model.generate_content(prompt)
            text = (getattr(resp, "text", "") or "").strip()
            return text or None
        except Exception:  # noqa: BLE001
            logger.exception("Gemini generation failed; using fallback.")
            return None

    # ------------------------------- headline ------------------------------- #
    def improve_headline(
        self, headline: str, skills: list[str], target_role: str | None
    ) -> tuple[str, bool]:
        prompt = (
            "Rewrite this LinkedIn headline to be punchy and keyword-rich for "
            "recruiters. Return ONLY the headline, max ~120 characters, using ' | ' "
            "to separate a role and 3-4 signature skills. No quotes, no preamble.\n\n"
            f"Current headline: {headline!r}\n"
            f"Target role: {target_role or 'infer from skills'}\n"
            f"Skills: {', '.join(skills) or 'n/a'}"
        )
        text = self._generate(prompt)
        if text:
            return text.splitlines()[0].strip(' "'), True
        return self._fallback_headline(headline, skills, target_role), False

    @staticmethod
    def _fallback_headline(headline: str, skills: list[str], target_role: str | None) -> str:
        role = target_role or ("Aspiring Data Scientist" if not headline else headline.strip())
        picked = [s.title() for s in skills[:4]] or ["Python", "SQL", "Machine Learning"]
        base = headline.strip() or "Professional"
        if target_role and target_role.lower() not in base.lower():
            base = f"{base} | {target_role}"
        return " | ".join([base, *picked]) if base != role else " | ".join([role, *picked])

    # -------------------------------- about --------------------------------- #
    def improve_about(
        self,
        name: str | None,
        headline: str | None,
        skills: list[str],
        experience_years: float,
        target_role: str | None,
        current_about: str | None,
    ) -> tuple[str, bool]:
        prompt = (
            "Write a professional, first-person LinkedIn About section (3 short "
            "paragraphs, ~120-160 words). Confident but not arrogant; weave in the "
            "skills naturally; end with what the person is looking for. Return ONLY "
            "the About text.\n\n"
            f"Name: {name or 'n/a'}\n"
            f"Headline: {headline or 'n/a'}\n"
            f"Target role: {target_role or 'infer'}\n"
            f"Years of experience: {experience_years:.0f}\n"
            f"Skills: {', '.join(skills) or 'n/a'}\n"
            f"Existing about (improve, don't copy): {current_about or 'none'}"
        )
        text = self._generate(prompt)
        if text:
            return text.strip(), True
        return self._fallback_about(headline, skills, experience_years, target_role), False

    @staticmethod
    def _fallback_about(
        headline: str | None, skills: list[str], years: float, target_role: str | None
    ) -> str:
        role = target_role or headline or "a results-driven professional"
        skill_str = ", ".join(s.title() for s in skills[:6]) or "Python, SQL, and Machine Learning"
        exp = (
            f"With {years:.0f}+ years of hands-on experience, "
            if years >= 1
            else "Early in my career but moving fast, "
        )
        return (
            f"I'm {role}, passionate about turning data and ideas into products that "
            f"create real impact. {exp}I focus on building practical, well-engineered "
            "solutions and learning continuously.\n\n"
            f"My core toolkit includes {skill_str}. I enjoy collaborating across teams, "
            "translating ambiguous problems into clear deliverables, and shipping work "
            "that moves the needle.\n\n"
            "I'm open to new opportunities and collaborations — feel free to connect "
            "if you're building something interesting."
        )

    # ----------------------------- career advice ---------------------------- #
    def career_advice(self, profile: ParsedProfile, top_role: str | None) -> tuple[str, bool]:
        prompt = (
            "Give 3 concise, actionable career-development tips (one sentence each, "
            "as a bullet list) for this person to become more competitive"
            f"{f' as a {top_role}' if top_role else ''}. Return ONLY the bullets.\n\n"
            f"Skills: {', '.join(profile.skills) or 'n/a'}\n"
            f"Experience years: {profile.experience_years:.0f}\n"
            f"Projects: {profile.projects_count}, Certifications: {profile.certifications_count}"
        )
        text = self._generate(prompt)
        if text:
            return text.strip(), True
        advice = (
            f"- Build a portfolio project that targets {top_role or 'your goal role'} and write it up.\n"
            "- Earn one recognized certification to validate your strongest skill.\n"
            "- Publish weekly posts about what you're learning to grow visibility."
        )
        return advice, False
