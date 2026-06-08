#!/usr/bin/env python3
"""
PreToolUse hook: intercepts WebFetch and checks source-collection cache first.

Exit 2 + stderr message → blocks WebFetch, tells Claude to use cached file.
Exit 0                   → allows WebFetch to proceed normally.

Hook input (stdin): {"tool_name": "WebFetch", "tool_input": {"url": "..."}, ...}
"""
import json
import sys
from pathlib import Path


def find_cache_dir(start: Path) -> Path | None:
    """Walk up from start looking for source-collection/cache/."""
    current = start.resolve()
    for _ in range(8):
        # Project layout: .../wikimedia-analysis/source-collection/cache/
        candidate = current / "source-collection" / "cache"
        if candidate.is_dir():
            return candidate
        # Already inside source-collection
        candidate = current / "cache"
        if candidate.is_dir() and (current / "fetch.py").exists():
            return candidate
        if current == current.parent:
            break
        current = current.parent
    return None


def find_cached_file(cache_dir: Path, url: str) -> Path | None:
    """Return the first cache .md file whose Source: header matches the URL."""
    url = url.strip().rstrip("/")
    for f in sorted(cache_dir.glob("*.md")):
        try:
            with f.open(encoding="utf-8") as fh:
                for i, line in enumerate(fh):
                    if i > 10:
                        break
                    if line.startswith("Source:"):
                        cached_url = line.removeprefix("Source:").strip().rstrip("/")
                        if cached_url == url:
                            return f
        except OSError:
            continue
    return None


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError, ValueError):
        sys.exit(0)

    if data.get("tool_name") != "WebFetch":
        sys.exit(0)

    url: str = data.get("tool_input", {}).get("url", "").strip()
    if not url:
        sys.exit(0)

    cache_dir = find_cache_dir(Path.cwd())
    if cache_dir is None:
        sys.exit(0)

    cached = find_cached_file(cache_dir, url)
    if cached:
        rel = cached.relative_to(Path.cwd()) if cached.is_relative_to(Path.cwd()) else cached
        sys.stderr.write(
            f"[fetch-interceptor] Cache hit — use Read tool instead of WebFetch.\n"
            f"File: {rel}\n"
            f"URL:  {url}\n"
        )
        sys.exit(2)

    # No cache hit. Suggest the fetch pipeline but don't block.
    fetch_script = cache_dir.parent / "fetch.py"
    if fetch_script.exists():
        rel_script = (
            fetch_script.relative_to(Path.cwd())
            if fetch_script.is_relative_to(Path.cwd())
            else fetch_script
        )
        sys.stderr.write(
            f"[fetch-interceptor] No cache hit for this URL.\n"
            f"Consider fetching via the pipeline first (portable module form):\n"
            f"  uv run python -m source_collection.fetch --citekey <key>\n"
            f"Proceeding with WebFetch.\n"
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
