"""End-to-end test of the download→verify→import pipeline (no HTTP server)."""
import os
os.environ.setdefault("YTA_DB_PATH", "/root/youtubarr/data/youtubarr.db")
os.environ.setdefault("YTA_LIBRARY_PATH", "/root/youtubarr/data/library")
os.environ.setdefault("YTA_DOWNLOAD_PATH", "/root/youtubarr/data/downloads")
os.environ.setdefault("YTA_RADARR_URL", "http://192.168.68.72:7878")
os.environ.setdefault("YTA_RADARR_API_KEY", "1eed942099954c5aad386a8da11d58b1")
# small/fast format for the test
os.environ.setdefault("YTA_YT_FORMAT", "bv*[height<=360]+ba/b[height<=360]/worst")

from sqlmodel import Session, select  # noqa: E402

from app.db import engine, init_db  # noqa: E402
from app.models import DownloadJob, Film  # noqa: E402
from app.services import tasks  # noqa: E402
from app.services.matcher import match_and_store  # noqa: E402

init_db()
TITLE = "Süt Kardeşler"

with Session(engine) as s:
    film = s.exec(select(Film).where(Film.original_title == TITLE)).first()
    if not film:
        # ensure synced
        tasks.sync_from_radarr()
        film = s.exec(select(Film).where(Film.original_title == TITLE)).first()
    print(f"film: {film.original_title} ({film.year}) {film.runtime}dk  id={film.id}")
    rep = match_and_store(film, s)
    b = rep["best"]
    assert b, "eşleşme bulunamadı"
    print(f"eşleşme: {b['title']} [{b['channel']}] {b['duration_min']}dk skor={b['score']}")
    fid = film.id

print("indirme başlıyor (360p test)...")
tasks.run_download(fid)

with Session(engine) as s:
    film = s.get(Film, fid)
    job = s.exec(select(DownloadJob).where(DownloadJob.film_id == fid)
                 .order_by(DownloadJob.id.desc())).first()
    print("\n=== SONUÇ ===")
    print("film durumu:", film.status)
    print("kütüphane yolu:", film.library_path)
    print("job durumu:", job.state, "| mesaj:", job.message)
    if film.library_path and os.path.exists(film.library_path):
        sz = os.path.getsize(film.library_path) / 1e6
        print(f"DOSYA VAR ✅ {sz:.0f} MB")
    else:
        print("DOSYA YOK ❌")
