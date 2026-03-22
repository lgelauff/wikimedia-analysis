"""
find_sources.py

For claims with no strong source, generate targeted web search queries
using the LLM, then optionally fetch and evaluate candidate pages.

Workflow:
  1. Read claims_v2.json + verification_results.json
  2. Identify claims where best score < strong (or specific --claim-ids)
  3. LLM generates 2–3 search queries per claim
  4. Optionally fetch top results and score relevance
  5. Write candidate sources to tmp/source_candidates.json

Usage:
    python -m scripts.find_sources [--claim-ids A1 B3 ...] [--fetch] [--verbose]

Options:
    --claim-ids   Only process these claim IDs (default: all partial/none claims)
    --min-score   Process claims where best score >= this (default: partial)
    --fetch       Attempt to fetch and score candidate URLs
    --verbose     Print progress
    --output      Output path (default: tmp/source_candidates.json)
"""

import argparse
import json
import re
import time
import html
import ssl
import urllib.request
from collections import defaultdict
from pathlib import Path

import certifi

from scripts.llm import query_llm, CHEAP

_SSL_CTX = ssl.create_default_context(cafile=certifi.where())
_UA = "WikimediaAnalysis/1.0 (personal research project; https://github.com/lgelauff/wikimedia-analysis)"

SCORE_ORDER = {"strong": 0, "partial": 1, "weak": 2, "none": 3, "contradicts": 4, "error": 5}

_CLAIMS_JSON   = Path(__file__).parent.parent / "claims_v2.json"
_RESULTS_JSON  = Path(__file__).parent.parent / "tmp" / "verification_results.json"
_CACHE_DIR     = Path(__file__).parent.parent / "tmp" / "pdf_cache"
_OUTPUT_DEFAULT = Path(__file__).parent.parent / "tmp" / "source_candidates.json"

# ---------------------------------------------------------------------------
# Query generation
# ---------------------------------------------------------------------------
_QUERY_SYSTEM = (
    "You are a research librarian helping find empirical sources for a white paper "
    "on AI's effects on the knowledge ecosystem. Generate search queries that will "
    "find the most direct evidence for the claim."
)

_QUERY_PROMPT = """\
We need to find better empirical sources for the following claim. Current sources \
provide only partial support.

CLAIM ({claim_id}):
{claim_text}

CURRENT SOURCES (partial/none):
{current_sources}

Generate 3 targeted web search queries that would find:
- Empirical studies, reports, or data directly supporting this claim
- Include specific statistics, datasets, or institutional sources likely to have data
- Prefer queries that would surface peer-reviewed studies, government/NGO reports, or \
  well-documented journalism

Return a JSON array of exactly 3 strings, e.g.:
["query 1", "query 2", "query 3"]
Return only the JSON array.
"""


def generate_queries(claim_id: str, claim_text: str, current_sources: list[dict]) -> list[str]:
    src_summary = "; ".join(
        f"{r['citekey']} ({r['score']})" for r in current_sources
    ) or "none"
    prompt = _QUERY_PROMPT.format(
        claim_id=claim_id,
        claim_text=claim_text,
        current_sources=src_summary,
    )
    raw = query_llm(prompt, system=_QUERY_SYSTEM, model=CHEAP, temperature=0.3)
    m = re.search(r"\[.*?\]", raw, re.DOTALL)
    if not m:
        return []
    try:
        return json.loads(m.group())
    except json.JSONDecodeError:
        return []


# ---------------------------------------------------------------------------
# Optional: fetch a URL and score relevance
# ---------------------------------------------------------------------------
_SCORE_SYSTEM = (
    "You are a research verification assistant. "
    "Score whether a web page provides empirical support for a given claim."
)

_SCORE_PROMPT = """\
CLAIM:
{claim}

PAGE TEXT (excerpt):
{text}

Does this page provide empirical support for the claim?
Return JSON: {{"score": "strong|partial|weak|none", "notes": "one sentence", \
"suggested_citekey": "lastname+year+firstword (all lowercase)", \
"suggested_title": "full title of source"}}
Return only JSON.
"""


def _fetch_url(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=15, context=_SSL_CTX) as resp:
        return resp.read()


def _strip_html(raw: str, max_chars: int = 6000) -> str:
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()[:max_chars]


def fetch_and_score(url: str, claim_text: str) -> dict:
    try:
        raw = _fetch_url(url).decode("utf-8", errors="replace")
        text = _strip_html(raw)
        if len(text) < 200:
            return {"score": "none", "notes": "page too short or blocked", "url": url}
        prompt = _SCORE_PROMPT.format(claim=claim_text, text=text)
        raw_resp = query_llm(prompt, system=_SCORE_SYSTEM, model=CHEAP, temperature=0.0)
        m = re.search(r"\{.*?\}", raw_resp, re.DOTALL)
        if not m:
            return {"score": "error", "notes": "unparseable LLM response", "url": url}
        result = json.loads(m.group())
        result["url"] = url
        return result
    except Exception as exc:
        return {"score": "error", "notes": str(exc)[:120], "url": url}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def load_weak_claims(min_score: str, only_ids: list[str] | None) -> list[dict]:
    data = json.loads(_CLAIMS_JSON.read_text())
    results_raw = json.loads(_RESULTS_JSON.read_text()) if _RESULTS_JSON.exists() else []

    by_claim: dict[str, list] = defaultdict(list)
    for r in results_raw:
        by_claim[r["claim_id"]].append(r)

    threshold = SCORE_ORDER[min_score]
    weak = []
    for theme in data.get("themes", []):
        for claim in theme.get("claims", []):
            cid = claim["id"]
            if only_ids and cid not in only_ids:
                continue
            rs = by_claim.get(cid, [])
            best_score = min((SCORE_ORDER.get(r["score"], 9) for r in rs), default=9)
            if best_score > SCORE_ORDER.get("strong", 0) or only_ids:
                weak.append({
                    "claim_id": cid,
                    "theme": theme["id"],
                    "claim_text": claim["text"],
                    "sources": rs,
                    "best_score": min(
                        (r["score"] for r in rs),
                        key=lambda s: SCORE_ORDER.get(s, 9),
                        default="unverified",
                    ),
                })
    return weak


def run(claim_ids: list[str] | None, min_score: str, do_fetch: bool,
        verbose: bool, output_path: Path) -> None:

    weak_claims = load_weak_claims(min_score, claim_ids)
    print(f"Claims to process: {len(weak_claims)}")

    # Load existing candidates to allow resuming
    candidates: list[dict] = []
    done_ids: set[str] = set()
    if output_path.exists():
        try:
            candidates = json.loads(output_path.read_text())
            done_ids = {c["claim_id"] for c in candidates}
            if verbose and done_ids:
                print(f"Resuming: {len(done_ids)} claims already have queries.")
        except (json.JSONDecodeError, KeyError):
            pass

    for i, claim in enumerate(weak_claims, 1):
        cid = claim["claim_id"]
        if cid in done_ids:
            if verbose:
                print(f"  [{i}/{len(weak_claims)}] {cid} — skipped (already done)")
            continue

        if verbose:
            print(f"  [{i}/{len(weak_claims)}] {cid} (best={claim['best_score']}) — generating queries...", end=" ", flush=True)

        queries = generate_queries(cid, claim["claim_text"], claim["sources"])

        entry = {
            "claim_id": cid,
            "theme": claim["theme"],
            "best_score": claim["best_score"],
            "claim_text": claim["claim_text"][:300],
            "queries": queries,
            "candidates": [],
        }

        if do_fetch and queries:
            if verbose:
                print(f"fetching {len(queries)} queries...", end=" ", flush=True)
            for q in queries:
                # Encode query for DuckDuckGo HTML (simple approach)
                q_enc = urllib.parse.quote_plus(q) if hasattr(urllib, "parse") else q.replace(" ", "+")
                url = f"https://html.duckduckgo.com/html/?q={q_enc}"
                result = fetch_and_score(url, claim["claim_text"])
                result["query"] = q
                entry["candidates"].append(result)
                time.sleep(1.5)

        candidates.append(entry)
        done_ids.add(cid)
        output_path.write_text(json.dumps(candidates, indent=2, ensure_ascii=False))

        if verbose:
            print(f"ok — {len(queries)} queries")

        if i < len(weak_claims):
            time.sleep(1.0)

    print(f"\nDone. {len(candidates)} claims written to {output_path}")


def main() -> None:
    import urllib.parse  # noqa: ensure available
    parser = argparse.ArgumentParser(description="Generate search queries for weak claims")
    parser.add_argument("--claim-ids", nargs="+", metavar="ID", help="Only these claim IDs")
    parser.add_argument("--min-score", default="partial",
                        choices=["strong", "partial", "weak", "none"],
                        help="Process claims where best score is at least this weak (default: partial)")
    parser.add_argument("--fetch", action="store_true", help="Attempt to fetch and score candidate URLs")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--output", "-o", default=str(_OUTPUT_DEFAULT))
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    run(
        claim_ids=args.claim_ids,
        min_score=args.min_score,
        do_fetch=args.fetch,
        verbose=args.verbose,
        output_path=output_path,
    )


if __name__ == "__main__":
    main()
