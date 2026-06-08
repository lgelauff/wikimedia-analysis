#!/usr/bin/env python3
"""
PreToolUse hook: intercepts Bash calls that run fetch.py with --ignore-robots.

For each URL in sources.txt that would be fetched, checks robots.txt and
reports which domains disallow our User-Agent. Blocks the run and lists
violating domains so the user can make an informed decision.

Exit 2 + stderr  → block the run and show violations.
Exit 0           → allow run to proceed (no violations, or not a fetch.py call).
"""
import json
import re
import ssl
import sys
import urllib.parse
import urllib.request
import urllib.robotparser
from pathlib import Path

_UA = "WikimediaAnalysis/1.0 (personal research project; https://github.com/lgelauff/wikimedia-analysis)"
# Matches both the script form (fetch.py) and the packaged module form
# (python -m source_collection.fetch), so the guard fires either way.
_IGNORE_ROBOTS_RE = re.compile(r"(?:\bfetch\.py\b|source_collection\.fetch).*--ignore-robots\b")
_SOURCES_RE = re.compile(r"--sources\s+(\S+)")
_SSL_CTX = None

SKIP_ACCESS = {"paywall", "login", "blocked"}


def ssl_ctx():
    global _SSL_CTX
    if _SSL_CTX is None:
        try:
            import certifi
            _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            _SSL_CTX = ssl.create_default_context()
    return _SSL_CTX


def find_sources_txt(command: str) -> Path | None:
    """Find sources.txt: explicit --sources arg, or walk up from cwd."""
    m = _SOURCES_RE.search(command)
    if m:
        p = Path(m.group(1))
        return p if p.exists() else None
    for candidate in [
        Path.cwd() / "sources.txt",
        Path.cwd().parent / "source-collection" / "sources.txt",
    ]:
        if candidate.exists():
            return candidate
    return None


def parse_urls(sources_path: Path) -> list[str]:
    urls = []
    current: dict[str, str] = {}
    for line in sources_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("---"):
            if current.get("url") and current.get("access", "").lower() not in SKIP_ACCESS:
                urls.append(current["url"])
            current = {}
        elif ":" in line:
            k, _, v = line.partition(":")
            k, v = k.strip(), v.strip()
            if k and v:
                current[k] = v
    if current.get("url") and current.get("access", "").lower() not in SKIP_ACCESS:
        urls.append(current["url"])
    return urls


def check_robots(url: str) -> tuple[str, bool]:
    """Return (robots_url, is_disallowed). Treats fetch errors as allowed."""
    parsed = urllib.parse.urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(robots_url)
    try:
        req = urllib.request.Request(robots_url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=8, context=ssl_ctx()) as resp:
            rp.parse(resp.read().decode("utf-8", errors="replace").splitlines())
    except Exception:
        return robots_url, False  # can't fetch robots.txt → assume allowed
    return robots_url, not rp.can_fetch(_UA, url)


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError, ValueError):
        sys.exit(0)

    if data.get("tool_name") != "Bash":
        sys.exit(0)

    command = data.get("tool_input", {}).get("command", "")
    if not _IGNORE_ROBOTS_RE.search(command):
        sys.exit(0)

    sources_path = find_sources_txt(command)
    if sources_path is None:
        sys.stderr.write("[robots-checker] Could not find sources.txt — proceeding anyway.\n")
        sys.exit(0)

    urls = parse_urls(sources_path)
    if not urls:
        sys.exit(0)

    # Deduplicate by domain to avoid redundant robots.txt fetches
    seen_domains: dict[str, bool] = {}
    violations: list[tuple[str, str]] = []  # (domain, robots_url)

    sys.stderr.write(f"[robots-checker] Checking robots.txt for {len(urls)} URLs…\n")
    for url in urls:
        domain = urllib.parse.urlparse(url).netloc
        if domain in seen_domains:
            if seen_domains[domain]:
                violations.append((domain, f"https://{domain}/robots.txt"))
            continue
        robots_url, disallowed = check_robots(url)
        seen_domains[domain] = disallowed
        if disallowed:
            violations.append((domain, robots_url))

    if not violations:
        sys.stderr.write("[robots-checker] No robots.txt violations found — proceeding.\n")
        sys.exit(0)

    sys.stderr.write("\n[robots-checker] ⚠ The following domains disallow our User-Agent:\n\n")
    for domain, robots_url in sorted(set(violations)):
        sys.stderr.write(f"  • {domain}\n    robots.txt: {robots_url}\n")
    sys.stderr.write(
        "\n--ignore-robots was set, which would scrape these domains in violation of their policy.\n"
        "Remove --ignore-robots, or explicitly confirm you have permission to proceed.\n"
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
