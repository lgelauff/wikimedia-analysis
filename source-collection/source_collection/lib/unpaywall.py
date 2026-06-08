"""
unpaywall.py — resolve a DOI to its open-access PDF via the Unpaywall API.

For scholarly sources a legal OA PDF beats any web-archive HTML snapshot.
Unpaywall requires an email query param (no key). Best-effort: returns None on
any failure so the caller falls through to the next pipeline stage.

API: https://unpaywall.org/products/api
"""

import urllib.parse

import requests

from .ratelimits import RateLimitRegistry
from .http import _UA
from .text import pdf_to_text

_API = "https://api.unpaywall.org/v2/"
_EMAIL = "lodewijk@stanford.edu"


def best_oa_pdf_url(doi: str, rl: RateLimitRegistry, session: requests.Session | None = None) -> str | None:
    """Return the best open-access PDF URL for a DOI, or None."""
    doi = doi.strip()
    if not doi:
        return None
    api_url = _API + urllib.parse.quote(doi, safe="") + "?email=" + urllib.parse.quote(_EMAIL)
    rl.wait(api_url)
    try:
        getter = session.get if session is not None else requests.get
        resp = getter(api_url, headers={"User-Agent": _UA}, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return None
    loc = data.get("best_oa_location") or {}
    return loc.get("url_for_pdf") or loc.get("url")


def fetch_text(doi: str, rl: RateLimitRegistry, session: requests.Session | None = None) -> tuple[str, str] | None:
    """Resolve DOI → OA PDF, download it, return (text, pdf_bytes_url). None on miss."""
    pdf_url = best_oa_pdf_url(doi, rl, session)
    if not pdf_url:
        return None
    rl.wait(pdf_url)
    try:
        getter = session.get if session is not None else requests.get
        resp = getter(pdf_url, headers={"User-Agent": _UA}, timeout=30)
        resp.raise_for_status()
        body = resp.content
    except Exception:
        return None
    if b"%PDF" not in body[:1024]:
        return None
    return pdf_to_text(body), pdf_url
