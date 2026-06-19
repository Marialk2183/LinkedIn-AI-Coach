"""Impact-prioritized recommendation engine: strengths, weaknesses, and actions.

Rather than emit generic advice, this estimates the *overall-score impact* of each
possible fix by actually applying it to a copy of the parsed profile and
re-scoring. Recommendations are then ranked highest-impact-first and annotated
with the expected gain (e.g. "~+12 pts"), so a user always knows what to do next
and why it matters. Fully deterministic — no AI required.

Each recommendation also carries a concrete, copy-pasteable ``example`` so the
advice is precise ("add quantified metrics") *and* actionable ("e.g. 'Cut model
training time 40% by parallelizing the pipeline'").

Writing-quality fixes (quantified achievements, strong action verbs) don't move
the rule-based dimension scores but are exactly what recruiters and the ML model
reward, so they're surfaced with a small, explicitly-estimated impact.
"""

from __future__ import annotations

from dataclasses import replace

from models.domain import CareerMatch, ParsedProfile, RecommendationItem, ScoreResult
from services.scoring_service import ScoringService
from utils import text as T
from utils.constants import ROLE_CERTIFICATIONS, TECHNICAL_SKILLS

# Neutral filler used to model "expand your About" without injecting fake metrics.
_FILLER = (
    "I focus on delivering measurable impact, collaborating across teams, and "
    "continuously improving how we work and the products we ship. "
)

# Estimated (not re-scored) gains for writing-quality fixes the rule scorer can't
# see but the ML model and recruiters reward. Kept small and honest.
_QUANTIFIED_IMPACT = 4
_ACTION_VERB_IMPACT = 3


def _with_skills(p: ParsedProfile, add: list[str]) -> ParsedProfile:
    skills = sorted(set(p.skills) | {s.lower() for s in add})
    technical = sorted(s for s in skills if s in TECHNICAL_SKILLS)
    return replace(p, skills=skills, technical_skills=technical)


def _expanded_about(p: ParsedProfile, target_words: int = 170) -> ParsedProfile:
    about = p.about
    while len((about or "").split()) < target_words:
        about = f"{about} {_FILLER}".strip()
    return replace(p, about=about)


class RecommendationService:
    def __init__(self, scoring: ScoringService | None = None) -> None:
        # A rule-only scorer keeps impact estimates deterministic and independent
        # of the ML model's noise; it still reflects the same dimension logic.
        self._scoring = scoring or ScoringService(predictor=None)

    def build(
        self,
        p: ParsedProfile,
        scores: ScoreResult,
        career: list[CareerMatch],
    ) -> tuple[list[str], list[str], list[RecommendationItem]]:
        strengths = self._strengths(p, scores)
        recommendations = self._recommendations(p, career)
        # Weaknesses mirror the top recommendations so the narrative stays consistent.
        weaknesses = self._weaknesses(p, scores, recommendations)
        return strengths, weaknesses, recommendations

    # ------------------------------------------------------------------ #
    def _base_overall(self, p: ParsedProfile) -> int:
        return self._scoring.score(p).overall

    def _impact(self, base: int, patched: ParsedProfile) -> int:
        return max(0, self._scoring.score(patched).overall - base)

    def _recommendations(
        self, p: ParsedProfile, career: list[CareerMatch]
    ) -> list[RecommendationItem]:
        base = self._base_overall(p)
        candidates: list[RecommendationItem] = []
        top = career[0] if career else None
        role = top.role if top else "your target role"

        # 1. Missing core skills for the best-matching role.
        if top and top.missing_skills:
            add = top.missing_skills[:4]
            gain = self._impact(base, _with_skills(p, add))
            pretty = ", ".join(s.title() for s in add)
            candidates.append(RecommendationItem(
                "missing_skill",
                f"Add {pretty} — core skills for {top.role} (your top role match, "
                f"currently {top.match_pct:.0f}%).",
                gain,
                example=(
                    f"List them in your Skills section and reference at least one in "
                    f"a project, e.g. \"Used {add[0].title()} to ...\"."
                ),
            ))

        # 2. Expand a thin About section, with role keywords baked in.
        if p.about_length < 150:
            gain = self._impact(base, _expanded_about(p))
            keywords = [s.title() for s in (top.matched_skills[:3] if top else p.skills[:3])]
            kw_hint = f" Weave in: {', '.join(keywords)}." if keywords else ""
            candidates.append(RecommendationItem(
                "action",
                f"Expand your About to ~150+ words with {role}-relevant keywords "
                f"recruiters search (currently {p.about_length} words).{kw_hint}",
                gain,
                example=(
                    f"\"{role} with hands-on experience in "
                    f"{', '.join(keywords) or 'your core stack'}. I turn ambiguous "
                    f"problems into shipped, measurable results — recently [your win].\""
                ),
            ))

        # 3. Add role-specific certifications.
        if p.certifications_count < 2:
            need = 2 - p.certifications_count
            patched = replace(p, certifications=p.certifications + ["Certification"] * need)
            gain = self._impact(base, patched)
            suggested = ROLE_CERTIFICATIONS.get(role, ["a recognized cloud or analytics credential"])
            candidates.append(RecommendationItem(
                "missing_certification",
                f"Earn {need} more certification(s) relevant to {role} to validate "
                f"your skills.",
                gain,
                example=f"Good fits: {', '.join(suggested[:3])}.",
            ))

        # 4. Add projects with measurable outcomes.
        if p.projects_count < 3:
            need = max(1, 3 - p.projects_count)
            patched = replace(p, projects=p.projects + ["Project"] * need)
            gain = self._impact(base, patched)
            candidates.append(RecommendationItem(
                "missing_project",
                f"Add {need} more project(s) with measurable outcomes to demonstrate "
                f"applied ability.",
                gain,
                example=(
                    "\"Built a churn model in Python/scikit-learn that improved "
                    "retention targeting accuracy by 18%.\""
                ),
            ))

        # 5. Strengthen the headline — surface the actual rewrite.
        has_role_kw = bool(p.technical_skills) and any(
            s in p.headline.lower() for s in p.technical_skills
        )
        if not p.headline.strip() or p.headline_length < 6 or not has_role_kw:
            skills = (p.technical_skills or p.skills)[:3]
            new_headline = (
                f"{role} | {' · '.join(s.title() for s in skills)}" if skills else role
            )
            gain = self._impact(base, replace(p, headline=new_headline))
            candidates.append(RecommendationItem(
                "action",
                "Rewrite your headline to lead with your role plus 3-4 signature skills.",
                gain,
                example=f"\"{new_headline}\"",
            ))

        # 6. Quantify achievements (writing quality — ML/recruiter signal).
        achievement_text = " ".join([p.about, *p.experiences, *p.projects])
        metrics = T.count_quantified_metrics(achievement_text)
        if achievement_text.strip() and metrics < 3:
            candidates.append(RecommendationItem(
                "action",
                f"Quantify your impact — only {metrics} measurable result(s) detected. "
                "Numbers (%/$/×/time saved) make achievements credible and searchable.",
                _QUANTIFIED_IMPACT,
                example=(
                    "Swap \"responsible for reporting\" → \"automated reporting, "
                    "saving ~10 hrs/week and cutting errors 30%.\""
                ),
            ))

        # 7. Lead bullets with strong action verbs.
        verbs = T.count_action_verbs(achievement_text)
        if achievement_text.strip() and verbs < 3:
            candidates.append(RecommendationItem(
                "action",
                "Open your experience/project bullets with strong action verbs to read "
                "as achievement-driven, not task-driven.",
                _ACTION_VERB_IMPACT,
                example="Built · Led · Designed · Optimized · Shipped · Automated.",
            ))

        # 8. Grow network reach.
        if (p.connections or 0) < 500:
            patched = replace(p, connections=max(500, p.connections or 0))
            gain = self._impact(base, patched)
            candidates.append(RecommendationItem(
                "action",
                "Grow your network toward 500+ connections and post regularly to lift "
                "visibility.",
                gain,
                example=(
                    "Connect with classmates/colleagues and share one short post a week "
                    "about what you're learning or building."
                ),
            ))

        # Highest-impact first; annotate the gain. Keep zero-impact items only if
        # nothing else qualifies, so the user always gets guidance.
        candidates.sort(key=lambda r: r.impact_points or 0, reverse=True)
        ranked = [r for r in candidates if (r.impact_points or 0) > 0] or candidates[:1]
        for r in ranked:
            if r.impact_points:
                r.content = f"{r.content} (~+{r.impact_points} pts)"
        if not ranked:
            ranked = [RecommendationItem(
                "action", "Keep your profile fresh — add new wins as they happen.", 0,
                example="Update your headline and About each time you ship something new.",
            )]
        return ranked

    def _strengths(self, p: ParsedProfile, s: ScoreResult) -> list[str]:
        out: list[str] = []
        if s.technical >= 70:
            out.append("Strong technical profile with relevant, in-demand skills.")
        if p.about_length >= 120:
            out.append("Detailed About section that tells your story well.")
        if p.projects_count >= 3:
            out.append(f"Solid project portfolio ({p.projects_count} projects listed).")
        if p.certifications_count >= 2:
            out.append("Certifications add credibility to your expertise.")
        if p.experience_years >= 3:
            out.append(f"~{p.experience_years:.0f} years of experience signal seniority.")
        if s.completeness >= 80:
            out.append("Profile is thorough across the key sections.")
        if T.count_quantified_metrics(" ".join([p.about, *p.experiences, *p.projects])) >= 4:
            out.append("Achievements are quantified — exactly what recruiters look for.")
        if not out:
            out.append("You have a foundation to build on — let's strengthen it below.")
        return out

    def _weaknesses(
        self, p: ParsedProfile, s: ScoreResult, recs: list[RecommendationItem]
    ) -> list[str]:
        out: list[str] = []
        if not p.headline.strip() or p.headline_length < 4:
            out.append("Headline is missing or too short to surface in search.")
        if p.about_length < 60:
            out.append("About section is thin — recruiters skim it first.")
        if p.skills_count < 8:
            out.append("Too few skills listed to rank for relevant searches.")
        if p.projects_count == 0:
            out.append("No projects listed to demonstrate applied ability.")
        if p.certifications_count == 0:
            out.append("No certifications to validate your skills.")
        if s.networking < 50:
            out.append("Networking signals are low (connections/activity).")
        if not out:
            out.append("No major gaps — focus on incremental polish.")
        return out
