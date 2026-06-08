"""
sources.py — sources.txt parsing and URL freshness classification.
"""

import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Freshness categories
# How old (in days) a Wayback snapshot can be before we seek a fresher one.
# ---------------------------------------------------------------------------
FRESHNESS: dict[str, int] = {
    "specific":  3650,  # dated/versioned URL — won't change (e.g. /2021-small.pdf, /v2/)
    "immutable":  365,  # academic papers, arXiv, DOI pages
    "docs":        30,  # /docs/, /wiki/, /documentation/ — updates occasionally
    "rolling":     14,  # news, blogs, homepages — assume stale after 2 weeks
}

# Regex patterns for 'specific' classification (date or version in path)
_SPECIFIC_RE = re.compile(
    r"/\d{4}[-/]\d{2}"            # /2021-08 or /2021/08
    r"|/v\d+[\./]"                # /v2. or /v3/
    r"|/\d{4}-[a-z]"              # /2021-small
    r"|[_-]\d{4}\."               # _2021. or -2021.
)

# Domains/patterns that imply immutable content
_IMMUTABLE_HOSTS = {"arxiv.org", "doi.org", "zenodo.org", "osf.io"}
_SPECIFIC_HOSTS  = {"medium.com"}  # published articles; content never changes after publication

# Path fragments that imply documentation
_DOCS_PATHS = {"/docs/", "/wiki/", "/documentation/", "/book/", "/help/", "/manual/"}


def freshness_category(url: str) -> str:
    """Classify a URL into one of: specific, immutable, docs, rolling."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()

    # .pdf extension → specific (a particular document, won't change)
    if path.endswith(".pdf"):
        return "specific"

    # Date or version pattern in path
    if _SPECIFIC_RE.search(path):
        return "specific"

    # Specific hosts (published content, never changes)
    if any(h in host for h in _SPECIFIC_HOSTS):
        return "specific"

    # Known immutable domains
    if any(h in host for h in _IMMUTABLE_HOSTS):
        return "immutable"

    # Documentation paths
    if any(frag in path for frag in _DOCS_PATHS):
        return "docs"

    return "rolling"


def max_age_days(url: str) -> int:
    """Return FRESHNESS[freshness_category(url)]."""
    return FRESHNESS[freshness_category(url)]


# ---------------------------------------------------------------------------
# sources.txt parser
# ---------------------------------------------------------------------------
def parse(path: Path) -> list[dict]:
    """
    Parse a sources.txt file of --- separated key: value blocks.
    Returns a list of dicts keyed by field name.
    """
    entries: list[dict] = []
    current: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("---"):
            if current.get("citekey"):
                entries.append(current)
            current = {}
        elif ":" in line:
            k, _, v = line.partition(":")
            k, v = k.strip(), v.strip()
            if k and v:
                current[k] = v
    if current.get("citekey"):
        entries.append(current)
    return entries
