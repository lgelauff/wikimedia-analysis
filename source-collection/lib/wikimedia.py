"""
wikimedia.py — Wikimedia domain detection and content fetch via MediaWiki API.

Wikimedia pages are fetched through the API rather than scraped, which gives
cleaner text, avoids exposing the user's IP, and is the explicitly recommended
access method per MediaWiki API:Etiquette.

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

import json
import os
import urllib.parse
import urllib.request
import ssl

import certifi

from .ratelimits import RateLimitRegistry

_SSL_CTX = ssl.create_default_context(cafile=certifi.where())
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


def is_wikimedia(url: str) -> bool:
    """Return True if the URL's host ends with any known Wikimedia domain."""
    host = urllib.parse.urlparse(url).netloc.lower()
    return any(host == d or host.endswith("." + d) for d in WIKIMEDIA_DOMAINS)


def fetch(url: str, rl: RateLimitRegistry, enterprise_key: str | None = None) -> str:
    """
    Fetch a Wikimedia page via API.

    If enterprise_key (or WIKIMEDIA_ENTERPRISE_KEY env var) is set, use the
    Wikimedia Enterprise API. Otherwise use the MediaWiki Action API
    (/w/api.php?action=query&prop=extracts).

    Returns plain text. Raises on HTTP error.
    """
    key = enterprise_key or os.environ.get("WIKIMEDIA_ENTERPRISE_KEY")
    if key:
        return _fetch_enterprise(url, rl, key)
    return _fetch_action_api(url, rl)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _fetch_action_api(url: str, rl: RateLimitRegistry) -> str:
    """Use /w/api.php to retrieve page extracts (plain text)."""
    parsed = urllib.parse.urlparse(url)
    # Extract page title from URL path (e.g. /wiki/Pol.is → Pol.is)
    path = parsed.path
    title = path.split("/wiki/", 1)[-1] if "/wiki/" in path else path.lstrip("/")
    title = urllib.parse.unquote(title)

    base = f"{parsed.scheme}://{parsed.netloc}"
    params = urllib.parse.urlencode({
        "action": "query",
        "titles": title,
        "prop": "extracts",
        "explaintext": "1",
        "exsectionformat": "plain",
        "format": "json",
        "formatversion": "2",
    })
    api_url = f"{base}/w/api.php?{params}"

    rl.wait(api_url)
    req = urllib.request.Request(api_url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=20, context=_SSL_CTX) as resp:
        data = json.loads(resp.read())

    pages = data.get("query", {}).get("pages", [])
    if not pages:
        raise RuntimeError(f"MediaWiki API returned no pages for: {url}")
    page = pages[0]
    if "missing" in page:
        raise RuntimeError(f"Page not found via MediaWiki API: {url}")
    return page.get("extract", "")


def _fetch_enterprise(url: str, rl: RateLimitRegistry, key: str) -> str:
    """Use Wikimedia Enterprise API to retrieve structured page content."""
    parsed = urllib.parse.urlparse(url)
    path = parsed.path
    title = path.split("/wiki/", 1)[-1] if "/wiki/" in path else path.lstrip("/")
    title = urllib.parse.unquote(title)
    lang = parsed.netloc.split(".")[0]  # e.g. "en" from en.wikipedia.org

    api_url = f"https://api.enterprise.wikimedia.com/v2/articles/{urllib.parse.quote(title)}"
    rl.wait(api_url)
    req = urllib.request.Request(
        api_url,
        headers={
            "User-Agent": _UA,
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
        },
    )
    req.add_header("X-WMF-Project", f"{lang}.wikipedia")
    with urllib.request.urlopen(req, timeout=20, context=_SSL_CTX) as resp:
        data = json.loads(resp.read())

    # Enterprise API returns article_body.wikitext or article_body.html
    return data.get("article_body", {}).get("wikitext", "")
