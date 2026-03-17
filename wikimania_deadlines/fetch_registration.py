"""
Phase 2 — Registration deadlines.
Fetches registration pages for every Wikimania edition and extracts:
  registration_open
  registration_earlybird_deadline
  registration_deadline
  registration_late_deadline

Updates editions/wikimania_YYYY.json in place.
"""

import json
import re
import time
import urllib.request
import urllib.parse
from pathlib import Path

HEADERS = {
    "User-Agent": "WikimaniaDeadlinesResearch/1.0 (https://github.com/lgelauff/wikimedia-analysis; research project)",
    "Accept": "application/json",
}

WM_API   = "https://wikimania.wikimedia.org/w/api.php"
META_API = "https://meta.wikimedia.org/w/api.php"

def wm_old(year):
    return f"https://wikimania{year}.wikimedia.org/w/api.php"

# Per-edition: list of (api_base, page_title) to try in order
REGISTRATION_SOURCES = {
    2026: [(WM_API,   "2026:Registration")],
    2025: [(WM_API,   "2025:Registration")],
    2024: [(WM_API,   "2024:Registration")],
    2023: [(WM_API,   "2023:Registration")],
    2022: [(WM_API,   "2022:Registration")],
    2021: [(WM_API,   "2021:Registration")],
    2020: [],  # cancelled
    2019: [(WM_API,   "2019:Registration")],
    2018: [(wm_old(2018), "Registration")],
    2017: [(wm_old(2017), "Registration")],
    2016: [(wm_old(2016), "Registration")],
    2015: [(wm_old(2015), "Registration")],
    2014: [(wm_old(2014), "Registration")],
    2013: [(wm_old(2013), "Registration")],
    2012: [(wm_old(2012), "Registration")],
    2011: [(wm_old(2011), "Registration")],
    2010: [(wm_old(2010), "Registration")],
    2009: [(wm_old(2009), "Registration")],
    2008: [(wm_old(2008), "Registration")],
    2007: [(wm_old(2007), "Registration")],
    2006: [(wm_old(2006), "Registration")],
    2005: [(wm_old(2005), "Registration"),
           (META_API, "Wikimania_2005/Registration")],
}

DEADLINE_KEYWORDS = {
    "registration_open": [
        "early registration starts", "registration starts",
        "registration opens", "registration is now open",
        "open for registration", "opens on", "open on",
        "registration open",
    ],
    "registration_earlybird_deadline": [
        "early bird pricing ends", "early bird pricing ended",
        "early bird rate ends", "early bird deadline",
        "early bird registration", "early registration",
        "earlybird",
    ],
    "registration_deadline": [
        "online registration deadline", "online registration ends",
        "online registration ended", "online registration closes",
        "registration deadline", "register by",
        "registration ends", "registration closes",
    ],
    "registration_late_deadline": [
        "late registration", "on-site registration deadline",
        "onsite registration deadline",
    ],
}

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}
MON_PAT = "|".join(MONTHS.keys())


def api_fetch(base, title):
    params = urllib.parse.urlencode({
        "action": "query", "titles": title,
        "prop": "revisions", "rvprop": "content",
        "format": "json", "formatversion": "2", "redirects": "1",
    })
    req = urllib.request.Request(f"{base}?{params}", headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        pages = data["query"]["pages"]
        if pages and "revisions" in pages[0]:
            return pages[0]["revisions"][0]["content"]
    except Exception as e:
        print(f"    API error ({base} / {title}): {e}")
    return None


def make_api_url(base, title):
    params = urllib.parse.urlencode({
        "action": "query", "titles": title,
        "prop": "revisions", "rvprop": "content",
        "format": "json", "formatversion": "2", "redirects": "1",
    })
    return f"{base}?{params}"


def extract_date(text, context_year):
    text = text.replace("&ndash;", "–").replace("&mdash;", "—")

    def fmt(yr, m, d):
        return f"{int(yr)}-{int(m):02d}-{int(d):02d}"

    # ISO
    p = re.search(r'\b(\d{4})-(\d{2})-(\d{2})\b', text)
    if p:
        return fmt(p.group(1), p.group(2), p.group(3)), "confirmed", p.group(0)

    # "Month D[th], YYYY"
    p = re.search(rf'({MON_PAT})\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})',
                  text, re.IGNORECASE)
    if p:
        return fmt(p.group(3), MONTHS[p.group(1).lower()], p.group(2)), \
               "confirmed", p.group(0)

    # "D[th] Month YYYY"
    p = re.search(rf'(\d{{1,2}})(?:st|nd|rd|th)?\s+({MON_PAT})\s+(\d{{4}})',
                  text, re.IGNORECASE)
    if p:
        return fmt(p.group(3), MONTHS[p.group(2).lower()], p.group(1)), \
               "confirmed", p.group(0)

    # "Month D" without year → use context_year
    p = re.search(rf'({MON_PAT})\s+(\d{{1,2}})(?:st|nd|rd|th)?(?!\s*\d{{3,4}})',
                  text, re.IGNORECASE)
    if p:
        return fmt(context_year, MONTHS[p.group(1).lower()], p.group(2)), \
               "approximate", p.group(0)

    return None, "unknown", None


def strip_wiki_markup(text):
    text = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]*)\]\]', r'\1', text)
    text = re.sub(r'\{\{[^}]*\}\}', ' ', text)
    text = re.sub(r"'''?", '', text)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'<!--T:\d+-->', '', text)
    return text


def classify_line(line, context_year):
    clean = strip_wiki_markup(line).lower()
    results = []
    for dtype, keywords in DEADLINE_KEYWORDS.items():
        if any(kw in clean for kw in keywords):
            date, conf, raw = extract_date(clean, context_year)
            if date:
                results.append((dtype, date, conf, raw, line.strip()))
    return results


def parse_registration_page(wikitext, year, source_url):
    found = {}

    for line in wikitext.splitlines():
        for dtype, date, conf, raw, orig_line in classify_line(line, year):
            if dtype in found and found[dtype]["date_confidence"] == "confirmed":
                continue
            found[dtype] = {
                "type": dtype,
                "date": date,
                "date_confidence": conf,
                "notes": f"Parsed from: '{orig_line[:120]}'",
                "sources": [{
                    "url": source_url,
                    "source_type": classify_source_type(source_url),
                    "verified": False,
                    "verified_date": None,
                    "verified_text_found": None,
                }],
            }

    return list(found.values())


def classify_source_type(url):
    if "meta.wikimedia.org" in url:
        return "meta_wiki"
    if "wikimania.wikimedia.org" in url or "wikimania20" in url:
        return "conference_site"
    return "other"


def main():
    editions_dir = Path(__file__).parent / "editions"

    for year in range(2005, 2027):
        json_path = editions_dir / f"wikimania_{year}.json"
        if not json_path.exists():
            print(f"{year}: JSON file missing, skipping")
            continue

        data = json.loads(json_path.read_text())
        sources = REGISTRATION_SOURCES.get(year, [])

        print(f"\nWikimania {year}...", end=" ", flush=True)

        if not sources:
            print("no sources (cancelled or not defined)")
            continue

        deadlines = []
        used_source = None

        for base, title in sources:
            wikitext = api_fetch(base, title)
            time.sleep(0.4)
            if wikitext:
                api_url = make_api_url(base, title)
                deadlines = parse_registration_page(wikitext, year, api_url)
                used_source = f"{base} / {title}"
                break

        if not deadlines:
            print(f"no deadlines parsed (source tried: {used_source})")
        else:
            types_found = [d["type"] for d in deadlines]
            print(f"found: {types_found}")

        data["buckets"]["registration"]["deadlines"] = deadlines
        json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    print("\n\nDone.")


if __name__ == "__main__":
    main()
