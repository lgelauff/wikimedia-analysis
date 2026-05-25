"""
ratelimits.py — documented rate-limit registry with override support.

Each entry carries the delay in seconds, a human-readable reason, and a reference URL
so the source can be checked if limits change or something breaks.

Priority for delay_for(url):
  1. Caller overrides (passed to RateLimitRegistry.__init__)
  2. robots.txt Crawl-delay for the domain
  3. DEFAULTS table (substring match, longest match wins)
  4. DEFAULT_DELAY fallback
"""

import urllib.parse
import urllib.robotparser
import time

# ---------------------------------------------------------------------------
# Documented defaults
# (delay_secs, reason, reference_url | None)
# ---------------------------------------------------------------------------
DEFAULTS: dict[str, tuple[float, str, str | None]] = {
    # arXiv: robots.txt specifies Crawl-delay: 15 for unknown user agents.
    # Policy explicitly forbids indiscriminate automated downloads.
    # Preferred bulk-access methods: OAI-PMH, arXiv API, RSS.
    "arxiv.org": (
        15.0,
        "robots.txt Crawl-delay: 15 for unknown agents; bulk downloads discouraged",
        "https://arxiv.org/robots.txt",
    ),
    # Internet Archive / Wayback Machine: no published per-user rate limit.
    # wayback (edgi) uses 0.8 req/s CDX / 8 req/s memento internally.
    # 1.5s is slightly more conservative than their CDX limit; user-adjustable.
    "web.archive.org": (
        1.5,
        "No published policy; slightly above wayback-edgi CDX limit (0.8 req/s)",
        None,
    ),
    "archive.org": (
        1.5,
        "No published policy; slightly above wayback-edgi CDX limit (0.8 req/s)",
        None,
    ),
    # Wikimedia REST API / API Gateway (api.wikimedia.org)
    # Anonymous rate limit is significantly lower than authenticated.
    # Check current limits at: https://api.wikimedia.org/wiki/Rate_limits
    "api.wikimedia.org": (
        8.0,
        "Conservative anonymous default; authenticated limit is significantly higher — see https://api.wikimedia.org/wiki/Rate_limits",
        "https://api.wikimedia.org/wiki/Rate_limits",
    ),
    # MediaWiki Action API (/w/api.php): no published numerical read limit.
    # Use maxlag=5 for write operations. 1s is a conservative default for reads.
    # See: https://www.mediawiki.org/wiki/API:Etiquette
    "wikipedia.org": (
        1.0,
        "Action API: no published read limit; 1s conservative default; use maxlag=5 for writes",
        "https://www.mediawiki.org/wiki/API:Etiquette",
    ),
    "wikimedia.org": (
        1.0,
        "Action API: no published read limit; 1s conservative default; use maxlag=5 for writes",
        "https://www.mediawiki.org/wiki/API:Etiquette",
    ),
    "mediawiki.org": (
        1.0,
        "Action API: no published read limit; 1s conservative default; use maxlag=5 for writes",
        "https://www.mediawiki.org/wiki/API:Etiquette",
    ),
    # Crossref REST API: polite pool (mailto: in UA) has significantly better
    # throughput than the anonymous pool. crossref.py manages its own rate limiting
    # (it knows which pool it is in at import time), so this entry is documentation
    # only — it is not used by RateLimitRegistry during normal fetch runs.
    # Current guidance: https://www.crossref.org/documentation/retrieve-metadata/rest-api/tips-for-using-the-crossref-rest-api/
    "api.crossref.org": (
        1.0,
        "Polite pool (mailto: in UA) has significantly better throughput than anonymous. crossref.py self-limits.",
        "https://www.crossref.org/documentation/retrieve-metadata/rest-api/tips-for-using-the-crossref-rest-api/",
    ),
}

DEFAULT_DELAY = 5.0   # fallback for domains not in DEFAULTS and without robots.txt Crawl-delay

# ---------------------------------------------------------------------------
# robots.txt cache (shared across all RateLimitRegistry instances in a process)
# ---------------------------------------------------------------------------
_robots_cache: dict[str, urllib.robotparser.RobotFileParser] = {}
_domain_last_request: dict[str, float] = {}

_UA = "WikimediaAnalysis/1.0 (personal research; lodewijk@stanford.edu; https://github.com/lgelauff/wikimedia-analysis)"


def _netloc(url: str) -> str:
    p = urllib.parse.urlparse(url)
    return f"{p.scheme}://{p.netloc}"


def _host(url: str) -> str:
    return urllib.parse.urlparse(url).netloc


def _robots_for(url: str) -> urllib.robotparser.RobotFileParser:
    dom = _netloc(url)
    if dom not in _robots_cache:
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(f"{dom}/robots.txt")
        try:
            rp.read()
        except Exception:
            pass  # fail-open: if robots.txt unreachable, assume allowed
        _robots_cache[dom] = rp
    return _robots_cache[dom]


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
class RateLimitRegistry:
    """
    Resolve per-domain rate-limit delays with full override support.

    Priority: caller overrides > robots.txt Crawl-delay > DEFAULTS > DEFAULT_DELAY
    """

    def __init__(self, overrides: dict[str, float] | None = None):
        """
        overrides: {domain_fragment: delay_seconds}
        Substring match — "archive.org" matches "web.archive.org".
        Longer/more-specific fragments win over shorter ones.
        """
        self._overrides: dict[str, float] = overrides or {}

    # ------------------------------------------------------------------
    def delay_for(self, url: str) -> float:
        host = _host(url)

        # 1. Caller overrides (longest matching fragment wins)
        match = self._best_match(host, {k: v for k, v in self._overrides.items()})
        if match is not None:
            return match

        # 2. robots.txt Crawl-delay
        rp = _robots_for(url)
        cd = rp.crawl_delay(_UA)
        if cd is not None:
            return float(cd)

        # 3. DEFAULTS (longest matching fragment wins)
        match = self._best_match(host, {k: v[0] for k, v in DEFAULTS.items()})
        if match is not None:
            return match

        return DEFAULT_DELAY

    def reference_for(self, url: str) -> str | None:
        host = _host(url)
        entry = self._best_match_key(host, DEFAULTS)
        if entry:
            return DEFAULTS[entry][2]
        return None

    def is_allowed(self, url: str) -> bool:
        return _robots_for(url).can_fetch(_UA, url)

    # ------------------------------------------------------------------
    @staticmethod
    def _best_match(host: str, table: dict[str, float]) -> float | None:
        candidates = [(k, v) for k, v in table.items() if k in host]
        if not candidates:
            return None
        return max(candidates, key=lambda kv: len(kv[0]))[1]

    @staticmethod
    def _best_match_key(host: str, table: dict) -> str | None:
        candidates = [k for k in table if k in host]
        if not candidates:
            return None
        return max(candidates, key=len)

    # ------------------------------------------------------------------
    def wait(self, url: str) -> None:
        """Sleep if we hit this domain too recently, then record the request time."""
        delay = self.delay_for(url)
        dom = _netloc(url)
        gap = time.time() - _domain_last_request.get(dom, 0.0)
        if gap < delay:
            time.sleep(delay - gap)
        _domain_last_request[dom] = time.time()
