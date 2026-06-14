"""Specification-based decision rules — ported from Radarr's DecisionEngine.

Each spec answers is_satisfied_by(release, film) -> Decision(accept, reason).
Specs are grouped by priority and evaluated short-circuit (see engine.py).
A separate scoring pass ranks the accepted candidates.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from ..config import get_settings
from ..providers.indexer import Release
from ..text import looks_like_series, normalize, title_overlap


@dataclass
class Decision:
    accepted: bool
    reason: str = ""

    @classmethod
    def accept(cls) -> "Decision":
        return cls(True)

    @classmethod
    def reject(cls, reason: str) -> "Decision":
        return cls(False, reason)


class Spec:
    priority = 5
    def is_satisfied_by(self, release: Release, film) -> Decision:  # noqa: ANN001
        raise NotImplementedError


class NotSeriesEpisodeSpec(Spec):
    priority = 1
    def is_satisfied_by(self, release, film):
        if looks_like_series(release.title):
            return Decision.reject("dizi bölümü/klip/fragman")
        return Decision.accept()


class MinDurationSpec(Spec):
    priority = 1
    def is_satisfied_by(self, release, film):
        s = get_settings()
        if release.duration_sec and release.duration_min < s.min_duration_min:
            return Decision.reject(f"çok kısa ({round(release.duration_min)}dk)")
        return Decision.accept()


class DurationMatchSpec(Spec):
    priority = 2
    def is_satisfied_by(self, release, film):
        s = get_settings()
        runtime = film.runtime or 0
        if not runtime or not release.duration_sec:
            return Decision.accept()  # can't check; let scoring handle it
        ratio = release.duration_min / runtime
        lo, hi = 1 - s.duration_tolerance, 1 + s.duration_tolerance + 0.10
        if ratio < lo or ratio > hi:
            return Decision.reject(
                f"süre uymadı ({round(release.duration_min)}dk vs {runtime}dk)")
        return Decision.accept()


class TitleMatchSpec(Spec):
    priority = 2
    def is_satisfied_by(self, release, film):
        s = get_settings()
        ref = film.original_title or film.title
        if title_overlap(ref, release.title) < s.min_title_overlap:
            return Decision.reject("başlık uymadı")
        return Decision.accept()


# ---- scoring -------------------------------------------------------------

def is_official(channel: str) -> bool:
    s = get_settings()
    ch = normalize(channel)
    return any(o in ch for o in (normalize(c) for c in s.official_channels))


def score(release: Release, film) -> float:
    """0..~1 confidence that this release IS the film. Higher = better."""
    runtime = film.runtime or 0
    if runtime and release.duration_sec:
        ratio = release.duration_min / runtime
        dur_score = max(0.0, 1 - abs(1 - ratio) * 2)
    else:
        dur_score = 0.3
    overlap = title_overlap(film.original_title or film.title, release.title)
    view_score = min(1.0, math.log10(release.view_count + 1) / 7.0)
    official_bonus = 0.10 if is_official(release.channel) else 0.0
    return dur_score * 0.45 + overlap * 0.30 + view_score * 0.15 + official_bonus


DEFAULT_SPECS: list[Spec] = [
    NotSeriesEpisodeSpec(),
    MinDurationSpec(),
    DurationMatchSpec(),
    TitleMatchSpec(),
]
