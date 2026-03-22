"""
verify_source_agent.py

Agentic source verification. An LLM agent is given search tools over the
extracted PDF text and tasked with finding where (if anywhere) a claim is
discussed, then judging whether that discussion supports, contradicts, or is
ambiguous about the claim.

Unlike verify_source.py (single-pass whole-text dump), this agent iterates:
it searches for relevant terms, reads context around hits, and forms a verdict
from multiple passes. It only sees the text it asks to see.

Usage:
    python -m scripts.verify_source_agent --pdf <path.pdf> --claim "Claim text"
    python -m scripts.verify_source_agent --batch claims_v2.json [options]

Single mode:
    --pdf     Path to the PDF (in pdf sources/)
    --claim   Claim text to verify against
    --citekey Override citekey (default: PDF stem)

Batch mode:
    --batch   Path to claims JSON (claims_v2.json)

Options:
    --model    LLM model/alias (default: bulk = mistral-large-latest)
               Use 'judge' (claude-sonnet-4-6) for hard or ambiguous cases.
    --pdf-dir  Directory containing PDFs (batch mode, default: 'pdf sources')
    --output   Output JSON path (default: tmp/agent_verification_results.json)
    --max-iter Maximum agent iterations per claim-source pair (default: 8)
    --verbose  Print each result as processed

Output format (per source-claim pair):
    {
      "citekey":     "...",
      "claim_id":    ...,
      "claim_text":  "...",
      "discussed":   true | false,
      "stance":      "supports" | "contradicts" | "ambiguous" | "not_discussed",
      "confidence":  "high" | "medium" | "low",
      "key_passage": "...most relevant passage...",
      "reasoning":   "...",
      "search_trace": ["query1", "query2", ...],
      "iterations":  3,
      "model_used":  "..."
    }
"""

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

import certifi
import ssl

from scripts.llm import _load_env, _resolve_model, _provider, _SSL_CTX, BULK, JUDGE
from scripts.verify_source import extract_pdf_text


# ---------------------------------------------------------------------------
# Tool schema (provider-neutral; converted on use)
# ---------------------------------------------------------------------------
_TOOLS = [
    {
        "name": "search_document",
        "description": (
            "Search the document for passages relevant to a query. "
            "Returns up to max_results text excerpts (each ~600 chars) with their "
            "character offset so you can read more context with read_section."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Keywords or short phrase to search for",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of excerpts to return (1–8, default 5)",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "read_section",
        "description": (
            "Read a specific section of the document by character offset. "
            "Use this to read more context around a search hit."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "offset": {
                    "type": "integer",
                    "description": "Character offset to start reading from (from a search_document result)",
                },
                "length": {
                    "type": "integer",
                    "description": "Characters to read (max 2000)",
                },
            },
            "required": ["offset", "length"],
        },
    },
    {
        "name": "get_document_info",
        "description": (
            "Get basic information about the document: total character count, "
            "estimated page count, and the opening text (title / abstract area). "
            "Call this first if you are unsure what the document is about."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "submit_verdict",
        "description": (
            "Submit your final verdict once you have gathered enough evidence. "
            "Call this when you are ready to give your answer. "
            "Do NOT call this without first searching the document."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "discussed": {
                    "type": "boolean",
                    "description": "Whether the claim topic is substantively discussed in the document",
                },
                "stance": {
                    "type": "string",
                    "enum": ["supports", "contradicts", "ambiguous", "not_discussed"],
                    "description": (
                        "supports: document explicitly supports the claim with data or assertion; "
                        "contradicts: document explicitly contradicts the claim; "
                        "ambiguous: document discusses the topic but stance is unclear; "
                        "not_discussed: the claim topic does not appear in the document"
                    ),
                },
                "confidence": {
                    "type": "string",
                    "enum": ["high", "medium", "low"],
                    "description": "Confidence in the verdict",
                },
                "key_passage": {
                    "type": "string",
                    "description": "The most relevant passage from the document (1–4 sentences, exact quote)",
                },
                "reasoning": {
                    "type": "string",
                    "description": "1–2 sentences explaining the verdict",
                },
            },
            "required": ["discussed", "stance", "confidence", "key_passage", "reasoning"],
        },
    },
]

_SYSTEM = (
    "You are a rigorous research verification assistant. "
    "You have been given tools to search a source document. "
    "Your task: determine whether a specific claim is discussed in the document "
    "and, if so, whether the document supports, contradicts, or is ambiguous about it. "
    "Be conservative: only mark 'supports' if the document explicitly addresses the claim "
    "with data or a clear assertion. Never infer beyond what the text says. "
    "Search at least twice with different terms before submitting a verdict."
)


# ---------------------------------------------------------------------------
# Tool implementations (pure Python over extracted text)
# ---------------------------------------------------------------------------

_STOPWORDS = {
    "the", "a", "an", "of", "in", "is", "are", "was", "were", "to", "for",
    "and", "or", "that", "this", "it", "with", "as", "at", "by", "from",
    "on", "be", "not", "have", "has", "their", "its", "which", "also",
}

WINDOW = 600   # chars per search window
STRIDE = 250   # stride between windows


def _tool_search_document(text: str, query: str, max_results: int = 5) -> str:
    max_results = max(1, min(8, int(max_results)))
    query_words = set(query.lower().split()) - _STOPWORDS
    if not query_words:
        query_words = set(query.lower().split())

    hits = []
    for offset in range(0, len(text), STRIDE):
        chunk = text[offset: offset + WINDOW]
        chunk_lower = chunk.lower()
        score = sum(1 for w in query_words if w in chunk_lower)
        if score > 0:
            hits.append((score, offset, chunk))

    # Sort by score desc, deduplicate windows that overlap heavily
    hits.sort(key=lambda h: -h[0])
    results = []
    used: list[int] = []
    for score, offset, chunk in hits:
        if all(abs(offset - u) >= WINDOW // 2 for u in used):
            results.append({"offset": offset, "score": score, "excerpt": chunk.strip()})
            used.append(offset)
        if len(results) >= max_results:
            break

    if not results:
        return json.dumps({"results": [], "note": "No matches found for those terms."})
    return json.dumps({"results": results})


def _tool_read_section(text: str, offset: int, length: int) -> str:
    length = max(1, min(2000, int(length)))
    offset = max(0, min(int(offset), len(text)))
    excerpt = text[offset: offset + length]
    return json.dumps({
        "offset": offset,
        "length": len(excerpt),
        "text": excerpt,
    })


def _tool_get_document_info(text: str, citekey: str) -> str:
    lines = text.splitlines()
    approx_pages = max(1, len(text) // 3000)
    opening = text[:400].strip()
    return json.dumps({
        "citekey": citekey,
        "total_chars": len(text),
        "approx_pages": approx_pages,
        "opening_text": opening,
    })


def _execute_tool(text: str, citekey: str, name: str, args: dict) -> str:
    if name == "search_document":
        return _tool_search_document(text, args.get("query", ""), args.get("max_results", 5))
    if name == "read_section":
        return _tool_read_section(text, args.get("offset", 0), args.get("length", 800))
    if name == "get_document_info":
        return _tool_get_document_info(text, citekey)
    if name == "submit_verdict":
        # Return it as-is so the loop can capture it
        return json.dumps(args)
    return json.dumps({"error": f"Unknown tool: {name}"})


# ---------------------------------------------------------------------------
# Provider-specific tool format converters
# ---------------------------------------------------------------------------

def _mistral_tools() -> list[dict]:
    return [{"type": "function", "function": t} for t in _TOOLS]


def _anthropic_tools() -> list[dict]:
    out = []
    for t in _TOOLS:
        out.append({
            "name": t["name"],
            "description": t["description"],
            "input_schema": t["parameters"],
        })
    return out


# ---------------------------------------------------------------------------
# Mistral agent loop
# ---------------------------------------------------------------------------
_MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"


def _run_agent_mistral(
    text: str, claim: str, citekey: str, model: str, max_iter: int
) -> dict:
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise RuntimeError("MISTRAL_API_KEY is not set.")

    user_msg = (
        f"SOURCE DOCUMENT: {citekey}\n\n"
        f"CLAIM TO VERIFY:\n{claim}\n\n"
        "Use the tools to search the document and verify whether this claim is "
        "discussed and whether it is supported, contradicted, or ambiguous. "
        "Call submit_verdict when you have your answer."
    )

    messages = [{"role": "user", "content": user_msg}]
    search_trace: list[str] = []
    verdict: dict | None = None
    iterations = 0

    for _ in range(max_iter):
        iterations += 1
        payload = json.dumps({
            "model": model,
            "temperature": 0.0,
            "tools": _mistral_tools(),
            "tool_choice": "auto",
            "messages": messages,
        }).encode()

        req = urllib.request.Request(
            _MISTRAL_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120, context=_SSL_CTX) as resp:
            data = json.loads(resp.read())

        msg = data["choices"][0]["message"]
        messages.append(msg)

        tool_calls = msg.get("tool_calls") or []
        if not tool_calls:
            # Model gave a text response without calling a tool — shouldn't happen
            # with a well-prompted setup but handle gracefully
            break

        for tc in tool_calls:
            fn = tc["function"]
            name = fn["name"]
            args = json.loads(fn.get("arguments") or "{}")

            if name == "search_document":
                search_trace.append(args.get("query", ""))

            result_str = _execute_tool(text, citekey, name, args)

            messages.append({
                "role": "tool",
                "content": result_str,
                "tool_call_id": tc["id"],
            })

            if name == "submit_verdict":
                verdict = args
                break

        if verdict:
            break

    return verdict, search_trace, iterations


# ---------------------------------------------------------------------------
# Anthropic agent loop
# ---------------------------------------------------------------------------
_ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"


def _run_agent_anthropic(
    text: str, claim: str, citekey: str, model: str, max_iter: int
) -> tuple[dict | None, list[str], int]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set.")

    user_content = (
        f"SOURCE DOCUMENT: {citekey}\n\n"
        f"CLAIM TO VERIFY:\n{claim}\n\n"
        "Use the tools to search the document and verify whether this claim is "
        "discussed and whether it is supported, contradicted, or ambiguous. "
        "Call submit_verdict when you have your answer."
    )

    messages = [{"role": "user", "content": user_content}]
    search_trace: list[str] = []
    verdict: dict | None = None
    iterations = 0

    for _ in range(max_iter):
        iterations += 1
        payload = json.dumps({
            "model": model,
            "max_tokens": 2048,
            "temperature": 0.0,
            "system": _SYSTEM,
            "tools": _anthropic_tools(),
            "messages": messages,
        }).encode()

        req = urllib.request.Request(
            _ANTHROPIC_URL,
            data=payload,
            headers={
                "x-api-key":         api_key,
                "anthropic-version": _ANTHROPIC_VERSION,
                "Content-Type":      "application/json",
                "Accept":            "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120, context=_SSL_CTX) as resp:
            data = json.loads(resp.read())

        stop_reason = data.get("stop_reason")
        content_blocks = data.get("content", [])

        # Append assistant turn
        messages.append({"role": "assistant", "content": content_blocks})

        if stop_reason != "tool_use":
            break

        # Process tool uses; collect results into a single user turn
        tool_results = []
        for block in content_blocks:
            if block.get("type") != "tool_use":
                continue
            name = block["name"]
            args = block.get("input", {})
            tool_use_id = block["id"]

            if name == "search_document":
                search_trace.append(args.get("query", ""))

            result_str = _execute_tool(text, citekey, name, args)

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use_id,
                "content": result_str,
            })

            if name == "submit_verdict":
                verdict = args
                break

        messages.append({"role": "user", "content": tool_results})

        if verdict:
            break

    return verdict, search_trace, iterations


# ---------------------------------------------------------------------------
# Public verify functions
# ---------------------------------------------------------------------------

def verify_single_agent(
    pdf_path: Path,
    claim: str,
    citekey: str | None = None,
    claim_id: int | None = None,
    model: str = BULK,
    max_iter: int = 8,
) -> dict:
    """Run the agent over one PDF + claim. Returns a result dict."""
    citekey = citekey or pdf_path.stem
    model = _resolve_model(model)
    provider = _provider(model)

    text = extract_pdf_text(pdf_path)

    if provider == "mistral":
        verdict, search_trace, iterations = _run_agent_mistral(
            text, claim, citekey, model, max_iter
        )
    else:
        verdict, search_trace, iterations = _run_agent_anthropic(
            text, claim, citekey, model, max_iter
        )

    if verdict is None:
        return {
            "citekey": citekey,
            "claim_id": claim_id,
            "claim_text": claim,
            "discussed": False,
            "stance": "error",
            "confidence": "low",
            "key_passage": "",
            "reasoning": "Agent did not produce a verdict within the iteration limit.",
            "search_trace": search_trace,
            "iterations": iterations,
            "model_used": model,
        }

    return {
        "citekey": citekey,
        "claim_id": claim_id,
        "claim_text": claim,
        "discussed": verdict.get("discussed", False),
        "stance": verdict.get("stance", "error"),
        "confidence": verdict.get("confidence", "low"),
        "key_passage": verdict.get("key_passage", ""),
        "reasoning": verdict.get("reasoning", ""),
        "search_trace": search_trace,
        "iterations": iterations,
        "model_used": model,
    }


def verify_batch_agent(
    claims_json: Path,
    pdf_dir: Path,
    model: str,
    verbose: bool,
    output_path: Path | None = None,
    max_iter: int = 8,
) -> list[dict]:
    """
    Process all (citekey, claim) pairs from claims_v2.json where a PDF exists.
    Writes incrementally to output_path so crashes don't lose work.
    Skips already-completed pairs on re-run.
    """
    data = json.loads(claims_json.read_text())

    # Load prior results for crash recovery
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
            pass

    # Flatten claims
    if "themes" in data:
        all_claims = [c for theme in data["themes"] for c in theme.get("claims", [])]
    else:
        all_claims = [c for claims in data.get("claims_by_theme", {}).values() for c in claims]

    for claim in all_claims:
        for source in claim.get("sources", []):
            citekey = source if isinstance(source, str) else source.get("citekey", "")
            pdf_path = pdf_dir / f"{citekey}.pdf"
            if not pdf_path.exists():
                continue
            if (citekey, claim["id"]) in done_keys:
                continue

            result = verify_single_agent(
                pdf_path=pdf_path,
                claim=claim["text"],
                citekey=citekey,
                claim_id=claim["id"],
                model=model,
                max_iter=max_iter,
            )
            results.append(result)
            done_keys.add((citekey, claim["id"]))

            if verbose:
                searched = ", ".join(result["search_trace"][:3])
                print(
                    f"  [{result['stance']:13s} {result['confidence']:6s}] "
                    f"{citekey} ← claim {claim['id']}  "
                    f"({result['iterations']} iters, searched: {searched})"
                )

            if output_path:
                output_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Agentic verification: agent searches document to verify a claim."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--pdf",   help="Path to a single PDF file")
    mode.add_argument("--batch", help="Path to claims JSON for batch processing")

    parser.add_argument("--claim",    help="Claim text (single mode)")
    parser.add_argument("--citekey",  help="Override citekey (single mode)")
    parser.add_argument(
        "--model", "-m", default="bulk",
        help="LLM model/alias (default: bulk = mistral-large-latest; use 'judge' for hard cases)",
    )
    parser.add_argument(
        "--pdf-dir", default="pdf sources",
        help="Directory containing PDFs (batch mode, default: 'pdf sources')",
    )
    parser.add_argument(
        "--output", "-o", default="tmp/agent_verification_results.json",
        help="Output JSON path",
    )
    parser.add_argument(
        "--max-iter", type=int, default=8,
        help="Maximum agent iterations per claim-source pair (default: 8)",
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
        result = verify_single_agent(
            pdf_path=pdf_path,
            claim=args.claim,
            citekey=args.citekey,
            model=args.model,
            max_iter=args.max_iter,
        )
        results = [result]
        print(f"Stance:      {result['stance']} ({result['confidence']} confidence)")
        print(f"Discussed:   {result['discussed']}")
        print(f"Key passage: {result['key_passage']}")
        print(f"Reasoning:   {result['reasoning']}")
        print(f"Searched:    {result['search_trace']}")
        print(f"Iterations:  {result['iterations']}")

    else:
        claims_path = Path(args.batch)
        if not claims_path.exists():
            print(f"Error: claims JSON not found: {claims_path}", file=sys.stderr)
            sys.exit(1)
        pdf_dir = Path(args.pdf_dir)
        print(f"Batch agent verification — model: {args.model}, max_iter: {args.max_iter}")
        results = verify_batch_agent(
            claims_path, pdf_dir, args.model, args.verbose, output_path, args.max_iter
        )
        print(f"Processed {len(results)} source-claim pairs")

        from collections import Counter
        stances = Counter(r["stance"] for r in results)
        for stance, count in sorted(stances.items()):
            print(f"  {stance}: {count}")

    output_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"Results written to {output_path}")


if __name__ == "__main__":
    main()
