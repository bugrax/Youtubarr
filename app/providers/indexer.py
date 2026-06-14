"""YouTube indexer — the Servarr 'Indexer' equivalent.

Wraps yt-dlp's search to return a normalized list of release candidates.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass

from ..config import get_settings


@dataclass
class Release:
    youtube_id: str
    title: str
    channel: str
    duration_sec: int          # 0 if unknown
    view_count: int
    url: str

    @property
    def duration_min(self) -> float:
        return self.duration_sec / 60.0


def _run_ytdlp(args: list[str], timeout: int = 120) -> str:
    proc = subprocess.run(
        ["yt-dlp", *args],
        capture_output=True, text=True, timeout=timeout,
    )
    return proc.stdout


class YouTubeIndexer:
    name = "youtube"

    def __init__(self, results: int | None = None):
        s = get_settings()
        self.results = results or s.search_results

    def _parse(self, raw: str) -> list[Release]:
        out: list[Release] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            vid = e.get("id")
            if not vid:
                continue
            out.append(Release(
                youtube_id=vid,
                title=e.get("title") or "",
                channel=e.get("channel") or e.get("uploader") or "",
                duration_sec=int(e.get("duration") or 0),
                view_count=int(e.get("view_count") or 0),
                url=e.get("url") or f"https://youtu.be/{vid}",
            ))
        return out

    def search(self, query: str) -> list[Release]:
        """Free-text YouTube search (ytsearchN)."""
        try:
            raw = _run_ytdlp([
                f"ytsearch{self.results}:{query}",
                "--flat-playlist", "--dump-json", "--no-warnings",
            ])
        except subprocess.TimeoutExpired:
            return []
        return self._parse(raw)

    def search_film(self, original_title: str, title: str = "", year: int | None = None) -> list[Release]:
        """Search a film by its title(s) across several query variants.

        Bare titles (e.g. "Uzak", "Yol") are common words that drown in unrelated
        results, so we also try "<title> full film", "<title> filmi" and
        "<title> <year>" and merge everything, de-duplicating by video id.
        """
        primary = original_title or title
        queries = [primary, f"{primary} full film"]
        if year:
            queries.append(f"{primary} {year}")
        if title and title != original_title:
            queries.append(f"{title} full movie")
        seen: dict[str, Release] = {}
        for q in dict.fromkeys(queries):
            for r in self.search(q):
                seen.setdefault(r.youtube_id, r)
        return list(seen.values())

    def channel_uploads(self, channel: str, limit: int = 30) -> list[Release]:
        """Recent uploads of a YouTube channel (@handle, /c/, or full URL)."""
        if channel.startswith("@"):
            url = f"https://www.youtube.com/{channel}/videos"
        elif channel.startswith("http"):
            url = channel if "/videos" in channel else channel.rstrip("/") + "/videos"
        else:
            url = f"https://www.youtube.com/@{channel}/videos"
        try:
            raw = _run_ytdlp([
                url, "--flat-playlist", "--dump-json", "--no-warnings",
                "--playlist-end", str(limit),
            ], timeout=120)
        except subprocess.TimeoutExpired:
            return []
        return self._parse(raw)
