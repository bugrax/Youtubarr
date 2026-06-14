"""Diagnose match rate: for every wanted film show best candidate + why missed."""
import os
os.environ.setdefault("YTA_DB_PATH", "/config/youtubarr.db")
from collections import Counter

from sqlmodel import Session, select

from app.db import engine, init_db
from app.models import Film, FilmStatus
from app.services.matcher import find_matches

init_db()
matched = missed = 0
reasons = Counter()
miss_lines = []
with Session(engine) as s:
    films = s.exec(select(Film)).all()
    for f in films:
        if f.status == FilmStatus.imported:
            continue
        best, evals = find_matches(f, s)
        if best:
            matched += 1
        else:
            missed += 1
            # why? look at the top candidate by score-ish
            cand = sorted(evals, key=lambda e: (e.accepted, e.score), reverse=True)
            top = cand[0] if cand else None
            if not evals:
                reasons["no YouTube results at all"] += 1
                why = "no results"
            elif top and top.accepted:
                reasons["below accept threshold"] += 1
                why = f"best score {top.score:.2f} < threshold"
            else:
                rej = top.rejections[0] if top and top.rejections else "?"
                reasons[rej] += 1
                why = f"{len(evals)} cand, top rejected: {rej}"
            miss_lines.append(f"  MISS {f.original_title or f.title} ({f.year}) {f.runtime}min -> {why}")

print(f"=== MATCHABLE NOW: {matched} | MISSED: {missed} ===\n")
print("Miss reasons:")
for r, c in reasons.most_common():
    print(f"  {c:3d}  {r}")
print("\nMisses:")
print("\n".join(miss_lines))
