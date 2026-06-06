#!/usr/bin/env python3
"""
PreToolUse hook: lint sources.txt on every Write or Edit.

Fires only when the target file is named sources.txt.
Validates each entry block for:
  - Required fields: citekey, url, access
  - Citekey naming convention: author+year+keyword (lowercase, no spaces)
  - Valid access values: open, paywall, login, blocked, unknown
  - Duplicate citekeys
  - Entries with access=open but no url

Exit 2 + stderr  → block the write and show errors to Claude.
Exit 0           → allow write to proceed.
"""
import json
import re
import sys
from pathlib import Path

REQUIRED = {"citekey", "url", "access"}
VALID_ACCESS = {"open", "paywall", "login", "blocked", "unknown"}
CITEKEY_RE = re.compile(r"^[a-z][a-z0-9]+\d{4}[a-z][a-z0-9]*$")


def parse_blocks(text: str) -> list[dict]:
    entries = []
    current: dict[str, str] = {}
    for line in text.splitlines():
        if line.startswith("---"):
            if current:
                entries.append(current)
            current = {}
        elif ":" in line and not line.startswith("#"):
            k, _, v = line.partition(":")
            k, v = k.strip(), v.strip()
            if k and v:
                current[k] = v
    if current:
        entries.append(current)
    return entries


def lint(entries: list[dict]) -> list[str]:
    errors = []
    seen_citekeys: dict[str, int] = {}

    for i, entry in enumerate(entries, 1):
        citekey = entry.get("citekey", f"(entry {i})")
        prefix = f"[{citekey}]"

        # Required fields
        for field in REQUIRED:
            if field not in entry:
                # url is not required if access is paywall/login/blocked
                if field == "url" and entry.get("access") in ("paywall", "login", "blocked"):
                    continue
                errors.append(f"{prefix} missing required field: {field}")

        # Citekey convention
        if "citekey" in entry:
            if not CITEKEY_RE.match(citekey):
                errors.append(
                    f"{prefix} citekey doesn't match author+year+keyword convention "
                    f"(lowercase letters+digits only, e.g. smith2024sources)"
                )
            # Duplicate check
            if citekey in seen_citekeys:
                errors.append(
                    f"{prefix} duplicate citekey — also appears at entry {seen_citekeys[citekey]}"
                )
            seen_citekeys[citekey] = i

        # Valid access values
        access = entry.get("access", "").lower()
        if access and access not in VALID_ACCESS:
            errors.append(
                f"{prefix} unknown access value '{access}' "
                f"(valid: {', '.join(sorted(VALID_ACCESS))})"
            )

        # open access entries should have a url
        if access == "open" and not entry.get("url"):
            errors.append(f"{prefix} access=open but no url provided")

    return errors


def is_sources_file(path_str: str) -> bool:
    return Path(path_str).name == "sources.txt"


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError, ValueError):
        sys.exit(0)

    tool = data.get("tool_name", "")
    inp = data.get("tool_input", {})

    # Determine target file path and content to lint
    if tool == "Write":
        path = inp.get("file_path", "")
        content = inp.get("content", "")
    elif tool == "Edit":
        path = inp.get("file_path", "")
        # Reconstruct approximate post-edit content from old→new substitution
        # We lint the new_string in context rather than full file for speed
        content = inp.get("new_string", "")
        if not content:
            sys.exit(0)
    else:
        sys.exit(0)

    if not is_sources_file(path):
        sys.exit(0)

    # For Write we have the full content; for Edit we lint only the changed block.
    # Either way, parse as blocks and lint what we have.
    entries = parse_blocks(content)
    if not entries:
        sys.exit(0)

    errors = lint(entries)
    if errors:
        sys.stderr.write("[sources-linter] Validation errors in sources.txt:\n")
        for err in errors:
            sys.stderr.write(f"  • {err}\n")
        sys.stderr.write("\nFix these before writing, or override if intentional.\n")
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
