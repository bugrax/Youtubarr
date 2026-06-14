"""For each still-wanted film, show top YouTube candidates and why they fail."""
import os, sys
os.environ.setdefault("YTA_DB_PATH", "/config/youtubarr.db")
from sqlmodel import Session, select

from app.db import engine, init_db
from app.models import Film, FilmStatus
from app.providers.indexer import YouTubeIndexer
from app.decision.engine import DecisionEngine

init_db()
idx = YouTubeIndexer()
eng = DecisionEngine()

with Session(engine) as s:
    wanted = s.exec(select(Film).where(Film.status == FilmStatus.wanted)).all()

print(f"=== {len(wanted)} eşleşmeyen film ===\n", flush=True)
for f in wanted:
    rels = idx.search_film(f.original_title, f.title, f.year)
    evals = sorted((eng.evaluate(r, f) for r in rels), key=lambda e: e.score, reverse=True)
    print(f"### {f.original_title} ({f.year}) {f.runtime}min  [{len(rels)} sonuç]", flush=True)
    if not rels:
        print("   ❌ YouTube'da hiç sonuç yok\n", flush=True)
        continue
    # show top 3 candidates with verdict
    for e in evals[:3]:
        r = e.release
        verdict = "KABUL" if e.accepted else "RET: " + "; ".join(e.rejections)
        print(f"   {round(r.duration_min):>4}min  {r.view_count:>10,}  [{r.channel[:22]:22}] {r.title[:40]}", flush=True)
        print(f"        -> score {e.score:.2f}  {verdict}", flush=True)
    print(flush=True)
print("DONE", flush=True)
