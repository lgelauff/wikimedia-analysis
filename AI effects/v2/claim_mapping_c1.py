"""
claim_mapping_c1.py — Map ingested papers to white paper claim directions.

Phase 1 (prepare): finds papers with cached text, writes batch metadata to .claude/.
Phase 2 (merge):   after agents have run, merges batch outputs into claim_mapping_c1.json.

Usage:
  uv run claim_mapping_c1.py            # prepare batches, print agent instructions
  uv run claim_mapping_c1.py --merge    # merge completed batch outputs
  uv run claim_mapping_c1.py --status   # show which batches are done/pending
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

_HERE      = Path(__file__).parent
_VAULT     = Path(__file__).parent.parent.parent.parent / "research-vault"
_CACHE_DIR = _VAULT / "cache"
_IDX_FILE  = _VAULT / "index.json"
_BATCHES   = _HERE / ".claude"
_OUT       = _HERE / "claim_mapping_c1.json"

BATCH_SIZE  = 3    # papers per agent (full-text is large)
CACHE_CHARS = 60_000  # chars per paper passed to agent

PRIORITY_ORDER   = {"high": 0, "medium": 1, "low": 2}
RELEVANCE_ORDER  = {"relevant": 0, "marginal": 1, "irrelevant": 2}


# ---------------------------------------------------------------------------
# Claim taxonomy (from core_doc.md theme directions)
# ---------------------------------------------------------------------------

CLAIM_TAXONOMY = """
## White paper claim directions (core_doc.md)

**Theme A — Changing information-seeking / source awareness**
A1: Users increasingly query AI instead of traditional search; click-throughs to source websites declining
A2: Users unaware of information provenance when consuming AI-summarized content
A3: AI search accelerates decisions and reduces scrutiny of sources

**Theme B — Platform traffic decline**
B1: Wikipedia human visitor numbers are dropping due to AI search substitution
B2: Stack Overflow / QA community activity is declining since ChatGPT launch
B3: News publisher and open-web traffic is declining due to AI Overviews and zero-click search

**Theme C — Contributor pipeline erosion**
C1: Wikipedia editor pipeline affected — fewer readers → fewer new editors
C2: Open source project contribution quality/quantity affected by AI-generated submissions
C3: Online QA community contributors are substituting or leaving due to AI

**Theme D — Financial sustainability of knowledge infrastructure**
D1: Wikimedia/Wikipedia donation revenue threatened by declining human traffic
D2: News publisher revenue models under pressure from traffic and ad revenue loss
D3: Academic/open-access infrastructure costs rising due to AI scraping

**Theme E — AI scraping harm to knowledge infrastructure**
E1: AI bots imposing measurable infrastructure costs on open knowledge platforms
E2: AI scraping causing service disruptions; platforms deploying countermeasures
E3: Content creators not receiving credit or compensation for training data use

**Theme F — Defensive countermeasures harming legitimate human users**
F1: CAPTCHAs, paywalls, rate limits, and IP blocks increasingly harm human users as countermeasures against AI bots

**Theme G — Wikipedia content quality and governance**
G1: AI-generated content infiltrating Wikipedia at scale
G2: Wikipedia governance and volunteer capacity under pressure from AI

**Theme H — AI reliability, hallucination, and misinformation**
H1: AI systems produce and propagate factual errors and hallucinations
H2: AI search results present information without reliable sourcing or verification pathways

**EC themes — Structural and economic effects**
EC-1: Value not flowing back to original content creators whose work trained the AI
EC-4: Platform power concentration — AI consolidates information access in few actors
EC-9: AI creating knowledge access inequality (literacy divides, deskilling of some groups)
EC-11: AI search disintermediating original sources; citation and attribution crisis
EC-12: Cognitive offloading / deskilling — users relying on AI reduce own knowledge-building
EC-13: Cultural and epistemic homogenization through AI-generated content at scale
EC-14: Labor displacement in knowledge work (journalism, editing, software, research)
"""


# ---------------------------------------------------------------------------
# Load helpers
# ---------------------------------------------------------------------------

def load_vault_index() -> tuple[dict, dict]:
    """Return (doi_map, title_map) → citekey."""
    idx = json.loads(_IDX_FILE.read_text(encoding="utf-8"))
    doi_map: dict[str, str] = {}
    title_map: dict[str, str] = {}
    for entry in idx:
        cid = entry.get("id", "")
        doi = (entry.get("DOI") or entry.get("doi") or "").lower().strip()
        title = (entry.get("title") or "").lower().strip()[:80]
        if doi:
            doi_map[doi] = cid
        if title:
            title_map[title] = cid
    return doi_map, title_map


def find_cached_papers() -> list[dict]:
    """Return hi+med triage papers that have a cached text file, sorted by priority."""
    triage = json.loads((_HERE / "triage_c1_combined.json").read_text(encoding="utf-8"))
    doi_map, title_map = load_vault_index()

    results = []
    seen = set()
    for p in triage:
        if p.get("priority") not in ("high", "medium"):
            continue
        doi   = (p.get("doi") or "").lower().strip()
        title = (p.get("title") or "").lower().strip()[:80]
        citekey = doi_map.get(doi) or title_map.get(title)
        if not citekey:
            continue
        cache_file = _CACHE_DIR / f"{citekey}.txt"
        if not cache_file.exists():
            continue
        if citekey in seen:
            continue
        seen.add(citekey)
        results.append({**p, "_citekey": citekey, "_cache_path": str(cache_file)})

    results.sort(key=lambda x: (
        RELEVANCE_ORDER.get(x.get("relevance", ""), 9),
        PRIORITY_ORDER.get(x.get("priority", ""), 9),
    ))
    return results


# ---------------------------------------------------------------------------
# Phase 1 — prepare
# ---------------------------------------------------------------------------

def prepare(batch_size: int = BATCH_SIZE) -> None:
    papers = find_cached_papers()
    print(f"Papers with cached text: {len(papers)}")

    batches = [papers[i:i+batch_size] for i in range(0, len(papers), batch_size)]
    print(f"Batches ({batch_size} papers each): {len(batches)}")

    _BATCHES.mkdir(exist_ok=True)
    for i, batch in enumerate(batches, 1):
        out = _BATCHES / f"claim_mapping_batch{i}.json"
        if not out.exists():
            out.write_text(json.dumps(batch, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"  Wrote {out.name}  ({len(batch)} papers)")
        else:
            print(f"  {out.name} already exists — skipping")

    print()
    print(f"Batch files written to {_BATCHES}/")
    print(f"Output files expected: claim_mapping_part{{1..{len(batches)}}}.json")


# ---------------------------------------------------------------------------
# Phase 2 — merge
# ---------------------------------------------------------------------------

def merge() -> None:
    parts = sorted(_HERE.glob("claim_mapping_part*.json"),
                   key=lambda p: int(p.stem.replace("claim_mapping_part", "")))
    if not parts:
        print("No claim_mapping_part*.json files found. Run agents first.")
        return

    all_mappings: list[dict] = []
    for p in parts:
        items = json.loads(p.read_text(encoding="utf-8"))
        all_mappings.extend(items)
        print(f"  {p.name}: {len(items)} entries")

    # Summary
    total_claims = sum(len(m.get("claims_mapped", [])) for m in all_mappings)
    stances = Counter()
    themes_hit: Counter = Counter()
    for m in all_mappings:
        for c in m.get("claims_mapped", []):
            stances[c.get("relation", "")] += 1
            themes_hit[c.get("claim_id", "")[:2]] += 1

    _OUT.write_text(json.dumps(all_mappings, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n{'═'*60}")
    print(f"CLAIM MAPPING — CYCLE 1")
    print(f"{'─'*60}")
    print(f"Papers mapped:   {len(all_mappings)}")
    print(f"Total claims:    {total_claims}")
    print(f"\nStances:")
    for s, n in stances.most_common():
        print(f"  {s:12s}: {n}")
    print(f"\nTop themes hit:")
    for t, n in themes_hit.most_common(10):
        print(f"  {t:6s}: {n}")
    print(f"\nOutput: {_OUT}")


# ---------------------------------------------------------------------------
# Phase 3 — status
# ---------------------------------------------------------------------------

def status() -> None:
    batch_files  = sorted(_BATCHES.glob("claim_mapping_batch*.json"))
    output_files = {p.stem.replace("claim_mapping_part", ""): p
                    for p in _HERE.glob("claim_mapping_part*.json")}
    print(f"{'Batch':<10} {'Papers':<8} {'Output':<10}")
    print("─" * 30)
    total_done = 0
    for bf in batch_files:
        n = bf.stem.replace("claim_mapping_batch", "")
        papers = json.loads(bf.read_text())
        done = n in output_files
        if done:
            total_done += len(papers)
        print(f"  batch{n:<6} {len(papers):<8} {'✓' if done else 'pending'}")
    print(f"\nDone: {total_done} / {sum(len(json.loads(b.read_text())) for b in batch_files)} papers")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--merge",  action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    args = parser.parse_args()

    if args.merge:
        merge()
    elif args.status:
        status()
    else:
        prepare(batch_size=args.batch_size)


if __name__ == "__main__":
    main()
