"""
wikimedia.py — Wikimedia domain detection and content fetch via MediaWiki API.

Wikimedia pages are fetched through the API rather than scraped, which gives
cleaner text, avoids exposing the user's IP, and is the explicitly recommended
access method per MediaWiki API:Etiquette.

Uses requests.Session for connection reuse across multiple API calls to the
same host. A single session is held per host (keyed by scheme://netloc) and
reused for the lifetime of a fetch run, reducing TCP handshake overhead.

Authentication tiers (set via environment variables):

  Anonymous (default)
    No credentials needed. Current rate limits:
    https://www.mediawiki.org/wiki/API:Etiquette

  Bot password  — WIKIMEDIA_USERNAME + WIKIMEDIA_BOT_PASSWORD
    Create at https://en.wikipedia.org/wiki/Special:BotPasswords
    Username format: "YourAccount@bot-name"  (e.g. "Lgelauff@source-collection")
    Identifies your traffic to Wikimedia ops; good practice for any automated tool.
    Currently not wired into fetch() — placeholder for future use.

  OAuth 2.0  — WIKIMEDIA_OAUTH_ACCESS_TOKEN
    Create an owner-only consumer at Special:OAuthConsumerRegistration.
    Owner-only consumers are active immediately (no admin approval needed).
    Significantly increases the rate limit on api.wikimedia.org vs. anonymous.
    Use scope "basic" — "openid" is not supported and returns invalid_scope.
    Current rate limits: https://api.wikimedia.org/wiki/Rate_limits
    Reference: https://www.mediawiki.org/wiki/OAuth/For_Developers/OAuth_2.0
    Currently not wired into fetch() — placeholder for future use.

  Enterprise API  — WIKIMEDIA_ENTERPRISE_KEY
    Set this env var to use the Wikimedia Enterprise API instead of the
    public Action API. Richer output and higher rate limits.
    Current rate limits and pricing: https://enterprise.wikimedia.com/
"""

import os
import urllib.parse

# Below this many characters, a TextExtracts result is treated as a failed
# extraction rather than a short page, and the raw-wikitext fallback runs.
# 500 is comfortably below any real documentation page and comfortably above
# the near-empty results a table-only page produces.
_EXTRACT_MIN_CHARS = 500

import requests

from .ratelimits import RateLimitRegistry

_UA = "WikimediaAnalysis/1.0 (personal research; lodewijk@stanford.edu; https://github.com/lgelauff/wikimedia-analysis)"

WIKIMEDIA_DOMAINS = {
    "wikipedia.org",
    "wikimedia.org",
    "wikidata.org",
    "wiktionary.org",
    "wikisource.org",
    "wikibooks.org",
    "wikivoyage.org",
    "wikinews.org",
    "wikiquote.org",
    "mediawiki.org",
}

# One Session per host, reused across all calls in a process.
# requests.Session reuses the underlying TCP connection (HTTP keep-alive),
# eliminating the handshake cost on repeated calls to the same host.
_sessions: dict[str, requests.Session] = {}


def _session_for(url: str) -> requests.Session:
    parsed = urllib.parse.urlparse(url)
    key = f"{parsed.scheme}://{parsed.netloc}"
    if key not in _sessions:
        s = requests.Session()
        s.headers.update({"User-Agent": _UA})
        _sessions[key] = s
    return _sessions[key]


def is_wikimedia(url: str) -> bool:
    """Return True if the URL's host ends with any known Wikimedia domain."""
    host = urllib.parse.urlparse(url).netloc.lower()
    return any(host == d or host.endswith("." + d) for d in WIKIMEDIA_DOMAINS)


def fetch(url: str, rl: RateLimitRegistry, enterprise_key: str | None = None) -> str:
    """
    Fetch a Wikimedia page via API, reusing a per-host requests.Session.

    If enterprise_key (or WIKIMEDIA_ENTERPRISE_KEY env var) is set, use the
    Wikimedia Enterprise API. Otherwise use the MediaWiki Action API
    (/w/api.php?action=query&prop=extracts).

    Returns plain text. Raises on HTTP error.
    """
    key = enterprise_key or os.environ.get("WIKIMEDIA_ENTERPRISE_KEY")
    session = _session_for(url)
    if key:
        return _fetch_enterprise(url, rl, key, session)
    return _fetch_action_api(url, rl, session)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _fetch_action_api(url: str, rl: RateLimitRegistry, session: requests.Session) -> str:
    """Use /w/api.php to retrieve page extracts (plain text)."""
    parsed = urllib.parse.urlparse(url)
    path = parsed.path
    title = path.split("/wiki/", 1)[-1] if "/wiki/" in path else path.lstrip("/")
    title = urllib.parse.unquote(title)

    base = f"{parsed.scheme}://{parsed.netloc}"
    params = {
        "action": "query",
        "titles": title,
        "prop": "extracts",
        "explaintext": "1",
        "exsectionformat": "plain",
        # Follow redirects. Without this, a redirect page returns an EMPTY
        # extract and the fetch is recorded as a failure, even though the
        # target exists. Found 2026-08-15: two different URLs for wikitech's
        # bot-detection page both failed this way; both were redirects to
        # "Data Platform/Data Lake/Traffic/Bot detection".
        "redirects": "1",
        "format": "json",
        "formatversion": "2",
    }
    api_url = f"{base}/w/api.php"

    rl.wait(api_url)
    resp = session.get(api_url, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    pages = data.get("query", {}).get("pages", [])
    if not pages:
        raise RuntimeError(f"MediaWiki API returned no pages for: {url}")
    page = pages[0]
    if "missing" in page:
        raise RuntimeError(f"Page not found via MediaWiki API: {url}")

    extract = page.get("extract", "") or ""

    # prop=extracts (TextExtracts) DROPS TABLES and many templates. On a page
    # whose substance IS a table, it returns almost nothing, and the caller
    # records that as "no cache output" — indistinguishable from a network
    # failure, so the page looks unreachable when it is merely unextractable.
    #
    # Found 2026-08-15: wikitech Data_Platform/Data_Lake/Traffic/BotDetection
    # (a version/date table) failed this way twice, while its prose-heavy
    # sibling Webrequest fetched fine from the same host in the same run.
    #
    # Fall back to raw wikitext, which preserves table content. Wikitext markup
    # is noisier than a plain-text extract, so this is used only when the
    # extract is empty or implausibly short for a real page.
    if len(extract.strip()) >= _EXTRACT_MIN_CHARS:
        return extract

    raw_url = f"{base}/w/index.php"
    rl.wait(raw_url)
    try:
        raw_resp = session.get(
            raw_url, params={"title": title, "action": "raw"}, timeout=20
        )
        raw_resp.raise_for_status()
        raw = raw_resp.text or ""
    except Exception:
        return extract  # never make things worse than the extract we already have

    if len(raw.strip()) > len(extract.strip()):
        header = (
            f"[source-collection] TextExtracts returned only "
            f"{len(extract.strip())} chars for this page, so this is the RAW "
            f"WIKITEXT ({len(raw.strip())} chars) instead. Tables are included "
            f"but markup is unprocessed.\n\n"
        )
        return header + raw
    return extract


def _fetch_enterprise(url: str, rl: RateLimitRegistry, key: str, session: requests.Session) -> str:
    """Use Wikimedia Enterprise API to retrieve structured page content."""
    parsed = urllib.parse.urlparse(url)
    path = parsed.path
    title = path.split("/wiki/", 1)[-1] if "/wiki/" in path else path.lstrip("/")
    title = urllib.parse.unquote(title)
    lang = parsed.netloc.split(".")[0]

    api_url = f"https://api.enterprise.wikimedia.com/v2/articles/{urllib.parse.quote(title)}"
    rl.wait(api_url)
    resp = session.get(
        api_url,
        headers={"Authorization": f"Bearer {key}", "X-WMF-Project": f"{lang}.wikipedia"},
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("article_body", {}).get("wikitext", "")
