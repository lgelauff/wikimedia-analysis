"""
collect_s3_openalex.py — Re-run S3 adversarial queries via OpenAlex search.

Replaces the Semantic Scholar S3 run which failed due to rate limits.
Appends new candidates to candidates_new_c1.json (deduped against existing).

Usage:
  uv run collect_s3_openalex.py
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
_OUT_NEW    = _HERE / "candidates_new_c1.json"
_ERRORS_LOG = _HERE / "fetch_errors_c1.log"

_UA  = "WikimediaAnalysis/1.0 (personal research project; https://github.com/lgelauff/wikimedia-analysis; mailto:lodewijk@stanford.edu)"
_SSL = ssl.create_default_context(cafile=certifi.where())

YEAR_FROM = 2022  # broader window for counter-evidence

S3_QUERIES = [
    ("S3-complementarity",
     "AI search complementarity traffic website visits"),
    ("S3-wiki-no-decline",
     "AI Wikipedia editing no decline increase contributions"),
    ("S3-oss-improves",
     "generative AI improves open source software quality contribution"),
    ("S3-literacy-benefits",
     "generative AI benefits information literacy source evaluation"),
    ("S3-neutral-traffic",
     "AI overview search traffic neutral effect no change"),
    ("S3-stackoverflow-complement",
     "ChatGPT Stack Overflow complementary not substitute"),
    ("S3-wiki-quality",
     "large language model Wikipedia quality improvement"),
    # Additional adversarial angles
    ("S3-ai-augments-creators",
     "generative AI augments human creativity content production"),
    ("S3-no-displacement",
     "AI does not displace human workers knowledge tasks no substitution"),
    ("S3-search-increases-clicks",
     "AI answer engine increases website referral traffic clicks"),
]


def log_error(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with _ERRORS_LOG.open("a") as f:
        f.write(f"{ts} | s3_openalex | {msg}\n")


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
        "strategy": "S3",
        "query":    query_label,
        "source":   "openalex",
    }


def dedup_key(c: dict) -> str:
    doi = (c.get("doi") or "").lower().strip()
    if doi:
        return doi
    return (c.get("title") or "").lower().strip()[:80]


def main() -> None:
    existing_keys: set[str] = set()
    existing_candidates: list[dict] = []
    if _OUT_NEW.exists():
        existing_candidates = json.loads(_OUT_NEW.read_text(encoding="utf-8"))
        for c in existing_candidates:
            k = dedup_key(c)
            if k:
                existing_keys.add(k)
    print(f"Existing candidates: {len(existing_candidates)}")

    if _INDEX.exists():
        vault = json.loads(_INDEX.read_text(encoding="utf-8"))
        for entry in vault:
            doi = (entry.get("DOI") or "").lower().strip()
            if doi:
                existing_keys.add(doi)

    new_candidates: list[dict] = []
    for label, query in S3_QUERIES:
        print(f"  [{label}] {query[:60]}…", end=" ", flush=True)
        results = openalex_search(query, per_page=50, pages=2)
        added = 0
        for item in results:
            cand = openalex_to_candidate(item, f"S3-OA-{label}")
            k = dedup_key(cand)
            if k and k not in existing_keys:
                existing_keys.add(k)
                new_candidates.append(cand)
                added += 1
        print(f"{added} new ({len(results)} fetched)")
        time.sleep(0.3)

    print(f"\nNew S3/OpenAlex candidates: {len(new_candidates)}")

    if not new_candidates:
        print("Nothing new to add.")
        return

    combined = existing_candidates + new_candidates
    _OUT_NEW.write_text(json.dumps(combined, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Written {len(combined)} total → {_OUT_NEW.name}")


if __name__ == "__main__":
    main()
