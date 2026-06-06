"""
triage.py — Abstract triage for Cycle 1 candidates.

Scores each candidate using Claude Opus:
  - relevance:  relevant | marginal | irrelevant
  - stance:     supporting | contradicting | qualifying | unclear
  - themes:     list of theme codes (A–H, EC-1 through EC-14)
  - rationale:  one sentence
  - priority:   high | medium | low (for retrieval ordering)

Usage:
  uv run triage.py                          # triage S1 (Elicit) candidates
  uv run triage.py --input candidates_new_c1.json   # triage full S2-S5 set
  uv run triage.py --input candidates_s1_new_c1.json candidates_new_c1.json  # merge + triage all

Resumes automatically: already-triaged titles are skipped.
Output: triage_c1.json (appended on each run)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import anthropic

_HERE       = Path(__file__).parent
_TRIAGE_OUT = _HERE / "triage_c1.json"
_ERRORS_LOG = _HERE / "fetch_errors_c1.log"

MODEL = "claude-opus-4-7"

# ---------------------------------------------------------------------------
# Theme reference (derived from core_doc.md — independent of v1)
# ---------------------------------------------------------------------------

THEMES = """
A  — Changing information-seeking behaviour: AI search summaries reducing click-through to source sites; users bypassing original sources.
B  — Platform traffic decline: measurable drops in human visits to Wikipedia, Stack Overflow, news sites, and other knowledge platforms.
C  — Contributor pipeline erosion: declining editor/contributor recruitment and retention on Wikipedia, open source, and Q&A platforms.
D  — Financial sustainability: threat to donation, advertising, and revenue models that fund open knowledge infrastructure.
E  — AI scraping harm: bandwidth and infrastructure costs imposed on platforms by AI crawlers; service disruptions.
F  — Defensive countermeasures and collateral harm: CAPTCHAs, IP blocks, paywalls, and other anti-bot measures that harm legitimate users.
G  — Credit attribution and creator recognition: AI systems using source content without directing traffic or credit back to creators.
H  — Information literacy and source awareness: AI-generated answers eroding critical thinking, source-checking habits, and epistemic autonomy.
EC-1 — Synthetic content contamination: AI-generated content entering training data, encyclopaedias, and scientific literature.
EC-4 — Policy responses: regulatory and platform responses to AI knowledge-ecosystem effects.
EC-5 — Journalism: specific effects on news production, journalism economics, and press freedom.
EC-6 — Power concentration: AI accelerating concentration of information access and distribution in a few large platforms.
EC-8 — Disinformation: AI enabling cheaper, more scalable production of mis/disinformation.
EC-9 — Demographic stratification: differential AI effects across age, income, education, and geography.
EC-10 — Global South / language exclusion: smaller-language communities disproportionately harmed.
EC-11 — Model opacity: lack of transparency in AI systems obscuring knowledge provenance.
EC-12 — Children and psychological effects: developmental and wellbeing impacts of AI on young people.
EC-13 — Intellectual monoculture: AI homogenising knowledge production and narrowing epistemic diversity.
EC-14 — Deep expertise pipeline erosion: AI reducing incentives to develop genuine deep expertise.
""".strip()

SYSTEM_PROMPT = f"""You are a research assistant helping triage academic papers for a literature review on the effects of AI on the open knowledge ecosystem.

The review covers these themes:
{THEMES}

For each paper you receive, respond with a JSON object with exactly these fields:
{{
  "relevance": "relevant" | "marginal" | "irrelevant",
  "stance": "supporting" | "contradicting" | "qualifying" | "unclear",
  "themes": ["A", "B", ...],
  "priority": "high" | "medium" | "low",
  "rationale": "One sentence explaining the relevance and stance."
}}

Definitions:
- relevant: directly addresses one or more themes with empirical evidence or important analysis
- marginal: touches a theme but obliquely, or is methodologically too weak to be useful
- irrelevant: does not address any theme in a useful way
- supporting: evidence or argument that the AI effects described in the themes are real and significant
- contradicting: evidence or argument that those effects are absent, overstated, or reversed
- qualifying: evidence that nuances, complicates, or contextualises (e.g. "depends on use case")
- high priority: should be retrieved and verified regardless of stance; could change a claim
- medium priority: worth retrieving if retrieval is easy
- low priority: marginal relevance; retrieve only if the high/medium pool is thin

Respond with JSON only. No other text."""

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def load_candidates(paths: list[Path]) -> list[dict]:
    all_cands: list[dict] = []
    seen: set[str] = set()
    for p in paths:
        if not p.exists():
            print(f"  WARNING: {p.name} not found — skipping", file=sys.stderr)
            continue
        items = json.loads(p.read_text(encoding="utf-8"))
        for item in items:
            key = (item.get("doi") or "").lower() or (item.get("url") or "").rstrip("/") or item.get("title", "")[:80].lower()
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            all_cands.append(item)
    return all_cands


def load_existing_triage() -> dict[str, dict]:
    """Load already-triaged results keyed by title (lowercase)."""
    if not _TRIAGE_OUT.exists():
        return {}
    results = json.loads(_TRIAGE_OUT.read_text(encoding="utf-8"))
    return {r["title"].lower(): r for r in results}


def save_triage(results: list[dict]) -> None:
    results_sorted = sorted(results, key=lambda r: (r.get("relevance", "z"), r.get("priority", "z"), r.get("title", "")))
    _TRIAGE_OUT.write_text(json.dumps(results_sorted, indent=2, ensure_ascii=False), encoding="utf-8")


def triage_one(client: anthropic.Anthropic, candidate: dict) -> dict:
    title    = candidate.get("title") or ""
    abstract = candidate.get("abstract") or "(no abstract available)"
    year     = candidate.get("year") or "unknown"
    authors  = ", ".join(candidate.get("authors") or []) or "unknown"

    user_msg = f"Title: {title}\nAuthors: {authors}\nYear: {year}\nAbstract: {abstract[:800]}"

    for attempt in range(3):
        try:
            resp = client.messages.create(
                model=MODEL,
                max_tokens=256,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            )
            text = resp.content[0].text.strip()
            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            scores = json.loads(text)
            return {
                "title":     title,
                "year":      year,
                "authors":   candidate.get("authors") or [],
                "doi":       candidate.get("doi"),
                "url":       candidate.get("url"),
                "strategy":  candidate.get("strategy", ""),
                "query":     candidate.get("query", ""),
                "relevance": scores.get("relevance", "unclear"),
                "stance":    scores.get("stance", "unclear"),
                "themes":    scores.get("themes", []),
                "priority":  scores.get("priority", "medium"),
                "rationale": scores.get("rationale", ""),
            }
        except anthropic.RateLimitError:
            wait = 30 * (attempt + 1)
            print(f"  [rate limit] waiting {wait}s…", end=" ", flush=True)
            time.sleep(wait)
        except (json.JSONDecodeError, Exception) as exc:
            from datetime import datetime, timezone
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            with _ERRORS_LOG.open("a") as f:
                f.write(f"{ts} | triage | {type(exc).__name__}: {str(exc)[:120]} | title: {title[:60]}\n")
            return {
                "title": title, "year": year, "authors": candidate.get("authors") or [],
                "doi": candidate.get("doi"), "url": candidate.get("url"),
                "strategy": candidate.get("strategy", ""), "query": candidate.get("query", ""),
                "relevance": "error", "stance": "unclear", "themes": [], "priority": "low",
                "rationale": f"Triage error: {exc}",
            }
    return {
        "title": title, "relevance": "error", "stance": "unclear",
        "themes": [], "priority": "low", "rationale": "Failed after 3 retries",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input", nargs="+",
        default=["candidates_s1_new_c1.json"],
        help="Candidate JSON files to triage (default: S1 Elicit results)",
    )
    parser.add_argument(
        "--batch-size", type=int, default=200,
        help="Max candidates to triage per run (default: 200). Re-run to continue.",
    )
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        # Try loading from .env in wikimedia-analysis root
        env_path = Path(__file__).parent.parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("ANTHROPIC_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"\'')
                    os.environ["ANTHROPIC_API_KEY"] = api_key
                    break
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not found in environment or .env", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    input_paths = [_HERE / p for p in args.input]
    candidates  = load_candidates(input_paths)
    existing    = load_existing_triage()

    todo = [c for c in candidates if c.get("title", "").lower() not in existing]
    done = list(existing.values())

    total_remaining = len(todo)
    batch = todo[:args.batch_size]
    batches_left = max(0, (total_remaining - args.batch_size + args.batch_size - 1) // args.batch_size)

    print(f"Candidates loaded:  {len(candidates)} total")
    print(f"Already triaged:    {len(done)}")
    print(f"Remaining:          {total_remaining}")
    print(f"This batch:         {len(batch)} (--batch-size {args.batch_size})")
    if batches_left > 0:
        print(f"Further runs needed: {batches_left} more batch(es) after this one")
    print(f"Model: {MODEL}\n")

    for i, cand in enumerate(batch, 1):
        title = cand.get("title", "(no title)")[:70]
        print(f"[{i}/{len(todo)}] {title}…", end=" ", flush=True)
        result = triage_one(client, cand)
        print(f"{result['relevance']:10s}  {result['stance']:14s}  themes={result['themes']}  priority={result['priority']}")
        done.append(result)
        save_triage(done)

    # Summary
    from collections import Counter
    rel   = Counter(r["relevance"] for r in done)
    pri   = Counter(r["priority"]  for r in done if r["relevance"] in ("relevant", "marginal"))
    print(f"\n{'─'*60}")
    print(f"Relevance (all triaged so far): {dict(rel)}")
    print(f"Priority (relevant+marginal):   {dict(pri)}")
    remaining_after = total_remaining - len(batch)
    if remaining_after > 0:
        print(f"\n{remaining_after} candidates still untriaged — re-run to continue next batch.")
    else:
        print(f"\nAll candidates triaged.")
    print(f"Output: {_TRIAGE_OUT}")


if __name__ == "__main__":
    main()
