# Reference repositories

Repos reviewed for patterns, ideas, or code applicable to this package.
Each entry notes what was found and whether anything was adopted.

---

## edgi-govdata-archiving/wayback

**URL:** https://github.com/edgi-govdata-archiving/wayback
**Language:** Python
**What it is:** Python client library for the Internet Archive Wayback Machine.
Provides CDX-based search and memento retrieval.

**Used directly** as a dependency in this package (`lib/wayback.py`).

**References:**
- Documentation: https://wayback.readthedocs.io/

---

## edgi-govdata-archiving/web-monitoring-processing

**URL:** https://github.com/edgi-govdata-archiving/web-monitoring-processing
**Language:** Python
**What it is:** Tools for accessing, diffing, and analyzing archived web pages,
built on top of the Wayback Machine. Developed for tracking changes to
government websites.

**Relevant patterns found:**
- `detect_encoding()` in `web_monitoring/utils.py` — reads charset from
  `<meta http-equiv="Content-Type">`, `<meta charset>`, and XML prologs before
  falling back to HTTP headers and heuristic detection (`charset_normalizer`).
  More robust than relying on `Content-Type` header alone. Worth considering
  for `lib/text.py` if encoding errors become a recurring problem.
- PDF extraction via `pypdf` with graceful error handling — same approach as ours.

**Adopted:** `_detect_encoding()` in `lib/text.py` implements the same priority order
(BOM → `<meta charset>` → Content-Type header → heuristic → UTF-8 default) as
`web_monitoring/utils.py`. Written independently from the HTML5 spec
(https://html.spec.whatwg.org/multipage/parsing.html#determining-the-character-encoding)
to keep this package MIT-licensed; EDGI's implementation is GPL-3. `html_to_text()`
now accepts `bytes` directly so callers no longer call `.decode("utf-8", errors="replace")`.

---

## internetarchive/heritrix3

**URL:** https://github.com/internetarchive/heritrix3
**Language:** Java
**What it is:** Internet Archive's industrial-scale web crawler. Large-scale
infrastructure; most of it does not apply to per-entry research fetching.

**Relevant patterns found:**
- `FetchStatusCodes` — distinguishes internal error states beyond HTTP status:
  `S_TIMEOUT`, `S_CONNECT_FAILED`, `S_DEEMED_CHAFF` (content of negligible
  value), `S_TOO_MANY_RETRIES`. Useful conceptual vocabulary for a future
  fetch-result enum in `lib/verify.py`.
- `IdenticalPayloadDigestRevisit` + `IdenticalDigestDecideRule` — SHA digest of
  fetched content stored per URL; on recrawl, skip write if digest unchanged.
  Directly applicable to cache refresh logic, but skipped for now because our
  fetch path (Wayback) does not guarantee identical bytes across fetches.
- `ContentLengthDecideRule` — configurable threshold to reject short documents.
  Maps to the thin-content check planned for `lib/verify.py`.

**Adopted:** None yet. Concepts inform the planned `lib/verify.py` design.

---

## internetarchive/brozzler

**URL:** https://github.com/internetarchive/brozzler
**Language:** Python
**What it is:** Distributed browser-based web crawler using Chrome/Chromium,
warcprox (WARC proxy), and RethinkDB. Too heavy for per-entry research fetching,
but reviewed for ethical crawling patterns.

**Relevant patterns found:**
- `robots.py` — confirms three practices already in `lib/ratelimits.py`:
  fail-open on robots.txt fetch errors, per-domain cache, substring user-agent
  matching. Their policy note: "treat any kind of error fetching robots.txt as
  allow all."
- `ignore_robots` flag — per-job and per-seed opt-out in job config. Adopted:
  added `ignore_robots` param to `RateLimitRegistry` and `--ignore-robots` CLI
  flag; also supported as `ignore_robots: true` per-entry in sources.txt.
- User-agent guidance (from `job-conf.rst`): UA should explain why you are
  crawling, how to block the crawler via robots.txt, and how to contact the
  operator. Our UA already satisfies this.
- `behaviors.yaml` — per-site Chrome automation scripts for JS-rendered pages.
  Not applicable, but confirms that thin text output from a large HTML document
  is the right signal for JS-rendering detection in `lib/verify.py`.

**Adopted:** `ignore_robots` flag pattern.

---

## fuzheado/Wikipedia-AI-Skills

**URL:** https://github.com/fuzheado/Wikipedia-AI-Skills
**Language:** Claude skill definitions (Markdown + prompts)
**What it is:** Claude skill definitions for Wikipedia/Wikimedia research tasks.
Not a code library, but the skill descriptions enumerate what the Wikimedia
ecosystem can provide: article text, revision history, talk pages, Wikidata
entities, Commons media, citation networks.

**Relevant patterns found:**
- Reinforces using the MediaWiki Action API (`/w/api.php`) for article text
  rather than scraping HTML — matches our `lib/wikimedia.py` approach.
- Highlights talk pages and revision history as sources of editorial context
  not available via `prop=extracts`. Potential future extension.

**Adopted:** Nothing directly; confirms existing API approach.

---

## edgi-govdata-archiving/warcprox

**URL:** https://github.com/edgi-govdata-archiving/warcprox
**Language:** Python
**What it is:** WARC-writing MITM HTTP/S proxy. Used by brozzler to intercept
and archive traffic from Chrome. Not applicable to our architecture (we fetch
directly or via Wayback, not through a proxy).

**Not reviewed in detail.**

---

## edgi-govdata-archiving/grab-site

**URL:** https://github.com/edgi-govdata-archiving/grab-site
**Language:** Python
**What it is:** Simplified web crawler with WARC output and a real-time
dashboard. Wraps wpull/heritrix concepts into a friendlier CLI.
Out of scope for per-entry research fetching.

**Not reviewed in detail.**
