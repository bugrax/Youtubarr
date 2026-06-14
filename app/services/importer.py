"""Import service — verify the downloaded file and move it into the library.

Mirrors Radarr's import step: validate (ffprobe), build a Jellyfin-friendly
name, move into {Title} ({Year}) [tmdbid-N]/.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess

from ..config import get_settings


def _safe(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    return re.sub(r"\s+", " ", name).strip()


def ffprobe_duration(path: str) -> int:
    """Container duration in seconds (0 if unknown)."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "json", path],
            capture_output=True, text=True, timeout=60,
        ).stdout
        return int(float(json.loads(out)["format"]["duration"]))
    except Exception:
        return 0


def verify(path: str, expected_runtime_min: int) -> tuple[bool, str]:
    if not os.path.exists(path):
        return False, "dosya yok"
    if os.path.getsize(path) < 50 * 1024 * 1024:
        return False, "dosya çok küçük (<50MB)"
    if expected_runtime_min:
        dur = ffprobe_duration(path)
        if dur:
            ratio = (dur / 60) / expected_runtime_min
            if ratio < 0.80 or ratio > 1.30:
                return False, f"süre uyuşmuyor ({round(dur/60)}dk vs {expected_runtime_min}dk)"
    return True, "ok"


def import_file(src: str, film, dest_dir: str | None = None) -> str:  # noqa: ANN001
    """Move src into the library; return the destination path.

    If dest_dir is given (e.g. Radarr's exact movie folder path), import there so
    a downstream Radarr rescan finds the file; otherwise build a Jellyfin-style
    `{Title} ({Year}) [tmdbid-N]` folder.
    """
    s = get_settings()
    year = film.year or ""
    if dest_dir:
        os.makedirs(dest_dir, exist_ok=True)
        base = os.path.basename(dest_dir.rstrip("/")) or _safe(film.title)
    else:
        base = _safe(f"{film.title} ({year})") if year else _safe(film.title)
        dest_dir = os.path.join(s.library_path, f"{base} [tmdbid-{film.tmdb_id}]")
        os.makedirs(dest_dir, exist_ok=True)
    ext = os.path.splitext(src)[1] or ".mkv"
    dest = os.path.join(dest_dir, _safe(base) + ext)
    shutil.move(src, dest)
    # tidy up the now-empty per-id working dir
    try:
        os.rmdir(os.path.dirname(src))
    except OSError:
        pass
    return dest
