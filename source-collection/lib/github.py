"""
github.py — fetch documentation files from GitHub via the REST API.

Uses the /repos/{owner}/{repo}/contents/{path} endpoint, which is the
officially recommended method. raw.githubusercontent.com is NOT used:
it does not support authentication, shares the unauthenticated rate-limit
quota (60 req/hour), and github.com/robots.txt blocks /*/raw/ paths.

Authentication: set GITHUB_TOKEN in your environment (a personal access
token with public_repo scope, or no scope for public repos). Authenticated
requests get 5,000 req/hour vs 60 unauthenticated.

Conditional requests: the module caches ETags and sends If-None-Match on
repeat fetches. A 304 Not Modified response does not count against the
rate-limit quota and returns the cached content instantly.

Rate-limit headers: x-ratelimit-remaining and x-ratelimit-reset are
checked after every response; the registry wait() call handles pacing.

API reference: https://docs.github.com/en/rest/repos/contents
"""

import base64
import os
import time
import urllib.parse

import requests

from .ratelimits import RateLimitRegistry

_UA = "WikimediaAnalysis/1.0 (personal research; lodewijk@stanford.edu; https://github.com/lgelauff/wikimedia-analysis)"
_API_BASE = "https://api.github.com"

# ETag cache: url → (etag, content_bytes)
_etag_cache: dict[str, tuple[str, bytes]] = {}


def _session() -> requests.Session:
    """Return an authenticated Session (token from GITHUB_TOKEN env var)."""
    s = requests.Session()
    s.headers.update({
        "User-Agent": _UA,
        "Accept": "application/vnd.github.raw+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        s.headers["Authorization"] = f"Bearer {token}"
    return s


_shared_session: requests.Session | None = None


def _get_session() -> requests.Session:
    global _shared_session
    if _shared_session is None:
        _shared_session = _session()
        if "Authorization" not in _shared_session.headers:
            print("  [github] GITHUB_TOKEN not set — using unauthenticated (60 req/hour)")
    return _shared_session


def fetch_file(
    owner: str,
    repo: str,
    path: str,
    rl: RateLimitRegistry,
    ref: str = "HEAD",
) -> str:
    """
    Fetch a file from a GitHub repository and return its text content.

    Uses conditional requests (If-None-Match) so repeated calls for the
    same file only consume quota when the file has actually changed.

    Args:
        owner: GitHub username or org (e.g. "fuzheado")
        repo:  Repository name (e.g. "Wikipedia-AI-Skills")
        path:  File path within the repo (e.g. ".claude/skills/pywikibot.md")
        rl:    RateLimitRegistry for pacing
        ref:   Branch, tag, or commit SHA (default: HEAD)

    Returns:
        File content as a UTF-8 string.

    Raises:
        requests.HTTPError on non-200/304 responses.
    """
    url = f"{_API_BASE}/repos/{owner}/{repo}/contents/{urllib.parse.quote(path)}"
    if ref != "HEAD":
        url += f"?ref={urllib.parse.quote(ref)}"

    session = _get_session()
    headers = {}
    cached = _etag_cache.get(url)
    if cached:
        headers["If-None-Match"] = cached[0]

    rl.wait(url)
    resp = session.get(url, headers=headers, timeout=20)

    _update_rate_limit_info(resp)

    if resp.status_code == 304 and cached:
        return cached[1].decode("utf-8", errors="replace")

    resp.raise_for_status()

    # With Accept: application/vnd.github.raw+json the body is the raw file bytes
    content = resp.content
    etag = resp.headers.get("ETag", "")
    if etag:
        _etag_cache[url] = (etag, content)

    return content.decode("utf-8", errors="replace")


def fetch_readme(owner: str, repo: str, rl: RateLimitRegistry, ref: str = "HEAD") -> str:
    """
    Fetch the preferred README for a repository (GitHub picks the best match).

    Equivalent to fetch_file for the README but uses the dedicated /readme
    endpoint which handles README.md / readme.rst / etc. automatically.
    """
    url = f"{_API_BASE}/repos/{owner}/{repo}/readme"
    if ref != "HEAD":
        url += f"?ref={urllib.parse.quote(ref)}"

    session = _get_session()
    headers = {}
    cached = _etag_cache.get(url)
    if cached:
        headers["If-None-Match"] = cached[0]

    rl.wait(url)
    # README endpoint returns JSON with base64 content unless we request raw
    resp = session.get(url, headers=headers, timeout=20)
    _update_rate_limit_info(resp)

    if resp.status_code == 304 and cached:
        return cached[1].decode("utf-8", errors="replace")

    resp.raise_for_status()
    content = resp.content
    etag = resp.headers.get("ETag", "")
    if etag:
        _etag_cache[url] = (etag, content)

    return content.decode("utf-8", errors="replace")


def list_directory(
    owner: str,
    repo: str,
    path: str,
    rl: RateLimitRegistry,
    ref: str = "HEAD",
) -> list[dict]:
    """
    List files in a directory within a GitHub repository.

    Returns a list of dicts with keys: name, path, type ('file' or 'dir'), size, sha.
    """
    url = f"{_API_BASE}/repos/{owner}/{repo}/contents/{urllib.parse.quote(path)}"
    if ref != "HEAD":
        url += f"?ref={urllib.parse.quote(ref)}"

    session = _get_session()
    # Directory listings use JSON, not raw
    rl.wait(url)
    resp = session.get(url, headers={"Accept": "application/vnd.github+json"}, timeout=20)
    _update_rate_limit_info(resp)
    resp.raise_for_status()

    return [
        {
            "name": item["name"],
            "path": item["path"],
            "type": item["type"],
            "size": item.get("size", 0),
            "sha": item["sha"],
        }
        for item in resp.json()
        if isinstance(resp.json(), list)
    ]


def _update_rate_limit_info(resp: requests.Response) -> None:
    """Log rate-limit status and sleep if nearly exhausted."""
    remaining = resp.headers.get("x-ratelimit-remaining")
    reset = resp.headers.get("x-ratelimit-reset")
    if remaining is not None and int(remaining) < 5:
        wait = max(0, int(reset or 0) - int(time.time())) + 1
        print(f"  [github] Rate limit nearly exhausted ({remaining} remaining) — sleeping {wait}s")
        time.sleep(wait)
