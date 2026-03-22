"""
fetch_source_text.py

Fetch and cache text content for all open-access sources in sources.txt
that do not yet have a local PDF or text cache.

Saves to tmp/pdf_cache/<citekey>.txt — the same cache path verify_source.py reads.

Strategies by URL type:
  - arxiv.org:         fetch HTML abstract page (title + abstract + metadata)
  - PMC links:         fetch HTML, strip to text
  - PDF links (.pdf):  download and extract with pypdf
  - Other web pages:   fetch HTML, strip to text

Usage:
    python fetch_source_text.py [--dry-run] [--citekey KEY]

Options:
    --dry-run    Show what would be fetched without writing anything
    --citekey    Process only this one citekey
    --force      Re-fetch even if cache file already exists
"""

import argparse
import html
import re
import ssl
import sys
import time
import urllib.request
from io import BytesIO
from pathlib import Path

import certifi

_SSL_CTX = ssl.create_default_context(cafile=certifi.where())
_UA = "WikimediaAnalysis/1.0 (personal research project; https://github.com/lgelauff/wikimedia-analysis)"
_CACHE_DIR = Path(__file__).parent.parent / "tmp" / "pdf_cache"
_SOURCES_TXT = Path(__file__).parent.parent / "sources.txt"
_PDF_DIR = Path(__file__).parent.parent / "pdf sources"

DELAY_BETWEEN_REQUESTS = 2.0  # seconds


# ---------------------------------------------------------------------------
# sources.txt parsing
# ---------------------------------------------------------------------------
def parse_sources_txt(path: Path) -> list[dict]:
    entries = []
    current: dict = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("---"):
            if current.get("citekey"):
                entries.append(current)
            current = {}
        elif ":" in line:
            key, _, val = line.partition(":")
            k = key.strip()
            v = val.strip()
            if k and v:
                current[k] = v
    if current.get("citekey"):
        entries.append(current)
    return entries


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
def fetch_url(url: str, accept: str = "text/html") -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": _UA, "Accept": accept},
    )
    with urllib.request.urlopen(req, timeout=20, context=_SSL_CTX) as resp:
        return resp.read()


def strip_html(raw_html: str, max_chars: int = 80_000) -> str:
    """Very simple HTML → plain text: strip tags, decode entities, collapse whitespace."""
    # Remove script/style blocks
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw_html, flags=re.DOTALL | re.IGNORECASE)
    # Strip tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Decode HTML entities
    text = html.unescape(text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


# ---------------------------------------------------------------------------
# Fetch strategies
# ---------------------------------------------------------------------------
def fetch_arxiv(arxiv_id: str) -> str:
    """Fetch arXiv HTML abstract page for a given arXiv ID."""
    # Try the HTML full-paper version first (not always available)
    try:
        raw = fetch_url(f"https://arxiv.org/html/{arxiv_id}").decode("utf-8", errors="replace")
        text = strip_html(raw)
        if len(text) > 2000:
            return text
    except Exception:
        pass
    # Fall back to the abs page (abstract only — but better than nothing)
    raw = fetch_url(f"https://arxiv.org/abs/{arxiv_id}").decode("utf-8", errors="replace")
    return strip_html(raw)


def fetch_pdf_bytes(url: str) -> str:
    """Download a PDF and extract text with pypdf."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return f"[pypdf not installed — could not extract PDF from {url}]"
    data = fetch_url(url, accept="application/pdf")
    reader = PdfReader(BytesIO(data))
    pages = []
    total = 0
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)
        total += len(text)
        if total >= 80_000:
            break
    return "\n".join(pages)[:80_000]


def fetch_html_page(url: str) -> str:
    """Fetch a generic web page and return stripped text."""
    raw = fetch_url(url).decode("utf-8", errors="replace")
    return strip_html(raw)


def fetch_text_for_entry(entry: dict) -> str:
    url = entry.get("url", "").strip()
    arxiv = entry.get("arxiv", "").strip()
    doi = entry.get("doi", "").strip()

    # arXiv via explicit field
    if arxiv and arxiv != "—":
        return fetch_arxiv(arxiv)

    # arXiv via URL
    arxiv_m = re.search(r"arxiv\.org/(?:abs|pdf|html)/([0-9]+\.[0-9v]+)", url)
    if arxiv_m:
        return fetch_arxiv(arxiv_m.group(1))

    # Direct PDF URL
    if url.lower().endswith(".pdf"):
        return fetch_pdf_bytes(url)

    # Generic DOI / web page
    if url:
        return fetch_html_page(url)

    return f"[No URL available for {entry.get('citekey', 'unknown')}]"


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------
def should_fetch(entry: dict, force: bool) -> bool:
    citekey = entry.get("citekey", "")
    if not citekey:
        return False
    # Already have a PDF on disk
    if (_PDF_DIR / f"{citekey}.pdf").exists():
        return False
    # Already have a cache file
    cache = _CACHE_DIR / f"{citekey}.txt"
    if cache.exists() and not force:
        return False
    # Paywalled
    access = entry.get("access", "").lower()
    if "paywall" in access:
        return False
    return True


def run(dry_run: bool = False, only_citekey=None, force: bool = False) -> None:
    entries = parse_sources_txt(_SOURCES_TXT)

    if only_citekey:
        entries = [e for e in entries if e.get("citekey") == only_citekey]
        if not entries:
            print(f"Citekey not found: {only_citekey}", file=sys.stderr)
            sys.exit(1)

    to_fetch = [e for e in entries if should_fetch(e, force)]
    print(f"Sources to fetch: {len(to_fetch)}  (dry_run={dry_run})")

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    ok = skip = err = 0

    for i, entry in enumerate(to_fetch, 1):
        citekey = entry["citekey"]
        url = entry.get("url", "(no url)")
        print(f"  [{i}/{len(to_fetch)}] {citekey}  {url[:70]}", end=" … ", flush=True)

        if dry_run:
            print("(dry run)")
            continue

        try:
            text = fetch_text_for_entry(entry)
            if not text.strip():
                print("EMPTY — skipped")
                skip += 1
                continue
            cache = _CACHE_DIR / f"{citekey}.txt"
            cache.write_text(text, encoding="utf-8")
            print(f"ok ({len(text):,} chars)")
            ok += 1
        except Exception as exc:
            print(f"ERROR: {exc}")
            err += 1

        if i < len(to_fetch):
            time.sleep(DELAY_BETWEEN_REQUESTS)

    print(f"\nDone: {ok} fetched, {skip} empty/skipped, {err} errors")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch and cache text for open-access sources in sources.txt"
    )
    parser.add_argument("--dry-run", action="store_true", help="List what would be fetched")
    parser.add_argument("--citekey", help="Process only this one citekey")
    parser.add_argument("--force", action="store_true", help="Re-fetch even if cache exists")
    args = parser.parse_args()
    run(dry_run=args.dry_run, only_citekey=args.citekey, force=args.force)


if __name__ == "__main__":
    main()
