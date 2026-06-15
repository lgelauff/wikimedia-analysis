# /// script
# dependencies = []
# ///
"""
collect_rfc_listings.py — RfC population from the topical listing pages' edit history.

API-only (no replica/PAWS). For each `Wikipedia:Requests for comment/<topic>` page, walk
its full revision history and parse the edit summaries:
  "Added:   [[Talk:X]]"  -> an RfC open  (listed under that topic)
  "Removed: [[Talk:X]]"  -> a close/delist
Classifies each remove by actor (bot = routine close/delist; human = manual close OR
disqualification) and flags disqualification language. Goes back to 2005 (incl. the
manual pre-bot era, where summaries are unstructured -> counted as 'other').

Output: data/listings/rfc_listing_events.csv  (topic, action, target, ts, actor, is_bot, flag)
        + a printed per-year / per-topic summary.

This is Track-B population (see IMETAL_REPRODUCTION.md). Outcome classification
(formal/informal/stale) still needs talk-page content and is a separate pass.
"""

import csv, json, re, time, urllib.parse, urllib.request
from pathlib import Path

UA = {"User-Agent": "WikimediaAnalysis/1.0 (research; https://github.com/lgelauff/wikimedia-analysis)"}
API = "https://en.wikipedia.org/w/api.php"
OUT = Path(__file__).parent / "data" / "listings"

TOPICS = [
    "Biographies", "Economy, trade, and companies", "History and geography",
    "Language and linguistics", "Maths, science, and technology",
    "Media, the arts, and architecture", "Politics, government, and law",
    "Religion and philosophy", "Society, sports, and culture",
    "WikiProjects and collaborations", "Wikipedia policies and guidelines",
    "Wikipedia proposals", "Wikipedia style and naming",
    "Wikipedia technical issues and templates", "Unsorted",
]
BOTS = {"Legobot", "RFC bot", "RfC bot", "Cyberbot I"}
DISQUALIFY = re.compile(r"disqualif|malform|invalid|not a (policy|guideline|rfc|valid|dr)|"
                        r"incorrectly placed|improper|not an rfc|withdrawn|rant", re.I)
ADD = re.compile(r"^\s*Added:\s*\[\[([^\]]+)\]\]", re.I)
REM = re.compile(r"^\s*Removed:\s*\[\[([^\]]+)\]\]", re.I)


def revisions(title):
    cont = None
    while True:
        p = {"action": "query", "titles": "Wikipedia:Requests for comment/" + title,
             "prop": "revisions", "rvprop": "user|timestamp|comment", "rvlimit": "500",
             "rvdir": "newer", "format": "json", "formatversion": "2", "maxlag": "5"}
        if cont: p["rvcontinue"] = cont
        for attempt in range(5):
            try:
                with urllib.request.urlopen(
                        urllib.request.Request(API + "?" + urllib.parse.urlencode(p), headers=UA),
                        timeout=60) as r:
                    d = json.load(r); break
            except Exception as e:
                time.sleep(5 * (2 ** attempt))
        else:
            raise RuntimeError("API failed: " + title)
        pages = d.get("query", {}).get("pages", [])
        if pages and not pages[0].get("missing"):
            for rev in pages[0].get("revisions", []):
                yield rev
        cont = d.get("continue", {}).get("rvcontinue")
        if not cont: break
        time.sleep(0.2)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for topic in TOPICS:
        n = 0
        for rev in revisions(topic):
            c = (rev.get("comment") or "").strip()
            user = rev.get("user", ""); ts = rev.get("timestamp", "")[:10]
            is_bot = user in BOTS
            m = ADD.match(c)
            if m:
                rows.append((topic, "open", m.group(1), ts, user, int(is_bot), "")); n += 1; continue
            m = REM.match(c)
            if m:
                flag = "disqualified" if (not is_bot and DISQUALIFY.search(c)) else (
                       "human_close" if not is_bot else "")
                rows.append((topic, "close", m.group(1), ts, user, int(is_bot), flag)); n += 1; continue
            if not is_bot and DISQUALIFY.search(c):
                rows.append((topic, "other", "", ts, user, 0, "disqualified")); n += 1
        print(f"  {topic:45} {n:6,} events")

    with (OUT / "rfc_listing_events.csv").open("w", newline="") as f:
        w = csv.writer(f); w.writerow(["topic", "action", "target", "ts", "actor", "is_bot", "flag"])
        w.writerows(rows)

    # summary
    opens = [r for r in rows if r[1] == "open"]
    closes = [r for r in rows if r[1] == "close"]
    disq = [r for r in rows if r[6] == "disqualified"]
    hclose = [r for r in rows if r[6] == "human_close"]
    print(f"\n=== {len(rows):,} listing events | opens {len(opens):,} · closes {len(closes):,} "
          f"· human-closes {len(hclose):,} · disqualified {len(disq):,} ===")
    print("\nopens by year:")
    yr = {}
    for r in opens: yr[r[3][:4]] = yr.get(r[3][:4], 0) + 1
    for y in sorted(yr): print(f"  {y}  {yr[y]:5,}")
    print("\nopens by topic:")
    tp = {}
    for r in opens: tp[r[0]] = tp.get(r[0], 0) + 1
    for t, c in sorted(tp.items(), key=lambda x: -x[1]): print(f"  {c:6,}  {t}")


if __name__ == "__main__":
    main()
