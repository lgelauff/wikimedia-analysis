"""
cache.py — fetch and cache MediaWiki pages for the RFC process analysis.

Each page is stored as a JSON file under tmp/cache/ keyed by a stable slug.
A sources manifest (tmp/sources.json) tracks every fetched page with metadata:
  - url          : canonical URL of the page
  - wiki         : e.g. "en.wikipedia"
  - title        : MediaWiki page title
  - revid        : revision ID at time of fetch (for reproducibility)
  - fetched_at   : ISO-8601 UTC timestamp
  - cache_file   : relative path to the cached text file

Usage:
    from cache import fetch_page, load_sources
    text = fetch_page("https://en.wikipedia.org/wiki/Wikipedia:Requests_for_comment")
"""

import json
import re
import ssl
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import certifi

_SSL_CTX = ssl.create_default_context(cafile=certifi.where())

CACHE_DIR   = Path(__file__).parent / "tmp" / "cache"
SOURCES_FILE = Path(__file__).parent / "tmp" / "sources.json"

UA = (
    "WikimediaAnalysis/1.0 "
    "(personal research project; https://github.com/lgelauff/wikimedia-analysis)"
)

# Seconds between API calls — be a good citizen on shared infrastructure
RATE_DELAY = 1.0


def _slug(wiki: str, title: str) -> str:
    """Stable filename slug from wiki + title."""
    safe = re.sub(r"[^\w]+", "_", f"{wiki}__{title}").strip("_")
    return safe[:120]


def _api_base(url: str) -> str:
    p = urllib.parse.urlparse(url)
    return f"{p.scheme}://{p.netloc}/w/api.php"


def _wiki_id(url: str) -> str:
    """Return e.g. 'en.wikipedia' from a URL."""
    host = urllib.parse.urlparse(url).netloc  # en.wikipedia.org
    parts = host.split(".")
    if len(parts) >= 3:
        return f"{parts[0]}.{parts[1]}"
    return host


def _title_from_url(url: str) -> str:
    path = urllib.parse.urlparse(url).path
    title = path.split("/wiki/", 1)[-1] if "/wiki/" in path else path.lstrip("/")
    return urllib.parse.unquote(title).replace("_", " ")


def load_sources() -> dict:
    """Return the sources manifest as a dict keyed by page URL."""
    if SOURCES_FILE.exists():
        return json.loads(SOURCES_FILE.read_text())
    return {}


def _save_sources(sources: dict) -> None:
    SOURCES_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = SOURCES_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(sources, indent=2, ensure_ascii=False))
    tmp.replace(SOURCES_FILE)  # atomic rename


def fetch_page(url: str, force: bool = False) -> str:
    """
    Fetch a Wikimedia wiki page and cache it locally.

    Uses action=query&prop=revisions to get raw wikitext + revid in one call.
    Returns the wikitext string. Updates tmp/sources.json with source metadata.
    Skips the network call if the page is already cached (unless force=True).
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    wiki  = _wiki_id(url)
    title = _title_from_url(url)
    slug  = _slug(wiki, title)
    cache_file = CACHE_DIR / f"{slug}.json"

    sources = load_sources()

    if not force and url in sources and cache_file.exists():
        cached = json.loads(cache_file.read_text())
        print(f"[cache] {wiki} / {title}  (revid {sources[url]['revid']})")
        return cached["wikitext"]

    api = _api_base(url)
    params = {
        "action":        "query",
        "titles":        title,
        "prop":          "revisions|info",
        "rvprop":        "content|ids",
        "rvslots":       "main",
        "inprop":        "url",
        "format":        "json",
        "formatversion": "2",
        "redirects":     "1",
        "maxlag":        "5",
    }
    query = urllib.parse.urlencode(params)
    req = urllib.request.Request(
        f"{api}?{query}",
        headers={"User-Agent": UA, "Accept": "application/json"},
    )

    time.sleep(RATE_DELAY)
    with urllib.request.urlopen(req, timeout=20, context=_SSL_CTX) as resp:
        data = json.loads(resp.read())

    pages = data.get("query", {}).get("pages", [])
    if not pages or "missing" in pages[0]:
        raise RuntimeError(f"Page not found: {url}")

    page     = pages[0]
    revid    = page["revisions"][0]["revid"]
    wikitext = page["revisions"][0]["slots"]["main"]["content"]

    # Write cache file
    cache_file.write_text(
        json.dumps({"wikitext": wikitext}, ensure_ascii=False, indent=2)
    )

    # Update sources manifest
    sources[url] = {
        "url":        url,
        "wiki":       wiki,
        "title":      title,
        "revid":      revid,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "cache_file": str(cache_file.relative_to(Path(__file__).parent)),
    }
    _save_sources(sources)

    print(f"[fetch] {wiki} / {title}  (revid {revid})")
    return wikitext
