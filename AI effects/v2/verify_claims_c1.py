"""
verify_claims_c1.py — Verify that claimed passages exist in cached paper text.

Pass 1: exact case-insensitive substring match
Pass 2 (fallback): normalize both texts (collapse whitespace, strip hyphens/line-breaks)

Outputs:
  verification_c1.json   — per-mapping result with found/not_found and match details
  verification_c1.md     — human-readable summary

Usage:
  uv run verify_claims_c1.py
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

_HERE      = Path(__file__).parent
_VAULT     = Path(__file__).parent.parent.parent.parent / "research-vault"
_CACHE_DIR = _VAULT / "cache"
_MAP_FILE  = _HERE / "claim_mapping_c1.json"
_OUT_JSON  = _HERE / "verification_c1.json"
_OUT_MD    = _HERE / "verification_c1.md"

MIN_PASSAGE_LEN = 15  # ignore trivially short passages


def normalize(text: str) -> str:
    """Collapse whitespace, normalize unicode, lowercase."""
    text = unicodedata.normalize("NFKC", text)
    text = text.lower()
    # Collapse all whitespace (including newlines, tabs, non-breaking spaces)
    text = re.sub(r"\s+", " ", text)
    # Remove soft hyphens and zero-width chars
    text = re.sub(r"[­​‌‍﻿]", "", text)
    return text.strip()


def normalize_hard(text: str) -> str:
    """More aggressive: also strip punctuation runs and PDF ligature noise."""
    text = normalize(text)
    # Normalize typographic quotes and dashes
    text = text.replace("‘", "'").replace("’", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("–", "-").replace("—", "-")
    # Remove hyphenation artifacts (word- \n word → word word)
    text = re.sub(r"-\s+", "", text)
    # Collapse remaining punctuation variations: remove all non-alphanumeric except spaces
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    text = re.sub(r" +", " ", text)
    return text.strip()


def search_passage(passage: str, cache_text: str) -> tuple[bool, str]:
    """
    Returns (found: bool, method: str).
    method is one of: 'exact', 'normalized', 'hard', 'not_found'
    """
    if len(passage.strip()) < MIN_PASSAGE_LEN:
        return True, "too_short_skip"

    # Pass 1: case-insensitive exact
    if passage.lower() in cache_text.lower():
        return True, "exact"

    # Pass 2: normalize both
    norm_p = normalize(passage)
    norm_c = normalize(cache_text)
    if norm_p and norm_p in norm_c:
        return True, "normalized"

    # Pass 3: aggressive normalize
    hard_p = normalize_hard(passage)
    hard_c = normalize_hard(cache_text)
    # Allow partial match for very long passages — check first 80 chars
    if hard_p and hard_p in hard_c:
        return True, "hard"
    if len(hard_p) > 80 and hard_p[:80] in hard_c:
        return True, "hard_partial"

    return False, "not_found"


def main() -> None:
    mappings = json.loads(_MAP_FILE.read_text(encoding="utf-8"))
    print(f"Loaded {len(mappings)} mapped papers")

    results = []
    method_counts: Counter = Counter()
    not_found_entries = []

    cache_cache: dict[str, str] = {}

    for paper in mappings:
        citekey = paper.get("citekey", "")
        cache_file = _CACHE_DIR / f"{citekey}.txt"

        if not cache_file.exists():
            for cm in paper.get("claims_mapped", []):
                method_counts["no_cache"] += 1
            results.append({**paper, "_verification": "no_cache"})
            print(f"  {citekey}: NO CACHE — skipping")
            continue

        if citekey not in cache_cache:
            cache_cache[citekey] = cache_file.read_text(encoding="utf-8", errors="replace")
        cache_text = cache_cache[citekey]

        verified_claims = []
        paper_has_failure = False

        for cm in paper.get("claims_mapped", []):
            passage = cm.get("passage", "")
            found, method = search_passage(passage, cache_text)
            method_counts[method] += 1
            verified_cm = {**cm, "_found": found, "_method": method}
            verified_claims.append(verified_cm)
            if not found:
                paper_has_failure = True
                not_found_entries.append({
                    "citekey":   citekey,
                    "claim_id":  cm.get("claim_id"),
                    "passage":   passage[:200],
                    "confidence": cm.get("confidence"),
                })

        status = "ok" if not paper_has_failure else "has_failures"
        results.append({**paper, "claims_mapped": verified_claims, "_verification": status})

        n_fail = sum(1 for c in verified_claims if not c["_found"])
        n_ok   = len(verified_claims) - n_fail
        if paper_has_failure:
            print(f"  {citekey}: {n_ok} OK, {n_fail} NOT FOUND")
        else:
            print(f"  {citekey}: {len(verified_claims)} OK")

    # Write JSON
    _OUT_JSON.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    # Write MD report
    total_claims = sum(v for k, v in method_counts.items() if k != "no_cache")
    found_total  = sum(v for k, v in method_counts.items()
                       if k in ("exact","normalized","hard","hard_partial","too_short_skip"))
    not_found_n  = method_counts["not_found"]

    lines = [
        "# Claim Verification — Cycle 1",
        f"*{len(mappings)} papers, {total_claims} claim mappings checked*",
        "",
        "## Match method breakdown",
        "",
        f"| Method | Count |",
        f"|---|---|",
    ]
    for method in ("exact","normalized","hard","hard_partial","too_short_skip","not_found","no_cache"):
        n = method_counts[method]
        if n:
            lines.append(f"| {method} | {n} |")
    pct_found = 100 * found_total / total_claims if total_claims else 0
    lines += [
        "",
        f"**Found: {found_total}/{total_claims} ({pct_found:.1f}%)**  "
        f"Not found: {not_found_n}",
        "",
        "---",
        "",
        "## Not-found passages",
        "",
        "*These need manual review — passage may be hallucinated, truncated, or from an uncached section.*",
        "",
    ]
    for e in not_found_entries:
        lines.append(f"**{e['citekey']}** → claim {e['claim_id']} (confidence: {e['confidence']})")
        lines.append(f"  > \"{e['passage'][:180]}\"")
        lines.append("")

    _OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(f"\n{'─'*60}")
    print(f"Found:     {found_total}/{total_claims} ({pct_found:.1f}%)")
    print(f"Not found: {not_found_n}")
    print(f"No cache:  {method_counts['no_cache']}")
    print(f"\nOutputs:")
    print(f"  {_OUT_JSON}")
    print(f"  {_OUT_MD}")


if __name__ == "__main__":
    main()
