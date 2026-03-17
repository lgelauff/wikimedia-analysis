"""
Phase 3 — Blind validation via Mistral.

For each deadline entry with verified=false:
  1. Fetch the source page/archive content.
  2. Send to Mistral (NOT the stored date) and extract a date.
  3a. Match  → verified=true.
  3b. Not found (None) → leave unverified, skip.
  3c. Date disagreement → binary search wiki revision history:
       Try revisions at 3 months, 5 months, 1 month before conference.
       If any historical revision confirms the stored date → verified=true.
       If revisions consistently point to a different date → update stored
       date and mark verified=true with a note.

Conference start/end mismatches are noted but not auto-corrected (pre-conf
days vary by edition).

Run:  python validate_deadlines.py [year ...]
      python validate_deadlines.py          # all editions
"""

import email as _email
import gzip
import html
import html.parser
import json
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import certifi

SSL_CTX = ssl.create_default_context(cafile=certifi.where())

sys.path.insert(0, str(Path(__file__).parent))
from cache import WIKI_DIR, EMAIL_DIR, HEADERS
from fetch_email_deadlines import parse_messages, is_relevant, format_for_prompt
from fetch_revision_history import fetch_revision_html, PROGRAM_SOURCE_OVERRIDES
from fetch_program import PROGRAM_SOURCES
from llm import query_mistral

EDITIONS_DIR = Path(__file__).parent / "editions"
CHECKPOINT_FILE = Path("/tmp/wikimania_validate_checkpoint.json")

# Months before August conference to try in binary search (descending)
BINARY_SEARCH_OFFSETS = [5, 3, 1]   # months before August = March, May, July

VALIDATION_SYSTEM = (
    "You are a precise date extraction assistant. "
    "Extract only dates that are explicitly stated in the text. "
    "Do not infer, guess, or use context. Return valid JSON only."
)

VALIDATION_PROMPT = """\
Below is content from a Wikimania {year} source page/archive.

Task: find the date for this specific deadline type:
  {dtype}

Rules:
- Only return a date that is explicitly written in the text.
- Prefer the most specific date (exact day over month-only).
- If no year is given for a date, assume {year}.
- If you find the date, return the exact phrase where you found it.
- If not found, return null.

Return JSON only, exactly this shape:
{{
  "date": "<YYYY-MM-DD if exact, YYYY-MM if only month known, null if not found>",
  "evidence": "<the exact phrase or sentence where you found the date, max 200 chars, or null>"
}}

--- CONTENT ---
{content}
--- END ---

JSON:"""


# ---------------------------------------------------------------------------
# HTML stripping
# ---------------------------------------------------------------------------

class _HTMLStripper(html.parser.HTMLParser):
    BLOCK = {"p", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6",
             "div", "br", "dt", "dd", "th", "td"}
    def __init__(self):
        super().__init__()
        self._parts = []
    def handle_starttag(self, tag, attrs):
        if tag in self.BLOCK:
            self._parts.append("\n")
    def handle_data(self, data):
        self._parts.append(data)
    def handle_entityref(self, name):
        self._parts.append(html.unescape(f"&{name};"))
    def handle_charref(self, name):
        self._parts.append(html.unescape(f"&#{name};"))
    def get_text(self):
        return "".join(self._parts)


def _html_to_text(raw: str) -> str:
    p = _HTMLStripper()
    p.feed(raw)
    return p.get_text()


# ---------------------------------------------------------------------------
# Content fetchers
# ---------------------------------------------------------------------------

def _fetch_url(url: str) -> bytes | None:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20, context=SSL_CTX) as r:
            return r.read()
    except Exception as e:
        print(f"    fetch error ({url[:80]}): {e}")
        return None


def _wiki_api_to_html(api_url: str) -> str | None:
    """Fetch current rendered HTML from an action=query API URL."""
    parsed = urllib.parse.urlparse(api_url)
    base   = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    params = dict(urllib.parse.parse_qsl(parsed.query))
    title  = params.get("titles", "")

    q_params = urllib.parse.urlencode({
        "action": "query", "titles": title,
        "prop": "revisions", "rvprop": "ids",
        "rvlimit": "1", "format": "json", "formatversion": "2", "redirects": "1",
    })
    data = _fetch_url(f"{base}?{q_params}")
    if not data:
        return None
    j = json.loads(data)
    pages = j.get("query", {}).get("pages", [])
    if not pages or "revisions" not in pages[0]:
        return None
    revid = pages[0]["revisions"][0]["revid"]
    time.sleep(0.3)

    p_params = urllib.parse.urlencode({
        "action": "parse", "oldid": revid,
        "prop": "text", "disablelimitreport": "1", "format": "json",
    })
    data2 = _fetch_url(f"{base}?{p_params}")
    if not data2:
        return None
    j2 = json.loads(data2)
    raw_html = j2.get("parse", {}).get("text", {}).get("*", "")
    return _html_to_text(raw_html)


def _oldid_url_to_html(url: str) -> str | None:
    """Fetch rendered HTML for a ?oldid=NNN URL."""
    parsed = urllib.parse.urlparse(url)
    base   = f"{parsed.scheme}://{parsed.netloc}/w/api.php"
    params = dict(urllib.parse.parse_qsl(parsed.query))
    oldid  = params.get("oldid")
    if not oldid:
        return None
    p_params = urllib.parse.urlencode({
        "action": "parse", "oldid": oldid,
        "prop": "text", "disablelimitreport": "1", "format": "json",
    })
    data = _fetch_url(f"{base}?{p_params}")
    if not data:
        return None
    j = json.loads(data)
    raw_html = j.get("parse", {}).get("text", {}).get("*", "")
    return _html_to_text(raw_html)


def _mailing_list_text(url: str) -> str | None:
    """Return filtered relevant emails from a mbox archive."""
    m = re.search(r'/pipermail/([^/]+)/(\d{4})-(\w+)\.txt', url)
    if not m:
        return None
    list_name, yr, month = m.group(1), m.group(2), m.group(3)
    cache = EMAIL_DIR / f"{list_name}_{yr}-{month}.txt"

    if cache.exists():
        raw = cache.read_text(errors="replace")
    else:
        gz_url = url if url.endswith(".gz") else url + ".gz"
        data = _fetch_url(gz_url)
        if not data:
            return None
        try:
            raw = gzip.decompress(data).decode("utf-8", errors="replace")
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(raw)
        except Exception:
            return None

    msgs     = parse_messages(raw)
    relevant = [msg for msg in msgs if is_relevant(msg)]
    if not relevant:
        return raw[:15_000]
    return format_for_prompt(relevant)


def get_source_text(source: dict) -> str | None:
    url   = source.get("url", "")
    stype = source.get("source_type", "")

    if stype == "mailing_list":
        return _mailing_list_text(url)
    if "oldid=" in url and "action" not in url:
        return _oldid_url_to_html(url)
    if "action=query" in url:
        return _wiki_api_to_html(url)
    return None


# ---------------------------------------------------------------------------
# Binary search on revision history
# ---------------------------------------------------------------------------

def _wiki_base_and_title(source: dict, year: int) -> tuple[str, str] | None:
    """Extract (api_base, page_title) from a wiki source, or None."""
    url   = source.get("url", "")
    stype = source.get("source_type", "")

    if stype == "mailing_list":
        return None   # no wiki revision for email sources

    # First: check per-year overrides (same logic as fetch_revision_history)
    override = PROGRAM_SOURCE_OVERRIDES.get(year)
    if override:
        return override[0]

    # From action=query URL
    if "action=query" in url:
        parsed = urllib.parse.urlparse(url)
        base   = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        title  = dict(urllib.parse.parse_qsl(parsed.query)).get("titles", "")
        if title:
            return base, title

    # From ?oldid= URL — derive base, need page title from API
    if "oldid=" in url and "action" not in url:
        parsed = urllib.parse.urlparse(url)
        base   = f"{parsed.scheme}://{parsed.netloc}/w/api.php"
        oldid  = dict(urllib.parse.parse_qsl(parsed.query)).get("oldid")
        if oldid:
            data = _fetch_url(f"{base}?action=query&revids={oldid}&format=json&formatversion=2")
            if data:
                j = json.loads(data)
                pages = j.get("query", {}).get("pages", [])
                if pages:
                    return base, pages[0].get("title", "")

    # Fall back to PROGRAM_SOURCES
    sources = PROGRAM_SOURCES.get(year, [])
    if sources:
        return sources[0]

    return None


def binary_search_revision(base: str, title: str, year: int, dtype: str
                            ) -> tuple[str | None, str | None, str | None]:
    """
    Try revisions at several points before the conference.
    Returns (date_found, evidence, revision_timestamp) from the first revision
    where Mistral finds a date, or (None, None, None).
    """
    # Conference month is roughly August; offsets are months before that
    for offset in BINARY_SEARCH_OFFSETS:
        month = 8 - offset          # e.g. offset=5 → month=3 (March)
        yr    = year
        if month <= 0:
            month += 12
            yr -= 1
        target = f"{yr}-{month:02d}-01"

        text, timestamp, revid = fetch_revision_html(base, title, target)
        time.sleep(0.4)
        if not text:
            continue

        date_found, evidence = validate_with_mistral(text, dtype, year)
        time.sleep(0.5)

        if date_found:
            print(f"    [bisect rev {timestamp} target={target}] found={date_found}")
            return date_found, evidence, timestamp

    return None, None, None


# ---------------------------------------------------------------------------
# Mistral extraction
# ---------------------------------------------------------------------------

def validate_with_mistral(content: str, dtype: str, year: int
                           ) -> tuple[str | None, str | None]:
    snippet = content[:15_000]
    prompt  = VALIDATION_PROMPT.format(year=year, dtype=dtype, content=snippet)
    try:
        raw = query_mistral(prompt, system=VALIDATION_SYSTEM)
        raw = re.sub(r'^```(?:json)?\s*', '', raw.strip(), flags=re.MULTILINE)
        raw = re.sub(r'\s*```$',           '', raw.strip(), flags=re.MULTILINE)
        m   = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            obj = json.loads(m.group(0))
            return obj.get("date"), obj.get("evidence")
    except Exception as e:
        print(f"    Mistral error: {e}")
    return None, None


# ---------------------------------------------------------------------------
# Date comparison
# ---------------------------------------------------------------------------

def dates_match(stored: str, found: str) -> bool:
    if not stored or not found:
        return False
    s = str(stored).strip()[:10]
    f = str(found).strip()[:10]
    if len(f) == 7:
        return s[:7] == f
    if len(s) == 7:
        return s == f[:7]
    return s == f


CONFERENCE_DATE_TYPES = {"conference_start", "conference_end"}


# ---------------------------------------------------------------------------
# Main validation loop
# ---------------------------------------------------------------------------

def _load_checkpoint() -> set:
    """Return set of years already fully validated."""
    if CHECKPOINT_FILE.exists():
        try:
            return set(json.loads(CHECKPOINT_FILE.read_text()).get("completed", []))
        except Exception:
            pass
    return set()


def _save_checkpoint(completed: set) -> None:
    CHECKPOINT_FILE.write_text(json.dumps({"completed": sorted(completed)}, indent=2))


def process_edition(year: int) -> None:
    json_path = EDITIONS_DIR / f"wikimania_{year}.json"
    if not json_path.exists():
        return

    data    = json.loads(json_path.read_text())
    changed = 0

    for bname, bucket in data["buckets"].items():
        for d in bucket.get("deadlines", []):
            dtype       = d["type"]
            stored_date = d.get("date")
            conf        = d.get("date_confidence")

            if not stored_date or conf in ("not_applicable", "unknown"):
                continue

            for source in d.get("sources", []):
                if source.get("verified"):
                    continue

                print(f"  [{year}] {dtype} ({stored_date}) — fetching source...", flush=True)
                content = get_source_text(source)
                time.sleep(0.3)

                if not content:
                    print(f"    could not fetch source, skipping")
                    continue

                found_date, evidence = validate_with_mistral(content, dtype, year)
                time.sleep(0.5)

                if dates_match(stored_date, found_date):
                    # ── PASS on primary source ──────────────────────────────
                    source["verified"]            = True
                    source["verified_date"]       = found_date
                    source["verified_text_found"] = (evidence or "")[:300]
                    changed += 1
                    print(f"    stored={stored_date}  found={found_date}  → PASS ✓")

                elif found_date is None:
                    # ── Not found in primary source — leave unverified ──────
                    print(f"    not found in source — skipping")

                else:
                    # ── Date disagreement — binary search revisions ─────────
                    print(f"    stored={stored_date}  found={found_date}  → MISMATCH — trying revision history...")

                    # Conference date mismatches: note but don't auto-correct
                    if dtype in CONFERENCE_DATE_TYPES:
                        source["verified"]            = False
                        source["verified_date"]       = found_date
                        source["verified_text_found"] = (
                            f"[conf-date-discrepancy] {(evidence or '')[:250]}"
                        )
                        changed += 1
                        print(f"    Conference date discrepancy noted (pre-conf days may differ)")
                        json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
                        continue

                    bt = _wiki_base_and_title(source, year)
                    if not bt:
                        # No wiki source to search — record disagreement
                        source["verified"]            = False
                        source["verified_date"]       = found_date
                        source["verified_text_found"] = (evidence or "")[:300]
                        changed += 1
                        print(f"    No wiki source for bisect — disagreement recorded")
                        json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
                        continue

                    base, title = bt
                    bisect_date, bisect_ev, bisect_ts = binary_search_revision(
                        base, title, year, dtype
                    )

                    if dates_match(stored_date, bisect_date):
                        # Historical revision confirms our stored date
                        source["verified"]            = True
                        source["verified_date"]       = bisect_date
                        source["verified_text_found"] = (
                            f"[rev {bisect_ts}] {(bisect_ev or '')[:250]}"
                        )
                        changed += 1
                        print(f"    Bisect confirms stored={stored_date} ✓ (rev {bisect_ts})")

                    elif dates_match(found_date, bisect_date):
                        # Historical revision agrees with primary source — update stored date
                        old_date       = d["date"]
                        d["date"]      = bisect_date
                        d["notes"]     = (d.get("notes", "") +
                                          f" [corrected {old_date}→{bisect_date} via bisect rev {bisect_ts}]")
                        source["verified"]            = True
                        source["verified_date"]       = bisect_date
                        source["verified_text_found"] = (
                            f"[rev {bisect_ts}] {(bisect_ev or '')[:250]}"
                        )
                        changed += 1
                        print(f"    Bisect confirms found={bisect_date} → stored date updated ✓")

                    elif bisect_date:
                        # Bisect found a third date — record all, flag for review
                        source["verified"]            = False
                        source["verified_date"]       = bisect_date
                        source["verified_text_found"] = (
                            f"[REVIEW: stored={stored_date} primary={found_date} bisect={bisect_date}]"
                            f" {(bisect_ev or '')[:200]}"
                        )
                        changed += 1
                        print(f"    Three-way discrepancy — flagged for review")

                    else:
                        # Bisect also found nothing — record primary mismatch
                        source["verified"]            = False
                        source["verified_date"]       = found_date
                        source["verified_text_found"] = (evidence or "")[:300]
                        changed += 1
                        print(f"    Bisect inconclusive — disagreement recorded")

                # Write after every processed source so progress survives interruption
                if changed:
                    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    if changed:
        print(f"  {year}: {changed} sources processed.\n")
    else:
        print(f"  {year}: nothing to validate.\n")


def main():
    explicit_years = [int(a) for a in sys.argv[1:]]
    target_years   = explicit_years or list(range(2005, 2027))
    target_years   = [y for y in target_years if y != 2020]

    completed = _load_checkpoint()
    if completed and not explicit_years:
        skipped = sorted(y for y in target_years if y in completed)
        if skipped:
            print(f"Resuming — skipping already-completed years: {skipped}")
        target_years = [y for y in target_years if y not in completed]

    if not target_years:
        print("All editions already validated (checkpoint). Delete /tmp/wikimania_validate_checkpoint.json to re-run.")
        return

    print(f"Validating {len(target_years)} editions...\n")
    for year in target_years:
        print(f"Wikimania {year}:")
        process_edition(year)
        completed.add(year)
        _save_checkpoint(completed)

    print("Done.")


if __name__ == "__main__":
    main()
