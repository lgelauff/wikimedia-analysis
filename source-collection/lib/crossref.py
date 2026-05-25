"""
crossref.py — Crossref REST API lookup for DOI metadata.

Crossref operates two request pools:
  Polite pool  — set CROSSREF_MAILTO in your environment. Requests include a
                 mailto: contact in the User-Agent, routing them to dedicated
                 infrastructure with stable, generous throughput.
  Anonymous    — no env var set. Works but is throttled more aggressively.

Rate limits applied here:
  Polite pool:  1.0s between requests (well within their capacity)
  Anonymous:    5.0s between requests (conservative; no published limit)

Reference: https://api.crossref.org/swagger-ui/index.html
Etiquette:  https://www.crossref.org/documentation/retrieve-metadata/rest-api/tips-for-using-the-crossref-rest-api/

Credentials: set CROSSREF_MAILTO to opt into the polite pool.
"""

import json
import os
import ssl
import time
import urllib.parse
import urllib.request

import certifi

_MAILTO = os.environ.get("CROSSREF_MAILTO", "").strip()
_POLITE = bool(_MAILTO)
_RATE   = 1.0 if _POLITE else 5.0   # seconds between requests

_UA = (
    f"WikimediaAnalysis/1.0 (mailto:{_MAILTO}; https://github.com/lgelauff/wikimedia-analysis)"
    if _POLITE
    else "WikimediaAnalysis/1.0 (https://github.com/lgelauff/wikimedia-analysis)"
)

_API     = "https://api.crossref.org/works/{}"
_SSL_CTX = ssl.create_default_context(cafile=certifi.where())
_last: float = 0.0   # module-level timestamp of last request


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def pool() -> str:
    """Return 'polite' or 'anonymous' — useful for logging."""
    return "polite" if _POLITE else "anonymous"


def lookup(doi: str) -> dict | None:
    """
    Fetch metadata for a DOI from Crossref.

    Returns a normalised dict (see _normalize) or None if the DOI is not found
    or the request fails. Rate-limits itself using the module-level _last timestamp.
    """
    global _last
    gap = time.time() - _last
    if gap < _RATE:
        time.sleep(_RATE - gap)

    url = _API.format(urllib.parse.quote(doi, safe=""))
    req = urllib.request.Request(
        url,
        headers={"User-Agent": _UA, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20, context=_SSL_CTX) as resp:
            data = json.loads(resp.read())
    except Exception:
        return None
    finally:
        _last = time.time()

    if data.get("status") != "ok":
        return None
    return _normalize(doi, data.get("message", {}))


def to_bibtex(citekey: str, meta: dict) -> str:
    """
    Render a normalised Crossref metadata dict as a BibTeX entry string.

    The returned string is ready to paste into a .bib file or embed in a
    cache header block. Fields are omitted when empty rather than left blank.
    """
    bib_type = _bibtex_type(meta.get("type", ""))

    author_str = " and ".join(
        f"{a['family']}, {a['given']}" if a.get("given") else a["family"]
        for a in meta.get("authors", [])
    )

    fields: list[tuple[str, str]] = []
    if author_str:               fields.append(("author",    author_str))
    if meta.get("title"):        fields.append(("title",     meta["title"]))
    if meta.get("journal"):      fields.append(("journal",   meta["journal"]))
    if meta.get("year"):         fields.append(("year",      str(meta["year"])))
    if meta.get("volume"):       fields.append(("volume",    meta["volume"]))
    if meta.get("issue"):        fields.append(("number",    meta["issue"]))
    if meta.get("pages"):        fields.append(("pages",     meta["pages"]))
    if meta.get("publisher"):    fields.append(("publisher", meta["publisher"]))
    if meta.get("doi"):          fields.append(("doi",       meta["doi"]))
    if meta.get("issn"):         fields.append(("issn",      meta["issn"]))
    if meta.get("url"):          fields.append(("url",       meta["url"]))

    width = max(len(k) for k, _ in fields) if fields else 0
    lines = [f"  {k:<{width}} = {{{v}}}" for k, v in fields]
    return f"@{bib_type}{{{citekey},\n" + ",\n".join(lines) + "\n}"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _normalize(doi: str, msg: dict) -> dict:
    """Extract and flatten the fields we care about from a Crossref works message."""
    authors = [
        {"given": a.get("given", ""), "family": a.get("family", "")}
        for a in msg.get("author", [])
        if a.get("family")
    ]

    year = None
    for date_field in ("published", "published-print", "published-online", "issued"):
        parts = msg.get(date_field, {}).get("date-parts", [[]])[0]
        if parts:
            year = int(parts[0])
            break

    return {
        "doi":       doi,
        "title":     " ".join(msg.get("title", [])),
        "authors":   authors,
        "year":      year,
        "journal":   " ".join(msg.get("container-title", [])),
        "volume":    msg.get("volume"),
        "issue":     msg.get("issue"),
        "pages":     msg.get("page"),
        "publisher": msg.get("publisher"),
        "type":      msg.get("type"),        # e.g. "journal-article"
        "url":       msg.get("URL"),
        "issn":      (msg.get("ISSN") or [None])[0],
        "abstract":  msg.get("abstract", ""),
        "pool":      pool(),
    }


def _bibtex_type(crossref_type: str) -> str:
    return {
        "journal-article":     "article",
        "book-chapter":        "inbook",
        "book":                "book",
        "proceedings-article": "inproceedings",
        "dissertation":        "phdthesis",
        "report":              "techreport",
        "posted-content":      "misc",       # preprints, e.g. bioRxiv
    }.get(crossref_type, "misc")
