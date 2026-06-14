"""Decision engine — priority-grouped, short-circuit evaluation (à la Radarr)."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import groupby

from ..config import get_settings
from ..providers.indexer import Release
from .specs import DEFAULT_SPECS, Decision, Spec, score


@dataclass
class Evaluation:
    release: Release
    accepted: bool
    score: float
    rejections: list[str]

    @property
    def confidence(self) -> str:
        if not self.accepted:
            return "rejected"
        if self.score >= 0.75:
            return "high"
        if self.score >= 0.6:
            return "medium"
        return "low"


class DecisionEngine:
    def __init__(self, specs: list[Spec] | None = None):
        self.specs = specs or DEFAULT_SPECS

    def evaluate(self, release: Release, film) -> Evaluation:  # noqa: ANN001
        rejections: list[str] = []
        # Group by priority ascending; stop at the first group with a rejection.
        for _, group in groupby(sorted(self.specs, key=lambda s: s.priority),
                                key=lambda s: s.priority):
            group_rejections = []
            for spec in group:
                d: Decision = spec.is_satisfied_by(release, film)
                if not d.accepted:
                    group_rejections.append(d.reason)
            if group_rejections:
                rejections = group_rejections
                break
        accepted = not rejections
        return Evaluation(
            release=release,
            accepted=accepted,
            score=score(release, film) if accepted else 0.0,
            rejections=rejections,
        )

    def best(self, releases: list[Release], film) -> tuple[Evaluation | None, list[Evaluation]]:  # noqa: ANN001
        """Return (best accepted evaluation above threshold, all evaluations)."""
        evals = [self.evaluate(r, film) for r in releases]
        accepted = sorted([e for e in evals if e.accepted],
                          key=lambda e: e.score, reverse=True)
        threshold = get_settings().accept_score
        best = next((e for e in accepted if e.score >= threshold), None)
        return best, evals
