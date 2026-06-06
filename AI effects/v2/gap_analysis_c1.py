"""
gap_analysis_c1.py — Produce gap_analysis_c1.md from claim_mapping_c1.json.

Reads all claim_mapping_part*.json files (merges on the fly if needed) or
the consolidated claim_mapping_c1.json, then writes gap_analysis_c1.md covering:
  - Evidence strength per claim (well-evidenced / partial / thin / none)
  - Counter-evidence (contradicting mappings)
  - New themes flagged by agents
  - Recommended Cycle 2 seed priorities

Usage:
  uv run gap_analysis_c1.py
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

_HERE = Path(__file__).parent
_OUT  = _HERE / "gap_analysis_c1.md"

CLAIM_TAXONOMY = {
    "A1": "Users query AI instead of search; click-throughs to source websites declining",
    "A2": "Users unaware of information provenance in AI-summarized content",
    "A3": "AI search accelerates decisions and reduces scrutiny of sources",
    "B1": "Wikipedia human visitor numbers dropping due to AI search substitution",
    "B2": "Stack Overflow / QA community activity declining since ChatGPT",
    "B3": "News publisher and open-web traffic declining due to AI Overviews / zero-click",
    "C1": "Wikipedia editor pipeline affected — fewer readers → fewer new editors",
    "C2": "Open source contribution quality/quantity affected by AI-generated submissions",
    "C3": "Online QA community contributors substituting or leaving due to AI",
    "D1": "Wikimedia donation revenue threatened by declining traffic",
    "D2": "News publisher revenue under pressure",
    "D3": "Academic/open-access infrastructure costs rising due to scraping",
    "E1": "AI bots imposing measurable infrastructure costs on open knowledge platforms",
    "E2": "AI scraping causing service disruptions",
    "E3": "Content creators not receiving credit or compensation for training data use",
    "F1": "CAPTCHAs, paywalls, rate limits increasingly harm human users as bot countermeasures",
    "G1": "AI-generated content infiltrating Wikipedia at scale",
    "G2": "Wikipedia governance and volunteer capacity under pressure from AI",
    "H1": "AI systems produce and propagate factual errors and hallucinations",
    "H2": "AI search presents information without reliable sourcing or verification pathways",
    "EC-1":  "Value not flowing back to content creators whose work trained the AI",
    "EC-4":  "Platform power concentration — AI consolidates information access",
    "EC-9":  "Knowledge access inequality and deskilling divides",
    "EC-11": "AI search disintermediating original sources; citation and attribution crisis",
    "EC-12": "Cognitive offloading / deskilling through AI reliance",
    "EC-13": "Cultural and epistemic homogenization through AI-generated content at scale",
    "EC-14": "Labor displacement in knowledge work",
}

STRENGTH_THRESHOLDS = {
    "strong":  8,   # 8+ papers
    "partial": 4,   # 4-7 papers
    "thin":    1,   # 1-3 papers
    "none":    0,   # 0 papers
}


def load_mapping() -> list[dict]:
    # Prefer consolidated file; also pick up any new part files not yet merged
    parts_in_main = sorted(_HERE.glob("claim_mapping_part*.json"),
                           key=lambda p: int(p.stem.replace("claim_mapping_part", "")))
    base_file = _HERE / "claim_mapping_c1.json"

    papers: list[dict] = []
    seen_citekeys: set[str] = set()

    if base_file.exists():
        for p in json.loads(base_file.read_text(encoding="utf-8")):
            ck = p.get("citekey", "")
            if ck not in seen_citekeys:
                seen_citekeys.add(ck)
                papers.append(p)

    for pf in parts_in_main:
        for p in json.loads(pf.read_text(encoding="utf-8")):
            ck = p.get("citekey", "")
            if ck not in seen_citekeys:
                seen_citekeys.add(ck)
                papers.append(p)

    return papers


def strength_label(n: int) -> str:
    if n >= STRENGTH_THRESHOLDS["strong"]:  return "STRONG"
    if n >= STRENGTH_THRESHOLDS["partial"]: return "PARTIAL"
    if n >= STRENGTH_THRESHOLDS["thin"]:    return "THIN"
    return "NONE"


def analyse(papers: list[dict]) -> dict:
    claim_papers: dict[str, list[dict]]  = defaultdict(list)
    claim_contradicting: dict[str, list] = defaultdict(list)
    claim_qualifying: dict[str, list]    = defaultdict(list)
    new_themes: list[tuple[str, str]]    = []  # (citekey, description)

    for paper in papers:
        for cm in paper.get("claims_mapped", []):
            cid = cm.get("claim_id", "")
            rel = cm.get("relation", "")
            entry = {
                "citekey":  paper.get("citekey", ""),
                "title":    paper.get("title", "")[:70],
                "year":     paper.get("year"),
                "priority": paper.get("priority", ""),
                "passage":  cm.get("passage", ""),
                "confidence": cm.get("confidence", ""),
            }
            claim_papers[cid].append(entry)
            if rel == "contradicting":
                claim_contradicting[cid].append(entry)
            elif rel == "qualifying":
                claim_qualifying[cid].append(entry)

        for flag in (paper.get("new_themes_flagged") or []):
            if flag and flag.strip():
                new_themes.append((paper.get("citekey", ""), flag.strip()))

    return {
        "papers":               papers,
        "claim_papers":         dict(claim_papers),
        "claim_contradicting":  dict(claim_contradicting),
        "claim_qualifying":     dict(claim_qualifying),
        "new_themes":           new_themes,
    }


def write_report(data: dict) -> None:
    lines: list[str] = []
    cp   = data["claim_papers"]
    contr = data["claim_contradicting"]
    qual  = data["claim_qualifying"]
    new_t = data["new_themes"]

    lines += [
        "# Gap Analysis — Cycle 1",
        f"*Generated from {len(data['papers'])} papers with full-text claim mappings*",
        "",
        "---",
        "",
        "## Evidence strength by claim",
        "",
        "| Claim | Description | Papers | Strength | Counter |",
        "|---|---|---|---|---|",
    ]

    for cid, desc in CLAIM_TAXONOMY.items():
        n = len(cp.get(cid, []))
        strength = strength_label(n)
        n_contra = len(contr.get(cid, []))
        contra_flag = f"⚠ {n_contra}" if n_contra else "—"
        lines.append(f"| {cid} | {desc[:55]}… | {n} | {strength} | {contra_flag} |")

    # ---------- Filled gaps ----------
    strong_claims = [cid for cid in CLAIM_TAXONOMY if strength_label(len(cp.get(cid,[]))) == "STRONG"]
    lines += ["", "---", "", "## Gaps filled this cycle", ""]
    if strong_claims:
        for cid in strong_claims:
            entries = cp[cid]
            high_conf = [e for e in entries if e.get("confidence") == "high"]
            lines.append(f"**{cid}** — {CLAIM_TAXONOMY[cid]}")
            lines.append(f"  {len(entries)} papers ({len(high_conf)} high-confidence). "
                         f"Key sources: {', '.join(e['citekey'] for e in entries[:4])}")
            lines.append("")
    else:
        lines.append("*No claims reached STRONG evidence threshold this cycle.*")
        lines.append("")

    # ---------- Partial ----------
    partial_claims = [cid for cid in CLAIM_TAXONOMY if strength_label(len(cp.get(cid,[]))) == "PARTIAL"]
    lines += ["---", "", "## Gaps narrowed (partial evidence)", ""]
    for cid in partial_claims:
        entries = cp[cid]
        lines.append(f"**{cid}** — {CLAIM_TAXONOMY[cid]}")
        lines.append(f"  {len(entries)} papers. Sources: {', '.join(e['citekey'] for e in entries[:4])}")
        lines.append("")

    # ---------- Thin / None ----------
    thin_claims = [cid for cid in CLAIM_TAXONOMY if strength_label(len(cp.get(cid,[]))) in ("THIN","NONE")]
    lines += ["---", "", "## Gaps still open (thin or no evidence)", ""]
    for cid in thin_claims:
        n = len(cp.get(cid, []))
        label = "NONE" if n == 0 else f"THIN ({n} paper{'s' if n>1 else ''})"
        lines.append(f"**{cid}** [{label}] — {CLAIM_TAXONOMY[cid]}")
        if n > 0:
            for e in cp[cid]:
                lines.append(f"  - {e['citekey']} ({e['year']}): \"{e['passage'][:120]}…\"")
        lines.append("")

    # ---------- Counter-evidence ----------
    lines += ["---", "", "## Counter-evidence (contradicting mappings)", ""]
    all_contra = [(cid, e) for cid, entries in contr.items() for e in entries]
    if all_contra:
        for cid, e in all_contra:
            lines.append(f"**{cid}** — {e['citekey']} ({e['year']})")
            lines.append(f"  \"{e['passage'][:200]}\"")
            lines.append("")
    else:
        lines.append("*No contradicting mappings.*")
        lines.append("")

    # ---------- Qualifying evidence ----------
    qual_summary = {cid: len(v) for cid, v in qual.items() if v}
    lines += ["---", "", "## Claims with significant qualifying evidence", ""]
    for cid, n in sorted(qual_summary.items(), key=lambda x: -x[1]):
        if n >= 2:
            lines.append(f"**{cid}** — {n} qualifying papers: "
                         f"{', '.join(e['citekey'] for e in qual[cid][:4])}")
    lines.append("")

    # ---------- New themes flagged ----------
    lines += ["---", "", "## New themes flagged by agents", "",
              "*These are themes not covered by the current claim taxonomy — "
              "candidates for Cycle 2 expansion or a new claims section.*", ""]
    for citekey, flag in new_t:
        lines.append(f"- **[{citekey}]** {flag}")
    lines.append("")

    # ---------- Cycle 2 recommendations ----------
    lines += ["---", "", "## Cycle 2 seed recommendations", ""]

    thin_none = [cid for cid in CLAIM_TAXONOMY
                 if strength_label(len(cp.get(cid,[]))) in ("THIN","NONE")]
    lines.append("### Priority gaps for targeted S5 queries")
    for cid in thin_none:
        lines.append(f"- **{cid}**: {CLAIM_TAXONOMY[cid]}")
    lines.append("")

    lines.append("### New themes worth adding to Cycle 2 scope")
    lines.append("Based on agent flags above — highest value additions:")
    for _, flag in new_t[:5]:
        lines.append(f"- {flag[:100]}")
    lines.append("")

    lines.append("### Claims with counter-evidence — needs adversarial deepening")
    for cid, entries in contr.items():
        lines.append(f"- **{cid}**: {', '.join(e['citekey'] for e in entries)}")
    lines.append("")

    _OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Written: {_OUT}")
    print(f"Papers: {len(data['papers'])}, Claims covered: {len(cp)}, "
          f"Strong: {len(strong_claims)}, Thin/None: {len(thin_claims)}, "
          f"Counter: {len(all_contra)}")


def main() -> None:
    papers = load_mapping()
    print(f"Loaded {len(papers)} mapped papers")
    data = analyse(papers)
    write_report(data)


if __name__ == "__main__":
    main()
