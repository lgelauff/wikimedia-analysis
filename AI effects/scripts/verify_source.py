"""
verify_source.py

Given a PDF and a claim, extract the most relevant passage and score whether
the passage supports the claim. Designed to be run on all candidate sources
after PDFs are collected.

Usage:
    python verify_source.py --pdf <path.pdf> --claim "Claim text" [options]
    python verify_source.py --batch <claims.json> [options]

Single mode:
    --pdf     Path to the PDF (in pdf sources/)
    --claim   Claim text to verify against
    --citekey Override citekey (default: PDF stem)

Batch mode:
    --batch   Path to claims JSON (tmp/core_doc_claims.json or similar)
              Processes all claims that have an assigned PDF source.

Options:
    --model   LLM model/alias (default: bulk = mistral-large-latest)
              Use 'judge' (claude-sonnet-4-6) for ambiguous or high-stakes claims.
    --output  Where to write results JSON (default: tmp/verification_results.json)
    --verbose Print each result as it is processed

Output format (per source-claim pair):
    {
      "citekey": "...",
      "claim_id": ...,
      "claim_text": "...",
      "passage": "...extracted text...",
      "score": "strong" | "partial" | "weak" | "none" | "contradicts",
      "notes": "...",
      "model_used": "..."
    }
"""

import argparse
import json
import re
import sys
from pathlib import Path

# PDF extraction — requires pypdf (pip install pypdf)
try:
    from pypdf import PdfReader
    _PYPDF_AVAILABLE = True
except ImportError:
    _PYPDF_AVAILABLE = False

from scripts.llm import query_llm, BULK


# ---------------------------------------------------------------------------
# PDF text extraction with caching
# ---------------------------------------------------------------------------
_CACHE_DIR = Path(__file__).parent.parent / "tmp" / "pdf_cache"


def _cache_path(pdf_path: Path) -> Path:
    return _CACHE_DIR / (pdf_path.stem + ".txt")


def extract_pdf_text(pdf_path: Path, max_chars: int = 80_000) -> str:
    """
    Extract plain text from a PDF, truncated to max_chars.
    Result is cached to tmp/pdf_cache/<citekey>.txt so subsequent calls
    read from disk rather than re-parsing the PDF.
    """
    cache = _cache_path(pdf_path)
    if cache.exists():
        return cache.read_text(encoding="utf-8")

    if not _PYPDF_AVAILABLE:
        raise RuntimeError(
            "pypdf is required for PDF extraction. Install it with: pip install pypdf"
        )
    reader = PdfReader(str(pdf_path))
    pages = []
    total = 0
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)
        total += len(text)
        if total >= max_chars:
            break
    full = "\n".join(pages)[:max_chars]

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache.write_text(full, encoding="utf-8")
    return full


# ---------------------------------------------------------------------------
# Verification prompt
# ---------------------------------------------------------------------------
_SYSTEM = (
    "You are a research verification assistant. "
    "Your job is to check whether a specific claim is supported by a source passage. "
    "Be precise and conservative — only mark a claim as 'strong' if the passage explicitly "
    "addresses it. Never infer or extrapolate beyond what the text says."
)

_PROMPT_TEMPLATE = """\
SOURCE TEXT (excerpt):
{text}

---
CLAIM TO VERIFY:
{claim}

---
Instructions:
1. Find the passage (1–5 sentences) in the source text most relevant to the claim.
   If no relevant passage exists, say so.
2. Score the match:
   - strong:      passage explicitly supports the claim with specific data or assertion
   - partial:     passage is relevant but does not fully support the claim as stated
   - weak:        passage only tangentially relates to the claim
   - none:        no relevant passage found
   - contradicts: passage directly contradicts the claim

Return a JSON object with these exact keys:
{{
  "passage": "<extracted passage or empty string>",
  "score": "strong|partial|weak|none|contradicts",
  "notes": "<one sentence explaining the score>"
}}
Return only the JSON object, no other text.
"""


def verify_single(
    pdf_path: Path,
    claim: str,
    citekey: str | None = None,
    claim_id: int | None = None,
    model: str = BULK,
) -> dict:
    """Verify one claim against one PDF. Returns a result dict."""
    citekey = citekey or pdf_path.stem
    text = extract_pdf_text(pdf_path)
    prompt = _PROMPT_TEMPLATE.format(text=text, claim=claim)

    raw = query_llm(prompt, system=_SYSTEM, model=model, temperature=0.0)

    # Extract JSON from response (handle potential markdown fencing)
    json_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not json_match:
        return {
            "citekey": citekey,
            "claim_id": claim_id,
            "claim_text": claim,
            "passage": "",
            "score": "error",
            "notes": f"LLM returned unparseable response: {raw[:200]}",
            "model_used": model,
        }

    parsed = json.loads(json_match.group())
    return {
        "citekey": citekey,
        "claim_id": claim_id,
        "claim_text": claim,
        "passage": parsed.get("passage", ""),
        "score": parsed.get("score", "error"),
        "notes": parsed.get("notes", ""),
        "model_used": model,
    }


def verify_batch(
    claims_json: Path,
    pdf_dir: Path,
    model: str,
    verbose: bool,
    output_path: Path | None = None,
) -> list[dict]:
    """
    Process all (citekey, claim) pairs from a claims JSON where a PDF exists.
    Supports both formats:
      - claims_v2.json: {themes: [{id, claims: [{id, text, sources}]}]}
      - legacy:         {claims_by_theme: {theme: [{id, text, sources}]}}

    If output_path is given, results are written incrementally after each pair
    so a crash does not lose completed work. Already-processed pairs (same
    citekey + claim_id) are skipped on re-run.
    """
    data = json.loads(claims_json.read_text())

    # Load existing results so we can resume after a crash
    done_keys: set[tuple] = set()
    results: list[dict] = []
    if output_path and output_path.exists():
        try:
            existing = json.loads(output_path.read_text())
            results = existing
            done_keys = {(r["citekey"], r["claim_id"]) for r in existing}
            if verbose and done_keys:
                print(f"Resuming: {len(done_keys)} pairs already done, skipping.")
        except (json.JSONDecodeError, KeyError):
            pass  # corrupted checkpoint — start fresh

    # claims_v2.json format
    if "themes" in data:
        all_claims = [claim for theme in data["themes"] for claim in theme.get("claims", [])]
    else:
        all_claims = [claim for claims in data.get("claims_by_theme", {}).values() for claim in claims]

    for claim in all_claims:
        for source in claim.get("sources", []):
            citekey = source if isinstance(source, str) else source.get("citekey", "")
            pdf_path = pdf_dir / f"{citekey}.pdf"
            cache_path = _CACHE_DIR / f"{citekey}.txt"
            if not pdf_path.exists() and not cache_path.exists():
                continue
            if (citekey, claim["id"]) in done_keys:
                continue
            result = verify_single(
                pdf_path=pdf_path,
                claim=claim["text"],
                citekey=citekey,
                claim_id=claim["id"],
                model=model,
            )
            results.append(result)
            done_keys.add((citekey, claim["id"]))
            if verbose:
                print(f"  [{result['score']:10s}] {citekey} ← claim {claim['id']}")
            # Write incrementally so a crash doesn't lose work
            if output_path:
                output_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify whether a PDF source supports a given claim."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--pdf",   help="Path to a single PDF file")
    mode.add_argument("--batch", help="Path to claims JSON for batch processing")

    parser.add_argument("--claim",   help="Claim text (single mode)")
    parser.add_argument("--citekey", help="Override citekey (single mode)")
    parser.add_argument(
        "--model", "-m", default="bulk",
        help="LLM model/alias (default: bulk = mistral-large-latest; use 'judge' for hard cases)",
    )
    parser.add_argument(
        "--pdf-dir", default="pdf sources",
        help="Directory containing PDFs (batch mode, default: 'pdf sources')",
    )
    parser.add_argument(
        "--output", "-o", default="tmp/verification_results.json",
        help="Output JSON path",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.pdf:
        if not args.claim:
            parser.error("--claim is required in single mode")
        pdf_path = Path(args.pdf)
        if not pdf_path.exists():
            print(f"Error: PDF not found: {pdf_path}", file=sys.stderr)
            sys.exit(1)
        result = verify_single(
            pdf_path=pdf_path,
            claim=args.claim,
            citekey=args.citekey,
            model=args.model,
        )
        results = [result]
        print(f"Score: {result['score']}")
        print(f"Passage: {result['passage']}")
        print(f"Notes: {result['notes']}")

    else:
        claims_path = Path(args.batch)
        if not claims_path.exists():
            print(f"Error: claims JSON not found: {claims_path}", file=sys.stderr)
            sys.exit(1)
        pdf_dir = Path(args.pdf_dir)
        print(f"Batch verification using model: {args.model}")
        results = verify_batch(claims_path, pdf_dir, args.model, args.verbose, output_path)
        print(f"Processed {len(results)} source-claim pairs")

        # Summary
        from collections import Counter
        scores = Counter(r["score"] for r in results)
        for score, count in sorted(scores.items()):
            print(f"  {score}: {count}")

    output_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"Results written to {output_path}")


if __name__ == "__main__":
    main()
