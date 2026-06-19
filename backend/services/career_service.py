"""Career prediction: percentage match for each target role.

Weighted skill overlap (core skills count more than nice-to-haves), lightly
boosted by experience. Pure and deterministic.
"""

from __future__ import annotations

from models.domain import CareerMatch, ParsedProfile
from utils.constants import ROLE_DEFINITIONS


class CareerService:
    def predict(self, p: ParsedProfile) -> list[CareerMatch]:
        owned = {s.lower() for s in p.skills}
        results: list[CareerMatch] = []

        for role, spec in ROLE_DEFINITIONS.items():
            core = spec["core"]
            nice = spec["nice"]

            core_hits = [s for s in core if s in owned]
            nice_hits = [s for s in nice if s in owned]

            core_cov = len(core_hits) / len(core) if core else 0.0
            nice_cov = len(nice_hits) / len(nice) if nice else 0.0

            # 75% weight on core coverage, 15% on nice-to-haves, 10% on experience.
            exp_factor = min(1.0, p.experience_years / 5.0)
            score = core_cov * 0.75 + nice_cov * 0.15 + exp_factor * 0.10
            match_pct = round(score * 100, 1)

            missing = [s for s in core if s not in owned]
            results.append(
                CareerMatch(
                    role=role,
                    match_pct=match_pct,
                    matched_skills=core_hits + nice_hits,
                    missing_skills=missing,
                )
            )

        results.sort(key=lambda m: m.match_pct, reverse=True)
        return results
