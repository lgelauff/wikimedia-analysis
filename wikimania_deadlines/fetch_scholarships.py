"""
Phase 2 — Scholarship deadlines.
Fetches scholarship pages for every Wikimania edition and extracts:
  scholarship_applications_open
  scholarship_deadline
  scholarship_deadline_extended
  scholarship_results_notification  (first wave only)
  scholarship_acceptance_confirmation

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

# Per-edition: list of (api_base, page_title) to try in order
SCHOLARSHIP_SOURCES = {
    2025: [(WM_API,   "2025:Scholarships")],
    2024: [(WM_API,   "2024:Scholarships")],
    2023: [(WM_API,   "2023:Scholarships")],
    2022: [(WM_API,   "2022:Scholarships")],
    2021: [(WM_API,   "2021:Scholarships")],
    2020: [],  # cancelled
    2026: [(WM_API, "2026:Scholarships")],  # may not be published yet
    2019: [(WM_API,   "2019:Scholarships")],
    2018: [("https://wikimania2018.wikimedia.org/w/api.php", "Scholarships")],
    2017: [("https://wikimania2017.wikimedia.org/w/api.php", "Scholarships")],
    2016: [("https://wikimania2016.wikimedia.org/w/api.php", "Scholarships")],
    2015: [("https://wikimania2015.wikimedia.org/w/api.php", "Scholarships")],
    2014: [("https://wikimania2014.wikimedia.org/w/api.php", "Scholarships")],
    2013: [("https://wikimania2013.wikimedia.org/w/api.php", "Scholarships")],
    2012: [("https://wikimania2012.wikimedia.org/w/api.php", "Scholarships")],
    2011: [("https://wikimania2011.wikimedia.org/w/api.php", "Scholarships")],
    2010: [("https://wikimania2010.wikimedia.org/w/api.php", "Scholarships")],
    2009: [("https://wikimania2009.wikimedia.org/w/api.php", "Scholarships")],
    2008: [("https://wikimania2008.wikimedia.org/w/api.php", "Scholarships")],
    2007: [("https://wikimania2007.wikimedia.org/w/api.php", "Scholarships"),
           (META_API, "Wikimania_2007/Scholarships")],
    2006: [("https://wikimania2006.wikimedia.org/w/api.php", "Scholarships"),
           (META_API, "Wikimania_2006/Scholarships")],
    2005: [("https://wikimania2005.wikimedia.org/w/api.php", "Scholarships"),
           (META_API, "Wikimania_2005/Scholarships")],
}


# ---------------------------------------------------------------------------
# Keyword rules: each entry maps a deadline_type to a list of keyword phrases.
# A line/bullet matches if it contains at least one keyword AND a parseable date.
# ---------------------------------------------------------------------------
DEADLINE_KEYWORDS = {
    "scholarship_applications_open": [
        "applications open", "application open", "applications opens",
        "scholarship opens", "open for applications", "opens on", "open on",
        "applications phase opens",
    ],
    "scholarship_deadline": [
        "deadline for applying", "deadline to apply", "application deadline",
        "applications close", "applications closed", "apply by",
        "closes on", "closes december", "closes october", "closes november",
        "closes january", "closes february", "closes march",
        "applications phase closes",
        "received by", "must be received", "be received by",
        "submitted by", "send it to",
        "original deadline",  # 2007-style: "original deadline was April 1"
        # Note: "close" and "closed" alone are intentionally excluded —
        # too generic; they fire on "now closed. All applicants were notified on DATE"
    ],
    "scholarship_deadline_extended": [
        "new deadline", "revised deadline",
        "deadline is extended", "deadline extended",
        "extended deadline",
    ],
    "scholarship_results_notification": [
        "notified", "notification", "notify", "decisions",
        "applicants are notified", "outcome", "results announced",
        "get back to every applicant", "sending out e-mails",
        "completed by",  # 2007: "selection will be completed by April 22"
        "selection of scholarship recipients",
    ],
    "scholarship_acceptance_confirmation": [
        "confirm", "confirmation", "accept the scholarship", "accepting the scholarship",
        "acceptance deadline",
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


def extract_date(text, context_year):
    """
    Try to extract a single date from a short text snippet.
    Returns (date_str, confidence, raw_match) or (None, 'unknown', None).
    """
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
    """Remove common wiki markup to make keyword matching cleaner."""
    text = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]*)\]\]', r'\1', text)   # [[link|text]]
    text = re.sub(r'\{\{[^}]*\}\}', ' ', text)                        # templates
    text = re.sub(r"'''?", '', text)                                   # bold/italic
    text = re.sub(r'<[^>]+>', ' ', text)                              # HTML tags
    text = re.sub(r'<translate>|</translate>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<!--T:\d+-->', '', text)
    text = re.sub(r'<tvar[^>]*>|</tvar>', '', text, flags=re.IGNORECASE)
    return text


def classify_line(line, context_year):
    """
    Given a text line, return list of (deadline_type, date, confidence, raw_match, raw_line).
    A line can match multiple types (e.g. an extension notice).
    """
    clean = strip_wiki_markup(line).lower()
    results = []
    for dtype, keywords in DEADLINE_KEYWORDS.items():
        if any(kw in clean for kw in keywords):
            date, conf, raw = extract_date(clean, context_year)
            if date:
                results.append((dtype, date, conf, raw, line.strip()))
    return results


def parse_scholarship_page(wikitext, year, source_url):
    """
    Parse a scholarship page and return a list of deadline dicts.
    """
    found = {}  # deadline_type → best match dict

    for line in wikitext.splitlines():
        for dtype, date, conf, raw, orig_line in classify_line(line, year):
            # Keep the entry with best confidence; skip if already confirmed
            if dtype in found and found[dtype]["date_confidence"] == "confirmed":
                continue
            # Skip notification/confirmation if date doesn't look plausible
            # (e.g. far outside the Wikimania prep window)
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
    if "lists.wikimedia.org" in url:
        return "mailing_list"
    if "blog.wikimedia.org" in url:
        return "blog"
    return "other"


def make_api_url(base, title):
    params = urllib.parse.urlencode({
        "action": "query", "titles": title,
        "prop": "revisions", "rvprop": "content",
        "format": "json", "formatversion": "2", "redirects": "1",
    })
    return f"{base}?{params}"


def main():
    editions_dir = Path(__file__).parent / "editions"

    for year in range(2005, 2027):
        json_path = editions_dir / f"wikimania_{year}.json"
        if not json_path.exists():
            print(f"{year}: JSON file missing, skipping")
            continue

        data = json.loads(json_path.read_text())
        sources = SCHOLARSHIP_SOURCES.get(year, [])

        print(f"\nWikimania {year}...", end=" ", flush=True)

        if not sources:
            print("no sources (cancelled or not defined)")
            continue

        # 2021: Wikimania was virtual; only affiliate stipends were offered,
        # not individual travel scholarships. Mark all individual deadline types
        # as not_applicable.
        if year == 2021:
            na_deadlines = [
                {
                    "type": t,
                    "date": None,
                    "date_confidence": "not_applicable",
                    "notes": (
                        "Wikimania 2021 was virtual (COVID). Individual travel scholarships "
                        "were not offered; only affiliate stipends. No individual deadline applicable."
                    ),
                    "sources": [],
                }
                for t in [
                    "scholarship_applications_open", "scholarship_deadline",
                    "scholarship_results_notification", "scholarship_acceptance_confirmation",
                ]
            ]
            data["buckets"]["scholarship"]["deadlines"] = na_deadlines
            json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            print("virtual event — individual scholarships not applicable")
            continue

        deadlines = []
        used_source = None

        for base, title in sources:
            wikitext = api_fetch(base, title)
            time.sleep(0.4)
            if wikitext:
                api_url = make_api_url(base, title)
                deadlines = parse_scholarship_page(wikitext, year, api_url)
                used_source = f"{base} / {title}"
                break

        if not deadlines:
            print(f"no deadlines parsed (source tried: {used_source})")
        else:
            types_found = [d["type"] for d in deadlines]
            print(f"found: {types_found}")

        # Update the JSON
        data["buckets"]["scholarship"]["deadlines"] = deadlines
        json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    print("\n\nDone.")


if __name__ == "__main__":
    main()
