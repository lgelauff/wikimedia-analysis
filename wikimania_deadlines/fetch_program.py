"""
Phase 2 — Program deadlines.
Collects:
  program_submission_open
  program_submission_deadline
  program_submission_deadline_extended
  program_acceptance_notification
  program_speaker_confirmation
  program_schedule_published
"""

import json, re, time, urllib.request, urllib.parse
from pathlib import Path

HEADERS = {
    "User-Agent": "WikimaniaDeadlinesResearch/1.0 (https://github.com/lgelauff/wikimedia-analysis; research project)",
    "Accept": "application/json",
}
META = "https://meta.wikimedia.org/w/api.php"
WM   = "https://wikimania.wikimedia.org/w/api.php"

def wm_old(year): return f"https://wikimania{year}.wikimedia.org/w/api.php"

# Per-edition sources (api_base, page_title)
PROGRAM_SOURCES = {
    2005: [(wm_old(2005), "Call_for_participation")],
    2006: [(wm_old(2006), "Call_for_participation")],
    2007: [(wm_old(2007), "Call_for_Participation")],
    2008: [(wm_old(2008), "Call_for_participation")],
    2009: [(wm_old(2009), "Call_for_Participation")],
    2010: [(wm_old(2010), "Call_for_Participation")],
    2011: [(wm_old(2011), "Submissions")],
    2012: [(wm_old(2012), "Submissions")],
    2013: [(wm_old(2013), "Call_for_participation")],
    2014: [(wm_old(2014), "Submissions")],
    2015: [(wm_old(2015), "Submissions")],
    2016: [(wm_old(2016), "Submissions")],
    2017: [(wm_old(2017), "Submissions")],
    2018: [(wm_old(2018), "Submissions")],
    2019: [(WM, "2019:Submissions")],
    2020: [],  # cancelled
    2021: [(WM, "2021:Program")],
    2022: [(WM, "2022:Program")],
    2023: [(WM, "2023:Program/Submissions")],
    2024: [(WM, "2024:Program")],
    2025: [(WM, "2025:Program")],
    2026: [(WM, "2026:Program")],
}

DEADLINE_KEYWORDS = {
    "program_submission_open": [
        "call for submissions open", "call for participation open",
        "submissions will open", "submissions open",
        "call for proposals opens", "call for proposals open",
        "submission period open", "open on", "opens on",
        "call for submissions opened",
    ],
    "program_submission_deadline": [
        "deadline for submitting", "submission deadline",
        "deadline for submission", "abstract deadline",
        "proposals deadline", "proposals was",
        "original deadline", "del>",  # <del> tags mark original crossed-out deadline
        "submissions closed", "submissions is closed",
    ],
    "program_submission_deadline_extended": [
        "extended", "new deadline", "extension",
        "extended to", "extended until", "extended the submission",
    ],
    "program_acceptance_notification": [
        "notified", "notification of acceptance", "notification",
        "authors will be notified", "will be notified",
        "review, feedback and notification",
        "results will be published", "decisions",
    ],
    "program_speaker_confirmation": [
        "speaker confirmation", "confirm your", "confirmation deadline",
        "confirm participation", "speaker must confirm",
    ],
    "program_schedule_published": [
        "schedule published", "programme published", "schedule available",
        "full schedule", "program published",
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
        print(f"    API error: {e}")
    return None


def api_url(base, title):
    return (f"{base}?action=query&titles={urllib.parse.quote(title)}"
            "&prop=revisions&rvprop=content&format=json&formatversion=2&redirects=1")


def strip_wiki(text):
    text = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]*)\]\]', r'\1', text)
    text = re.sub(r'\{\{[^}]*\}\}', ' ', text)
    text = re.sub(r"'''?", '', text)
    text = re.sub(r'<(?!del|/del)[^>]+>', ' ', text)
    text = re.sub(r'<!--T:\d+-->', '', text)
    return text


def extract_date(text, context_year):
    text = text.replace("&ndash;", "–").replace("&mdash;", "—")
    def fmt(yr, m, d): return f"{int(yr)}-{int(m):02d}-{int(d):02d}"

    # ISO
    p = re.search(r'\b(\d{4})-(\d{2})-(\d{2})\b', text)
    if p: return fmt(p.group(1), p.group(2), p.group(3)), "confirmed", p.group(0)

    # "Month D[th], YYYY"
    p = re.search(rf'({MON_PAT})\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})',
                  text, re.IGNORECASE)
    if p: return fmt(p.group(3), MONTHS[p.group(1).lower()], p.group(2)), "confirmed", p.group(0)

    # "D[th] Month YYYY"
    p = re.search(rf'(\d{{1,2}})(?:st|nd|rd|th)?\s+({MON_PAT})\s+(\d{{4}})',
                  text, re.IGNORECASE)
    if p: return fmt(p.group(3), MONTHS[p.group(2).lower()], p.group(1)), "confirmed", p.group(0)

    # "D Month" or "Month D" without year → context
    p = re.search(rf'(\d{{1,2}})\s+({MON_PAT})(?!\s*\d{{3}})', text, re.IGNORECASE)
    if p: return fmt(context_year, MONTHS[p.group(2).lower()], p.group(1)), "approximate", p.group(0)

    p = re.search(rf'({MON_PAT})\s+(\d{{1,2}})(?:st|nd|rd|th)?(?!\s*,?\s*\d{{3}})',
                  text, re.IGNORECASE)
    if p: return fmt(context_year, MONTHS[p.group(1).lower()], p.group(2)), "approximate", p.group(0)

    return None, "unknown", None


def classify_line(line, context_year):
    clean = strip_wiki(line).lower()
    results = []
    for dtype, keywords in DEADLINE_KEYWORDS.items():
        if any(kw in clean for kw in keywords):
            date, conf, raw = extract_date(clean, context_year)
            if date:
                results.append((dtype, date, conf, raw, line.strip()))
    return results


def parse_program_page(wikitext, year, source_url):
    found = {}
    for line in wikitext.splitlines():
        for dtype, date, conf, raw, orig in classify_line(line, year):
            if dtype in found and found[dtype]["date_confidence"] == "confirmed":
                continue
            found[dtype] = {
                "type": dtype, "date": date, "date_confidence": conf,
                "notes": f"Parsed from: '{orig[:120]}'",
                "sources": [{"url": source_url,
                             "source_type": classify_source(source_url),
                             "verified": False, "verified_date": None,
                             "verified_text_found": None}],
            }
    return list(found.values())


def classify_source(url):
    if "meta.wikimedia.org" in url: return "meta_wiki"
    if "wikimania.wikimedia.org" in url or "wikimania20" in url: return "conference_site"
    return "other"


def main():
    editions_dir = Path(__file__).parent / "editions"

    for year in range(2005, 2027):
        json_path = editions_dir / f"wikimania_{year}.json"
        if not json_path.exists():
            continue
        data = json.loads(json_path.read_text())
        sources = PROGRAM_SOURCES.get(year, [])

        print(f"\nWikimania {year}...", end=" ", flush=True)

        if not sources:
            print("no sources defined")
            continue

        deadlines = []
        for base, title in sources:
            wikitext = api_fetch(base, title)
            time.sleep(0.4)
            if wikitext:
                deadlines = parse_program_page(wikitext, year, api_url(base, title))
                break

        if deadlines:
            print(f"found: {[d['type'] for d in deadlines]}")
        else:
            print("no deadlines parsed")

        data["buckets"]["program"]["deadlines"] = deadlines
        json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
