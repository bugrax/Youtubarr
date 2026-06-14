"""yt-dlp download client — the Servarr 'DownloadClient' equivalent."""
from __future__ import annotations

import os
import re
from collections.abc import Callable

import yt_dlp

from ..config import get_settings

ProgressCb = Callable[[dict], None]

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


class YtDlpDownloader:
    name = "yt-dlp"

    def __init__(self):
        self.s = get_settings()
        os.makedirs(self.s.download_path, exist_ok=True)

    def download(self, youtube_id: str, on_progress: ProgressCb | None = None) -> str:
        """Download a video; return the final file path. Raises on failure."""
        outtmpl = os.path.join(self.s.download_path, "%(id)s", "%(title)s [%(id)s].%(ext)s")
        result_path: dict[str, str] = {}

        def _hook(d: dict):
            if d.get("status") == "downloading" and on_progress:
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                done = d.get("downloaded_bytes") or 0
                pct = (done / total * 100) if total else 0.0
                on_progress({
                    "progress": round(pct, 1),
                    "speed": _ANSI.sub("", d.get("_speed_str", "") or "").strip(),
                    "eta": _ANSI.sub("", d.get("_eta_str", "") or "").strip(),
                })
            elif d.get("status") == "finished":
                result_path["path"] = d.get("filename", "")

        opts = {
            "format": self.s.yt_format,
            "outtmpl": outtmpl,
            "merge_output_format": "mkv",
            "noprogress": True,
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [_hook],
            "writesubtitles": True,
            "subtacklanguages": ["tr", "en"],
            "writethumbnail": False,
            "retries": 5,
            "fragment_retries": 5,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={youtube_id}", download=True)
            final = ydl.prepare_filename(info)
            # account for merge remux to mkv
            base, _ = os.path.splitext(final)
            for cand in (base + ".mkv", final, result_path.get("path", "")):
                if cand and os.path.exists(cand):
                    return cand
        raise RuntimeError("indirme tamamlandı ama dosya bulunamadı")

    def probe_duration(self, youtube_id: str) -> int:
        """Return the video duration in seconds without downloading (0 if unknown)."""
        opts = {"quiet": True, "no_warnings": True, "skip_download": True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={youtube_id}", download=False)
            return int(info.get("duration") or 0)
