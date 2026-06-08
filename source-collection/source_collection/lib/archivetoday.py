"""
archivetoday.py — look up an archived copy on archive.today (archive.ph).

archive.today captures many news / JS-heavy / soft-paywalled pages the Internet
Archive misses, so it is a useful complement. There is no official API; we use
the public `…/newest/<url>` redirect endpoint. Best-effort: returns None on any
failure (including the occasional bot block).
"""

import requests

from .ratelimits import RateLimitRegistry
from .http import _UA
from .text import html_to_text

_BASE = "https://archive.ph"


def newest(url: str, rl: RateLimitRegistry, session: requests.Session | None = None) -> str | None:
    """Return the URL of the newest archive.today snapshot for `url`, or None."""
    url = url.strip()
    if not url:
        return None
    lookup = f"{_BASE}/newest/{url}"
    rl.wait(lookup)
    try:
        getter = session.get if session is not None else requests.get
        resp = getter(lookup, headers={"User-Agent": _UA}, timeout=20)
    except Exception:
        return None
    # A hit redirects to the snapshot page; a miss returns the search/landing page.
    final = resp.url
    if "/newest/" in final or final.rstrip("/") == _BASE:
        return None
    return final


def fetch_text(url: str, rl: RateLimitRegistry, session: requests.Session | None = None) -> tuple[str, str] | None:
    """Find newest archive.today snapshot and return (text, snapshot_url). None on miss."""
    snap = newest(url, rl, session)
    if not snap:
        return None
    rl.wait(snap)
    try:
        getter = session.get if session is not None else requests.get
        resp = getter(snap, headers={"User-Agent": _UA}, timeout=25)
        resp.raise_for_status()
        ct = resp.headers.get("Content-Type", "").lower()
        text = html_to_text(resp.content, content_type=ct)
    except Exception:
        return None
    return text, snap
