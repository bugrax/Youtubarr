"""Notifier — pushes events to ntfy (the Servarr 'Notification' equivalent)."""
from __future__ import annotations

import logging

import httpx

from ..config import get_settings

log = logging.getLogger("youtubarr.notify")


def _send(title: str, message: str, priority: str = "default", tags: str = "") -> None:
    s = get_settings()
    if not s.ntfy_topic:
        return
    try:
        httpx.post(
            f"{s.ntfy_url}/{s.ntfy_topic}",
            content=message.encode("utf-8"),
            # HTTP headers must be latin-1; ntfy reads UTF-8 titles from X-Title
            # only as latin-1, so keep Title ASCII and use Tags for the icon.
            headers={
                "Title": title.encode("ascii", "ignore").decode().strip() or "Youtubarr",
                "Priority": priority,
                "Tags": tags,
            },
            timeout=10,
        )
    except Exception as e:  # noqa: BLE001
        log.warning("ntfy gönderilemedi: %s", e)


def notify_imported(film, path: str) -> None:  # noqa: ANN001
    _send(
        "🎬 Youtubarr: film eklendi",
        f"{film.title} ({film.year or '?'})\nKanal: {film.youtube_channel or '-'}",
        priority="default", tags="clapper,white_check_mark",
    )


def notify_failed(film, message: str) -> None:  # noqa: ANN001
    _send(
        "⚠️ Youtubarr: indirme başarısız",
        f"{film.title} ({film.year or '?'})\n{message}",
        priority="high", tags="warning",
    )


def notify_grabbed(film) -> None:  # noqa: ANN001
    _send(
        "⬇️ Youtubarr: indirme başladı",
        f"{film.title} ({film.year or '?'})\n{film.youtube_title or ''}",
        priority="low", tags="arrow_down",
    )
