"""
collect_s5_openalex.py — Re-run S5 gap-specific queries via OpenAlex search.

Replaces the Semantic Scholar S5 run which failed due to rate limits.
Appends new candidates to candidates_new_c1.json (deduped against existing).

Usage:
  uv run collect_s5_openalex.py
"""

from __future__ import annotations

import json
import ssl
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import certifi

_HERE       = Path(__file__).parent
_VAULT_ROOT = Path.home() / "Documents" / "GitHub" / "research-vault"
_INDEX      = _VAULT_ROOT / "index.json"
_OUT_NEW    = _HERE / "candidates_new_c1.json"
_ERRORS_LOG = _HERE / "fetch_errors_c1.log"

_UA  = "WikimediaAnalysis/1.0 (personal research project; https://github.com/lgelauff/wikimedia-analysis; mailto:lodewijk@stanford.edu)"
_SSL = ssl.create_default_context(cafile=certifi.where())

YEAR_FROM = 2023

S5_QUERIES = [
    # A1: longitudinal CTR
    ("A1-CTR-longitudinal",
     "AI search click-through rate longitudinal before after"),
    # B3: audited revenue
    ("B3-publisher-revenue",
     "news publisher revenue AI search traffic decline"),
    # C1: reader-to-editor conversion
    ("C1-Wikipedia-pipeline",
     "Wikipedia reader editor conversion recruitment pipeline"),
    # D1: WMF/platform sustainability
    ("D1-WMF-revenue",
     "Wikimedia Foundation donation revenue traffic financial"),
    # F2: bot detection false positives
    ("F2-bot-detection",
     "bot detection false positive human user misclassification"),
    # G2: AI crawler referral ratio
    ("G2-crawler-referral",
     "AI crawler referral traffic ratio measurement methodology"),
    # G3: contributor motivation attribution
    ("G3-contributor-motivation",
     "Wikipedia editor contributor motivation AI attribution"),
    # H3: source checking motivation
    ("H3-source-checking",
     "AI use source checking verification motivation students"),
    # Extra: zero-click search empirical
    ("A2-zero-click",
     "zero-click search AI overview empirical traffic"),
    # Extra: AI scraping infrastructure costs
    ("E1-scraping-costs",
     "AI scraping infrastructure bandwidth cost web crawlers"),
    # Extra: knowledge platform financial sustainability
    ("D2-platform-sustainability",
     "open knowledge platform financial sustainability AI effects"),
]


def log_error(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with _ERRORS_LOG.open("a") as f:
        f.write(f"{ts} | s5_openalex | {msg}\n")


def openalex_search(query: str, per_page: int = 50, pages: int = 2) -> list[dict]:
    results = []
    for page in range(1, pages + 1):
        params = urllib.parse.urlencode({
            "search": query,
            "filter": f"publication_year:>{YEAR_FROM - 1}",
            "per-page": per_page,
            "page": page,
            "select": "id,doi,title,authorships,publication_year,primary_location,abstract_inverted_index,open_access",
            "mailto": "lodewijk@stanford.edu",
        })
        url = f"https://api.openalex.org/works?{params}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, context=_SSL, timeout=20) as r:
                data = json.loads(r.read())
            items = data.get("results") or []
            if not items:
                break
            results.extend(items)
            time.sleep(0.15)
        except Exception as exc:
            log_error(f"OpenAlex search '{query[:60]}' page {page} — {type(exc).__name__}: {exc}")
            break
    return results


def reconstruct_abstract(inv_index: dict | None) -> str:
    if not inv_index:
        return ""
    words: dict[int, str] = {}
    for word, positions in inv_index.items():
        for pos in positions:
            words[pos] = word
    return " ".join(words[i] for i in sorted(words))


def openalex_to_candidate(item: dict, query_label: str) -> dict:
    doi = (item.get("doi") or "").replace("https://doi.org/", "")
    authors = []
    for a in (item.get("authorships") or [])[:5]:
        name = (a.get("author") or {}).get("display_name") or ""
        if name:
            authors.append(name)
    loc = item.get("primary_location") or {}
    url = (loc.get("landing_page_url") or item.get("id") or "")
    abstract = reconstruct_abstract(item.get("abstract_inverted_index"))
    return {
        "title":    item.get("title") or "",
        "year":     item.get("publication_year"),
        "authors":  authors,
        "doi":      doi or None,
        "url":      url,
        "abstract": abstract[:800] if abstract else "",
        "strategy": "S5",
        "query":    query_label,
        "source":   "openalex",
    }


def dedup_key(c: dict) -> str:
    doi = (c.get("doi") or "").lower().strip()
    if doi:
        return doi
    return (c.get("title") or "").lower().strip()[:80]


def main() -> None:
    # Load existing candidates to dedup against
    existing_keys: set[str] = set()
    existing_candidates: list[dict] = []
    if _OUT_NEW.exists():
        existing_candidates = json.loads(_OUT_NEW.read_text(encoding="utf-8"))
        for c in existing_candidates:
            k = dedup_key(c)
            if k:
                existing_keys.add(k)
    print(f"Existing candidates: {len(existing_candidates)}")

    # Load vault index keys too
    if _INDEX.exists():
        vault = json.loads(_INDEX.read_text(encoding="utf-8"))
        for entry in vault:
            doi = (entry.get("DOI") or "").lower().strip()
            if doi:
                existing_keys.add(doi)

    new_candidates: list[dict] = []
    for label, query in S5_QUERIES:
        print(f"  [{label}] {query[:60]}…", end=" ", flush=True)
        results = openalex_search(query, per_page=50, pages=2)
        added = 0
        for item in results:
            cand = openalex_to_candidate(item, f"S5-OA-{label}")
            k = dedup_key(cand)
            if k and k not in existing_keys:
                existing_keys.add(k)
                new_candidates.append(cand)
                added += 1
        print(f"{added} new candidates ({len(results)} fetched)")
        time.sleep(0.3)

    print(f"\nNew S5/OpenAlex candidates: {len(new_candidates)}")

    if not new_candidates:
        print("Nothing new to add.")
        return

    combined = existing_candidates + new_candidates
    _OUT_NEW.write_text(json.dumps(combined, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Written {len(combined)} total candidates → {_OUT_NEW.name}")


if __name__ == "__main__":
    main()
