"""
Phase 2b — Wiki revision history (rendered HTML).

For each Wikimania program page, fetches the wiki revision that existed
approximately 3 months before the conference (target: May 1 of conference year).
Uses action=parse to get rendered HTML — avoids template-parsing issues.

Merges results into editions/wikimania_YYYY.json:
  - never overwrites confirmed or not_applicable
  - upgrades approximate → confirmed when new data is better
"""

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
from fetch_program import PROGRAM_SOURCES, classify_source, classify_line
from cache import WIKI_DIR, HEADERS

EDITIONS_DIR = Path(__file__).parent / "editions"

TARGET_MONTH = 5
TARGET_DAY   = 1

# Per-year override when default target predates the page creation
TARGET_DATE_OVERRIDES = {
    2011: "2011-07-01",  # Call for Participation created May 21; conference Aug 4
    2021: "2021-07-15",  # page created June 6 2021; conference Aug 13
}

# Per-year page overrides (e.g. redirect targets)
PROGRAM_SOURCE_OVERRIDES = {
    2011: [("https://wikimania2011.wikimedia.org/w/api.php", "Call_for_Participation")],
}


# ---------------------------------------------------------------------------
# HTML stripping
# ---------------------------------------------------------------------------

class _HTMLTextExtractor(html.parser.HTMLParser):
    """Convert HTML to plain text, inserting newlines at block-level tags."""
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


def html_to_text(raw_html: str) -> str:
    p = _HTMLTextExtractor()
    p.feed(raw_html)
    return p.get_text()


# ---------------------------------------------------------------------------
# Two-step fetch: revision ID → rendered HTML (cached)
# ---------------------------------------------------------------------------

def _cache_path(base: str, title: str, target_date: str) -> Path:
    host = urllib.parse.urlparse(base).netloc.replace(".", "_")
    slug = urllib.parse.quote(title, safe="").replace("%", "_")[:60]
    return WIKI_DIR / f"{host}__{slug}__html_{target_date}.json"


def _api(base: str, params: dict) -> dict | None:
    req = urllib.request.Request(
        f"{base}?{urllib.parse.urlencode(params)}", headers=HEADERS
    )
    try:
        with urllib.request.urlopen(req, timeout=20, context=SSL_CTX) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"    API error ({base}): {e}")
        return None


def fetch_revision_html(base: str, title: str, target_date: str) -> tuple[str | None, str | None, int | None]:
    """
    Return (plain_text, timestamp, revid) for the last revision of `title`
    that existed before `target_date`.  Results are cached locally.
    """
    WIKI_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = _cache_path(base, title, target_date)

    if cache_path.exists():
        c = json.loads(cache_path.read_text())
        return c.get("text"), c.get("timestamp"), c.get("revid")

    # Step 1: find the revision ID
    data = _api(base, {
        "action": "query", "titles": title,
        "prop": "revisions", "rvprop": "ids|timestamp",
        "rvlimit": "1", "rvdir": "older",
        "rvstart": f"{target_date}T00:00:00Z",
        "format": "json", "formatversion": "2", "redirects": "1",
    })
    if not data:
        return None, None, None

    pages = data.get("query", {}).get("pages", [])
    if not pages or "revisions" not in pages[0]:
        cache_path.write_text(json.dumps({"text": None, "timestamp": None, "revid": None}))
        return None, None, None

    rev = pages[0]["revisions"][0]
    revid     = rev["revid"]
    timestamp = rev["timestamp"]
    time.sleep(0.3)

    # Step 2: fetch rendered HTML for that revision
    parse_data = _api(base, {
        "action": "parse", "oldid": revid,
        "prop": "text", "disablelimitreport": "1",
        "format": "json",
    })
    if not parse_data:
        return None, timestamp, revid

    raw_html = parse_data.get("parse", {}).get("text", {}).get("*", "")
    plain = html_to_text(raw_html)

    cache_path.write_text(json.dumps(
        {"text": plain, "timestamp": timestamp, "revid": revid}, ensure_ascii=False
    ))
    return plain, timestamp, revid


def source_url(base: str, revid: int) -> str:
    host = urllib.parse.urlparse(base).netloc.replace("/w/api.php", "")
    return f"https://{host}/w/index.php?oldid={revid}"


# ---------------------------------------------------------------------------
# Parse plain text → deadlines  (reuses classify_line from fetch_program)
# ---------------------------------------------------------------------------

def parse_plain_text(text: str, year: int, src_url: str, timestamp: str) -> list[dict]:
    found = {}
    for line in text.splitlines():
        for dtype, date, conf, raw, orig in classify_line(line, year):
            if dtype in found and found[dtype]["date_confidence"] == "confirmed":
                continue
            found[dtype] = {
                "type": dtype,
                "date": date,
                "date_confidence": conf,
                "notes": f"[rev {timestamp}] Parsed from: '{orig[:120]}'",
                "sources": [{
                    "url": src_url,
                    "source_type": classify_source(base_from_url(src_url)),
                    "verified": False,
                    "verified_date": None,
                    "verified_text_found": None,
                }],
            }
    return list(found.values())


def base_from_url(url: str) -> str:
    p = urllib.parse.urlparse(url)
    return f"{p.scheme}://{p.netloc}/w/api.php"


# ---------------------------------------------------------------------------
# Merge
# ---------------------------------------------------------------------------

def merge_into_program(data: dict, new_deadlines: list[dict]) -> int:
    bucket   = data["buckets"]["program"]["deadlines"]
    existing = {d["type"]: d for d in bucket}
    updated  = 0

    for nd in new_deadlines:
        dtype    = nd["type"]
        cur      = existing.get(dtype)
        cur_conf = cur.get("date_confidence") if cur else None
        cur_date = cur.get("date")            if cur else None

        if cur_conf == "not_applicable":
            continue
        if cur_conf == "confirmed" and cur_date:
            continue
        if cur_conf == "approximate" and cur_date and nd["date_confidence"] != "confirmed":
            continue

        replaced = False
        for i, d in enumerate(bucket):
            if d["type"] == dtype:
                bucket[i] = nd
                replaced = True
                break
        if not replaced:
            bucket.append(nd)

        existing[dtype] = nd
        updated += 1

    return updated


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def process_year(year: int) -> None:
    json_path = EDITIONS_DIR / f"wikimania_{year}.json"
    if not json_path.exists():
        print(f"  {year}: JSON file missing, skipping")
        return

    sources = PROGRAM_SOURCE_OVERRIDES.get(year) or PROGRAM_SOURCES.get(year, [])
    if not sources:
        print(f"  {year}: no program sources defined")
        return

    data        = json.loads(json_path.read_text())
    target_date = TARGET_DATE_OVERRIDES.get(year, f"{year}-{TARGET_MONTH:02d}-{TARGET_DAY:02d}")

    for base, title in sources:
        text, timestamp, revid = fetch_revision_html(base, title, target_date)
        time.sleep(0.4)

        if not text:
            print(f"  {year}: no revision found before {target_date} for {title}")
            continue

        src = source_url(base, revid)
        deadlines = parse_plain_text(text, year, src, timestamp)

        n = merge_into_program(data, deadlines)

        if deadlines:
            print(f"  {year}: rev {timestamp} (id {revid}) → "
                  f"{[d['type'] for d in deadlines]}, {n} updated")
        else:
            print(f"  {year}: rev {timestamp} (id {revid}) → no deadlines parsed")

        break

    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def main():
    target_years = None
    if len(sys.argv) > 1:
        target_years = [int(a) for a in sys.argv[1:]]

    years = target_years or list(range(2005, 2027))
    years = [y for y in years if y != 2020]

    print("Fetching historical revisions (rendered HTML, target: May 1)...\n")
    for year in years:
        process_year(year)

    print("\nDone.")


if __name__ == "__main__":
    main()
