"""
openalex.py — enrich sources.txt entries via the OpenAlex API.

OpenAlex is a free, open scholarly knowledge graph. Given a DOI or title,
it returns structured metadata including open-access PDF URLs, abstracts,
citation counts, and publication year.

No API key required. Polite-pool access (higher rate limits) is unlocked
automatically when a mailto: address is included in the User-Agent.

API docs: https://docs.openalex.org/
Rate limits: https://docs.openalex.org/how-to-use-the-api/rate-limits-and-authentication
"""

import urllib.parse

import requests

from .ratelimits import RateLimitRegistry

_UA = "WikimediaAnalysis/1.0 (personal research; lodewijk@stanford.edu; https://github.com/lgelauff/wikimedia-analysis)"
_BASE = "https://api.openalex.org/works"

_OPENALEX_DELAY = 0.1  # polite pool allows up to 10 req/s


def enrich(entry: dict, rl: RateLimitRegistry, session: requests.Session) -> None:
    """
    Query OpenAlex for the entry's DOI or title and fill any missing metadata.

    Priority:
      1. DOI lookup (exact match, most reliable)
      2. Title search (fuzzy, only used when no DOI and title is present)

    Adds to entry (only when field is absent):
      - url: open-access PDF URL (best_oa_location.pdf_url)
      - year: publication year
      - abstract: inverted-index abstract (reconstructed to plain text)
      - openalex_id: OpenAlex work ID (for traceability)

    Modifies entry in-place. Silently skips on API errors.
    """
    work = _lookup(entry, rl, session)
    if work is None:
        return

    if "openalex_id" not in entry:
        entry["openalex_id"] = work.get("id", "")

    if "year" not in entry and work.get("publication_year"):
        entry["year"] = str(work["publication_year"])

    # Open-access PDF URL
    if "url" not in entry:
        oa_url = _extract_oa_url(work)
        if oa_url:
            entry["url"] = oa_url

    # Abstract (reconstructed from inverted index)
    if "abstract" not in entry:
        abstract = _reconstruct_abstract(work.get("abstract_inverted_index"))
        if abstract:
            entry["abstract"] = abstract


def _lookup(entry: dict, rl: RateLimitRegistry, session: requests.Session) -> dict | None:
    doi = entry.get("doi", "").strip()
    if doi:
        return _fetch(_BASE, {"filter": f"doi:{doi}"}, rl, session)

    title = entry.get("title", "").strip()
    if title:
        return _fetch(_BASE, {"filter": f"title.search:{title}", "per-page": "1"}, rl, session)

    return None


def _fetch(base_url: str, params: dict, rl: RateLimitRegistry, session: requests.Session) -> dict | None:
    url = base_url + "?" + urllib.parse.urlencode(params)
    rl.wait(url)
    try:
        resp = session.get(url, headers={"User-Agent": _UA}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return None

    results = data.get("results", [])
    return results[0] if results else None


def _extract_oa_url(work: dict) -> str | None:
    best = work.get("best_oa_location") or {}
    return best.get("pdf_url") or best.get("landing_page_url")


def _reconstruct_abstract(inverted: dict | None) -> str:
    """Reconstruct plain-text abstract from OpenAlex inverted-index format."""
    if not inverted:
        return ""
    positions: list[tuple[int, str]] = []
    for word, pos_list in inverted.items():
        for pos in pos_list:
            positions.append((pos, word))
    return " ".join(w for _, w in sorted(positions))
