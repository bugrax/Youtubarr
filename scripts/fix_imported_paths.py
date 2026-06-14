"""Relocate already-imported films into Radarr's exact folder + rescan."""
import os, shutil
os.environ.setdefault("YTA_DB_PATH", "/config/youtubarr.db")
from sqlmodel import Session, select

from app.db import engine, init_db
from app.models import Film, FilmStatus
from app.services.radarr import RadarrClient
from app.services.importer import _safe

init_db()
rc = RadarrClient()
with Session(engine) as s:
    for f in s.exec(select(Film).where(Film.status == FilmStatus.imported)).all():
        if not f.library_path or not os.path.exists(f.library_path):
            continue
        m = rc.get_movie(f.tmdb_id)
        if not m:
            continue
        target_dir = m["path"]
        base = os.path.basename(target_dir.rstrip("/"))
        ext = os.path.splitext(f.library_path)[1]
        target = os.path.join(target_dir, _safe(base) + ext)
        if os.path.abspath(target) == os.path.abspath(f.library_path):
            print("ok zaten doğru:", base); continue
        os.makedirs(target_dir, exist_ok=True)
        shutil.move(f.library_path, target)
        old_dir = os.path.dirname(f.library_path)
        try:
            os.rmdir(old_dir)
        except OSError:
            pass
        f.library_path = target
        s.add(f); s.commit()
        rc.rescan_movie(m["id"])
        print("taşındı + rescan:", base)
print("bitti")
