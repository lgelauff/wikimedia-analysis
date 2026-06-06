"""
wayback.py — Wayback Machine availability check and snapshot fetch.

availability() uses the Wayback availability API directly (urllib, 20s timeout)
— fast, reliable, no external dependency for a simple freshness check.

fetch_snapshot() uses the `wayback` package by EDGI for its built-in rate
limiting on memento fetches (8 req/s), falling back to http_get if not installed.
Our RateLimitRegistry enforces 1.5s between archive.org requests regardless,
which is more conservative than their 1.25s CDX limit.

EDGI wayback package: https://github.com/edgi-govdata-archiving/wayback
"""

import json
import ssl
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import certifi

from .ratelimits import RateLimitRegistry
from .text import html_to_text
from .http import get as http_get, _UA

_SSL_CTX = ssl.create_default_context(cafile=certifi.where())

_AVAILABILITY_API = "https://archive.org/wayback/available?url={}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def availability(url: str, rl: RateLimitRegistry) -> dict | None:
    """
    Query the Wayback availability API for the most recent snapshot of url.

    Returns {"url": snapshot_url, "timestamp": "YYYYMMDDHHMMSS", "status": "200"}
    or None if no snapshot exists.

    Uses urllib directly (20s timeout) so we control the timeout precisely.
    Applies rl.wait() before the request.
    """
    api_url = _AVAILABILITY_API.format(urllib.parse.quote(url, safe=":/?=&#"))
    rl.wait(api_url)
    try:
        req = urllib.request.Request(
            api_url,
            headers={"User-Agent": _UA, "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=20, context=_SSL_CTX) as resp:
            data = json.loads(resp.read())
    except Exception:
        return None

    snap = data.get("archived_snapshots", {}).get("closest", {})
    if snap.get("available"):
        return {
            "url": snap["url"],
            "timestamp": snap["timestamp"],
            "status": snap.get("status", "200"),
        }
    return None


def snapshot_age_days(timestamp: str) -> int:
    """Return how many days ago a Wayback timestamp (YYYYMMDDHHMMSS) was taken."""
    dt = datetime.strptime(timestamp[:14], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).days


def fetch_snapshot(snapshot_url: str, rl: RateLimitRegistry) -> str:
    """
    Fetch a Wayback snapshot and return cleaned plain text.

    Uses http_get() so rl.wait() is applied before the request.
    """
    body, ct = http_get(snapshot_url, rl, accept="text/html")
    return html_to_text(body, content_type=ct)
