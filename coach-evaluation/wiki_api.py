"""Shared MediaWiki Action API helpers for the coach-evaluation scripts.

Follows the repo's fetching conventions: API-first, descriptive User-Agent,
maxlag, one Session per host, small delay between calls, provenance stamping.
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

import config

_sessions: dict[str, requests.Session] = {}


def _session_for(url: str) -> requests.Session:
    key = "{0.scheme}://{0.netloc}".format(urlparse(url))
    if key not in _sessions:
        s = requests.Session()
        s.headers.update({"User-Agent": config.USER_AGENT})
        _sessions[key] = s
    return _sessions[key]


def api_get(params: dict) -> dict:
    """One Action API call with maxlag handling. Exits with guidance on proxy denial."""
    full = {"format": "json", "formatversion": "2", "maxlag": config.MAXLAG, **params}
    try:
        resp = _session_for(config.API_URL).get(config.API_URL, params=full, timeout=30)
    except requests.exceptions.ConnectionError:
        sys.exit(
            f"Cannot reach {config.WIKI}: the egress proxy refused the connection.\n"
            f"Add {config.WIKI} to this environment's network allowlist and rerun."
        )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        if data["error"].get("code") == "maxlag":
            wait = int(resp.headers.get("Retry-After", "5"))
            time.sleep(wait)
            return api_get(params)
        raise RuntimeError(f"API error: {data['error']}")
    return data


def paginate(params: dict, list_key: str):
    """Yield items from a list= query, following continue cursors politely."""
    cont: dict = {}
    while True:
        data = api_get({**params, **cont})
        yield from data.get("query", {}).get(list_key, [])
        if "continue" not in data:
            return
        cont = data["continue"]
        time.sleep(config.REQUEST_DELAY)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def save_snapshot(name: str, payload: dict, params_used: list[dict]) -> Path:
    """Write a provenance-stamped JSON snapshot into DATA_DIR."""
    out_dir = Path(__file__).parent / config.DATA_DIR
    out_dir.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = out_dir / f"{name}_{stamp}.json"
    payload = {
        "_provenance": {
            "endpoint": config.API_URL,
            "params": params_used,
            "collected_utc": utc_now_iso(),
            "user_agent": config.USER_AGENT,
        },
        **payload,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    return path
