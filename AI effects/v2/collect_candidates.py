"""
collect_candidates.py — Cycle 1 seed collection: strategies S2, S3, S4, S5

S2: Forward citations via OpenAlex (8 anchor papers)
S3: Adversarial queries via Semantic Scholar
S4: arXiv sweep — cs.IR + cs.CY, May 2025 to present
S5: Gap-specific queries via Semantic Scholar (derived from v1 gap notes)

Outputs → v2/
  candidates_new_c1.json      papers not yet in the vault
  candidates_existing_c1.json papers already in the vault
  fetch_errors_c1.log         all runtime failures

Usage:
  uv run collect_candidates.py
  uv run collect_candidates.py --dry-run   (print counts, no writes)
"""

from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import certifi

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_HERE       = Path(__file__).parent                                    # v2/
_VAULT_ROOT = Path(__file__).parent.parent.parent.parent / "research-vault"  # ../../research-vault relative to AI effects/v2
# Resolve relative to actual location
_VAULT_ROOT = Path.home() / "Documents" / "GitHub" / "research-vault"
_INDEX      = _VAULT_ROOT / "index.json"
_OUT_NEW      = _HERE / "candidates_new_c1.json"
_OUT_EXIST    = _HERE / "candidates_existing_c1.json"
_CHECKPOINT   = _HERE / "candidates_checkpoint_c1.json"   # written after each strategy
_ERRORS_LOG   = _HERE / "fetch_errors_c1.log"

_CHECKPOINT_INTERVAL = 50   # also save mid-strategy every N papers

_UA = "WikimediaAnalysis/1.0 (personal research project; https://github.com/lgelauff/wikimedia-analysis)"
_SSL = ssl.create_default_context(cafile=certifi.where())

# ---------------------------------------------------------------------------
# Anchor papers for S2 (citekey → DOI or URL lookup from vault)
# ---------------------------------------------------------------------------

S2_ANCHOR_KEYS = [
    "khosravi2026impact",
    "delriochanona2024large",
    "burtch2024consequences",
    "aral2026rise",
    "shumailov2024ai",
    "wikimedia2025crawlers",
    "pew2025click",
    "gerlich2025ai",
]

# ---------------------------------------------------------------------------
# S3 adversarial queries
# ---------------------------------------------------------------------------

S3_QUERIES = [
    "AI search complementarity traffic website visits",
    "AI Wikipedia editing no decline increase contributions",
    "generative AI improves open source software quality contribution",
    "generative AI benefits information literacy source evaluation",
    "AI overview search traffic neutral effect no change",
    "ChatGPT Stack Overflow complementary not substitute",
    "large language model Wikipedia quality improvement",
]

# ---------------------------------------------------------------------------
# S4 arXiv keywords (combined with category filter)
# ---------------------------------------------------------------------------

S4_KEYWORDS = [
    "wikipedia traffic AI",
    "AI overviews click-through search",
    "knowledge ecosystem generative AI",
    "AI scraping open knowledge",
    "AI search substitution platform traffic",
    "large language model open source contribution",
    "AI information literacy critical thinking",
]

S4_CATEGORIES = ["cs.IR", "cs.CY"]
S4_DATE_FROM  = "20250501"  # YYYYMMDD — arXiv date filter

S2_YEAR_FROM  = 2024  # only forward citations from 2024 onwards

# ---------------------------------------------------------------------------
# S5 gap-specific queries (derived from v1 gap notes)
# ---------------------------------------------------------------------------

S5_QUERIES = [
    # A1: longitudinal CTR
    "AI search click-through rate longitudinal before after time series",
    # B3: audited revenue data
    "news publisher revenue advertising AI search traffic decline audited",
    # C1: reader-to-editor conversion
    "Wikipedia reader editor conversion rate recruitment pipeline empirical",
    # D1/D2: WMF / knowledge platform revenue
    "Wikimedia Foundation revenue donation traffic 2024 2025 financial",
    # F2: bot detection false positive
    "bot detection false positive rate human user misclassification measurement",
    # G2: crawl-to-referral ratio methodology
    "AI crawler referral traffic ratio OpenAI Google measurement methodology",
    # G3: contributor motivation attribution
    "Wikipedia editor volunteer motivation AI attribution survey",
    # H3: source checking motivation longitudinal
    "AI tool use source checking verification motivation longitudinal survey students",
]

# ---------------------------------------------------------------------------
# Vault index helpers
# ---------------------------------------------------------------------------

def load_vault_index() -> dict[str, dict]:
    """Return dict keyed by (doi.lower(), url.rstrip('/')) → record."""
    if not _INDEX.exists():
        return {}
    records = json.loads(_INDEX.read_text(encoding="utf-8"))
    lookup: dict[str, dict] = {}
    for r in records:
        if r.get("DOI"):
            lookup[r["DOI"].lower()] = r
        if r.get("URL"):
            lookup[r["URL"].rstrip("/")] = r
        lookup[r["id"]] = r
    return lookup


def in_vault(doi: str | None, url: str | None, vault: dict) -> dict | None:
    if doi:
        hit = vault.get(doi.lower()) or vault.get(re.sub(r"^https?://(dx\.)?doi\.org/", "", doi).lower())
        if hit:
            return hit
    if url:
        hit = vault.get(url.rstrip("/"))
        if hit:
            return hit
    return None

# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

_last_req: dict[str, float] = {}


def _get_json(url: str, rate_domain: str, rate_sec: float = 1.0, retries: int = 3) -> dict | None:
    for attempt in range(retries):
        gap = time.time() - _last_req.get(rate_domain, 0)
        if gap < rate_sec:
            time.sleep(rate_sec - gap)
        req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=20, context=_SSL) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            _last_req[rate_domain] = time.time()
            if exc.code == 429:
                wait = 30 * (attempt + 1)
                print(f"  [rate limit] waiting {wait}s…", end=" ", flush=True)
                time.sleep(wait)
                continue
            _log_error(url, exc)
            return None
        except Exception as exc:
            _log_error(url, exc)
            return None
        finally:
            _last_req[rate_domain] = time.time()
    _log_error(url, Exception(f"failed after {retries} retries"))
    return None


def _get_xml(url: str, rate_domain: str, rate_sec: float = 3.0) -> str | None:
    gap = time.time() - _last_req.get(rate_domain, 0)
    if gap < rate_sec:
        time.sleep(rate_sec - gap)
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    try:
        with urllib.request.urlopen(req, timeout=30, context=_SSL) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as exc:
        _log_error(url, exc)
        return None
    finally:
        _last_req[rate_domain] = time.time()


def _log_error(url: str, exc: Exception) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    status = ""
    if hasattr(exc, "code"):
        status = f" | http={exc.code}"
    line = f"{ts} | {url} | {type(exc).__name__}: {str(exc)[:120]}{status}\n"
    with _ERRORS_LOG.open("a", encoding="utf-8") as f:
        f.write(line)
    print(f"  ERROR: {type(exc).__name__} — {url[:80]}", file=sys.stderr)

# ---------------------------------------------------------------------------
# Candidate normalisation
# ---------------------------------------------------------------------------

def make_candidate(
    title: str,
    abstract: str,
    year: int | None,
    authors: list[str],
    doi: str | None,
    url: str | None,
    strategy: str,
    query: str,
) -> dict:
    return {
        "title":    title.strip(),
        "abstract": abstract.strip()[:1000],
        "year":     year,
        "authors":  authors[:5],
        "doi":      doi,
        "url":      url,
        "strategy": strategy,
        "query":    query,
    }

# ---------------------------------------------------------------------------
# S2 — OpenAlex forward citations
# ---------------------------------------------------------------------------

def _openalex_id_for(record: dict) -> str | None:
    """Resolve a vault record to an OpenAlex work ID."""
    doi = record.get("DOI")
    url = record.get("URL", "")
    # Try DOI lookup
    if doi:
        doi_clean = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
        data = _get_json(
            f"https://api.openalex.org/works/https://doi.org/{urllib.parse.quote(doi_clean, safe='')}",
            rate_domain="openalex",
        )
        if data and data.get("id"):
            return data["id"].split("/")[-1]  # W1234567
    # Try arXiv URL lookup
    arxiv_m = re.search(r"arxiv\.org/abs/([0-9]+\.[0-9]+)", url)
    if arxiv_m:
        arxiv_id = arxiv_m.group(1)
        data = _get_json(
            f"https://api.openalex.org/works/https://arxiv.org/abs/{arxiv_id}",
            rate_domain="openalex",
        )
        if data and data.get("id"):
            return data["id"].split("/")[-1]
    return None


def _openalex_forward_citations(openalex_id: str, anchor_key: str) -> list[dict]:
    candidates = []
    cursor = "*"
    pages = 0
    while cursor and pages < 5:
        url = (
            f"https://api.openalex.org/works"
            f"?filter=cites:{openalex_id},publication_year:>{S2_YEAR_FROM - 1}"
            f"&per-page=100"
            f"&cursor={urllib.parse.quote(cursor, safe='')}"
            f"&select=id,title,abstract_inverted_index,publication_year,authorships,ids"
        )
        data = _get_json(url, rate_domain="openalex")
        if not data:
            break
        for work in data.get("results", []):
            title    = work.get("title") or ""
            year     = work.get("publication_year")
            doi      = (work.get("ids") or {}).get("doi", "").replace("https://doi.org/", "") or None
            oa_url   = work.get("id", "")
            authors  = [
                a.get("author", {}).get("display_name", "")
                for a in (work.get("authorships") or [])[:5]
            ]
            abstract = _decode_inverted_index(work.get("abstract_inverted_index") or {})
            if title:
                candidates.append(make_candidate(
                    title, abstract, year, authors, doi, oa_url,
                    strategy="S2", query=f"cites:{anchor_key}",
                ))
        meta   = data.get("meta", {})
        cursor = meta.get("next_cursor")
        pages += 1
        if not data.get("results"):
            break
    return candidates


def _decode_inverted_index(inv: dict) -> str:
    """Reconstruct abstract text from OpenAlex inverted index."""
    if not inv:
        return ""
    words: list[tuple[int, str]] = []
    for word, positions in inv.items():
        for pos in positions:
            words.append((pos, word))
    words.sort()
    return " ".join(w for _, w in words)


def run_s2(vault: dict) -> list[dict]:
    print("\n=== S2: Forward citation tracking via OpenAlex ===")
    vault_records = json.loads(_INDEX.read_text(encoding="utf-8")) if _INDEX.exists() else []
    vault_by_key  = {r["id"]: r for r in vault_records}
    all_candidates: list[dict] = []
    for key in S2_ANCHOR_KEYS:
        record = vault_by_key.get(key)
        if not record:
            print(f"  [{key}] not found in vault — skipping")
            continue
        print(f"  [{key}] resolving OpenAlex ID…", end=" ", flush=True)
        oa_id = _openalex_id_for(record)
        if not oa_id:
            print("not found")
            continue
        print(f"{oa_id} — fetching citations…", end=" ", flush=True)
        cands = _openalex_forward_citations(oa_id, key)
        print(f"{len(cands)} papers")
        all_candidates.extend(cands)
        if len(all_candidates) % _CHECKPOINT_INTERVAL == 0 or len(cands) > 100:
            save_checkpoint(all_candidates)
    print(f"  S2 total: {len(all_candidates)} candidates")
    return all_candidates

# ---------------------------------------------------------------------------
# S3 — Semantic Scholar adversarial queries
# ---------------------------------------------------------------------------

def _ss_search(query: str, limit: int = 50) -> list[dict]:
    url = (
        "https://api.semanticscholar.org/graph/v1/paper/search"
        f"?query={urllib.parse.quote(query)}"
        f"&limit={limit}"
        "&fields=title,abstract,year,authors,externalIds,url"
    )
    data = _get_json(url, rate_domain="semanticscholar", rate_sec=6.0, retries=4)
    if not data:
        return []
    results = []
    for p in data.get("data", []):
        doi     = (p.get("externalIds") or {}).get("DOI")
        url_out = p.get("url") or (f"https://doi.org/{doi}" if doi else None)
        authors = [a.get("name", "") for a in (p.get("authors") or [])[:5]]
        results.append(make_candidate(
            title    = p.get("title") or "",
            abstract = p.get("abstract") or "",
            year     = p.get("year"),
            authors  = authors,
            doi      = doi,
            url      = url_out,
            strategy = "S3",
            query    = query,
        ))
    return results


def run_s3(vault: dict) -> list[dict]:
    print("\n=== S3: Adversarial queries via Semantic Scholar ===")
    all_candidates: list[dict] = []
    for query in S3_QUERIES:
        print(f"  Query: {query[:60]}…", end=" ", flush=True)
        cands = _ss_search(query)
        print(f"{len(cands)} papers")
        all_candidates.extend(cands)
    print(f"  S3 total: {len(all_candidates)} candidates")
    return all_candidates

# ---------------------------------------------------------------------------
# S4 — arXiv sweep
# ---------------------------------------------------------------------------

_ARXIV_NS = "http://www.w3.org/2005/Atom"


def _arxiv_search(query: str, category: str, date_from: str) -> list[dict]:
    search_query = (
        f"cat:{category}"
        f" AND submittedDate:[{date_from}000000 TO 99991231235959]"
        f" AND ({query})"
    )
    url = (
        "https://export.arxiv.org/api/query"
        f"?search_query={urllib.parse.quote(search_query)}"
        "&start=0&max_results=100&sortBy=submittedDate&sortOrder=descending"
    )
    xml_text = _get_xml(url, rate_domain="arxiv", rate_sec=3.0)
    if not xml_text:
        return []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    ns = {"a": _ARXIV_NS}
    results = []
    for entry in root.findall("a:entry", ns):
        title    = (entry.findtext("a:title", default="", namespaces=ns) or "").strip().replace("\n", " ")
        abstract = (entry.findtext("a:summary", default="", namespaces=ns) or "").strip().replace("\n", " ")
        year_raw = entry.findtext("a:published", default="", namespaces=ns) or ""
        year     = int(year_raw[:4]) if len(year_raw) >= 4 else None
        authors  = [
            (a.findtext("a:name", default="", namespaces=ns) or "")
            for a in entry.findall("a:author", ns)
        ][:5]
        arxiv_url = ""
        doi       = None
        for link in entry.findall("a:link", ns):
            if link.attrib.get("type") == "text/html":
                arxiv_url = link.attrib.get("href", "")
        for link in entry.findall("a:link", ns):
            if "doi" in link.attrib.get("href", ""):
                doi = link.attrib["href"].replace("https://doi.org/", "")
        if title:
            results.append(make_candidate(
                title, abstract, year, authors, doi, arxiv_url or None,
                strategy="S4", query=f"{category}: {query}",
            ))
    return results


def run_s4(vault: dict) -> list[dict]:
    print("\n=== S4: arXiv sweep ===")
    all_candidates: list[dict] = []
    for kw in S4_KEYWORDS:
        for cat in S4_CATEGORIES:
            print(f"  [{cat}] {kw[:50]}…", end=" ", flush=True)
            cands = _arxiv_search(kw, cat, S4_DATE_FROM)
            print(f"{len(cands)} papers")
            all_candidates.extend(cands)
    print(f"  S4 total: {len(all_candidates)} candidates")
    return all_candidates

# ---------------------------------------------------------------------------
# S5 — Gap-specific queries via Semantic Scholar
# ---------------------------------------------------------------------------

def run_s5(vault: dict) -> list[dict]:
    print("\n=== S5: Gap-specific queries via Semantic Scholar ===")
    all_candidates: list[dict] = []
    for query in S5_QUERIES:
        print(f"  Query: {query[:60]}…", end=" ", flush=True)
        cands = _ss_search(query, limit=30)
        # Tag as S5
        for c in cands:
            c["strategy"] = "S5"
        print(f"{len(cands)} papers")
        all_candidates.extend(cands)
    print(f"  S5 total: {len(all_candidates)} candidates")
    return all_candidates

# ---------------------------------------------------------------------------
# Deduplication and output
# ---------------------------------------------------------------------------

def dedup_candidates(candidates: list[dict]) -> list[dict]:
    """Remove duplicate candidates (same DOI or URL)."""
    seen: set[str] = set()
    out = []
    for c in candidates:
        key = c.get("doi", "").lower() if c.get("doi") else c.get("url", "").rstrip("/")
        if not key:
            # Use title as fallback key
            key = re.sub(r"\s+", " ", c.get("title", "").lower()[:80])
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        out.append(c)
    return out


def split_vault(candidates: list[dict], vault: dict) -> tuple[list[dict], list[dict]]:
    """Split into (not_in_vault, already_in_vault)."""
    new_ones, existing = [], []
    for c in candidates:
        hit = in_vault(c.get("doi"), c.get("url"), vault)
        if hit:
            c["vault_citekey"] = hit["id"]
            existing.append(c)
        else:
            new_ones.append(c)
    return new_ones, existing


def save_checkpoint(candidates: list[dict]) -> None:
    """Write current accumulated candidates to checkpoint file."""
    _CHECKPOINT.write_text(json.dumps(candidates, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  [checkpoint] {len(candidates)} candidates saved → {_CHECKPOINT.name}", flush=True)


def write_outputs(new_ones: list[dict], existing: list[dict], dry_run: bool) -> None:
    if dry_run:
        print(f"\n[dry-run] Would write {len(new_ones)} new / {len(existing)} existing candidates")
        return
    _HERE.mkdir(parents=True, exist_ok=True)
    _OUT_NEW.write_text(json.dumps(new_ones, indent=2, ensure_ascii=False), encoding="utf-8")
    _OUT_EXIST.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
    # Remove checkpoint now that final output is written
    if _CHECKPOINT.exists():
        _CHECKPOINT.unlink()
    print(f"\nWrote {len(new_ones)} new candidates → {_OUT_NEW}")
    print(f"Wrote {len(existing)} existing candidates → {_OUT_EXIST}")
    if _ERRORS_LOG.exists():
        lines = _ERRORS_LOG.read_text().count("\n")
        print(f"Fetch errors: {lines} → {_ERRORS_LOG}")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Collect Cycle-1 candidates (S2–S5).")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--strategy", choices=["s2", "s3", "s4", "s5", "all"], default="all")
    args = parser.parse_args()

    print(f"Loading vault index…", end=" ", flush=True)
    vault = load_vault_index()
    print(f"{len(vault)} entries")

    # Resume from checkpoint if it exists
    all_candidates: list[dict] = []
    if _CHECKPOINT.exists() and not args.dry_run:
        all_candidates = json.loads(_CHECKPOINT.read_text(encoding="utf-8"))
        print(f"Resumed from checkpoint: {len(all_candidates)} candidates already collected")

    run_all = args.strategy == "all"
    if run_all or args.strategy == "s2":
        all_candidates.extend(run_s2(vault))
        save_checkpoint(all_candidates)
    if run_all or args.strategy == "s3":
        all_candidates.extend(run_s3(vault))
        save_checkpoint(all_candidates)
    if run_all or args.strategy == "s4":
        all_candidates.extend(run_s4(vault))
        save_checkpoint(all_candidates)
    if run_all or args.strategy == "s5":
        all_candidates.extend(run_s5(vault))
        save_checkpoint(all_candidates)

    print(f"\nTotal before dedup: {len(all_candidates)}")
    all_candidates = dedup_candidates(all_candidates)
    print(f"After dedup:        {len(all_candidates)}")

    new_ones, existing = split_vault(all_candidates, vault)
    print(f"New (not in vault): {len(new_ones)}")
    print(f"Existing in vault:  {len(existing)}")

    write_outputs(new_ones, existing, args.dry_run)


if __name__ == "__main__":
    main()
