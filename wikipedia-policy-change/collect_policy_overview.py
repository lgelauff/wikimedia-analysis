# /// script
# dependencies = ["certifi"]
# ///
"""
collect_policy_overview.py — download the policy-overview/index page for each
of the top-N Wikipedia projects and save the raw wikitext.

The "policy overview page" is the page that lists all policies and guidelines
for that wiki (e.g. en: Wikipedia:List_of_policies_and_guidelines).

Discovery strategy (in order):
  1. Wikidata sitelinks for the enwiki seed page
  2. Direct langlinks from enwiki
  3. Hardcoded fallbacks for languages known to use a different title

Output:
  data/policy_overview/<wiki>.wikitext   — raw wikitext
  data/policy_overview/index.csv         — wiki, lang, title, fetched_at, char_count
"""

import csv
import json
import re
import ssl
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Top ~20 Wikipedia language codes by active-editor community size (2024).
# Ordered roughly by monthly active editors.
TOP_LANGS = [
    "en", "de", "fr", "es", "ru", "it", "pt", "ja", "zh",
    "nl", "pl", "ar", "sv", "uk", "fa", "ko", "he", "tr",
    "vi", "cs",
]

# enwiki seed page — the master list of policies and guidelines
EN_SEED = "Wikipedia:List of policies and guidelines"

# Manual overrides where Wikidata / langlinks don't find a match.
# Maps lang code → local page title.
OVERRIDES = {
    "zh": "Wikipedia:方针与指引",
    "ar": "ويكيبيديا:سياسات وإرشادات",
    "fa": "ویکی‌پدیا:سیاست‌ها و راهنماها",
    "ko": "위키백과:정책과 지침",
    "he": "ויקיפדיה:מדיניות",
    "tr": "Vikipedi:Politikalar ve kurallar",
    "vi": "Wikipedia:Quy định và hướng dẫn",
    "cs": "Wikipedie:Pravidla a doporučení",
    "sv": "Wikipedia:Policies och riktlinjer",
    "uk": "Вікіпедія:Правила",           # redirects to full list
    "pl": "Wikipedia:Zasady",
    "ru": "Википедия:Правила и руководства",
    "it": "Wikipedia:Politiche e linee guida",
    "pt": "Wikipédia:Políticas e recomendações",
    "de": "Wikipedia:Grundprinzipien",
    "nl": "Portaal:Hulp en beheer",
    "fa": "ویکی‌پدیا:قوانین و رهنمودها",
    "tr": "Vikipedi:Kurallar ve yönergeler",
}

OUT_DIR  = Path(__file__).parent / "data" / "policy_overview"
RATE_DELAY = 1.2  # seconds between API calls
UA = "WikimediaAnalysis/1.0 (personal research project; https://github.com/lgelauff/wikimedia-analysis)"
_SSL_CTX = ssl.create_default_context(cafile=__import__("certifi").where())

# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(5):
        time.sleep(RATE_DELAY * (2 ** attempt) if attempt else RATE_DELAY)
        try:
            with urllib.request.urlopen(req, timeout=30, context=_SSL_CTX) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 30 * (2 ** attempt)
                print(f"  429 – waiting {wait}s …")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError(f"Failed after 5 attempts: {url}")


def api(wiki: str, params: dict) -> dict:
    base = f"https://{wiki}.org/w/api.php"
    return _get(base + "?" + urllib.parse.urlencode(params))


def wikidata_api(params: dict) -> dict:
    base = "https://www.wikidata.org/w/api.php"
    return _get(base + "?" + urllib.parse.urlencode(params))

# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def sitelinks_via_wikidata(en_title: str, langs: list[str]) -> dict[str, str]:
    """Return {lang: title} for langs that have a sitelink on the Wikidata item
    corresponding to the given enwiki page."""
    data = wikidata_api({
        "action": "wbgetentities",
        "sites": "enwiki",
        "titles": en_title,
        "props": "sitelinks",
        "format": "json",
    })
    entities = data.get("entities", {})
    result = {}
    for item in entities.values():
        for sl in item.get("sitelinks", {}).values():
            site = sl.get("site", "")
            if site.endswith("wiki") and not site.endswith("wikimedia"):
                lang = site[:-4]   # strip trailing "wiki"
                if lang in langs:
                    result[lang] = sl["title"]
    return result


def langlinks_via_enwiki(en_title: str, langs: list[str]) -> dict[str, str]:
    """Fallback: fetch langlinks directly from enwiki."""
    data = api("en.wikipedia", {
        "action": "query",
        "titles": en_title,
        "prop": "langlinks",
        "lllimit": "max",
        "format": "json",
        "formatversion": "2",
        "redirects": "1",
    })
    pages = data.get("query", {}).get("pages", [])
    if not pages:
        return {}
    lang_set = set(langs)
    return {ll["lang"]: ll["title"]
            for ll in pages[0].get("langlinks", [])
            if ll["lang"] in lang_set}


def fetch_wikitext(wiki: str, title: str) -> str | None:
    """Return current wikitext for a page, or None if page doesn't exist."""
    data = api(wiki, {
        "action": "query",
        "titles": title,
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "format": "json",
        "formatversion": "2",
        "redirects": "1",
        "maxlag": "5",
    })
    pages = data.get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing"):
        return None
    try:
        return pages[0]["revisions"][0]["slots"]["main"]["content"]
    except (KeyError, IndexError):
        return None

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    index_path = OUT_DIR / "index.csv"
    langs_todo = [l for l in TOP_LANGS if l != "en"]

    print(f"Discovering policy overview pages for {len(TOP_LANGS)} languages …")

    # Step 1 — Wikidata sitelinks
    print("\n[1] Wikidata sitelinks …")
    found = sitelinks_via_wikidata(EN_SEED, langs_todo)
    print(f"    Found {len(found)} via Wikidata")

    # Step 2 — Langlinks fallback for any still missing
    missing = [l for l in langs_todo if l not in found]
    if missing:
        print(f"\n[2] Langlinks fallback for {len(missing)} missing …")
        ll = langlinks_via_enwiki(EN_SEED, missing)
        found.update(ll)
        print(f"    Found {len(ll)} more via langlinks")

    # Step 3 — Manual overrides for anything still missing
    still_missing = [l for l in langs_todo if l not in found]
    for lang in still_missing:
        if lang in OVERRIDES:
            found[lang] = OVERRIDES[lang]
            print(f"  [override] {lang}: {OVERRIDES[lang]}")

    # Always include English
    found["en"] = EN_SEED

    print(f"\nTotal mapped: {len(found)}/{len(TOP_LANGS)} languages")

    # Step 4 — Fetch and save wikitext
    rows = []
    print("\nFetching wikitext …")
    for lang in TOP_LANGS:
        if lang not in found:
            print(f"  [{lang}] SKIP — no title found")
            continue
        title = found[lang]
        wiki = f"{lang}.wikipedia"
        out_file = OUT_DIR / f"{wiki}.wikitext"
        if out_file.exists():
            print(f"  [{lang}] already cached: {title}")
            text = out_file.read_text(encoding="utf-8")
            rows.append({
                "wiki": wiki, "lang": lang, "title": title,
                "fetched_at": "cached", "char_count": len(text),
            })
            continue
        print(f"  [{lang}] fetching: {title} … ", end="", flush=True)
        text = fetch_wikitext(wiki, title)
        if text is None:
            print("NOT FOUND")
            continue
        out_file.write_text(text, encoding="utf-8")
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        print(f"{len(text):,} chars")
        rows.append({
            "wiki": wiki, "lang": lang, "title": title,
            "fetched_at": ts, "char_count": len(text),
        })

    # Write index
    cols = ["wiki", "lang", "title", "fetched_at", "char_count"]
    with index_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    print(f"\nWrote {len(rows)} entries → {index_path}")
    print("\nSummary:")
    for r in rows:
        print(f"  {r['lang']:4s}  {r['char_count']:>8,} chars  {r['title']}")


if __name__ == "__main__":
    main()
