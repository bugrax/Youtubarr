"""Youtubarr — FastAPI application entry point."""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from starlette.requests import Request

from .config import get_settings
from .db import engine, get_session, init_db
from .models import Blocklist, DownloadJob, Film, FilmStatus
from .services import tasks
from .services.matcher import match_and_store
from .services.radarr import RadarrClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("youtubarr")

_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="dl")
_scheduler = BackgroundScheduler()
_BASE = Path(__file__).parent
templates = Jinja2Templates(directory=str(_BASE / "web" / "templates"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    s = get_settings()
    if s.sync_interval_min > 0:
        _scheduler.add_job(_scheduled_cycle, "interval", minutes=s.sync_interval_min,
                           id="cycle", next_run_time=None)
        _scheduler.start()
        log.info("scheduler started (%s dk)", s.sync_interval_min)
    yield
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
    _pool.shutdown(wait=False)


def _scheduled_cycle():
    tasks.sync_from_radarr()
    res = tasks.search_wanted()
    if get_settings().auto_download:
        with Session(engine) as s:
            matched = s.exec(select(Film).where(Film.status == FilmStatus.matched)).all()
            for f in matched:
                _pool.submit(tasks.run_download, f.id)
    log.info("scheduled cycle: %s", res.get("matched"))


app = FastAPI(title="Youtubarr", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(_BASE / "web" / "static")), name="static")


# ---- UI ------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ---- API -----------------------------------------------------------------

@app.get("/api/health")
def health():
    rc = RadarrClient()
    radarr = {"configured": rc.configured}
    if rc.configured:
        try:
            st = rc.ping()
            radarr["ok"] = True
            radarr["version"] = st.get("version")
        except Exception as e:  # noqa: BLE001
            radarr["ok"] = False
            radarr["error"] = str(e)
    return {"app": "youtubarr", "version": "0.1.0", "radarr": radarr}


@app.post("/api/sync")
def sync():
    return tasks.sync_from_radarr()


@app.post("/api/search")
def search(limit: int = 50):
    return tasks.search_wanted(limit=limit)


@app.get("/api/films")
def list_films(status: str | None = None, session: Session = Depends(get_session)):
    q = select(Film)
    if status:
        q = q.where(Film.status == status)
    films = session.exec(q.order_by(Film.match_score.desc())).all()
    return films


@app.get("/api/films/{film_id}/search")
def search_one(film_id: int, session: Session = Depends(get_session)):
    film = session.get(Film, film_id)
    if not film:
        raise HTTPException(404, "film yok")
    return match_and_store(film, session)


@app.post("/api/films/{film_id}/grab")
def grab(film_id: int, session: Session = Depends(get_session)):
    film = session.get(Film, film_id)
    if not film:
        raise HTTPException(404, "film yok")
    if not film.youtube_id:
        raise HTTPException(400, "önce eşleştir (search)")
    _pool.submit(tasks.run_download, film_id)
    return {"ok": True, "queued": film_id, "youtube_id": film.youtube_id}


@app.post("/api/films/{film_id}/blocklist")
def blocklist(film_id: int, session: Session = Depends(get_session)):
    film = session.get(Film, film_id)
    if not film or not film.youtube_id:
        raise HTTPException(404, "eşleşme yok")
    session.add(Blocklist(youtube_id=film.youtube_id, film_id=film_id, reason="manual"))
    film.status = FilmStatus.wanted
    film.youtube_id = film.youtube_title = film.youtube_channel = None
    film.match_score = None
    session.add(film)
    session.commit()
    return {"ok": True}


@app.get("/api/jobs")
def jobs(session: Session = Depends(get_session)):
    return session.exec(select(DownloadJob).order_by(DownloadJob.id.desc())).all()


@app.get("/api/stats")
def stats(session: Session = Depends(get_session)):
    out = {}
    for st in FilmStatus:
        out[st.value] = len(session.exec(select(Film).where(Film.status == st)).all())
    return out
