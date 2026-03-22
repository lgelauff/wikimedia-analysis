"""
build_bib.py

Scaffold a BibTeX entry from a DOI, URL, or sources.txt citekey block.
Fetches metadata where possible (Crossref for DOIs, OpenAlex for titles),
then uses an LLM to format the BibTeX entry.

Usage:
    python build_bib.py --doi 10.1038/s41586-024-07566-y
    python build_bib.py --url https://arxiv.org/abs/2602.18455
    python build_bib.py --citekey khosravi2026impact          # looks up in sources.txt
    python build_bib.py --batch sources.txt                   # process all pending entries

Options:
    --model   LLM model/alias (default: cheap = mistral-small-latest)
              BibTeX formatting is a mechanical task; small model is fine.
    --output  Append new entries to this .bib file (default: sources.bib)
    --dry-run Print entries to stdout without writing to file
"""

import argparse
import json
import re
import ssl
import sys
import urllib.request
from pathlib import Path

import certifi

from scripts.llm import query_llm, CHEAP

_SSL_CTX = ssl.create_default_context(cafile=certifi.where())
_UA = "WikimediaAnalysis/1.0 (personal research project; https://github.com/lgelauff/wikimedia-analysis)"
_CACHE_DIR = Path(__file__).parent.parent / "tmp" / "metadata_cache"


# ---------------------------------------------------------------------------
# Metadata fetching with caching
# ---------------------------------------------------------------------------
def _cache_key(identifier: str) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9._-]", "_", identifier)
    return _CACHE_DIR / f"{safe}.json"


def _fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15, context=_SSL_CTX) as resp:
        return json.loads(resp.read())


def _fetch_json_cached(url: str, cache_key: str) -> dict | None:
    """Fetch JSON from URL, caching result to tmp/metadata_cache/<key>.json."""
    cache = _cache_key(cache_key)
    if cache.exists():
        return json.loads(cache.read_text())
    try:
        data = _fetch_json(url)
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(data, indent=2))
        return data
    except Exception:
        return None


def fetch_crossref(doi: str) -> dict | None:
    """Fetch metadata from Crossref for a given DOI."""
    data = _fetch_json_cached(
        f"https://api.crossref.org/works/{doi}",
        cache_key=f"crossref_{doi}",
    )
    return data.get("message", {}) if data else None


def fetch_openalex_by_doi(doi: str) -> dict | None:
    """Fetch metadata from OpenAlex for a given DOI."""
    doi_clean = doi.lstrip("https://doi.org/").lstrip("http://doi.org/")
    return _fetch_json_cached(
        f"https://api.openalex.org/works/https://doi.org/{doi_clean}",
        cache_key=f"openalex_{doi_clean}",
    )


def fetch_arxiv(arxiv_id: str) -> dict | None:
    """Fetch metadata from arXiv for a given arXiv ID."""
    cache = _cache_key(f"arxiv_{arxiv_id}")
    if cache.exists():
        return json.loads(cache.read_text())
    try:
        url = f"https://export.arxiv.org/abs/{arxiv_id}"
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=15, context=_SSL_CTX) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        title_m = re.search(r"<title>(.*?)</title>", html, re.DOTALL)
        result = {"url": url, "arxiv_id": arxiv_id,
                  "title_guess": title_m.group(1).strip() if title_m else "",
                  "raw_html_snippet": html[:3000]}
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(result, indent=2))
        return result
    except Exception:
        return None


# ---------------------------------------------------------------------------
# LLM-based BibTeX formatting
# ---------------------------------------------------------------------------
_SYSTEM_BIB = (
    "You are a precise academic citation formatter. "
    "Given metadata about a paper or report, produce a single valid BibTeX entry. "
    "Use the provided citekey exactly. Return only the BibTeX entry, no other text."
)

_PROMPT_TEMPLATE_BIB = """\
Produce a BibTeX entry for this source.

Citekey: {citekey}
Entry type hint: {entry_type}

Metadata:
{metadata}

Rules:
- Use the exact citekey provided.
- Choose the most appropriate BibTeX type (@article, @inproceedings, @techreport, @misc, etc.)
- Include: author, title, year, journal/booktitle/institution (as applicable), doi, url, note
- For note, write: "Status: candidate"
- Wrap title words that must stay capitalised in {{double braces}}.
- Return only the BibTeX entry.
"""


def metadata_to_bibtex(citekey: str, metadata: str, entry_type: str = "misc", model: str = CHEAP) -> str:
    prompt = _PROMPT_TEMPLATE_BIB.format(
        citekey=citekey,
        entry_type=entry_type,
        metadata=metadata,
    )
    return query_llm(prompt, system=_SYSTEM_BIB, model=model, temperature=0.0)


# ---------------------------------------------------------------------------
# Citekey generation
# ---------------------------------------------------------------------------
def make_citekey(author_last: str, year: str | int, first_title_word: str) -> str:
    """Generate citekey in format lastname+year+firstword."""
    last = re.sub(r"[^a-z]", "", author_last.lower())
    word = re.sub(r"[^a-z]", "", first_title_word.lower())
    return f"{last}{year}{word}"


# ---------------------------------------------------------------------------
# Entry point per source type
# ---------------------------------------------------------------------------
def bibtex_from_doi(doi: str, citekey: str | None, model: str) -> str:
    doi_clean = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
    meta = fetch_crossref(doi_clean)
    if not meta:
        meta = fetch_openalex_by_doi(doi_clean)

    if not citekey and meta:
        authors = meta.get("author", [{}])
        last = authors[0].get("family", "unknown") if authors else "unknown"
        year = str(meta.get("published", {}).get("date-parts", [[0]])[0][0] or "")
        title_words = (meta.get("title", [""])[0] if meta.get("title") else "").split()
        first_word = title_words[0] if title_words else "untitled"
        citekey = make_citekey(last, year, first_word)

    meta_str = json.dumps(meta or {"doi": doi_clean}, indent=2)
    return metadata_to_bibtex(citekey or doi_clean, meta_str, entry_type="article", model=model)


def bibtex_from_url(url: str, citekey: str | None, model: str) -> str:
    # For arXiv URLs, extract the ID and fetch metadata
    arxiv_m = re.search(r"arxiv\.org/(abs|pdf)/([0-9]+\.[0-9]+)", url)
    if arxiv_m:
        arxiv_id = arxiv_m.group(2)
        meta = fetch_arxiv(arxiv_id)
        meta_str = json.dumps({"url": url, "arxiv_id": arxiv_id, **(meta or {})}, indent=2)
        return metadata_to_bibtex(citekey or arxiv_id, meta_str, entry_type="misc", model=model)

    # Generic URL: pass the URL and ask LLM to scaffold a @misc entry
    meta_str = json.dumps({"url": url}, indent=2)
    return metadata_to_bibtex(citekey or "unknown", meta_str, entry_type="misc", model=model)


# ---------------------------------------------------------------------------
# Batch mode: process sources.txt entries missing from sources.bib
# ---------------------------------------------------------------------------
def _parse_sources_txt(sources_txt: Path) -> list[dict]:
    """Extract citekey blocks from sources.txt."""
    entries = []
    current: dict = {}
    for line in sources_txt.read_text().splitlines():
        if line.startswith("citekey:"):
            if current.get("citekey"):
                entries.append(current)
            current = {"citekey": line.split(":", 1)[1].strip()}
        elif ":" in line and current:
            key, _, val = line.partition(":")
            current[key.strip()] = val.strip()
    if current.get("citekey"):
        entries.append(current)
    return entries


def _citekeys_in_bib(bib_path: Path) -> set[str]:
    if not bib_path.exists():
        return set()
    return set(re.findall(r"@\w+\{(\w+),", bib_path.read_text()))


def batch_from_sources_txt(sources_txt: Path, bib_path: Path, model: str, dry_run: bool) -> None:
    entries = _parse_sources_txt(sources_txt)
    existing = _citekeys_in_bib(bib_path)

    pending = [e for e in entries if e["citekey"] not in existing]
    print(f"{len(pending)} entries in sources.txt not yet in sources.bib")

    for entry in pending:
        citekey = entry["citekey"]
        print(f"  Building: {citekey} …", end=" ", flush=True)
        doi = entry.get("doi", "").strip("—").strip()
        url = entry.get("url", "").strip()
        meta_str = json.dumps(entry, indent=2)

        if doi and doi != "—":
            bib = bibtex_from_doi(doi, citekey, model)
        elif url:
            bib = bibtex_from_url(url, citekey, model)
        else:
            bib = metadata_to_bibtex(citekey, meta_str, model=model)

        print("done")
        if dry_run:
            print(bib)
            print()
        else:
            with bib_path.open("a") as f:
                f.write("\n" + bib + "\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scaffold BibTeX entries from DOIs, URLs, or sources.txt."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--doi",     help="DOI of the paper")
    source.add_argument("--url",     help="URL of the paper")
    source.add_argument("--batch",   help="Process sources.txt entries missing from sources.bib")

    parser.add_argument("--citekey", help="Override generated citekey (single mode)")
    parser.add_argument(
        "--model", "-m", default="cheap",
        help="LLM model/alias (default: cheap = mistral-small-latest)",
    )
    parser.add_argument(
        "--output", "-o", default="sources.bib",
        help="Append new entries to this .bib file (default: sources.bib)",
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Print to stdout, do not write to file")
    args = parser.parse_args()

    bib_path = Path(args.output)

    if args.doi:
        bib = bibtex_from_doi(args.doi, args.citekey, args.model)
        if args.dry_run:
            print(bib)
        else:
            with bib_path.open("a") as f:
                f.write("\n" + bib + "\n")
            print(f"Appended to {bib_path}")

    elif args.url:
        bib = bibtex_from_url(args.url, args.citekey, args.model)
        if args.dry_run:
            print(bib)
        else:
            with bib_path.open("a") as f:
                f.write("\n" + bib + "\n")
            print(f"Appended to {bib_path}")

    else:
        sources_path = Path(args.batch)
        if not sources_path.exists():
            print(f"Error: not found: {sources_path}", file=sys.stderr)
            sys.exit(1)
        batch_from_sources_txt(sources_path, bib_path, args.model, args.dry_run)


if __name__ == "__main__":
    main()
