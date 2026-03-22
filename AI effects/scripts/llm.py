"""
scripts/llm.py

Unified LLM wrapper for the AI Effects research project.
Routes to Mistral or Anthropic based on the model string.
Reuses the .env loading pattern from ../wikimania_deadlines/llm.py.

Supported providers (detected from model name prefix):
  mistral-*     → Mistral AI API  (MISTRAL_API_KEY)
  claude-*      → Anthropic API   (ANTHROPIC_API_KEY)

Named aliases (expand to the model string before routing):
  cheap         → mistral-small-latest       fast, low-cost bulk tasks
  bulk          → mistral-large-latest        default for extraction/verification
  judge         → claude-sonnet-4-6           judgment/synthesis/scoping
  fast          → claude-haiku-4-5-20251001   fast Claude, good for classification

Usage (as a module):
    from scripts.llm import query_llm, BULK, JUDGE

    text = query_llm("Summarise this passage.", model=BULK)
    text = query_llm("Is this claim supported?", model=JUDGE)

Usage (CLI):
    python -m scripts.llm --model bulk "Summarise: ..."
    python -m scripts.llm --model judge --system "You are..." "Prompt text"
    echo "prompt" | python -m scripts.llm --model cheap
"""

import json
import os
import ssl
import sys
import urllib.request
from pathlib import Path

import certifi

_SSL_CTX = ssl.create_default_context(cafile=certifi.where())

# ---------------------------------------------------------------------------
# Named aliases
# ---------------------------------------------------------------------------
CHEAP  = "mistral-small-latest"
BULK   = "mistral-large-latest"
JUDGE  = "claude-sonnet-4-6"
FAST   = "claude-haiku-4-5-20251001"
BEST   = "claude-opus-4-6"

ALIASES: dict[str, str] = {
    "cheap": CHEAP,
    "bulk":  BULK,
    "judge": JUDGE,
    "fast":  FAST,
    "best":  BEST,
}

DEFAULT_MODEL = BULK  # default: Mistral Large for affordable bulk processing


# ---------------------------------------------------------------------------
# .env loading
# ---------------------------------------------------------------------------
def _load_env() -> None:
    """Load .env from project root if API keys are not already in environment."""
    needed = {"MISTRAL_API_KEY", "ANTHROPIC_API_KEY"}
    if needed.issubset(os.environ):
        return
    for candidate in [
        Path(__file__).parent / ".env",
        Path(__file__).parent.parent / ".env",
        Path(__file__).parent.parent.parent / ".env",
    ]:
        if candidate.exists():
            for line in candidate.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            return


_load_env()


# ---------------------------------------------------------------------------
# Provider routing
# ---------------------------------------------------------------------------
def _resolve_model(model: str) -> str:
    """Expand named aliases to full model strings."""
    return ALIASES.get(model.lower(), model)


def _provider(model: str) -> str:
    if model.startswith("mistral") or model.startswith("open-mistral"):
        return "mistral"
    if model.startswith("claude"):
        return "anthropic"
    raise ValueError(
        f"Cannot determine provider for model '{model}'. "
        "Model must start with 'mistral', 'open-mistral', or 'claude', "
        "or be one of the named aliases: " + ", ".join(ALIASES)
    )


# ---------------------------------------------------------------------------
# Mistral
# ---------------------------------------------------------------------------
_MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"


def _query_mistral(prompt: str, system: str, model: str, temperature: float) -> str:
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise RuntimeError("MISTRAL_API_KEY is not set.")

    payload = json.dumps({
        "model": model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ],
    }).encode()

    req = urllib.request.Request(
        _MISTRAL_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=120, context=_SSL_CTX) as resp:
        data = json.loads(resp.read())

    return data["choices"][0]["message"]["content"]


# ---------------------------------------------------------------------------
# Anthropic / Claude
# ---------------------------------------------------------------------------
_ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"
_DEFAULT_MAX_TOKENS = 4096


def _query_anthropic(
    prompt: str,
    system: str,
    model: str,
    temperature: float,
    max_tokens: int,
) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set.")

    payload = json.dumps({
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system,
        "messages": [
            {"role": "user", "content": prompt},
        ],
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

    return data["content"][0]["text"]


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------
def query_llm(
    prompt: str,
    system: str = "You are a precise research assistant.",
    model: str = DEFAULT_MODEL,
    temperature: float = 0.0,
    max_tokens: int = _DEFAULT_MAX_TOKENS,
) -> str:
    """
    Send a prompt to the specified model and return the text response.

    Args:
        prompt:      The user message.
        system:      System prompt / role description.
        model:       Model string or alias (cheap | bulk | judge | fast | best
                     | mistral-large-latest | claude-sonnet-4-6 | …).
        temperature: Sampling temperature (0.0 = deterministic).
        max_tokens:  Max output tokens (Anthropic only; Mistral ignores this).

    Returns:
        The model's text response.

    Raises:
        ValueError:   Unknown model / provider.
        RuntimeError: Missing API key.
    """
    model = _resolve_model(model)
    provider = _provider(model)

    if provider == "mistral":
        return _query_mistral(prompt, system, model, temperature)
    else:
        return _query_anthropic(prompt, system, model, temperature, max_tokens)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def _cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Query an LLM from the command line.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Model aliases:
  cheap   mistral-small-latest       (fast, low-cost bulk tasks)
  bulk    mistral-large-latest       (default)
  judge   claude-sonnet-4-6          (judgment / synthesis)
  fast    claude-haiku-4-5-20251001  (fast Claude)
  best    claude-opus-4-6            (most capable)

Examples:
  python -m scripts.llm --model bulk "Summarise this passage."
  echo "Is this supported?" | python -m scripts.llm --model judge
        """,
    )
    parser.add_argument("prompt", nargs="?", help="Prompt text (or pipe via stdin)")
    parser.add_argument("--model",  "-m", default=DEFAULT_MODEL, help="Model or alias")
    parser.add_argument("--system", "-s", default="You are a precise research assistant.",
                        help="System prompt")
    parser.add_argument("--temperature", "-t", type=float, default=0.0)
    parser.add_argument("--max-tokens",  "-n", type=int, default=_DEFAULT_MAX_TOKENS)
    args = parser.parse_args()

    prompt = args.prompt
    if not prompt:
        if not sys.stdin.isatty():
            prompt = sys.stdin.read().strip()
        else:
            parser.error("Provide a prompt as an argument or via stdin.")

    result = query_llm(
        prompt,
        system=args.system,
        model=args.model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    )
    print(result)


if __name__ == "__main__":
    _cli()
