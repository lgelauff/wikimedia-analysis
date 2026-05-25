# External services

This package fetches research sources through a configurable pipeline. Each stage
relies on one or more external services. This document describes what each service
does, which module handles it, and how authentication works.

Specific rate limits are intentionally not listed here — they change over time.
Each service section links to the canonical documentation where current limits
are published. See `lib/ratelimits.py` for the conservative defaults we apply
and their cited sources.

Credentials are never hardcoded. See `.env.example` for the environment variables
each service expects.

---

## Internet Archive — Wayback Machine

**Type:** Web archive
**Commercial use:** Permitted for reasonable use; large-scale or commercial deployments should review the Terms of Service and consider contacting the Internet Archive. https://archive.org/about/terms.php

**Used for:** Retrieving archived snapshots of web pages without exposing the
user's IP address to the origin server. The Wayback Machine acts as an intermediary:
we fetch from archive.org, not from the target site directly.

**Module:** `lib/wayback.py`

**Two distinct APIs we use:**

| API | Purpose | Stable endpoint |
|---|---|---|
| Availability API | Check whether a snapshot exists and its timestamp | `https://archive.org/wayback/available?url=…` |
| Memento fetch | Retrieve the archived page content | `https://web.archive.org/web/<timestamp>/<url>` |

**Authentication:** None required for read access.

**References:**
- Availability API: https://archive.org/help/wayback_api.php
- Memento protocol (the standard the Wayback Machine implements): https://mementoweb.org/guide/quick-intro/

---

## Internet Archive — SavePageNow v2 (SPN2)

**Type:** Archiving service (API)
**Commercial use:** Same terms as the Wayback Machine. https://archive.org/about/terms.php

**Used for:** Requesting a fresh capture of a URL when no recent Wayback snapshot
exists. SPN2 submits the URL to the Wayback Machine for archiving; we then retrieve
the result via the Availability API.

**Module:** `lib/spn2.py`

**Authentication:** Required. Internet Archive S3-like key pair loaded from
`IA_ACCESS_KEY` + `IA_SECRET_KEY`. Obtain at https://archive.org/account/s3.php

The auth header format is `Authorization: LOW <access_key>:<secret_key>` — this
is a stable design decision of the SPN2 API, not subject to change without notice.

**References:**
- SPN2 API specification: https://docs.google.com/document/d/1Nsv52MvSjbLb2PCpHlat0gkzw0EvtSgpKHu4mk0MnrA
- Account S3 keys: https://archive.org/account/s3.php

---

## Crossref

**Type:** Metadata API — DOI registration agency
**Commercial use:** Permitted. The metadata API is openly available including for commercial use. https://www.crossref.org/documentation/retrieve-metadata/rest-api/

**Used for:** Looking up citation metadata for a DOI — authors, title, journal,
year, volume, pages, publisher — and generating BibTeX entries from that metadata.

**Module:** `lib/crossref.py`

**Authentication:** None required. Setting `CROSSREF_MAILTO` (your email address)
opts into the **polite pool**, which routes requests to dedicated infrastructure
with significantly better throughput. Crossref uses the address only to contact
you if your usage looks problematic; it appears in their server logs.

**Coverage:** Crossref is the registration agency for most academic publishers.
DOIs registered with other agencies (DataCite for datasets, OCLC for some library
content) will return no results from this API.

**References:**
- REST API overview: https://www.crossref.org/documentation/retrieve-metadata/rest-api/
- Polite pool and etiquette: https://www.crossref.org/documentation/retrieve-metadata/rest-api/tips-for-using-the-crossref-rest-api/
- API interactive docs: https://api.crossref.org/swagger-ui/index.html

---

## Wikimedia — MediaWiki Action API

**Type:** Content API
**Commercial use:** The API itself is freely usable. The content retrieved (e.g. Wikipedia articles) is licensed under CC BY-SA, which permits commercial use with attribution and share-alike conditions. Verify the license of each wiki — not all Wikimedia projects use the same terms. https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use

**Used for:** Fetching content from any Wikimedia project (Wikipedia, Wikidata,
MediaWiki.org, Wikitech, etc.) as clean plain text. This is the officially
recommended access method; scraping HTML is explicitly discouraged.

**Module:** `lib/wikimedia.py`

**Endpoint pattern:** `https://<wiki>/w/api.php` — works on every Wikimedia project,
just swap the domain. For example:
- `https://en.wikipedia.org/w/api.php`
- `https://www.wikidata.org/w/api.php`
- `https://commons.wikimedia.org/w/api.php`

**Authentication:**

*Anonymous (default)* — no credentials needed. Suitable for read-only access.

*Bot password* — `WIKIMEDIA_USERNAME` + `WIKIMEDIA_BOT_PASSWORD`
Identifies your traffic to Wikimedia infrastructure. Good practice for automated
tools. Create at https://en.wikipedia.org/wiki/Special:BotPasswords — you receive
a username in the format `YourAccount@bot-name` and a generated password.
Not yet wired into `fetch()` — placeholder for future implementation.

**References:**
- API etiquette and user-agent policy: https://www.mediawiki.org/wiki/API:Etiquette
- Action API main page: https://www.mediawiki.org/wiki/API:Main_page
- Bot passwords: https://www.mediawiki.org/wiki/Manual:Bot_passwords

---

## Wikimedia — REST API / API Gateway (api.wikimedia.org)

**Type:** Content API + ML inference API
**Commercial use:** Same content licensing as the Action API above. API access terms: https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use

**Used for:** (Planned) Higher-throughput access to Wikimedia content and the
Lift Wing ML models (article quality prediction, revert risk, topic classification).
The API Gateway at `api.wikimedia.org` is the modern successor to per-project
REST APIs.

**Authentication:** OAuth 2.0 significantly increases the rate limit compared to
anonymous access. Use an **owner-only consumer** — it is active immediately and
requires no admin approval, unlike public consumers which can take days.

Key implementation fact: use scope `basic`. The scope `openid` is not supported
on Wikimedia's OAuth 2.0 implementation and returns `invalid_scope` even when
"User identity verification only" is selected. [Source: wikimedia-coding-agent-lessons]

Environment variables: `WIKIMEDIA_OAUTH_CLIENT_ID`, `WIKIMEDIA_OAUTH_CLIENT_SECRET`,
`WIKIMEDIA_OAUTH_ACCESS_TOKEN`

**References:**
- OAuth 2.0 for developers: https://www.mediawiki.org/wiki/OAuth/For_Developers/OAuth_2.0
- Consumer registration: https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration
- API Gateway docs: https://api.wikimedia.org/wiki/
- Lift Wing ML API: https://api.wikimedia.org/wiki/Lift_Wing_API

---

## Wikimedia — Enterprise API

**Type:** Content API (commercial)
**Commercial use:** Designed for commercial and large-scale use; requires a contract with the Wikimedia Foundation. https://enterprise.wikimedia.com/

**Used for:** An alternative to the public Action API for Wikimedia content.
Provides richer structured output and higher throughput. Selected automatically
when `WIKIMEDIA_ENTERPRISE_KEY` is set.

**Module:** `lib/wikimedia.py`

**Authentication:** Required. API key loaded from `WIKIMEDIA_ENTERPRISE_KEY`.

**References:**
- Enterprise API overview: https://enterprise.wikimedia.com/
- API documentation: https://enterprise.wikimedia.com/docs/

---

## arXiv

**Type:** Preprint repository
**Commercial use:** API access is freely available. Content licensing varies per paper — authors choose their own license, ranging from CC BY to arXiv's non-exclusive licence which restricts commercial redistribution. Check the licence on each paper before any commercial use. https://arxiv.org/help/license

**Used for:** Fetching full text of arXiv preprints. The HTML full-text version
(`/html/<id>`) is tried first; if unavailable or too short, we fall back to the
abstract page (`/abs/<id>`).

**Module:** `fetch.py` (`_fetch_arxiv`, `_stage_arxiv`)

**Authentication:** None required.

**Access policy:** arXiv discourages indiscriminate automated downloading.
For bulk access they recommend their OAI-PMH feed or the arXiv API. Our use
is per-entry lookups, not bulk crawling.

**References:**
- API documentation: https://info.arxiv.org/help/api/index.html
- Robots and bulk access policy: https://info.arxiv.org/help/robots.html
- OAI-PMH feed (for bulk use): https://info.arxiv.org/help/oa/index.html
