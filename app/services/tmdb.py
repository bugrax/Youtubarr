"""TMDB import list — discover films independently of Radarr.

Pulls popular films of the configured original language/country from TMDB and
upserts them as wanted Film rows (source='tmdb'), fetching runtime (needed by
the duration decision spec).
"""
from __future__ import annotations

import logging

import httpx
from sqlmodel import Session, select

from ..config import get_settings
from ..db import engine
from ..models import Film, FilmStatus

log = logging.getLogger("youtubarr.tmdb")
_BASE = "https://api.themoviedb.org/3"


def _get(path: str, **params):
    s = get_settings()
    params["api_key"] = s.tmdb_api_key
    r = httpx.get(f"{_BASE}/{path}", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def discover(pages: int = 2) -> list[dict]:
    """Discover films by original language/country, most popular first."""
    s = get_settings()
    out: list[dict] = []
    for page in range(1, pages + 1):
        data = _get(
            "discover/movie",
            language=s.tmdb_language,
            with_original_language=s.tmdb_language,
            with_origin_country=s.tmdb_region,
            sort_by="popularity.desc",
            page=page,
            **{"vote_count.gte": s.tmdb_min_votes},
        )
        out.extend(data.get("results", []))
        if page >= data.get("total_pages", 1):
            break
    return out


def _details(tmdb_id: int) -> dict:
    s = get_settings()
    return _get(f"movie/{tmdb_id}", language=s.tmdb_language)


def sync(pages: int = 2) -> dict:
    """Discover + upsert into Film table. Returns a summary."""
    s = get_settings()
    if not s.tmdb_api_key:
        return {"ok": False, "error": "TMDB API anahtarı yok"}
    results = discover(pages)
    added = skipped = 0
    with Session(engine) as session:
        for r in results:
            tmdb_id = r.get("id")
            if not tmdb_id:
                continue
            if session.exec(select(Film).where(Film.tmdb_id == tmdb_id)).first():
                skipped += 1
                continue
            try:
                d = _details(tmdb_id)
                runtime = d.get("runtime") or 0
            except Exception:  # noqa: BLE001
                runtime = 0
            year = None
            if r.get("release_date"):
                year = int(r["release_date"][:4]) if r["release_date"][:4].isdigit() else None
            session.add(Film(
                tmdb_id=tmdb_id,
                title=r.get("title") or r.get("original_title") or "",
                original_title=r.get("original_title") or "",
                year=year, runtime=runtime,
                language=s.tmdb_language, status=FilmStatus.wanted, source="tmdb",
            ))
            added += 1
        session.commit()
    log.info("tmdb sync: +%s (atlanan %s)", added, skipped)
    return {"ok": True, "added": added, "skipped": skipped, "scanned": len(results)}
