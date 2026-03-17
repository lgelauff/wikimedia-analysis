"""
Thin wrapper for querying the Mistral API.
Set MISTRAL_API_KEY in your environment before running.
"""

import json
import os
import ssl
import urllib.request
from pathlib import Path

import certifi
_SSL_CTX = ssl.create_default_context(cafile=certifi.where())


def _load_env():
    """Load .env from project root if MISTRAL_API_KEY not already in environment."""
    if os.environ.get("MISTRAL_API_KEY"):
        return
    for candidate in [
        Path(__file__).parent / ".env",
        Path(__file__).parent.parent / ".env",
    ]:
        if candidate.exists():
            for line in candidate.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            return

_load_env()

MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"
DEFAULT_MODEL   = "mistral-large-latest"


def query_mistral(
    prompt: str,
    system: str = "You are a precise data extraction assistant.",
    model: str = DEFAULT_MODEL,
    temperature: float = 0.0,
) -> str:
    """
    Send a prompt to Mistral and return the text response.
    Raises RuntimeError if the API key is missing or the request fails.
    """
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise RuntimeError(
            "MISTRAL_API_KEY environment variable is not set."
        )

    payload = json.dumps({
        "model": model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ],
    }).encode()

    req = urllib.request.Request(
        MISTRAL_API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=60, context=_SSL_CTX) as resp:
        data = json.loads(resp.read())

    return data["choices"][0]["message"]["content"]
