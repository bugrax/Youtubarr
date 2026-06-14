# Youtubarr

An *arr-style automation app that **finds and downloads films from YouTube** and
delivers them into your media library (Jellyfin/Plex) — the same way Radarr does
for torrents/usenet, but with YouTube as the source.

The motivation: a huge catalogue of films — especially **Turkish / Yeşilçam
cinema** — is available *in full, in HD/4K, on official rights-holder channels*
(e.g. ARZU FİLM) on YouTube. Youtubarr discovers those uploads automatically,
verifies they are the real full film (not a clip or trailer), downloads them with
[yt-dlp](https://github.com/yt-dlp/yt-dlp), and organizes them for your library.

> Status: **early design / proof-of-concept.** The matching concept is validated
> (see below). The full application is under construction.

## Why it works

Films on YouTube can be told apart from clips/trailers/series-episodes with a few
strong signals:

- **Duration** must match the film's real runtime (from TMDB) within a tolerance
  → instantly filters out trailers, scenes, and edits.
- **Title token overlap** with the original title (Turkish-normalized) → filters
  out other films and series episodes.
- **Channel** — official/verified rights-holder channels rank highest.
- **View count** as a tie-breaker / popularity signal.

## Proof of concept

A standalone matcher ([`poc/find.py`](poc/find.py)) takes the *wanted* films from a
Radarr library, searches YouTube via `yt-dlp`, and scores candidates. Results on a
sample of 11 Turkish films:

| Film | Match | Duration (yt/TMDB) | Views | Channel |
|------|:-----:|:------------------:|------:|---------|
| Süt Kardeşler | ✅ | 81 / 80 min | 48M | ARZU FİLM *(official)* |
| Hababam Sınıfı Sınıfta Kaldı | ✅ | 92 / 91 min | 49M | ARZU FİLM *(official)* |
| Neşeli Günler | ✅ | 94 / 95 min | 48M | ARZU FİLM *(official)* |
| Şekerpare | ✅ | 90 / 90 min | 15M | ARZU FİLM *(official)* |
| Namuslu | ✅ | 90 / 93 min | 10M | UZMAN FİLMCİLİK *(restored)* |
| Issız Adam | ✅ | 104 / 113 min | 435K | Most Production |
| Tabutta Rövaşata | ✅ | 75 / 76 min | 83K | — |

False positives (series episodes whose title/duration coincidentally matched, e.g.
*Eşkıya* → "Eşkıya Dünyaya Hükümdar Olmaz") are eliminated by a "no series
episode" rule. The core idea — **duration + title + channel scoring** — proved
reliable, especially for the official Yeşilçam catalogue.

## Architecture

Youtubarr borrows its *concepts* (not its language) from Radarr/Sonarr (the
[Servarr](https://wiki.servarr.com) ecosystem):

- **Provider framework** — Indexers, Download clients and Notifiers share one
  pluggable shape (à la Servarr's *ThingiProvider*), with settings that
  auto-surface in the UI.
- **Specification-based decision pipeline** — many small, testable
  `is_satisfied_by(candidate, target) → Accept | Reject(reason)` rules, run in
  priority order with short-circuit and **explicit rejection reasons**. This is the
  heart of "did this YouTube result actually match the film?".
- **Command + event messaging** — scheduled jobs (search-wanted, channel poll,
  download worker) and live UI updates.
- **TMDB** as the canonical metadata source and primary key; its `runtime` drives
  the duration check.

### Mapping from Radarr

| Radarr | Youtubarr |
|--------|-----------|
| Indexer (Torznab/Newznab) | YouTube search via `yt-dlp ytsearch` + official-channel feeds |
| Release | `YoutubeRelease` (videoId, channel, duration, views, url) |
| Decision specifications | duration±tolerance, title-token, official-channel, min-duration, already-have |
| Quality profile | resolution/codec preference from yt-dlp formats |
| Download client (qBittorrent) | yt-dlp downloader |
| Metadata (TMDB) | TMDB (same) |
| Import lists | TMDB discover / Radarr *wanted* |
| Notifications | ntfy / webhook |

## Tech stack

- **Backend:** Python + FastAPI (yt-dlp used in-process), SQLite + Alembic,
  APScheduler.
- **Frontend:** React + Vite + TypeScript, live queue via SSE/WebSocket.
- **Deploy:** Docker, alongside an existing Radarr/Sonarr/Jellyfin setup.

## Roadmap

- [x] Validate YouTube matching concept (duration + title + channel)
- [x] Project scaffold (FastAPI backend, SQLite)
- [x] Wanted list via Radarr API sync (filter by original language)
- [x] Indexer: YouTube search (yt-dlp)
- [x] Decision engine: specifications with rejection reasons + scoring
- [x] Download client: yt-dlp worker with progress (+ subtitles)
- [x] Import: ffprobe verification + Jellyfin library rename
- [x] Minimal built-in web dashboard (wanted, search, queue)
- [x] Docker image + compose
- [ ] Indexer: official-channel feeds (poll for new uploads)
- [ ] Full React + Vite SPA (replace the built-in dashboard)
- [ ] Quality profiles (resolution/codec preference)
- [ ] Notifications (ntfy)
- [ ] TMDB import lists (independent of Radarr)

## Status

End-to-end working (validated locally against a real Radarr + on YouTube):
Radarr sync → YouTube search → decision → download → ffprobe verify → import.
Runs as a Docker container on the `media` network alongside Radarr/Sonarr.

### Configuration (environment variables)

| Var | Default | Meaning |
|-----|---------|---------|
| `YTA_RADARR_URL` | — | Radarr base URL (e.g. `http://radarr:7878`) |
| `YTA_RADARR_API_KEY` | — | Radarr API key |
| `YTA_RADARR_LANGUAGE` | `Turkish` | Only sync films with this original language (empty = all) |
| `YTA_LIBRARY_PATH` | `/movies` | Library destination |
| `YTA_DOWNLOAD_PATH` | `/downloads/youtubarr` | Working dir |
| `YTA_DURATION_TOLERANCE` | `0.15` | Allowed runtime deviation |
| `YTA_MIN_TITLE_OVERLAP` | `0.6` | Min title-token overlap to accept |
| `YTA_ACCEPT_SCORE` | `0.6` | Min score to auto-accept a match |
| `YTA_AUTO_DOWNLOAD` | `false` | Auto-grab matched films on each cycle |
| `YTA_SYNC_INTERVAL_MIN` | `360` | Scheduler interval (0 = disabled) |

### Run with Docker

```bash
cp .env.example .env   # put your Radarr API key in it
docker compose up -d --build
# dashboard at http://localhost:8585
```

## Running the PoC

```bash
pip install -U yt-dlp
# Provide a JSON list of target films at /tmp/targets.json
# (objects with: originalTitle, title, year, runtime, tmdbId)
python poc/find.py
```

## License

MIT — see [LICENSE](LICENSE).
