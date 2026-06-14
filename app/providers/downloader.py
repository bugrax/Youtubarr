"""yt-dlp download client — the Servarr 'DownloadClient' equivalent.

Runs yt-dlp as a SUBPROCESS (one process per download). The in-process
yt_dlp.YoutubeDL API is not safe to run concurrently across threads — two
parallel downloads in the same interpreter race on temp/rename operations and
fail ("Unable to rename ... No such file"). A separate process per download is
fully isolated and safe to run in parallel.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from collections.abc import Callable

from ..config import get_settings

ProgressCb = Callable[[dict], None]

# [download]  12.3% of ~600.00MiB at 4.50MiB/s ETA 02:10
_PROG = re.compile(r"\[download\]\s+([\d.]+)%\s+of\s+\S+\s+at\s+(\S+)\s+ETA\s+(\S+)")
_VIDEO_EXT = (".mkv", ".mp4", ".webm", ".avi", ".m4v")


class YtDlpDownloader:
    name = "yt-dlp"

    def __init__(self):
        self.s = get_settings()
        os.makedirs(self.s.download_path, exist_ok=True)

    def download(self, youtube_id: str, on_progress: ProgressCb | None = None) -> str:
        """Download a video; return the final merged file path. Raises on failure."""
        # Fresh per-video dir each time so a stale .part can't break the run.
        vid_dir = os.path.join(self.s.download_path, youtube_id)
        shutil.rmtree(vid_dir, ignore_errors=True)
        os.makedirs(vid_dir, exist_ok=True)

        cmd = [
            "yt-dlp",
            "-f", self.s.yt_format,
            "--merge-output-format", "mkv",
            "-o", os.path.join(vid_dir, "%(id)s.%(ext)s"),
            "--no-playlist", "--newline", "--no-warnings",
            "--no-progress",  # we read our own; avoids carriage-return spam
            "--progress",
            "--retries", "5", "--fragment-retries", "5",
            "--write-subs", "--sub-langs", "tr,en", "--no-write-auto-subs",
            f"https://www.youtube.com/watch?v={youtube_id}",
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        tail: list[str] = []
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.rstrip("\n")
            tail.append(line)
            if len(tail) > 30:
                tail.pop(0)
            m = _PROG.search(line)
            if m and on_progress:
                on_progress({
                    "progress": round(float(m.group(1)), 1),
                    "speed": m.group(2),
                    "eta": m.group(3),
                })
        rc = proc.wait()
        if rc != 0:
            raise RuntimeError("yt-dlp çıkış kodu %s: %s" % (rc, " | ".join(tail[-5:])))

        # pick the largest finished video file (the merged output)
        finished = [
            os.path.join(vid_dir, f) for f in os.listdir(vid_dir)
            if f.lower().endswith(_VIDEO_EXT) and not f.endswith(".part")
        ]
        if not finished:
            raise RuntimeError("indirme bitti ama video dosyası yok")
        return max(finished, key=os.path.getsize)
