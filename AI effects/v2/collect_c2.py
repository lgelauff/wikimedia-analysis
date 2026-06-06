"""
collect_c2.py — Cycle 2 targeted OpenAlex collection for thin/none claims.

Targeted at the 5 claims with little or no evidence after Cycle 1:
  C1: Wikipedia editor pipeline — fewer readers → fewer new editors
  D1: Wikimedia donation revenue threatened by declining traffic
  D3: Academic/open-access infrastructure costs rising due to AI scraping
  E1: AI bots imposing measurable infrastructure costs on open knowledge platforms
  E2: AI scraping causing service disruptions

Outputs: candidates_c2.json (new candidates only, deduped against vault + existing)

Usage:
  uv run collect_c2.py
"""

from __future__ import annotations

import json
import ssl
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import certifi

_HERE       = Path(__file__).parent
_VAULT_ROOT = Path.home() / "Documents" / "GitHub" / "research-vault"
_INDEX      = _VAULT_ROOT / "index.json"
_OUT        = _HERE / "candidates_c2.json"
_ERRORS_LOG = _HERE / "fetch_errors_c1.log"

_UA  = "WikimediaAnalysis/1.0 (personal research project; https://github.com/lgelauff/wikimedia-analysis; mailto:lodewijk@stanford.edu)"
_SSL = ssl.create_default_context(cafile=certifi.where())

YEAR_FROM = 2022  # broader window for thin claims


C2_QUERIES = [
    # C1 — Wikipedia editor pipeline
    ("C1-editor-pipeline",
     "Wikipedia editor recruitment new contributor pipeline decline"),
    ("C1-reader-editor",
     "Wikipedia reader editor conversion funnel AI search impact"),
    ("C1-contributor-decline",
     "Wikipedia contributor editor community size trend decline"),

    # D1 — Wikimedia/WMF donation revenue
    ("D1-WMF-donations",
     "Wikipedia donation revenue traffic decline Wikimedia Foundation"),
    ("D1-nonprofit-traffic",
     "nonprofit website traffic donation revenue AI search impact"),
    ("D1-WMF-financial",
     "Wikimedia Foundation financial sustainability AI generative"),

    # D3 — Academic/open-access scraping costs
    ("D3-OA-scraping",
     "academic repository scraping costs AI crawlers open access infrastructure"),
    ("D3-preprint-crawl",
     "arXiv PubMed Zenodo crawling AI bot traffic costs load"),
    ("D3-scholarly-infra",
     "scholarly infrastructure bandwidth cost AI data collection scraping"),

    # E1 — AI bot infrastructure costs
    ("E1-bot-infra-cost",
     "AI web crawler bot infrastructure cost bandwidth server load"),
    ("E1-llm-crawling-cost",
     "LLM training data crawling cost open web infrastructure impact"),
    ("E1-crawler-blocking",
     "website crawler blocking AI bot traffic measurement impact"),

    # E2 — AI scraping service disruptions
    ("E2-scraping-disruption",
     "AI scraping service disruption DDoS outage website availability"),
    ("E2-crawler-overload",
     "web crawler overload rate limiting service degradation"),
    ("E2-robots-txt-enforcement",
     "robots.txt AI crawler compliance enforcement disruption"),
]


def log_error(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with _ERRORS_LOG.open("a") as f:
        f.write(f"{ts} | collect_c2 | {msg}\n")


def openalex_search(query: str, per_page: int = 50, pages: int = 3) -> list[dict]:
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
            with urllib.request.urlopen(req, context=_SSL, timeout=25) as r:
                data = json.loads(r.read())
            items = data.get("results") or []
            if not items:
                break
            results.extend(items)
            time.sleep(0.2)
        except Exception as exc:
            log_error(f"search '{query[:60]}' page {page} — {type(exc).__name__}: {exc}")
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


def to_candidate(item: dict, query_label: str) -> dict:
    doi = (item.get("doi") or "").replace("https://doi.org/", "")
    authors = []
    for a in (item.get("authorships") or [])[:5]:
        name = (a.get("author") or {}).get("display_name") or ""
        if name:
            authors.append(name)
    loc = item.get("primary_location") or {}
    url = loc.get("landing_page_url") or item.get("id") or ""
    abstract = reconstruct_abstract(item.get("abstract_inverted_index"))
    oa = (item.get("open_access") or {}).get("is_oa", False)
    oa_url = (item.get("open_access") or {}).get("oa_url") or ""
    return {
        "title":    item.get("title") or "",
        "year":     item.get("publication_year"),
        "authors":  authors,
        "doi":      doi or None,
        "url":      url,
        "oa_url":   oa_url,
        "is_oa":    oa,
        "abstract": abstract[:1000] if abstract else "",
        "strategy": "C2",
        "query":    f"C2-OA-{query_label}",
        "source":   "openalex",
    }


def dedup_key(c: dict) -> str:
    doi = (c.get("doi") or "").lower().strip()
    if doi:
        return doi
    return (c.get("title") or "").lower().strip()[:80]


def main() -> None:
    # Seed dedup from vault index
    existing_keys: set[str] = set()
    if _INDEX.exists():
        vault = json.loads(_INDEX.read_text(encoding="utf-8"))
        for entry in vault:
            doi = (entry.get("DOI") or "").lower().strip()
            title = (entry.get("title") or "").lower().strip()[:80]
            if doi:
                existing_keys.add(doi)
            if title:
                existing_keys.add(title)
        print(f"Vault index: {len(vault)} entries loaded for dedup")

    # Also dedup against any existing c2 file
    existing_candidates: list[dict] = []
    if _OUT.exists():
        existing_candidates = json.loads(_OUT.read_text(encoding="utf-8"))
        for c in existing_candidates:
            k = dedup_key(c)
            if k:
                existing_keys.add(k)
        print(f"Existing C2 candidates: {len(existing_candidates)}")

    new_candidates: list[dict] = []
    for label, query in C2_QUERIES:
        print(f"  [{label}] {query[:65]}…", end=" ", flush=True)
        results = openalex_search(query)
        added = 0
        for item in results:
            cand = to_candidate(item, label)
            k = dedup_key(cand)
            if k and k not in existing_keys:
                existing_keys.add(k)
                new_candidates.append(cand)
                added += 1
        print(f"{added} new ({len(results)} fetched)")
        time.sleep(0.3)

    print(f"\nNew Cycle 2 candidates: {len(new_candidates)}")
    if not new_candidates:
        print("Nothing new to add.")
        return

    combined = existing_candidates + new_candidates
    _OUT.write_text(json.dumps(combined, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Written {len(combined)} total → {_OUT.name}")


if __name__ == "__main__":
    main()
