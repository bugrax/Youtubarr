"""Orchestrates indexer search + decision engine for a film."""
from __future__ import annotations

from dataclasses import asdict

from sqlmodel import Session, select

from ..decision.engine import DecisionEngine, Evaluation
from ..models import Blocklist, Film, FilmStatus
from ..providers.indexer import YouTubeIndexer

_indexer = YouTubeIndexer()
_engine = DecisionEngine()


def _blocked(session: Session) -> set[str]:
    return set(session.exec(select(Blocklist.youtube_id)).all())


def find_matches(film: Film, session: Session) -> tuple[Evaluation | None, list[Evaluation]]:
    blocked = _blocked(session)
    releases = [r for r in _indexer.search_film(film.original_title, film.title, film.year)
                if r.youtube_id not in blocked]
    return _engine.best(releases, film)


def evaluation_dict(e: Evaluation) -> dict:
    d = asdict(e.release)
    d.update({
        "accepted": e.accepted,
        "score": round(e.score, 3),
        "confidence": e.confidence,
        "rejections": e.rejections,
        "duration_min": round(e.release.duration_min),
    })
    return d


def match_and_store(film: Film, session: Session) -> dict:
    """Search + decide; persist the chosen release on the film. Returns a report."""
    best, evals = find_matches(film, session)
    if best:
        film.status = FilmStatus.matched
        film.youtube_id = best.release.youtube_id
        film.youtube_title = best.release.title
        film.youtube_channel = best.release.channel
        film.match_score = round(best.score, 3)
        session.add(film)
        session.commit()
    return {
        "film": film.original_title or film.title,
        "matched": bool(best),
        "best": evaluation_dict(best) if best else None,
        "candidates": [evaluation_dict(e) for e in
                       sorted(evals, key=lambda x: x.score, reverse=True)],
    }
