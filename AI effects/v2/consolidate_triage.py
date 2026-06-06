"""
consolidate_triage.py — Merge all triage_c1_part*.json files into triage_c1_combined.json.

Also deduplicates by title (case-insensitive) keeping the highest-priority entry,
and prints a summary breakdown by relevance, priority, theme, and strategy.

Usage:
  uv run consolidate_triage.py
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

_HERE = Path(__file__).parent
_OUT  = _HERE / "triage_c1_combined.json"

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2, "error": 3}
RELEVANCE_ORDER = {"relevant": 0, "marginal": 1, "irrelevant": 2, "error": 3}


def load_parts() -> list[dict]:
    # S1 base, all numbered C1 parts, S5/OA combined, and S3/OA combined
    base   = _HERE / "triage_c1.json"
    parts  = sorted(_HERE.glob("triage_c1_part*.json"))
    s5oa   = _HERE / "triage_s5oa_combined.json"
    s3oa   = _HERE / "triage_s3oa_combined.json"
    extras = [f for f in [s5oa, s3oa] if f.exists()]
    if not base.exists() and not parts:
        raise FileNotFoundError("No triage_c1*.json files found")
    all_papers: list[dict] = []
    for p in ([base] if base.exists() else []) + parts + extras:
        items = json.loads(p.read_text(encoding="utf-8"))
        all_papers.extend(items)
        print(f"  {p.name}: {len(items)} entries")
    return all_papers


def dedup(papers: list[dict]) -> list[dict]:
    seen: dict[str, dict] = {}
    for p in papers:
        key = (p.get("title") or "").strip().lower()
        if not key:
            continue
        if key not in seen:
            seen[key] = p
        else:
            existing = seen[key]
            # Keep whichever has better (lower) score
            if (RELEVANCE_ORDER.get(p.get("relevance","error"), 3),
                PRIORITY_ORDER.get(p.get("priority","error"), 3)) < \
               (RELEVANCE_ORDER.get(existing.get("relevance","error"), 3),
                PRIORITY_ORDER.get(existing.get("priority","error"), 3)):
                seen[key] = p
    return list(seen.values())


def sort_papers(papers: list[dict]) -> list[dict]:
    return sorted(papers, key=lambda p: (
        RELEVANCE_ORDER.get(p.get("relevance","error"), 3),
        PRIORITY_ORDER.get(p.get("priority","error"), 3),
        (p.get("title") or "").lower()
    ))


def print_summary(papers: list[dict]) -> None:
    rel   = Counter(p.get("relevance") for p in papers)
    pri   = Counter(p.get("priority") for p in papers if p.get("relevance") in ("relevant","marginal"))
    strat = Counter(p.get("strategy") for p in papers)

    theme_counts: Counter = Counter()
    for p in papers:
        if p.get("relevance") in ("relevant","marginal"):
            for t in (p.get("themes") or []):
                theme_counts[t] += 1

    print(f"\n{'═'*60}")
    print(f"COMBINED TRIAGE — CYCLE 1")
    print(f"{'─'*60}")
    print(f"Total papers:   {len(papers)}")
    print(f"\nRelevance:")
    for r in ("relevant","marginal","irrelevant","error"):
        n = rel.get(r, 0)
        if n:
            print(f"  {r:12s}: {n}")
    print(f"\nPriority (relevant+marginal only):")
    for pr in ("high","medium","low"):
        n = pri.get(pr, 0)
        if n:
            print(f"  {pr:8s}: {n}")
    print(f"\nBy strategy:")
    for s, n in sorted(strat.items()):
        print(f"  {s}: {n}")
    print(f"\nTop themes (relevant+marginal):")
    for theme, n in theme_counts.most_common(15):
        print(f"  {theme:6s}: {n}")
    print(f"\nOutput: {_OUT}")


def main() -> None:
    print("Loading triage parts…")
    all_papers = load_parts()
    print(f"Total before dedup: {len(all_papers)}")

    deduped = dedup(all_papers)
    print(f"After dedup:        {len(deduped)}")

    sorted_papers = sort_papers(deduped)
    _OUT.write_text(json.dumps(sorted_papers, indent=2, ensure_ascii=False), encoding="utf-8")

    print_summary(sorted_papers)


if __name__ == "__main__":
    main()
