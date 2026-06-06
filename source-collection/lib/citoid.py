"""
citoid.py — enrich sources.txt entries via the Wikipedia Citoid API.

Citoid resolves a URL or DOI into structured citation metadata (title, author,
year, publisher, etc.). Useful as a pre-flight step when sources.txt entries
are incomplete or when you want to validate that a DOI resolves as expected.

API: https://en.wikipedia.org/api/rest_v1/data/citation/mediawiki/{identifier}
Docs: https://www.mediawiki.org/wiki/Citoid
"""

import urllib.parse

import requests

from .ratelimits import RateLimitRegistry

_UA = "WikimediaAnalysis/1.0 (personal research; lodewijk@stanford.edu; https://github.com/lgelauff/wikimedia-analysis)"
_BASE = "https://en.wikipedia.org/api/rest_v1/data/citation/mediawiki/{}"

# Fields we copy from Citoid into the entry (only when missing)
_FIELD_MAP = {
    "title":     "title",
    "publisher": "publisher",
}


def enrich(entry: dict, rl: RateLimitRegistry, session: requests.Session) -> None:
    """
    Query Citoid for the entry's DOI or URL and fill any missing metadata fields.

    Modifies entry in-place. Never overwrites existing values.
    Silently skips if no identifier is available or the API returns an error.
    """
    identifier = entry.get("doi") or entry.get("url")
    if not identifier:
        return

    # Citoid expects a percent-encoded identifier in the path
    api_url = _BASE.format(urllib.parse.quote(identifier, safe=""))
    rl.wait(api_url)
    try:
        resp = session.get(api_url, headers={"User-Agent": _UA}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return

    # Citoid returns a list; take the first result
    result = data[0] if isinstance(data, list) and data else {}

    for citoid_key, entry_key in _FIELD_MAP.items():
        if entry_key not in entry and citoid_key in result:
            value = result[citoid_key]
            if isinstance(value, list):
                value = value[0] if value else None
            if value:
                entry[entry_key] = str(value)

    # Year: Citoid uses "date" (ISO 8601)
    if "year" not in entry:
        date = result.get("date", "")
        if date and len(date) >= 4:
            entry["year"] = date[:4]

    # URL: fill from Citoid if still missing
    if "url" not in entry:
        for key in ("url", "source"):
            val = result.get(key)
            if isinstance(val, list):
                val = val[0] if val else None
            if val:
                entry["url"] = str(val)
                break
