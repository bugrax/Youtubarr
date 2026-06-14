"""Radarr API client — pulls the 'wanted' film list to seed Youtubarr."""
from __future__ import annotations

import httpx

from ..config import get_settings


class RadarrClient:
    def __init__(self, url: str | None = None, api_key: str | None = None):
        s = get_settings()
        self.url = (url or s.radarr_url).rstrip("/")
        self.api_key = api_key or s.radarr_api_key

    @property
    def configured(self) -> bool:
        return bool(self.url and self.api_key)

    def _get(self, path: str, **params):
        r = httpx.get(
            f"{self.url}/api/v3/{path}",
            headers={"X-Api-Key": self.api_key},
            params=params, timeout=60,
        )
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, payload: dict):
        r = httpx.post(
            f"{self.url}/api/v3/{path}",
            headers={"X-Api-Key": self.api_key},
            json=payload, timeout=60,
        )
        r.raise_for_status()
        return r.json()

    def rescan_by_tmdb(self, tmdb_id: int) -> bool:
        """Ask Radarr to rescan a movie's folder so it picks up a file Youtubarr
        just dropped into the shared library. Returns True if a command was sent."""
        if not self.configured:
            return False
        movies = self._get("movie", tmdbId=tmdb_id)
        if not movies:
            return False
        self._post("command", {"name": "RescanMovie", "movieId": movies[0]["id"]})
        return True

    def ping(self) -> dict:
        return self._get("system/status")

    def wanted_films(self, language: str | None = None, only_missing: bool = True) -> list[dict]:
        """Films Radarr knows about, optionally filtered by original language and
        missing-on-disk. Returns normalized dicts ready to upsert as Film rows."""
        s = get_settings()
        language = language if language is not None else s.radarr_language
        movies = self._get("movie", excludeLocalCovers="true")
        out = []
        for m in movies:
            if only_missing and m.get("hasFile"):
                continue
            if not m.get("monitored", True):
                continue
            lang = (m.get("originalLanguage") or {}).get("name", "")
            if language and lang != language:
                continue
            out.append({
                "tmdb_id": m.get("tmdbId"),
                "title": m.get("title") or "",
                "original_title": m.get("originalTitle") or "",
                "year": m.get("year"),
                "runtime": m.get("runtime") or 0,
                "language": lang,
            })
        return [x for x in out if x["tmdb_id"]]
