"""
Collect all reported attendance/participation figures for every Wikimania edition.

For each edition we collect every distinct number reported, preserving:
  - the figure as reported (verbatim qualifier e.g. "800+")
  - the definition used by the source (e.g. "registered participants")
  - the full context sentence / table row
  - the source URL and type
  - any author information and their role (proxy for source credibility)

Sources mined (in order):
  1. Wikipedia "Wikimania" article  — multi-year table, seeded from hardcoded snapshot
  2. Meta-wiki main page for each edition
  3. Post-conference email archives  — conference month + 2 months after
  4. Already-cached conference wiki pages  (from wikimania_deadlines/tmp/)

Run:
    uv run fetch_attendees.py [year ...]   # specific year(s)
    uv run fetch_attendees.py              # all editions
"""

import email as emaillib
import email.header
import json
import re
import sys
import time
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Shared infrastructure from wikimania_deadlines
# ---------------------------------------------------------------------------
DEADLINES_DIR = Path(__file__).parent.parent / "wikimania_deadlines"
sys.path.insert(0, str(DEADLINES_DIR))

# Ensure the root-level .env is visible to llm.py (which looks in parent/grandparent)
# llm.py walks: __file__.parent (deadlines/) then __file__.parent.parent (repo root) ✓

from cache import (  # noqa: E402
    fetch_email_archive, fetch_wiki_page, MONTHS,
    EMAIL_DIR, WIKI_DIR,
)
from llm import query_mistral  # noqa: E402

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ATTENDEES_DIR = Path(__file__).parent
EDITIONS_DIR  = ATTENDEES_DIR / "editions"
TODAY         = date.today().isoformat()

# ---------------------------------------------------------------------------
# Edition metadata (year → conference start month, 1-indexed)
# ---------------------------------------------------------------------------
EDITIONS = [
    (2005, "Frankfurt, Germany",        8),
    (2006, "Boston, USA",               8),
    (2007, "Taipei, Taiwan",            8),
    (2008, "Alexandria, Egypt",         7),
    (2009, "Buenos Aires, Argentina",   8),
    (2010, "Gdańsk, Poland",            7),
    (2011, "Haifa, Israel",             8),
    (2012, "Washington DC, USA",        7),
    (2013, "Hong Kong SAR, China",      8),
    (2014, "London, United Kingdom",    8),
    (2015, "Mexico City, Mexico",       7),
    (2016, "Esino Lario, Italy",        6),
    (2017, "Montréal, Canada",          8),
    (2018, "Cape Town, South Africa",   7),
    (2019, "Stockholm, Sweden",         8),
    (2020, None,                        None),   # Cancelled
    (2021, "Virtual",                   8),
    (2022, "Virtual",                   8),
    (2023, "Singapore",                 8),
    (2024, "Katowice, Poland",          8),
    (2025, "Nairobi, Kenya",            8),
    (2026, "Paris, France",             7),
]

# ---------------------------------------------------------------------------
# Wikipedia baseline — snapshot retrieved 2026-04-15.
# Source: https://en.wikipedia.org/wiki/Wikimania
# These are the figures as they appear in the Wikipedia article table.
# Each entry: (qualifier_as_printed, definition_as_reported, context)
# ---------------------------------------------------------------------------
WIKIPEDIA_BASELINE = {
    2005: [("380",    "attendees", "2005 Frankfurt, Germany — 380 attendees")],
    2006: [("400",    "attendees", "2006 Cambridge/Boston, USA — 400 attendees")],
    2007: [("440",    "attendees", "2007 Taipei, Taiwan — 440 attendees")],
    2008: [("650",    "attendees", "2008 Alexandria, Egypt — 650 attendees")],
    2009: [("559",    "attendees", "2009 Buenos Aires, Argentina — 559 attendees")],
    2010: [("~500",   "attendees", "2010 Gdańsk, Poland — ~500 attendees")],
    2011: [("720",    "attendees", "2011 Haifa, Israel — 720 attendees")],
    2012: [("1,400",  "attendees", "2012 Washington D.C., USA — 1,400 attendees")],
    2013: [("700",    "attendees", "2013 Hong Kong, China — 700 attendees")],
    2014: [("1,762",  "attendees", "2014 London, United Kingdom — 1,762 attendees")],
    2015: [("800",    "attendees", "2015 Mexico City, Mexico — 800 attendees")],
    2016: [("1,365",  "attendees", "2016 Esino Lario, Italy — 1,365 attendees")],
    2017: [("915",    "attendees", "2017 Montreal, Canada — 915 attendees")],
    2018: [("700+",   "attendees", "2018 Cape Town, South Africa — 700+ attendees")],
    2019: [("800+",   "attendees", "2019 Stockholm, Sweden — 800+ attendees")],
    2023: [
        ("761",   "in-person attendees",  "2023 Singapore — 761 in-person attendees"),
        ("2,105+","virtual attendees",    "2023 Singapore — 2,105+ virtual attendees"),
    ],
    2024: [("2,200+", "attendees", "2024 Katowice, Poland — 2,200+ attendees from 143 countries")],
    2025: [
        ("776",   "in-person attendees",  "2025 Nairobi, Kenya — 776 in-person attendees"),
        ("1,900+","virtual attendees",    "2025 Nairobi, Kenya — 1,900+ virtual attendees"),
    ],
}

WIKIPEDIA_URL = "https://en.wikipedia.org/wiki/Wikimania"

# ---------------------------------------------------------------------------
# LLM extraction helpers
# ---------------------------------------------------------------------------
EXTRACTION_SYSTEM = (
    "You are a precise data extraction assistant. "
    "Extract only figures explicitly stated in the text. "
    "Do not infer, estimate, or guess. Return valid JSON only."
)

WIKI_EXTRACTION_PROMPT = """\
Below is wikitext from the Wikimania {year} page on Meta-wiki or its conference site.
Extract every number or statistic reported about attendance, participation, or conference scale.

INCLUDE only:
- Total attendees / participants / registrations / check-ins
- In-person vs. virtual attendees (separate figures)
- Unique online viewers / live stream viewers
- Countries or regions represented ("from N countries")
- Scholarship recipients / scholars funded
- Submitted presentations / proposals / talks
- Accepted presentations / talks / sessions
- Hackathon participants (if reported separately)

EXCLUDE — do NOT extract:
- Edition ordinals ("15th conference", "2nd year")
- Date ranges ("14th to 18th August")
- Number of days ("3-day event", "5 days")
- Session counts or room counts
- Capacity / venue limits unless described as actual attendance
- Any figure not about people or geographic reach

For each figure found, return a JSON object:
{{
  "figure_raw": "<exact number string as printed, e.g. '800+', '~500', '1,762'>",
  "figure_numeric": <integer approximation or null if not a simple number>,
  "definition_as_reported": "<exact label used by the source, e.g. 'registered participants', 'attendees', 'unique viewers'>",
  "context": "<the full sentence or table cell where this figure appears, max 300 chars>",
  "author": null,
  "author_role": null
}}

Return a JSON array. If nothing relevant found, return [].

--- WIKITEXT ---
{text}
--- END ---

JSON array:"""

EMAIL_EXTRACTION_PROMPT = """\
Below are emails from mailing list archives around Wikimania {year}.
Extract every number or statistic reported about Wikimania {year} attendance,
participation, or conference scale.

For each figure found, return a JSON object:
{{
  "figure_raw": "<exact number string as printed, e.g. '800+', 'over 900', 'approximately 700'>",
  "figure_numeric": <integer approximation, or null if not parseable>,
  "definition_as_reported": "<exact label used, e.g. 'participants', 'registered attendees'>",
  "context": "<the exact sentence or table row, max 300 chars>",
  "author": "<name of email sender if determinable, else null>",
  "author_role": "<any organizational role or affiliation mentioned for this person, e.g. 'WMF Executive Director', 'Wikimania 2019 organizer', or null>",
  "email_subject": "<subject line of the email>",
  "email_date": "<Date: header of the email>"
}}

Notes:
- Only include figures about Wikimania {year}, not other events.
- If the email compares multiple years (e.g. "last year we had 700, this year 900"),
  extract all years mentioned and label them with their year.
- Pay close attention to author role: WMF staff, local organizers, scholarship
  committee members are more credible sources than general list participants.
- Distinguish: registered vs. checked-in vs. in-person vs. virtual vs. unique viewers.

Return a JSON array. If nothing relevant found, return [].

--- EMAILS ---
{emails}
--- END ---

JSON array:"""


def _query_mistral_with_retry(prompt: str, label: str = "", max_retries: int = 4) -> str | None:
    """Call Mistral with exponential backoff on 429 rate-limit errors."""
    import urllib.error
    delay = 10
    for attempt in range(max_retries):
        try:
            return query_mistral(prompt, system=EXTRACTION_SYSTEM)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"    Rate limited on {label}, waiting {delay}s...")
                time.sleep(delay)
                delay = min(delay * 2, 120)
            else:
                print(f"    Mistral HTTP error {e.code} on {label}: {e}")
                return None
        except Exception as e:
            print(f"    Mistral error on {label}: {e}")
            return None
    print(f"    Gave up on {label} after {max_retries} retries")
    return None


def parse_figure(raw: str) -> int | None:
    """
    Convert a raw figure string like '1,762' or '~500' or '800+' to int.
    Returns None for ranges ('600 to 1,400'), ordinals, or non-numeric strings.
    """
    if not raw:
        return None
    # Ranges like "600 to 1,400" or "600–1,400" → not a single figure
    if re.search(r'\d\s*(to|-|–|—)\s*\d', raw):
        return None
    # Ordinals like "15th" → not a headcount
    if re.search(r'\d+(st|nd|rd|th)\b', raw, re.IGNORECASE):
        return None
    cleaned = re.sub(r'[~+,\s≈]', '', raw)
    cleaned = re.sub(r'(?i)approximately|about|over|under|around|nearly|almost', '', cleaned)
    cleaned = re.sub(r'[^\d]', '', cleaned)
    try:
        return int(cleaned) if cleaned else None
    except ValueError:
        return None


def make_figure(
    figure_raw: str,
    definition_as_reported: str,
    context: str,
    source_url: str,
    source_type: str,
    author: str | None = None,
    author_role: str | None = None,
    extra: dict | None = None,
) -> dict:
    return {
        "figure_raw": figure_raw,
        "figure_numeric": parse_figure(figure_raw),
        "definition_as_reported": definition_as_reported,
        "context": context,
        "author": author,
        "author_role": author_role,
        "source_url": source_url,
        "source_type": source_type,
        "retrieved": TODAY,
        "verified": False,
        "verified_date": None,
        "verified_text_found": None,
        **(extra or {}),
    }


# ---------------------------------------------------------------------------
# Source 1: Wikipedia baseline (hardcoded snapshot)
# ---------------------------------------------------------------------------
def seed_from_wikipedia(year: int) -> list[dict]:
    entries = WIKIPEDIA_BASELINE.get(year, [])
    return [
        make_figure(
            figure_raw=qualifier,
            definition_as_reported=defn,
            context=ctx,
            source_url=WIKIPEDIA_URL,
            source_type="wikipedia",
        )
        for qualifier, defn, ctx in entries
    ]


# ---------------------------------------------------------------------------
# Source 2: Meta-wiki main page
# ---------------------------------------------------------------------------
META_API = "https://meta.wikimedia.org/w/api.php"
CONF_API = "https://wikimania.wikimedia.org/w/api.php"

META_SUBPAGES = [
    "",                # main page
    "/Statistics",
    "/Report",
    "/Summary",
    "/Press",
    "/Evaluation",
]


def fetch_and_extract_wiki(year: int, base: str, title: str) -> list[tuple[str, str, list[dict]]]:
    """
    Fetch a wiki page and extract attendance figures via LLM.
    Returns list of (url, wikitext_snippet, figures).
    Caches the raw wikitext so it's not re-fetched.
    """
    wikitext = fetch_wiki_page(base, title, year)
    if not wikitext:
        return []

    # Truncate to ~30k chars for LLM
    text_for_llm = wikitext[:30_000]

    # Build the human-readable source URL
    host = base.replace("/w/api.php", "").replace("https://", "")
    human_url = f"https://{host}/wiki/{title.replace(' ', '_')}"

    prompt = WIKI_EXTRACTION_PROMPT.format(year=year, text=text_for_llm)
    raw = _query_mistral_with_retry(prompt, label=f"wiki:{title}")
    if raw is None:
        return []
    figures = _parse_llm_json(raw)
    return [(human_url, figures)]


def extract_from_metawiki(year: int) -> list[dict]:
    results = []
    # Try main page and known sub-pages
    for sub in META_SUBPAGES:
        title = f"Wikimania_{year}{sub}"
        pairs = fetch_and_extract_wiki(year, META_API, title)
        for url, figures in pairs:
            for f in figures:
                results.append(make_figure(
                    figure_raw=f.get("figure_raw", ""),
                    definition_as_reported=f.get("definition_as_reported", ""),
                    context=f.get("context", ""),
                    source_url=url,
                    source_type="meta_wiki",
                    author=f.get("author"),
                    author_role=f.get("author_role"),
                ))
        time.sleep(0.3)

    # Also try the conference site (wikimania.wikimedia.org/YYYY:Statistics etc.)
    conf_subpages = ["", ":Statistics", ":Report", ":Press"]
    for sub in conf_subpages:
        title = f"{year}{sub}"
        pairs = fetch_and_extract_wiki(year, CONF_API, title)
        for url, figures in pairs:
            for f in figures:
                results.append(make_figure(
                    figure_raw=f.get("figure_raw", ""),
                    definition_as_reported=f.get("definition_as_reported", ""),
                    context=f.get("context", ""),
                    source_url=url,
                    source_type="conference_wiki",
                    author=f.get("author"),
                    author_role=f.get("author_role"),
                ))
        time.sleep(0.3)

    return [r for r in results if r["figure_raw"]]


# ---------------------------------------------------------------------------
# Source 3: Cached conference wiki pages (from wikimania_deadlines)
# ---------------------------------------------------------------------------
def extract_from_cached_wiki_pages(year: int) -> list[dict]:
    """
    Scan already-cached wiki pages for this edition (e.g. registration pages)
    that might contain capacity or attendance figures.
    Uses the deadlines cache — no new network requests.
    """
    results = []
    prefix_patterns = [
        f"wikimania{year}_",
        f"wikimania_wikimedia_org__{year}",
    ]

    for cache_file in WIKI_DIR.glob("*.json"):
        name = cache_file.name
        if not any(name.startswith(p) for p in prefix_patterns):
            continue
        try:
            data = json.loads(cache_file.read_text())
            wikitext = data.get("wikitext") or ""
            if not wikitext:
                continue

            # Quick keyword filter before calling LLM
            keywords = r'attendee|participant|registered|attendance|visitor|delegate|' \
                       r'people|countries|scholarship|scholar|accepted|submitted'
            if not re.search(keywords, wikitext[:5000], re.IGNORECASE):
                continue

            # Reconstruct a human-readable URL from the filename
            # Format: {host_underscored}__{title_urlencoded}.json
            parts = name.replace(".json", "").split("__", 1)
            if len(parts) == 2:
                host = parts[0].replace("_", ".")
                title_slug = re.sub(r'_html_\d{4}-\d{2}-\d{2}$', '', parts[1])
                title_slug = re.sub(r'__html.*$', '', title_slug)
                import urllib.parse
                title = urllib.parse.unquote(title_slug.replace("_", "%20").replace("%2F", "/"))
                human_url = f"https://{host}/wiki/{title.replace(' ', '_')}"
            else:
                human_url = f"cached:{name}"

            prompt = WIKI_EXTRACTION_PROMPT.format(year=year, text=wikitext[:20_000])
            raw = _query_mistral_with_retry(prompt, label=f"cached:{cache_file.name[:40]}")
            if raw is None:
                continue
            figures = _parse_llm_json(raw)
            for f in figures:
                if f.get("figure_raw"):
                    results.append(make_figure(
                        figure_raw=f.get("figure_raw", ""),
                        definition_as_reported=f.get("definition_as_reported", ""),
                        context=f.get("context", ""),
                        source_url=human_url,
                        source_type="conference_wiki",
                        author=f.get("author"),
                        author_role=f.get("author_role"),
                    ))
            time.sleep(0.5)
        except Exception as e:
            print(f"    Cache parse error {cache_file.name}: {e}")

    return results


# ---------------------------------------------------------------------------
# Source 4: Email archives (post-conference months)
# ---------------------------------------------------------------------------
ATTENDANCE_KEYWORDS = [
    "attendee", "participant", "registered", "attendance", "visitor",
    "delegate", "people attended", "countries", "scholarship", "scholars",
    "report from", "wrap-up", "wrap up", "recap", "summary", "highlights",
    "in numbers", "stats", "statistics", "hundreds", "thousands",
]

MAX_CHARS_PER_CALL = 18_000


def parse_messages(raw_text: str) -> list[dict]:
    """Split mbox into list of {subject, body, date, from} dicts."""
    raw_msgs = re.split(r'(?m)^From \S+.*$', raw_text)
    results = []
    for chunk in raw_msgs:
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            msg = emaillib.message_from_string("From: x\n" + chunk)
            subject = str(emaillib.header.make_header(
                emaillib.header.decode_header(msg.get("Subject", ""))))
            date_str = msg.get("Date", "")
            from_str = msg.get("From", "")
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        try:
                            body += part.get_payload(decode=True).decode(errors="replace")
                        except Exception:
                            body += str(part.get_payload())
            else:
                try:
                    body = msg.get_payload(decode=True).decode(errors="replace")
                except Exception:
                    body = str(msg.get_payload())
            results.append({"subject": subject, "date": date_str,
                             "from": from_str, "body": body})
        except Exception:
            continue
    return results


def is_relevant(msg: dict) -> bool:
    text = (msg["subject"] + " " + msg["body"]).lower()
    return any(kw in text for kw in ATTENDANCE_KEYWORDS)


def format_for_prompt(msgs: list[dict]) -> str:
    parts = []
    for i, m in enumerate(msgs, 1):
        body_snippet = m["body"][:1200].strip()
        parts.append(
            f"[Email {i}]\nDate: {m['date']}\nFrom: {m['from']}\n"
            f"Subject: {m['subject']}\n\n{body_snippet}\n"
        )
    return "\n---\n".join(parts)


def extract_from_emails(msgs: list[dict], year: int, list_name: str,
                        arch_year: int, month: str) -> list[dict]:
    if not msgs:
        return []

    archive_url = (f"https://lists.wikimedia.org/pipermail/"
                   f"{list_name}/{arch_year}-{month}.txt.gz")

    # Batch into chunks
    batches, current, current_len = [], [], 0
    for m in msgs:
        chunk = format_for_prompt([m])
        if current_len + len(chunk) > MAX_CHARS_PER_CALL and current:
            batches.append(current)
            current, current_len = [], 0
        current.append(m)
        current_len += len(chunk)
    if current:
        batches.append(current)

    results = []
    for i, batch in enumerate(batches):
        prompt = EMAIL_EXTRACTION_PROMPT.format(
            year=year,
            emails=format_for_prompt(batch),
        )
        raw = _query_mistral_with_retry(prompt, label=f"email batch {i+1}")
        if raw is None:
            continue
        figures = _parse_llm_json(raw)
        for f in figures:
            if f.get("figure_raw"):
                results.append(make_figure(
                    figure_raw=f.get("figure_raw", ""),
                    definition_as_reported=f.get("definition_as_reported", ""),
                    context=f.get("context", ""),
                    source_url=archive_url,
                    source_type="mailing_list",
                    author=f.get("author"),
                    author_role=f.get("author_role"),
                    extra={
                        "email_subject": f.get("email_subject", ""),
                        "email_date": f.get("email_date", ""),
                    },
                ))
        time.sleep(1.0)

    return results


def extract_from_post_conference_emails(
    year: int, conf_month: int
) -> list[dict]:
    """
    Download and scan the conference month + 2 months after for each list.
    These are the months most likely to contain post-conference wrap-up reports.
    """
    results = []
    LISTS = ["wikimania-l", "wikimedia-l"]

    # Month indices to scan: conference month and +1, +2 after
    periods = []
    for delta in range(3):   # conference month, +1, +2
        total_month = conf_month - 1 + delta   # 0-indexed
        y = year + total_month // 12
        m = total_month % 12
        periods.append((y, MONTHS[m]))

    for list_name in LISTS:
        for arch_year, month in periods:
            text = fetch_email_archive(list_name, arch_year, month)
            time.sleep(0.2)
            if not text:
                continue

            msgs = parse_messages(text)
            relevant = [m for m in msgs if is_relevant(m)]
            if not relevant:
                continue

            # Deduplicate
            seen, deduped = set(), []
            for m in relevant:
                key = (m["subject"][:60], m["date"][:16])
                if key not in seen:
                    seen.add(key)
                    deduped.append(m)

            print(f"    {list_name} {arch_year}-{month}: "
                  f"{len(deduped)} relevant emails")

            figs = extract_from_emails(deduped, year, list_name, arch_year, month)
            results.extend(figs)

    return results


# ---------------------------------------------------------------------------
# JSON parsing helpers
# ---------------------------------------------------------------------------
def _parse_llm_json(raw: str) -> list[dict]:
    raw = re.sub(r'^```(?:json)?\s*', '', raw.strip(), flags=re.MULTILINE)
    raw = re.sub(r'\s*```$', '', raw.strip(), flags=re.MULTILINE)
    m = re.search(r'\[.*\]', raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    # fallback: individual objects
    result = []
    for obj_m in re.finditer(r'\{[^{}]*\}', raw, re.DOTALL):
        try:
            result.append(json.loads(obj_m.group(0)))
        except json.JSONDecodeError:
            pass
    return result


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------
def deduplicate(figures: list[dict]) -> list[dict]:
    """
    Remove near-duplicate figures (same numeric value + same source URL).
    Keeps the entry with the most context.
    """
    seen: dict[tuple, dict] = {}
    for f in figures:
        key = (f.get("figure_numeric"), f.get("source_url", "")[:60])
        if key not in seen:
            seen[key] = f
        else:
            # Keep the one with more context
            if len(f.get("context", "")) > len(seen[key].get("context", "")):
                seen[key] = f
    return list(seen.values())


# ---------------------------------------------------------------------------
# Per-edition output
# ---------------------------------------------------------------------------
def load_or_create(year: int, location: str | None) -> dict:
    path = EDITIONS_DIR / f"wikimania_{year}.json"
    if path.exists():
        return json.loads(path.read_text())
    return {
        "edition": f"Wikimania {year}",
        "year": year,
        "location": location or "N/A",
        "notes": "Cancelled — not held" if location is None else "",
        "reported_figures": [],
    }


def save(data: dict) -> None:
    path = EDITIONS_DIR / f"wikimania_{data['year']}.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Main per-edition processor
# ---------------------------------------------------------------------------
def process_edition(year: int, location: str | None, conf_month: int | None) -> None:
    data = load_or_create(year, location)

    if location is None:
        # Cancelled
        save(data)
        print(f"  {year}: cancelled — skipping")
        return

    all_figures: list[dict] = []

    # 1. Wikipedia baseline
    wp_figures = seed_from_wikipedia(year)
    if wp_figures:
        print(f"    Wikipedia: {len(wp_figures)} figure(s)")
    all_figures.extend(wp_figures)

    # 2. Meta-wiki + conference wiki pages (new fetches)
    print(f"    Fetching meta-wiki / conference site pages...")
    wiki_figures = extract_from_metawiki(year)
    print(f"    Meta/conf wiki: {len(wiki_figures)} figure(s)")
    all_figures.extend(wiki_figures)

    # 3. Already-cached conference wiki pages from deadlines project
    cached_figures = extract_from_cached_wiki_pages(year)
    print(f"    Cached wiki pages: {len(cached_figures)} figure(s)")
    all_figures.extend(cached_figures)

    # 4. Email archives (post-conference months)
    if conf_month:
        print(f"    Scanning post-conference email archives...")
        email_figures = extract_from_post_conference_emails(year, conf_month)
        print(f"    Email archives: {len(email_figures)} figure(s)")
        all_figures.extend(email_figures)

    # Merge with existing (don't overwrite already-verified figures)
    existing_keys = {
        (f.get("figure_raw"), f.get("source_url", "")[:60])
        for f in data["reported_figures"]
        if f.get("verified")
    }
    for f in all_figures:
        key = (f.get("figure_raw"), f.get("source_url", "")[:60])
        if key not in existing_keys:
            data["reported_figures"].append(f)

    data["reported_figures"] = deduplicate(data["reported_figures"])

    save(data)
    print(f"  {year}: {len(data['reported_figures'])} total figure(s) saved")


# ---------------------------------------------------------------------------
# Combined output
# ---------------------------------------------------------------------------
def write_combined() -> None:
    all_data = []
    for path in sorted(EDITIONS_DIR.glob("wikimania_*.json")):
        if "all" in path.name:
            continue
        all_data.append(json.loads(path.read_text()))
    out = ATTENDEES_DIR / "attendance_all.json"
    out.write_text(json.dumps(all_data, indent=2, ensure_ascii=False))
    print(f"Combined JSON written:    {out}")
    write_markdown(all_data)


def write_markdown(all_data: list[dict]) -> None:
    """
    Write the human-readable Markdown report of all collected attendance figures.
    One section per edition; one row per reported figure.
    Includes source, definition-as-reported, context, author/role, and verification status.
    """
    lines = [
        "# Wikimania Attendance Figures — Collected Data",
        "",
        f"*Generated: {TODAY}*",
        "",
        "This document collects every reported attendance or participation figure "
        "for each Wikimania edition, preserving the exact definition used by each "
        "source. Figures are **not** normalised — different sources use different "
        "definitions (registered vs. checked-in vs. in-person vs. virtual etc.).",
        "",
        "Verification status: ✅ verified | ⬜ unverified",
        "",
        "---",
        "",
    ]

    source_type_labels = {
        "wikipedia":       "Wikipedia",
        "meta_wiki":       "Meta-wiki",
        "conference_wiki": "Conference wiki",
        "mailing_list":    "Mailing list",
        "blog":            "Wikimedia blog",
        "other":           "Other",
    }

    for edition in all_data:
        year     = edition["year"]
        location = edition.get("location", "N/A")
        notes    = edition.get("notes", "")
        figures  = edition.get("reported_figures", [])

        lines.append(f"## {year} — {location}")
        if notes:
            lines.append(f"*{notes}*")
        lines.append("")

        if not figures:
            lines.append("*No figures collected yet.*")
            lines.append("")
            lines.append("---")
            lines.append("")
            continue

        # Sort: wikipedia first, then meta_wiki, then others; within type by figure_numeric desc
        def sort_key(f):
            type_order = {"wikipedia": 0, "meta_wiki": 1, "conference_wiki": 2,
                          "mailing_list": 3, "blog": 4, "other": 5}
            return (type_order.get(f.get("source_type", "other"), 9),
                    -(f.get("figure_numeric") or 0))
        figures_sorted = sorted(figures, key=sort_key)

        for f in figures_sorted:
            verified_icon = "✅" if f.get("verified") else "⬜"
            figure_raw    = f.get("figure_raw", "?")
            defn          = f.get("definition_as_reported", "")
            context       = f.get("context", "").strip()
            source_url    = f.get("source_url", "")
            source_type   = source_type_labels.get(f.get("source_type", ""), "Other")
            author        = f.get("author")
            author_role   = f.get("author_role")
            email_subject = f.get("email_subject", "")
            retrieved     = f.get("retrieved", "")

            lines.append(f"### {figure_raw} — {defn}")
            lines.append("")
            if context:
                lines.append(f"> {context}")
                lines.append("")

            meta_parts = [f"**Source:** [{source_type}]({source_url})"]
            if author:
                author_str = author
                if author_role:
                    author_str += f" *({author_role})*"
                meta_parts.append(f"**Author:** {author_str}")
            if email_subject:
                meta_parts.append(f"**Subject:** {email_subject}")
            if retrieved:
                meta_parts.append(f"**Retrieved:** {retrieved}")
            meta_parts.append(f"**Status:** {verified_icon}")

            lines.append(" · ".join(meta_parts))
            lines.append("")

        lines.append("---")
        lines.append("")

    out = ATTENDEES_DIR / "attendance_report.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Markdown report written:  {out}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    target_years = None
    if len(sys.argv) > 1:
        target_years = [int(a) for a in sys.argv[1:]]

    editions_to_run = [
        (y, loc, cm) for y, loc, cm in EDITIONS
        if target_years is None or y in target_years
    ]

    print(f"Processing {len(editions_to_run)} edition(s)...\n")
    for year, location, conf_month in editions_to_run:
        print(f"Wikimania {year}:")
        process_edition(year, location, conf_month)
        print()
        time.sleep(0.5)

    write_combined()


if __name__ == "__main__":
    main()
