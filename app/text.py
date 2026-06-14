"""Turkish-aware text normalization and tokenization for title matching."""
import re
import unicodedata

# Words that appear in YouTube upload titles but carry no film-identity signal.
_STOPWORDS = {
    "the", "a", "an", "of", "and", "ve", "ile",
    "film", "filmi", "filmler", "movie", "full", "hd", "fullhd", "4k", "1080p", "720p",
    "izle", "izleyin", "tek", "parca", "parça", "kesintisiz", "restorasyon",
    "restorasyonlu", "restore", "turk", "türk", "yerli", "sinema", "klasik",
    "official", "resmi", "kanal", "yeni",
}

# Markers that strongly indicate a TV-series episode rather than a film.
SERIES_MARKERS = (
    "bölüm", "bolum", "sezon", "season", "episode", "bölümü", "fragman",
    "fragmanı", "teaser", "klip", "sahne", "sahnesi", "kısa", "özet", "tanıtım",
)

_TR_MAP = str.maketrans({
    "ı": "i", "İ": "i", "I": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g",
    "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "ç": "c", "Ç": "c", "â": "a", "î": "i", "û": "u",
})


def normalize(s: str) -> str:
    """Lowercase, fold Turkish characters to ASCII, strip punctuation."""
    if not s:
        return ""
    s = s.translate(_TR_MAP).lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def tokens(s: str) -> list[str]:
    """Significant tokens of a title (stopwords and 1-char tokens removed).

    Consecutive single letters are merged into one token so acronym titles like
    "G.O.R.A." ("g o r a" → "gora") or "C.M.Y.L.M.Z" survive tokenization instead
    of being dropped as 1-char noise.
    """
    raw = normalize(s).split()
    merged: list[str] = []
    buf: list[str] = []
    for t in raw:
        if len(t) == 1:
            buf.append(t)
            continue
        if buf:
            merged.append("".join(buf))
            buf = []
        merged.append(t)
    if buf:
        merged.append("".join(buf))
    return [t for t in merged if len(t) > 1 and t not in _STOPWORDS]


def title_overlap(film_title: str, candidate_title: str) -> float:
    """Fraction of the film's title tokens present in the candidate title (0..1)."""
    ftok = set(tokens(film_title))
    if not ftok:
        return 0.0
    ctok = set(tokens(candidate_title))
    return len(ftok & ctok) / len(ftok)


def looks_like_series(candidate_title: str) -> bool:
    low = " " + normalize(candidate_title) + " "
    raw = (candidate_title or "").lower()
    if any(m in raw for m in SERIES_MARKERS):
        return True
    # "190. bölüm" style or "1.sezon"
    return bool(re.search(r"\b\d+\s*(bolum|sezon|season|episode)\b", low))
