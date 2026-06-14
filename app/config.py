"""Runtime configuration, sourced from environment variables.

Mirrors the *arr convention of env-driven config so it works the same locally
and in Docker.
"""
import os
from functools import lru_cache


def _bool(v: str | None, default: bool) -> bool:
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    # Where the SQLite database lives.
    db_path: str = os.getenv("YTA_DB_PATH", "/config/youtubarr.db")

    # Library destination (Jellyfin-style folders are created here).
    library_path: str = os.getenv("YTA_LIBRARY_PATH", "/movies")

    # Temp/working dir for in-progress downloads.
    download_path: str = os.getenv("YTA_DOWNLOAD_PATH", "/downloads/youtubarr")

    # Radarr integration (used to pull the "wanted" list).
    radarr_url: str = os.getenv("YTA_RADARR_URL", "").rstrip("/")
    radarr_api_key: str = os.getenv("YTA_RADARR_API_KEY", "")
    # Only consider films in this original language (empty = all).
    radarr_language: str = os.getenv("YTA_RADARR_LANGUAGE", "Turkish")

    # Decision-engine tuning.
    duration_tolerance: float = float(os.getenv("YTA_DURATION_TOLERANCE", "0.15"))
    min_duration_min: int = int(os.getenv("YTA_MIN_DURATION_MIN", "40"))
    min_title_overlap: float = float(os.getenv("YTA_MIN_TITLE_OVERLAP", "0.6"))
    accept_score: float = float(os.getenv("YTA_ACCEPT_SCORE", "0.6"))
    search_results: int = int(os.getenv("YTA_SEARCH_RESULTS", "12"))

    # yt-dlp download format.
    yt_format: str = os.getenv("YTA_YT_FORMAT", "bv*[height<=1080]+ba/b[height<=1080]/b")

    # Scheduler intervals (minutes); 0 disables.
    sync_interval_min: int = int(os.getenv("YTA_SYNC_INTERVAL_MIN", "360"))

    # Official / trusted channel name fragments (normalized contains-match).
    official_channels: list[str] = [
        c.strip() for c in os.getenv(
            "YTA_OFFICIAL_CHANNELS",
            "arzu film,turk sinemasi,dijital sanat,mars pictures,uzman filmcilik,"
            "most production,erler film,fono film",
        ).split(",") if c.strip()
    ]

    auto_download: bool = _bool(os.getenv("YTA_AUTO_DOWNLOAD"), False)


@lru_cache
def get_settings() -> Settings:
    return Settings()
