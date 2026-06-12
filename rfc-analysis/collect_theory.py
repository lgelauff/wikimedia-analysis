"""
collect_theory.py — A2 + A3: collect all en.wikipedia pages that explain
the RFC / policy / consensus process in theory.

Steps:
  1. Seed: the RFC page already cached.
  2. Category crawl (A2): enumerate members of target categories.
  3. Link expansion (A3): parse [[Wikipedia:...]] wikilinks from every
     fetched page; add unseen WP-namespace pages to the queue.
     Stops at depth 2 beyond the seed/category pages.
  4. Fetch + cache everything via cache.py.

Run:
    python3 collect_theory.py
"""

import re
import time
import urllib.parse
import urllib.request
import ssl
import json
import certifi
from pathlib import Path

import cache as _cache

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SEED_URLS = [
    "https://en.wikipedia.org/wiki/Wikipedia:Requests_for_comment",
]

# Categories whose members we want (namespace 4 = Wikipedia:)
TARGET_CATEGORIES = [
    "Category:Wikipedia policies",
    "Category:Wikipedia information pages",
    "Category:Wikipedia dispute resolution",
    "Category:Wikipedia consensus",
    "Category:Wikipedia conduct policies",
    "Category:Wikipedia requests for comment",
]

# WP: pages that are clearly out of scope (noticeboards, logs, archives, drafts)
SKIP_PATTERNS = [
    r"/Archive",
    r"/archive",
    r"Noticeboard",
    r"noticeboard",
    r"/Draft",
    r"Wikipedia:Requests for comment/",  # individual RfC pages
    r"Wikipedia:Village_pump",           # discussion boards, not theory
    r"Wikipedia:Wikipedia_Signpost",
    r"Wikipedia:Featured",
    r"Wikipedia:Good_article",
    r"Wikipedia:Did_you_know",
    r"Wikipedia:Today",
    r"Wikipedia:List_of",
    r"Wikipedia:Sockpuppet",
]

MAX_LINK_DEPTH = 2

SSL_CTX = ssl.create_default_context(cafile=certifi.where())
UA = "WikimediaAnalysis/1.0 (personal research; https://github.com/lgelauff/wikimedia-analysis)"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _api(params: dict) -> dict:
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    time.sleep(0.5)
    with urllib.request.urlopen(req, timeout=20, context=SSL_CTX) as r:
        return json.loads(r.read())


def _should_skip(title: str) -> bool:
    return any(re.search(pat, title) for pat in SKIP_PATTERNS)


def _title_to_url(title: str) -> str:
    encoded = urllib.parse.quote(title.replace(" ", "_"), safe=":/")
    return f"https://en.wikipedia.org/wiki/{encoded}"


def category_members(cat: str) -> list[str]:
    """Return all Wikipedia-namespace page titles in a category (handles continuation)."""
    titles = []
    params = {
        "action": "query", "list": "categorymembers",
        "cmtitle": cat, "cmnamespace": "4",
        "cmlimit": "500", "format": "json", "formatversion": "2",
    }
    while True:
        data = _api(params)
        titles += [m["title"] for m in data["query"]["categorymembers"]]
        cont = data.get("continue", {}).get("cmcontinue")
        if not cont:
            break
        params["cmcontinue"] = cont
    return titles


def extract_wp_links(wikitext: str) -> list[str]:
    """Extract [[Wikipedia:...]] wikilinks from wikitext, return as page titles."""
    raw = re.findall(r"\[\[(?:Wikipedia|WP):([^\]|#]+)", wikitext, re.IGNORECASE)
    titles = []
    for r in raw:
        title = "Wikipedia:" + r.strip().replace("_", " ")
        if not _should_skip(title):
            titles.append(title)
    return list(set(titles))


# ---------------------------------------------------------------------------
# Main collection
# ---------------------------------------------------------------------------

def collect():
    sources = _cache.load_sources()
    fetched_titles: set[str] = {v["title"] for v in sources.values()}
    queue: list[tuple[str, int]] = []  # (title, depth)

    # --- A2: category crawl ---
    print("=== A2: Category crawl ===")
    cat_titles: set[str] = set()
    for cat in TARGET_CATEGORIES:
        members = category_members(cat)
        print(f"  {cat}: {len(members)} members")
        for t in members:
            if not _should_skip(t):
                cat_titles.add(t)

    for t in sorted(cat_titles):
        if t not in fetched_titles:
            queue.append((t, 0))

    print(f"\n  → {len(cat_titles)} category pages, {len(queue)} not yet cached\n")

    # --- Fetch category pages + A3: link expansion ---
    print("=== A3: Fetch + link expansion ===")
    seen_titles: set[str] = set(fetched_titles) | cat_titles

    i = 0
    while i < len(queue):
        title, depth = queue[i]
        i += 1

        url = _title_to_url(title)
        try:
            wikitext = _cache.fetch_page(url)
        except Exception as e:
            print(f"  [skip] {title}: {e}")
            continue

        # A3: extract links and enqueue at depth+1
        if depth < MAX_LINK_DEPTH:
            links = extract_wp_links(wikitext)
            new = [t for t in links if t not in seen_titles and not _should_skip(t)]
            for t in new:
                seen_titles.add(t)
                queue.append((t, depth + 1))
            if new:
                print(f"    +{len(new)} links at depth {depth+1}")

    # --- Summary ---
    sources = _cache.load_sources()
    print(f"\n=== Done: {len(sources)} pages in sources.json ===")
    for url, meta in sorted(sources.items(), key=lambda x: x[1]["title"]):
        print(f"  [{meta['revid']}] {meta['title']}")


if __name__ == "__main__":
    collect()
