"""Background jobs: Radarr sync, search-wanted, and the download→import worker."""
from __future__ import annotations

import logging

from sqlmodel import Session, select

from ..db import engine
from ..models import DownloadJob, Film, FilmStatus, JobState
from ..config import get_settings
from ..decision.engine import DecisionEngine
from ..providers import notifier
from ..providers.downloader import YtDlpDownloader
from ..providers.indexer import YouTubeIndexer
from .importer import import_file, verify
from .matcher import match_and_store
from .radarr import RadarrClient

log = logging.getLogger("youtubarr.tasks")


def sync_from_radarr() -> dict:
    """Pull wanted films from Radarr and upsert them as Film rows."""
    client = RadarrClient()
    if not client.configured:
        return {"ok": False, "error": "Radarr yapılandırılmadı"}
    items = client.wanted_films()
    added = updated = 0
    with Session(engine) as s:
        for it in items:
            film = s.exec(select(Film).where(Film.tmdb_id == it["tmdb_id"])).first()
            if film:
                film.title = it["title"]
                film.original_title = it["original_title"]
                film.year = it["year"]
                film.runtime = it["runtime"]
                film.language = it["language"]
                s.add(film)
                updated += 1
            else:
                s.add(Film(status=FilmStatus.wanted, **it))
                added += 1
        s.commit()
    return {"ok": True, "added": added, "updated": updated, "total": len(items)}


def search_wanted(limit: int = 50) -> dict:
    """Run the matcher for wanted (unmatched) films."""
    results = []
    with Session(engine) as s:
        films = s.exec(
            select(Film).where(Film.status == FilmStatus.wanted, Film.monitored == True)  # noqa: E712
        ).all()[:limit]
        for film in films:
            try:
                results.append(match_and_store(film, s))
            except Exception as e:  # noqa: BLE001
                log.warning("search failed for %s: %s", film.title, e)
    matched = sum(1 for r in results if r["matched"])
    return {"ok": True, "searched": len(results), "matched": matched, "results": results}


def poll_channels() -> dict:
    """Fetch recent uploads from configured official channels and match them
    against still-wanted films (the RSS-sync equivalent)."""
    s = get_settings()
    if not s.channel_feeds:
        return {"ok": False, "error": "kanal feed'i yok"}
    indexer = YouTubeIndexer()
    engine_ = DecisionEngine()
    uploads = []
    for ch in s.channel_feeds:
        ups = indexer.channel_uploads(ch, s.channel_feed_limit)
        log.info("kanal %s: %s yükleme", ch, len(ups))
        uploads.extend(ups)
    matched = 0
    with Session(engine) as sess:
        wanted = sess.exec(
            select(Film).where(Film.status == FilmStatus.wanted, Film.monitored == True)  # noqa: E712
        ).all()
        threshold = s.accept_score
        for film in wanted:
            best = None
            for up in uploads:
                ev = engine_.evaluate(up, film)
                if ev.accepted and ev.score >= threshold and (not best or ev.score > best.score):
                    best = ev
            if best:
                film.status = FilmStatus.matched
                film.youtube_id = best.release.youtube_id
                film.youtube_title = best.release.title
                film.youtube_channel = best.release.channel
                film.match_score = round(best.score, 3)
                sess.add(film)
                matched += 1
        sess.commit()
    return {"ok": True, "channels": len(s.channel_feeds), "uploads": len(uploads), "matched": matched}


def run_download(film_id: int) -> None:
    """Download → verify → import a single film. Updates DownloadJob + Film."""
    dl = YtDlpDownloader()
    with Session(engine) as s:
        film = s.get(Film, film_id)
        if not film or not film.youtube_id:
            return
        job = DownloadJob(film_id=film.id, youtube_id=film.youtube_id, state=JobState.downloading)
        s.add(job)
        film.status = FilmStatus.downloading
        s.add(film)
        s.commit()
        s.refresh(job)
        job_id, yt_id, runtime = job.id, film.youtube_id, film.runtime
        notifier.notify_grabbed(film)

    def on_progress(p: dict):
        with Session(engine) as s:
            j = s.get(DownloadJob, job_id)
            if j:
                j.progress = p.get("progress", j.progress)
                j.speed = p.get("speed")
                j.eta = p.get("eta")
                s.add(j); s.commit()

    try:
        path = dl.download(yt_id, on_progress)
        _set_job(job_id, state=JobState.importing, progress=100.0, file_path=path)
        ok, msg = verify(path, runtime)
        if not ok:
            _fail(job_id, film_id, f"doğrulama başarısız: {msg}")
            return
        with Session(engine) as s:
            film = s.get(Film, film_id)
            dest = import_file(path, film)
            film.status = FilmStatus.imported
            film.library_path = dest
            s.add(film)
            j = s.get(DownloadJob, job_id)
            j.state = JobState.done
            j.file_path = dest
            s.add(j); s.commit()
            notifier.notify_imported(film, dest)
        log.info("imported %s -> %s", film_id, dest)
    except Exception as e:  # noqa: BLE001
        _fail(job_id, film_id, str(e))


def _set_job(job_id: int, **fields) -> None:
    with Session(engine) as s:
        j = s.get(DownloadJob, job_id)
        for k, v in fields.items():
            setattr(j, k, v)
        s.add(j); s.commit()


def _fail(job_id: int, film_id: int, message: str) -> None:
    log.warning("job %s failed: %s", job_id, message)
    with Session(engine) as s:
        j = s.get(DownloadJob, job_id)
        if j:
            j.state = JobState.failed
            j.message = message
            s.add(j)
        film = s.get(Film, film_id)
        if film:
            film.status = FilmStatus.failed
            s.add(film)
        s.commit()
        if film:
            notifier.notify_failed(film, message)
