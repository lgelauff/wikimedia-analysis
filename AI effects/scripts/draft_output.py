"""
draft_output.py

For each theme in claims_v2.json, build a prompt from verified claim passages
and ask the judge model to write a polished white paper theme block.

Writes output.md incrementally so a crash does not lose completed themes.
Already-drafted themes are skipped on re-run (resume support).

Usage:
    python -m scripts.draft_output [--theme-ids A B EC1 ...] [--model judge] [--force]
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from scripts.llm import query_llm, JUDGE
from scripts.format_citations import export_docx

_CLAIMS_JSON   = Path(__file__).parent.parent / "claims_v2.json"
_RESULTS_JSON  = Path(__file__).parent.parent / "tmp" / "verification_results.json"
_BIB_FILE      = Path(__file__).parent.parent / "sources.bib"
_OUTPUT        = Path(__file__).parent.parent / "output.md"

SCORE_ORDER = {"strong": 0, "partial": 1, "weak": 2, "none": 3, "contradicts": 4, "error": 5}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_bib(bib_path: Path) -> dict[str, dict]:
    """Parse BibTeX into {citekey: {author, year, title, url, doi}}."""
    entries: dict[str, dict] = {}
    text = bib_path.read_text(encoding="utf-8")
    for block in re.split(r"(?=@\w+\{)", text):
        m = re.match(r"@\w+\{(\w+),", block)
        if not m:
            continue
        key = m.group(1)
        entry: dict[str, str] = {}
        for field in ("author", "title", "year", "url", "doi", "journal",
                      "booktitle", "howpublished", "publisher"):
            fm = re.search(rf"{field}\s*=\s*\{{(.+?)\}}", block, re.DOTALL | re.IGNORECASE)
            if fm:
                entry[field] = re.sub(r"\s+", " ", fm.group(1)).replace("{", "").replace("}", "").strip()
        entries[key] = entry
    return entries


def best_passage(claim_id: str, results_by_claim: dict) -> tuple[str, str]:
    """Return (citekey, passage) for the strongest result for a claim."""
    rs = results_by_claim.get(claim_id, [])
    if not rs:
        return "", ""
    best = min(rs, key=lambda r: SCORE_ORDER.get(r["score"], 9))
    return best["citekey"], best.get("passage", "")


def format_source_ref(citekey: str, bib: dict[str, dict]) -> str:
    entry = bib.get(citekey, {})
    author = entry.get("author", citekey)
    # Shorten to first author last name
    first_author = author.split(",")[0].split(" and ")[0].strip().split()[-1]
    year = entry.get("year", "")
    title = entry.get("title", "")[:60]
    return f"{first_author} ({year}), \"{title}...\""


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

_SYSTEM = """\
You are a policy writer drafting a white paper called "AI Effects on the Knowledge Ecosystem."

Audience: policy makers, funders, journalists, and informed citizens — not academic specialists.
Tone: factual, clear, concerned but not alarmist. Plain language. No jargon unless unavoidable.

Structure per theme — three elements in this order:
  1. Summary line (1–2 sentences, bold) — the headline finding, defensible from sources alone
  2. Context paragraph — what the effect is, why it matters for knowledge infrastructure
  3. Evidence (1–2 paragraphs) — specific findings from sources; integrate counterevidence honestly

Paragraph length: 100–150 words maximum per paragraph (Chicago style). If the evidence is rich,
split it across two shorter paragraphs rather than writing one long one.

Citation style: use inline footnote markers like [^1], [^2] at the end of specific claims.
At the bottom of each theme block, list footnotes as:
  [^1]: Author (Year), "Title", URL/DOI
  [^2]: ...

Rules:
- Do NOT label paragraphs with "Summary line", "Context paragraph", or "Evidence paragraph" —
  write the text directly without any such headings or labels.
- If you cite the same source more than once within a section, reuse the same footnote number
  each time — do not create a duplicate entry in the footnote list.
- Only assert what the provided source passages directly support.
- Where evidence is partial or contested, say so explicitly (e.g. "preliminary evidence suggests",
  "one study found", "while the mechanism is not fully established").
- Never invent statistics, institutions, or study details.
- If a gap note says a claim cannot be stated as established, frame it as emerging concern.
- Integrate counterevidence in the evidence paragraph, not as a footnote disclaimer.
- Write each theme as a self-contained section that can stand alone.
"""

_PROMPT_TEMPLATE = """\
THEME: {theme_name} (ID: {theme_id})

CLAIMS TO COVER:
{claims_block}

VERIFIED SOURCE PASSAGES (use these to construct the evidence paragraph):
{passages_block}

SOURCES AVAILABLE FOR FOOTNOTES:
{sources_block}

Write the theme block now. Bold the summary line. Then write the context paragraph and evidence \
paragraph(s) as plain prose — no labels, no headings within the block.
Add footnote markers [^1], [^2] etc. inline and list them at the bottom of your output.
Do not add a section header — that will be added by the assembler.
"""


def build_prompt(theme: dict, results_by_claim: dict, bib: dict) -> str:
    claims_lines = []
    passages_lines = []
    cited_keys: list[str] = []

    for claim in theme.get("claims", []):
        cid = claim["id"]
        grade = claim.get("evidence_grade", "")
        gap = claim.get("gap_note", "")
        counter = claim.get("counter_sources", [])

        claims_lines.append(f"[{cid}] ({grade}) {claim['text']}")
        if gap:
            claims_lines.append(f"  GAP NOTE: {gap}")
        if counter:
            claims_lines.append(f"  COUNTER-SOURCES: {', '.join(counter)}")

        # Best passage
        best_key, passage = best_passage(cid, results_by_claim)
        if passage and passage.strip():
            passages_lines.append(f"[{cid} / {best_key}]: {passage[:500]}")
            if best_key and best_key not in cited_keys:
                cited_keys.append(best_key)

        # Also collect all sources cited
        for src in claim.get("sources", []):
            if src not in cited_keys:
                cited_keys.append(src)

    sources_lines = []
    for i, key in enumerate(cited_keys, 1):
        sources_lines.append(f"[^{i}] citekey={key}: {format_source_ref(key, bib)}")

    prompt = _PROMPT_TEMPLATE.format(
        theme_name=theme["name"],
        theme_id=theme["id"],
        claims_block="\n".join(claims_lines),
        passages_block="\n\n".join(passages_lines) or "(no verified passages available)",
        sources_block="\n".join(sources_lines),
    )
    return prompt, cited_keys


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(only_themes: list[str] | None, model: str, force: bool) -> None:
    data = json.loads(_CLAIMS_JSON.read_text())
    results_raw = json.loads(_RESULTS_JSON.read_text()) if _RESULTS_JSON.exists() else []
    bib = parse_bib(_BIB_FILE)

    results_by_claim: dict[str, list] = defaultdict(list)
    for r in results_raw:
        results_by_claim[r["claim_id"]].append(r)

    # Load existing output to support resuming
    existing_output = _OUTPUT.read_text(encoding="utf-8") if _OUTPUT.exists() else ""
    drafted_ids: set[str] = set(re.findall(r"<!-- theme:(\w+[\-\d]*) -->", existing_output))
    if drafted_ids:
        print(f"Resuming: {len(drafted_ids)} themes already drafted: {sorted(drafted_ids)}")

    themes = data.get("themes", [])
    if only_themes:
        themes = [t for t in themes if t["id"] in only_themes]

    # Preserve manually-added content before/after theme blocks.
    # <!-- end-themes --> marks the boundary between generated themes and hand-written sections.
    default_header = "# AI Effects on the Knowledge Ecosystem\n\n<!-- White paper — policy-focused, broad audience -->\n<!-- Citations: numbered footnotes -->\n<!-- Status: in production -->\n\n"
    first_theme = re.search(r"<!-- theme:", existing_output)
    pre_content = existing_output[:first_theme.start()] if first_theme else default_header

    end_marker = re.search(r"<!-- end-themes -->", existing_output)
    post_content = existing_output[end_marker.start():] if end_marker else "\n<!-- end-themes -->\n"

    # Collect all theme sections (existing + new); stop at end-themes marker
    body_text = existing_output[first_theme.start():end_marker.start()] if (first_theme and end_marker) else existing_output
    sections: dict[str, str] = {}
    for m in re.finditer(r"(<!-- theme:([\w\-\d]+) -->.*?)(?=<!-- theme:[\w\-\d]+ -->|\Z)", body_text, re.DOTALL):
        sections[m.group(2)] = m.group(1)

    print(f"Drafting {len(themes)} themes with model: {model}\n")

    for i, theme in enumerate(themes, 1):
        tid = theme["id"]
        if tid in drafted_ids and not force:
            print(f"  [{i}/{len(themes)}] {tid} — skipped (already drafted)")
            continue

        print(f"  [{i}/{len(themes)}] {tid}: {theme['name']}...", end=" ", flush=True)

        prompt, cited_keys = build_prompt(theme, results_by_claim, bib)
        try:
            draft = query_llm(prompt, system=_SYSTEM, model=model, temperature=0.4)
        except Exception as exc:
            print(f"ERROR: {exc}")
            continue

        fn_map = " ".join(f"{i+1}={k}" for i, k in enumerate(cited_keys))
        section = f"<!-- theme:{tid} -->\n<!-- fn-map: {fn_map} -->\n## {theme['name']}\n\n{draft.strip()}\n\n"
        sections[tid] = section

        # Write full output after each theme (preserving pre/post content)
        theme_order = [t["id"] for t in data.get("themes", [])]
        body = "".join(sections.get(t, "") for t in theme_order if t in sections)
        _OUTPUT.write_text(pre_content + body + post_content, encoding="utf-8")

        print("ok")

    total = len(sections)
    print(f"\nDone. {total} themes in output.md")
    export_docx(_OUTPUT)


def main() -> None:
    parser = argparse.ArgumentParser(description="Draft output.md from verified claims")
    parser.add_argument("--theme-ids", nargs="+", metavar="ID", help="Only draft these theme IDs")
    parser.add_argument("--model", "-m", default="judge", help="LLM model alias (default: judge)")
    parser.add_argument("--force", action="store_true", help="Re-draft even if already done")
    args = parser.parse_args()
    run(only_themes=args.theme_ids, model=args.model, force=args.force)


if __name__ == "__main__":
    main()
