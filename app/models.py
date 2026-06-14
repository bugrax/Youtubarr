"""Database models (SQLModel)."""
from datetime import datetime, timezone
from enum import Enum

from sqlmodel import Field, SQLModel


def _now() -> datetime:
    return datetime.now(timezone.utc)


class FilmStatus(str, Enum):
    wanted = "wanted"          # we want it, nothing found/grabbed yet
    matched = "matched"        # a good YouTube release was found
    downloading = "downloading"
    imported = "imported"      # in the library
    failed = "failed"


class Film(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    tmdb_id: int = Field(index=True, unique=True)
    title: str
    original_title: str = ""
    year: int | None = None
    runtime: int = 0           # minutes, from TMDB/Radarr
    language: str = ""
    status: FilmStatus = Field(default=FilmStatus.wanted, index=True)
    # Chosen YouTube release (when matched/imported)
    youtube_id: str | None = None
    youtube_title: str | None = None
    youtube_channel: str | None = None
    match_score: float | None = None
    library_path: str | None = None
    monitored: bool = True
    source: str = "radarr"     # where this wanted item came from
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class JobState(str, Enum):
    queued = "queued"
    downloading = "downloading"
    importing = "importing"
    done = "done"
    failed = "failed"


class DownloadJob(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    film_id: int = Field(index=True)
    youtube_id: str
    state: JobState = Field(default=JobState.queued, index=True)
    progress: float = 0.0      # 0..100
    speed: str | None = None
    eta: str | None = None
    message: str | None = None
    file_path: str | None = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class Blocklist(SQLModel, table=True):
    """YouTube videos rejected by the user / failed import, never re-grab."""
    id: int | None = Field(default=None, primary_key=True)
    youtube_id: str = Field(index=True, unique=True)
    film_id: int | None = None
    reason: str = ""
    created_at: datetime = Field(default_factory=_now)
