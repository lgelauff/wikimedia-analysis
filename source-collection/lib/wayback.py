"""
wayback.py — Wayback Machine snapshot lookup via CDX API and snapshot fetch.

Uses the CDX Server API instead of the availability API for snapshot selection.
CDX lets us filter to status=200 responses only (avoiding redirect/error snapshots),
and returns the most recent clean capture rather than whatever "closest" happens
to be — which can be a redirect chain or a soft-404.

CDX API docs: https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server
fetch_snapshot() fetches the snapshot and returns cleaned plain text.

Rate limiting: RateLimitRegistry enforces 1.5s between archive.org requests,
slightly more conservative than the wayback-edgi CDX limit (0.8 req/s).
"""

import ssl
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import certifi
import requests

from .ratelimits import RateLimitRegistry
from .text import html_to_text
from .http import get as http_get, _UA

_SSL_CTX = ssl.create_default_context(cafile=certifi.where())

_CDX_API = "https://web.archive.org/cdx/search/cdx"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def availability(url: str, rl: RateLimitRegistry, session: requests.Session | None = None) -> dict | None:
    """
    Find the most recent status=200 Wayback snapshot for url via CDX API.

    Filters out redirect and error snapshots, so the returned snapshot is
    guaranteed to be a clean capture. Returns:
        {"url": snapshot_url, "timestamp": "YYYYMMDDHHMMSS", "status": "200"}
    or None if no clean snapshot exists.
    """
    params = {
        "url": url,
        "output": "json",
        "filter": "statuscode:200",
        "fl": "timestamp,statuscode,original",
        "limit": "-1",   # most recent first when combined with from/to
        "fastLatest": "true",
    }
    cdx_url = _CDX_API + "?" + urllib.parse.urlencode(params)
    rl.wait(cdx_url)
    try:
        if session is not None:
            resp = session.get(cdx_url, headers={"User-Agent": _UA}, timeout=20)
            resp.raise_for_status()
            rows = resp.json()
        else:
            req = urllib.request.Request(cdx_url, headers={"User-Agent": _UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=20, context=_SSL_CTX) as r:
                import json
                rows = json.loads(r.read())
    except Exception:
        return None

    # CDX returns a list of lists; first row is the header, rest are results.
    # With limit=-1 and fastLatest=true we get the most recent match last.
    if not rows or len(rows) < 2:
        return None

    # Find the header row to map column names to indices
    header = rows[0]
    try:
        ts_idx = header.index("timestamp")
        st_idx = header.index("statuscode")
    except ValueError:
        return None

    # Last data row is the most recent snapshot
    row = rows[-1]
    timestamp = row[ts_idx]
    status = row[st_idx]

    snapshot_url = f"https://web.archive.org/web/{timestamp}/{url}"
    return {"url": snapshot_url, "timestamp": timestamp, "status": status}


def snapshot_age_days(timestamp: str) -> int:
    """Return how many days ago a Wayback timestamp (YYYYMMDDHHMMSS) was taken."""
    dt = datetime.strptime(timestamp[:14], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).days


def fetch_snapshot(snapshot_url: str, rl: RateLimitRegistry) -> str:
    """
    Fetch a Wayback snapshot and return cleaned plain text.

    Uses http_get() so rl.wait() and Retry-After handling are applied.
    """
    body, ct = http_get(snapshot_url, rl, accept="text/html")
    return html_to_text(body, content_type=ct)
