"""
memento.py — find an archived copy of a URL via the Memento Time Travel
aggregator, which federates many web archives (Wayback, Archive.today,
Library of Congress, UK Web Archive, Bibliotheca Alexandrina, …).

One query → the best memento across all participating archives, so it reaches
pages the Internet Archive alone has not captured.

API: http://timetravel.mementoweb.org/  (TimeGate / aggregator)
Best-effort: returns None on any failure.
"""

import urllib.parse

import requests

from .ratelimits import RateLimitRegistry
from .http import _UA
from .text import html_to_text

# Aggregator TimeGate: returns the memento closest to the given datetime.
_TIMEGATE = "http://timetravel.mementoweb.org/timegate/"


def find_memento(url: str, rl: RateLimitRegistry, session: requests.Session | None = None) -> str | None:
    """Return the URL of an archived memento for `url`, or None."""
    url = url.strip()
    if not url:
        return None
    gate = _TIMEGATE + url
    rl.wait(gate)
    try:
        getter = session.get if session is not None else requests.get
        # allow_redirects=False: the TimeGate answers with the memento in Location
        # or a Link header; we read whichever is present.
        resp = getter(gate, headers={"User-Agent": _UA}, timeout=20, allow_redirects=False)
    except Exception:
        return None
    loc = resp.headers.get("Location")
    if loc:
        return loc
    # Parse the Link header for rel="memento"
    link = resp.headers.get("Link", "")
    m = _first_memento(link)
    return m


def _first_memento(link_header: str) -> str | None:
    for part in link_header.split(","):
        if 'rel="memento"' in part or "rel=memento" in part:
            lt = part.find("<")
            gt = part.find(">", lt + 1)
            if lt != -1 and gt != -1:
                return part[lt + 1:gt]
    return None


def fetch_text(url: str, rl: RateLimitRegistry, session: requests.Session | None = None) -> tuple[str, str] | None:
    """Find a memento and return (cleaned_text, memento_url). None on miss."""
    memento = find_memento(url, rl, session)
    if not memento:
        return None
    rl.wait(memento)
    try:
        getter = session.get if session is not None else requests.get
        resp = getter(memento, headers={"User-Agent": _UA}, timeout=25)
        resp.raise_for_status()
        ct = resp.headers.get("Content-Type", "").lower()
        text = html_to_text(resp.content, content_type=ct)
    except Exception:
        return None
    return text, memento
