"""
Shared local cache for downloaded content.

  - wiki_pages: API responses (JSON) keyed by (api_base, page_title)
  - email_archives: decompressed mailing-list .txt files keyed by (list_name, YYYY-Mon)

Past-edition wiki pages and all email archives are treated as immutable once
downloaded (no expiry).  Pages for the current or future year are re-fetched
if older than MAX_WIKI_AGE_DAYS.
"""

import gzip
import hashlib
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

CACHE_DIR    = Path(__file__).parent / "tmp"
WIKI_DIR     = CACHE_DIR / "wiki_pages"
EMAIL_DIR    = CACHE_DIR / "email_archives"
MAX_WIKI_AGE_DAYS = 7          # only relevant for current/future editions
CURRENT_YEAR      = datetime.now(timezone.utc).year

HEADERS = {
    "User-Agent": (
        "WikimaniaDeadlinesResearch/1.0 "
        "(https://github.com/lgelauff/wikimedia-analysis; research project)"
    ),
    "Accept": "application/json",
}


# ---------------------------------------------------------------------------
# Wiki page cache
# ---------------------------------------------------------------------------

def _wiki_cache_path(base: str, title: str) -> Path:
    host = urllib.parse.urlparse(base).netloc.replace(".", "_")
    slug = urllib.parse.quote(title, safe="").replace("%", "_")[:80]
    return WIKI_DIR / f"{host}__{slug}.json"


def _is_stale(path: Path, year: int) -> bool:
    """Past editions are immutable; current/future edition pages expire."""
    if year < CURRENT_YEAR:
        return False
    if not path.exists():
        return True
    age = time.time() - path.stat().st_mtime
    return age > MAX_WIKI_AGE_DAYS * 86400


def fetch_wiki_page(base: str, title: str, year: int) -> str | None:
    """
    Return wikitext for the given page, using local cache when available.
    Returns None if the page does not exist or a network error occurs.
    """
    WIKI_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = _wiki_cache_path(base, title)

    if cache_path.exists() and not _is_stale(cache_path, year):
        cached = json.loads(cache_path.read_text())
        return cached.get("wikitext")   # None means "confirmed missing"

    params = urllib.parse.urlencode({
        "action": "query", "titles": title,
        "prop": "revisions", "rvprop": "content",
        "format": "json", "formatversion": "2", "redirects": "1",
    })
    req = urllib.request.Request(f"{base}?{params}", headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15, context=_SSL_CTX) as resp:
            data = json.loads(resp.read())
        pages = data["query"]["pages"]
        wikitext = None
        if pages and "revisions" in pages[0]:
            wikitext = pages[0]["revisions"][0]["content"]
        cache_path.write_text(json.dumps({"wikitext": wikitext}, ensure_ascii=False))
        return wikitext
    except Exception as e:
        print(f"    API error ({base} / {title}): {e}")
        return None


def make_api_url(base: str, title: str) -> str:
    params = urllib.parse.urlencode({
        "action": "query", "titles": title,
        "prop": "revisions", "rvprop": "content",
        "format": "json", "formatversion": "2", "redirects": "1",
    })
    return f"{base}?{params}"


# ---------------------------------------------------------------------------
# Email archive cache
# ---------------------------------------------------------------------------

EMAIL_BASE = "https://lists.wikimedia.org/pipermail"

# Months where wikimania-l traffic is likely to contain deadline announcements
# (roughly Sept prior year through August of conference year)
MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def _email_cache_path(list_name: str, year: int, month: str) -> Path:
    return EMAIL_DIR / f"{list_name}_{year}-{month}.txt"


def fetch_email_archive(list_name: str, year: int, month: str) -> str | None:
    """
    Return the plain-text mailing list archive for list_name / YYYY / Month.
    Downloads and decompresses from lists.wikimedia.org if not cached.
    Email archives are immutable once downloaded.
    """
    EMAIL_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = _email_cache_path(list_name, year, month)

    if cache_path.exists():
        return cache_path.read_text(errors="replace")

    url = f"{EMAIL_BASE}/{list_name}/{year}-{month}.txt.gz"
    req = urllib.request.Request(url, headers={
        "User-Agent": HEADERS["User-Agent"],
        "Accept-Encoding": "identity",
    })
    try:
        with urllib.request.urlopen(req, timeout=30, context=_SSL_CTX) as resp:
            compressed = resp.read()
        text = gzip.decompress(compressed).decode("utf-8", errors="replace")
        cache_path.write_text(text)
        return text
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None   # archive doesn't exist for this month
        print(f"    HTTP {e.code} fetching {url}")
        return None
    except Exception as e:
        print(f"    Error fetching {url}: {e}")
        return None


def fetch_email_archives_for_edition(
    list_name: str,
    conference_year: int,
    months_before: int = 9,
) -> list[tuple[str, str, str]]:
    """
    Fetch all relevant monthly archives for a given edition.
    Returns list of (year_str, month_str, archive_text) for non-empty months.
    Covers `months_before` months before August of conference_year
    through the conference month itself.
    """
    results = []
    # Build (year, month_name) pairs
    periods = []
    conf_month_idx = 7  # August = index 7 (0-based)
    for delta in range(months_before, -1, -1):
        total = conf_month_idx - delta
        y = conference_year + total // 12
        m = total % 12
        periods.append((y, MONTHS[m]))

    for y, month in periods:
        text = fetch_email_archive(list_name, y, month)
        if text:
            results.append((str(y), month, text))
        time.sleep(0.2)

    return results
