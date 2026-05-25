"""
http.py — low-level rate-limited HTTP GET.

Returns (body_bytes, content_type) so callers can decide how to handle the
response without re-checking the URL extension (e.g. a .pdf URL that returns
text/html is a download landing page, not a PDF).
"""

import ssl
import urllib.parse
import urllib.request

import certifi

from .ratelimits import RateLimitRegistry

_SSL_CTX = ssl.create_default_context(cafile=certifi.where())
_UA = "WikimediaAnalysis/1.0 (personal research; lodewijk@stanford.edu; https://github.com/lgelauff/wikimedia-analysis)"


def netloc(url: str) -> str:
    """Return scheme://host for use as a rate-limit domain key."""
    p = urllib.parse.urlparse(url)
    return f"{p.scheme}://{p.netloc}"


def get(url: str, rl: RateLimitRegistry, accept: str = "text/html") -> tuple[bytes, str]:
    """
    Rate-limited HTTP GET.

    Applies rl.wait(url) before the request to enforce per-domain spacing.
    Returns (body_bytes, content_type) where content_type is lowercased.
    """
    rl.wait(url)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": _UA, "Accept": accept},
    )
    with urllib.request.urlopen(req, timeout=20, context=_SSL_CTX) as resp:
        body = resp.read()
        ct = resp.headers.get("Content-Type", "").lower()
    return body, ct
