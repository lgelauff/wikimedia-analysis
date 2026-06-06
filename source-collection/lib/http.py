"""
http.py — low-level rate-limited HTTP GET with Retry-After support.

Returns (body_bytes, content_type) so callers can decide how to handle the
response without re-checking the URL extension (e.g. a .pdf URL that returns
text/html is a download landing page, not a PDF).

On HTTP 429 or 503, respects the Retry-After response header (integer seconds
or HTTP-date) before retrying — up to MAX_RETRIES times. This avoids hammering
a domain with a fixed delay when the server itself is telling us how long to wait.
"""

import email.utils
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import certifi

from .ratelimits import RateLimitRegistry

_SSL_CTX = ssl.create_default_context(cafile=certifi.where())
_UA = "WikimediaAnalysis/1.0 (personal research; lodewijk@stanford.edu; https://github.com/lgelauff/wikimedia-analysis)"

MAX_RETRIES = 3
MAX_RETRY_WAIT = 120  # never wait more than 2 minutes on a single Retry-After


def netloc(url: str) -> str:
    """Return scheme://host for use as a rate-limit domain key."""
    p = urllib.parse.urlparse(url)
    return f"{p.scheme}://{p.netloc}"


def _parse_retry_after(header: str) -> float:
    """Parse a Retry-After header value (integer seconds or HTTP-date)."""
    header = header.strip()
    if header.isdigit():
        return float(header)
    try:
        dt = email.utils.parsedate_to_datetime(header)
        wait = (dt - datetime.now(timezone.utc)).total_seconds()
        return max(0.0, wait)
    except Exception:
        return 5.0  # fallback if unparseable


def get(url: str, rl: RateLimitRegistry, accept: str = "text/html") -> tuple[bytes, str]:
    """
    Rate-limited HTTP GET with Retry-After support.

    Applies rl.wait(url) before each attempt to enforce per-domain spacing.
    On 429/503, reads Retry-After header and sleeps accordingly before retrying
    (capped at MAX_RETRY_WAIT seconds). Raises urllib.error.HTTPError after
    MAX_RETRIES exhausted.

    Returns (body_bytes, content_type) where content_type is lowercased.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        rl.wait(url)
        req = urllib.request.Request(
            url,
            headers={"User-Agent": _UA, "Accept": accept},
        )
        try:
            with urllib.request.urlopen(req, timeout=20, context=_SSL_CTX) as resp:
                body = resp.read()
                ct = resp.headers.get("Content-Type", "").lower()
            return body, ct
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 503) and attempt < MAX_RETRIES:
                wait = min(
                    _parse_retry_after(exc.headers.get("Retry-After", "5")),
                    MAX_RETRY_WAIT,
                )
                print(f"    HTTP {exc.code} — Retry-After {wait:.0f}s (attempt {attempt}/{MAX_RETRIES})", end=" ", flush=True)
                time.sleep(wait)
                continue
            raise
