"""
Phase 1: Fetch Wikimania edition metadata from the Wikimedia API.
Creates one JSON file per edition in editions/ and a combined index.json.
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

API_BASE = "https://meta.wikimedia.org/w/api.php"

EDITIONS = [
    (2005, "Frankfurt, Germany"),
    (2006, "Boston, USA"),
    (2007, "Taipei, Taiwan"),
    (2008, "Alexandria, Egypt"),
    (2009, "Buenos Aires, Argentina"),
    (2010, "Gdańsk, Poland"),
    (2011, "Haifa, Israel"),
    (2012, "Washington DC, USA"),
    (2013, "Hong Kong SAR, China"),
    (2014, "London, United Kingdom"),
    (2015, "Mexico City, Mexico"),
    (2016, "Esino Lario, Italy"),
    (2017, "Montréal, Canada"),
    (2018, "Cape Town, South Africa"),
    (2019, "Stockholm, Sweden"),
    (2020, None),  # Cancelled
    (2021, "Virtual"),
    (2022, "Virtual"),
    (2023, "Singapore"),
    (2024, "Katowice, Poland"),
    (2025, "Nairobi, Kenya"),
    (2026, "Paris, France"),
]


def api_fetch(title, follow_redirects=True):
    params = urllib.parse.urlencode({
        "action": "query",
        "titles": title,
        "prop": "revisions",
        "rvprop": "content",
        "format": "json",
        "formatversion": "2",
        "redirects": "1" if follow_redirects else "",
    })
    url = f"{API_BASE}?{params}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    pages = data["query"]["pages"]
    if not pages or "revisions" not in pages[0]:
        return None
    return pages[0]["revisions"][0]["content"]


def parse_dates(wikitext, year):
    """
    Try to extract conference start/end dates from wikitext.
    Returns (start_date, end_date, confidence, notes).
    Handles many natural-language date formats and HTML entities.
    Prefers matches whose year == the expected edition year.
    """
    months_en = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12,
    }
    months_fr = {
        "janvier": 1, "février": 2, "mars": 3, "avril": 4,
        "mai": 5, "juin": 6, "juillet": 7, "août": 8,
        "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12,
    }
    all_months = {**months_en, **months_fr}
    mon_pat = '|'.join(all_months.keys())
    # normalise HTML entities so regex works cleanly
    text = wikitext.replace("&ndash;", "–").replace("&mdash;", "—")

    def fmt(yr, m, d):
        return f"{yr}-{int(m):02d}-{int(d):02d}"

    # Each extractor returns (start, end, note_label) or None
    candidates = []

    def try_all(pattern, label, extractor):
        for p in re.finditer(pattern, text, re.IGNORECASE):
            result = extractor(p)
            if result:
                candidates.append((*result, label, p.group(0)))

    # 1. "D–D Month YYYY"
    try_all(rf'(\d{{1,2}})\s*[–\-—]\s*(\d{{1,2}})\s+({mon_pat})\s+(\d{{4}})',
            "D–D Month YYYY",
            lambda p: (fmt(p.group(4), all_months[p.group(3).lower()], p.group(1)),
                       fmt(p.group(4), all_months[p.group(3).lower()], p.group(2)),
                       p.group(4)))

    # 2. "Month D–D, YYYY"
    try_all(rf'({mon_pat})\s+(\d{{1,2}})\s*[–\-—]\s*(\d{{1,2}}),?\s+(\d{{4}})',
            "Month D–D YYYY",
            lambda p: (fmt(p.group(4), all_months[p.group(1).lower()], p.group(2)),
                       fmt(p.group(4), all_months[p.group(1).lower()], p.group(3)),
                       p.group(4)))

    # 3. "D to D Month YYYY"
    try_all(rf'(\d{{1,2}})\s+to\s+(\d{{1,2}})\s+({mon_pat})\s+(\d{{4}})',
            "D to D Month YYYY",
            lambda p: (fmt(p.group(4), all_months[p.group(3).lower()], p.group(1)),
                       fmt(p.group(4), all_months[p.group(3).lower()], p.group(2)),
                       p.group(4)))

    # 4. "Month D to D, YYYY"
    try_all(rf'({mon_pat})\s+(\d{{1,2}})\s+to\s+(\d{{1,2}}),?\s+(\d{{4}})',
            "Month D to D YYYY",
            lambda p: (fmt(p.group(4), all_months[p.group(1).lower()], p.group(2)),
                       fmt(p.group(4), all_months[p.group(1).lower()], p.group(3)),
                       p.group(4)))

    # 5. "Month Dth to Dth, YYYY"
    try_all(rf'({mon_pat})\s+(\d{{1,2}})(?:st|nd|rd|th)\s+to\s+(\d{{1,2}})(?:st|nd|rd|th),?\s+(\d{{4}})',
            "Month Dth to Dth YYYY",
            lambda p: (fmt(p.group(4), all_months[p.group(1).lower()], p.group(2)),
                       fmt(p.group(4), all_months[p.group(1).lower()], p.group(3)),
                       p.group(4)))

    # 6. "Month D, YYYY to Month D"
    try_all(rf'({mon_pat})\s+(\d{{1,2}}),?\s+(\d{{4}})\s+to\s+(?:{mon_pat})\s+(\d{{1,2}})',
            "Month D YYYY to Month D",
            lambda p: (fmt(p.group(3), all_months[p.group(1).lower()], p.group(2)),
                       fmt(p.group(3), all_months[p.group(1).lower()], p.group(4)),
                       p.group(3)))

    # 6b. "Dth to Dth of Month YYYY"
    try_all(rf'(\d{{1,2}})(?:st|nd|rd|th)\s+to\s+(\d{{1,2}})(?:st|nd|rd|th)\s+of\s+({mon_pat})\s+(\d{{4}})',
            "Dth to Dth of Month YYYY",
            lambda p: (fmt(p.group(4), all_months[p.group(3).lower()], p.group(1)),
                       fmt(p.group(4), all_months[p.group(3).lower()], p.group(2)),
                       p.group(4)))

    # 6c. "Month D through [Weekday,] Month D[, YYYY]"  (year may be absent → use context year)
    try_all(rf'({mon_pat})\s+(\d{{1,2}})\s+through\s+(?:\w+,\s+)?(?:{mon_pat})\s+(\d{{1,2}})(?:,\s+(\d{{4}}))?',
            "Month D through Month D",
            lambda p: (fmt(p.group(4) or str(year), all_months[p.group(1).lower()], p.group(2)),
                       fmt(p.group(4) or str(year), all_months[p.group(1).lower()], p.group(3)),
                       p.group(4) or str(year)))

    # 7. French "du D [Month] au D Month YYYY"
    try_all(rf'du\s+(\d{{1,2}})\s+(?:({mon_pat})\s+)?au\s+(\d{{1,2}})\s+({mon_pat})\s+(\d{{4}})',
            "du D au D Month YYYY (French)",
            lambda p: (fmt(p.group(5),
                           all_months[(p.group(2) or p.group(4)).lower()],
                           p.group(1)),
                       fmt(p.group(5), all_months[p.group(4).lower()], p.group(3)),
                       p.group(5)))

    if candidates:
        # Prefer a match whose year equals the expected edition year
        year_str = str(year)
        preferred = [c for c in candidates if c[2] == year_str]
        chosen = preferred[0] if preferred else candidates[0]
        start, end, _, label, raw = chosen
        return start, end, "confirmed", f"Pattern '{label}': '{raw}'"

    # 8. Only month + year found → approximate
    p = re.search(rf'({mon_pat})\s+({year})', text, re.IGNORECASE)
    if p:
        return None, None, "approximate", f"Only month/year found: '{p.group(0)}'"

    return None, None, "unknown", "No date pattern matched in wikitext"


def make_source(api_url):
    return {
        "url": api_url,
        "source_type": "meta_wiki",
        "verified": False,
        "verified_date": None,
        "verified_text_found": None,
    }


def build_edition(year, location, wikitext, api_url, notes=""):
    if wikitext:
        start, end, confidence, parse_note = parse_dates(wikitext, year)
    else:
        start, end, confidence, parse_note = None, None, "unknown", "No wikitext retrieved"

    source = make_source(api_url)

    return {
        "edition": f"Wikimania {year}",
        "year": year,
        "location": location,
        "conference_site_url": None,  # to be filled manually or in Phase 2
        "meta_wiki_url": f"https://meta.wikimedia.org/wiki/Wikimania_{year}",
        "notes": notes,
        "buckets": {
            "conference": {
                "deadlines": [
                    {
                        "type": "conference_start",
                        "date": start,
                        "date_confidence": confidence,
                        "notes": parse_note,
                        "sources": [source] if start else [],
                    },
                    {
                        "type": "conference_end",
                        "date": end,
                        "date_confidence": confidence,
                        "notes": parse_note,
                        "sources": [source] if end else [],
                    },
                ]
            },
            "program": {"deadlines": []},
            "scholarship": {"deadlines": []},
            "registration": {"deadlines": []},
        },
    }


def main():
    out_dir = Path(__file__).parent / "editions"
    out_dir.mkdir(exist_ok=True)

    index = []

    # Some edition pages redirect or have better content on a sub-page
    ALT_TITLES = {
        2005: "Wikimania 2005 overview",
        2006: "Wikimania 2006/en",
        2009: "Wikimania/2009",  # main page lacks dates; org summary has them
    }

    for year, location in EDITIONS:
        print(f"Fetching Wikimania {year}...", end=" ", flush=True)

        if location is None:
            # Cancelled
            data = build_edition(year, "N/A", None, "", notes="Cancelled — not held")
            data["buckets"]["conference"]["deadlines"][0]["date_confidence"] = "not_applicable"
            data["buckets"]["conference"]["deadlines"][1]["date_confidence"] = "not_applicable"
        else:
            title = ALT_TITLES.get(year, f"Wikimania_{year}")
            api_url = (
                f"{API_BASE}?action=query&titles={urllib.parse.quote(title)}"
                "&prop=revisions&rvprop=content&format=json&formatversion=2&redirects=1"
            )
            wikitext = api_fetch(title)
            data = build_edition(year, location, wikitext, api_url)

        # Write per-edition file
        out_file = out_dir / f"wikimania_{year}.json"
        out_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))

        start = data["buckets"]["conference"]["deadlines"][0]["date"]
        end = data["buckets"]["conference"]["deadlines"][1]["date"]
        conf = data["buckets"]["conference"]["deadlines"][0]["date_confidence"]
        print(f"{start} → {end} ({conf})")

        index.append({
            "year": year,
            "edition": data["edition"],
            "location": location or "N/A",
            "conference_start": start,
            "conference_end": end,
            "date_confidence": conf,
            "notes": data["notes"],
            "meta_wiki_url": data["meta_wiki_url"],
        })

        time.sleep(0.5)  # be polite to the API

    # Write index
    index_file = out_dir / "index.json"
    index_file.write_text(json.dumps(index, indent=2, ensure_ascii=False))
    print(f"\nDone. {len(index)} editions written to {out_dir}/")


if __name__ == "__main__":
    main()
