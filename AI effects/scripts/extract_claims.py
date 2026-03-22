"""
extract_claims.py

Parse a markdown document and extract factual claims grouped by theme.
Outputs a structured JSON file for use by the Scoper and Search agents.

Usage:
    python extract_claims.py <input.md> [output.json] [--model MODEL]

If output path is omitted, writes to <input_stem>_claims.json in the same directory.

--model controls the LLM used when --llm flag is passed for enhanced classification.
  Default: bulk (mistral-large-latest)
  Options: cheap | bulk | judge | fast | best | any full model string
  Without --llm, extraction is pure regex (no API calls, no cost).
"""

import argparse
import json
import re
import sys
from pathlib import Path


# --- Theme keywords for auto-classification ---
# Each theme has a list of keywords; a claim is assigned to the first matching theme.
# Claims that match nothing go to "unclassified" for the Scoper to assign manually.

THEMES = {
    "information_seeking": [
        "search", "find information", "information-seeking", "how people",
        "aware", "where information", "origin", "source of"
    ],
    "platform_traffic": [
        "wikipedia", "stack overflow", "traffic", "visitors", "declining",
        "dropping", "views", "pageviews", "usage"
    ],
    "contributor_pipelines": [
        "editor", "contributor", "pipeline", "good first issue", "open source",
        "volunteer", "matplotlib", "newcomer", "onboarding"
    ],
    "financial_sustainability": [
        "donation", "funding", "revenue", "financial", "sustain", "model"
    ],
    "scraping_harm": [
        "scraping", "crawl", "bot", "server", "bandwidth", "cost", "hostile",
        "wcna", "overwhelm", "infrastructure"
    ],
    "defensive_responses": [
        "paywall", "captcha", "check", "block", "friction", "false positive",
        "humanity check", "invasive", "access"
    ],
    "credit_attribution": [
        "credit", "attribution", "compensation", "creator", "acknowledge",
        "reward", "recognition"
    ],
    "information_literacy": [
        "critical", "literacy", "evaluate", "verify", "trust", "misinformation",
        "discern", "ability"
    ],
}

# Lines to skip — meta-commentary, not claims
SKIP_PATTERNS = [
    r"^\s*$",                          # blank lines
    r"^#",                             # markdown headings
    r"needs more thorough sourcing",   # editorial notes
    r"^in this tab",                   # intro sentence
    r"for example",                    # example markers (handled separately)
    r"^\s*[-*]\s*examples?:",          # example headers
]


def is_skippable(line: str) -> bool:
    line_lower = line.lower().strip()
    return any(re.search(p, line_lower) for p in SKIP_PATTERNS)


def classify_theme(text: str) -> str:
    text_lower = text.lower()
    for theme, keywords in THEMES.items():
        if any(kw in text_lower for kw in keywords):
            return theme
    return "unclassified"


def clean_line(line: str) -> str:
    """Strip markdown list markers and excess whitespace."""
    return re.sub(r"^\s*[-*]\s*", "", line).strip()


def extract_claims(md_path: Path) -> dict:
    raw_lines = md_path.read_text(encoding="utf-8").splitlines()

    claims_by_theme: dict[str, list[dict]] = {t: [] for t in THEMES}
    claims_by_theme["unclassified"] = []

    claim_id = 1
    for i, line in enumerate(raw_lines):
        if is_skippable(line):
            continue

        text = clean_line(line)
        if not text:
            continue

        # Mark lines that explicitly note a missing source
        needs_source = bool(re.search(r"\(source\)", text, re.IGNORECASE))
        text = re.sub(r"\s*\(source\)", "", text, flags=re.IGNORECASE).strip()

        theme = classify_theme(text)

        claims_by_theme[theme].append({
            "id": claim_id,
            "text": text,
            "line": i + 1,
            "needs_source": needs_source,
            "theme": theme,
            "sources": [],          # populated by find_sources.py
            "verified": False,      # set to True by verify_source.py
            "summary": ""           # filled in after verification
        })
        claim_id += 1

    # Build summary stats
    total = sum(len(v) for v in claims_by_theme.values())
    stats = {theme: len(claims) for theme, claims in claims_by_theme.items()}

    return {
        "source_document": str(md_path),
        "total_claims": total,
        "stats_by_theme": stats,
        "claims_by_theme": claims_by_theme
    }


def _llm_reclassify(claims_by_theme: dict, model: str) -> dict:
    """
    Pass unclassified claims to an LLM for theme assignment.
    Only called when --llm flag is set.
    """
    from scripts.llm import query_llm  # local import — only needed with --llm

    unclassified = claims_by_theme.get("unclassified", [])
    if not unclassified:
        return claims_by_theme

    theme_list = [t for t in claims_by_theme if t != "unclassified"]
    prompt_lines = [
        "Classify each claim into one of these themes:",
        ", ".join(theme_list),
        "",
        "For each claim return a JSON line: {\"id\": <id>, \"theme\": \"<theme>\"}",
        "Use 'unclassified' only if genuinely ambiguous.",
        "",
        "Claims:",
    ]
    for c in unclassified:
        prompt_lines.append(f"id={c['id']}: {c['text']}")

    response = query_llm(
        "\n".join(prompt_lines),
        system="You are a precise research classifier. Return only valid JSON lines.",
        model=model,
        temperature=0.0,
    )

    # Parse LLM response and reassign
    for line in response.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
            cid, new_theme = obj.get("id"), obj.get("theme", "unclassified")
        except json.JSONDecodeError:
            continue
        if new_theme not in claims_by_theme:
            continue
        # Move claim from unclassified to new_theme
        for i, claim in enumerate(claims_by_theme["unclassified"]):
            if claim["id"] == cid:
                claim["theme"] = new_theme
                claims_by_theme[new_theme].append(claim)
                claims_by_theme["unclassified"].pop(i)
                break

    return claims_by_theme


def main():
    parser = argparse.ArgumentParser(
        description="Extract factual claims from a markdown document."
    )
    parser.add_argument("input", help="Markdown file to parse")
    parser.add_argument("output", nargs="?", help="Output JSON path (default: <input>_claims.json)")
    parser.add_argument(
        "--model", "-m", default="bulk",
        help="LLM model/alias for --llm reclassification (default: bulk = mistral-large-latest)",
    )
    parser.add_argument(
        "--llm", action="store_true",
        help="Use LLM to reclassify unclassified claims (costs API tokens)",
    )
    args = parser.parse_args()

    md_path = Path(args.input)
    if not md_path.exists():
        print(f"Error: file not found: {md_path}")
        sys.exit(1)

    output_path = Path(args.output) if args.output else md_path.with_name(
        md_path.stem + "_claims.json"
    )

    result = extract_claims(md_path)

    if args.llm:
        unclassified_count = len(result["claims_by_theme"].get("unclassified", []))
        if unclassified_count:
            print(f"Reclassifying {unclassified_count} unclassified claims via LLM ({args.model})…")
            result["claims_by_theme"] = _llm_reclassify(result["claims_by_theme"], args.model)
            result["stats_by_theme"] = {
                t: len(c) for t, c in result["claims_by_theme"].items()
            }
            result["total_claims"] = sum(result["stats_by_theme"].values())

    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Extracted {result['total_claims']} claims → {output_path}")
    print("Breakdown by theme:")
    for theme, count in result["stats_by_theme"].items():
        if count > 0:
            print(f"  {theme}: {count}")


if __name__ == "__main__":
    main()
