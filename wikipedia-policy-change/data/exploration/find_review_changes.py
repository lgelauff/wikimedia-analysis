#!/usr/bin/env python3
"""
find_review_changes.py — surface the small-change ("typo / minor reword") edits that a human
should eyeball when deciding same-statement-vs-changed. Language-agnostic: works off whatever
wiki each dataset row names, via the MediaWiki API (never scrapes).

For each page it pulls the full revision history and flags edits whose byte-delta is in a small
band (default 1..300 B — big enough to maybe change meaning, small enough to maybe be a reword),
then enriches each with what a reviewer needs:
  author · edit (diff) URL · edit summary · was-it-reverted · same author immediately before/after.

Input dataset (CSV, unknown languages OK) — needs a wiki column + a title column. Accepts:
  wiki codes (`nlwiki`, `dewiki`) or hosts (`nl.wikipedia.org`), and `title` (or `page_id`).
  Our `data/network/nodes.csv` works directly.

Output: an HTML table (clickable diff links, grouped by page) + a CSV. Pure stdlib.

Usage:
  uv run python find_review_changes.py --dataset ../network/nodes.csv --wiki-filter nlwiki --limit 20 \
      --out review.html --out-csv review.csv
  uv run python find_review_changes.py --pages "nlwiki:Wikipedia:Stemprocedure" --out review.html
"""
import argparse, collections, csv, datetime, html, json, re, urllib.parse, urllib.request


def epoch(ts):
    return datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=datetime.timezone.utc).timestamp()

UA = "WikimediaAnalysis/1.0 (research; https://github.com/lgelauff/wikimedia-analysis)"
REVERTING = {"mw-manual-revert", "mw-rollback", "mw-undo", "mw-revert"}


def ns_names(host, _cache={}):
    if host not in _cache:
        d = api(host, {"action": "query", "meta": "siteinfo", "siprop": "namespaces"})
        _cache[host] = {str(n["id"]): n.get("name", "") for n in d["query"]["namespaces"].values()}
    return _cache[host]


def talk_title(host, title):
    """talk page of a project-namespace page (ns 4 → ns 5), language-agnostic via siteinfo."""
    if ":" not in title:
        return None
    talk_ns = ns_names(host).get("5")            # project-talk namespace name (Overleg Wikipedia / Wikipedia talk / …)
    return f"{talk_ns}:{title.split(':', 1)[1]}" if talk_ns else None


def host_of(wiki):
    if "." in wiki:
        return wiki
    if wiki.endswith("wiki"):
        return f"{wiki[:-4]}.wikipedia.org"
    return f"{wiki}.wikipedia.org"


def api(host, params):
    params = {**params, "format": "json", "formatversion": "2"}
    url = f"https://{host}/w/api.php?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as r:
        return json.loads(r.read())


def revisions(host, title, cap=3000):
    out, cont = [], None
    while len(out) < cap:
        p = {"action": "query", "prop": "revisions", "titles": title, "rvdir": "newer",
             "rvlimit": "500", "rvprop": "ids|timestamp|user|comment|size|tags"}
        if cont:
            p["rvcontinue"] = cont
        d = api(host, p)
        pg = d["query"]["pages"][0]
        if "missing" in pg:
            return None
        out.extend(pg.get("revisions", []))
        cont = d.get("continue", {}).get("rvcontinue")
        if not cont:
            break
    return out


def load_dataset(path, wiki_filter):
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    wcol = next((c for c in rows[0] if c.lower() in ("wiki", "host", "project")), None)
    tcol = next((c for c in rows[0] if c.lower() in ("title", "page", "page_title")), None)
    seen, out = set(), []
    for r in rows:
        w = r[wcol]
        if wiki_filter and w != wiki_filter:
            continue
        t = r[tcol]
        if (w, t) not in seen:
            seen.add((w, t)); out.append((w, t))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset")
    ap.add_argument("--pages", help="comma list of wiki:title")
    ap.add_argument("--wiki-filter", default=None)
    ap.add_argument("--min-bytes", type=int, default=1)
    ap.add_argument("--max-bytes", type=int, default=300)
    ap.add_argument("--series-window-hours", type=float, default=168.0,
                    help="same author editing OTHER dataset pages within this window = a series")
    ap.add_argument("--limit", type=int, default=None, help="max pages")
    ap.add_argument("--out", default="review_changes.html")
    ap.add_argument("--out-csv", default=None)
    a = ap.parse_args()

    if a.pages:
        pages = [(p.split(":", 1)[0], p.split(":", 1)[1]) for p in a.pages.split(",")]
    else:
        pages = load_dataset(a.dataset, a.wiki_filter)
    if a.limit:
        pages = pages[:a.limit]

    # pass 1 — fetch every page's history; build an author → all-edits index (across pages)
    allrevs = {}
    author_idx = collections.defaultdict(list)     # user -> [(epoch, title)]
    talk_idx, talk_url = {}, {}                     # (wiki,title) -> [(epoch,user)] ; -> talk page url
    for wiki, title in pages:
        host = host_of(wiki)
        revs = revisions(host, title)
        if not revs:
            continue
        allrevs[(wiki, title)] = revs
        for r in revs:
            u = r.get("user")
            if u:
                author_idx[u].append((epoch(r["timestamp"]), title))
        tt = talk_title(host, title)               # did the discussion happen on the talk page?
        trevs = revisions(host, tt) if tt else None
        talk_idx[(wiki, title)] = [(epoch(r["timestamp"]), r.get("user")) for r in (trevs or [])]
        talk_url[(wiki, title)] = f"https://{host}/wiki/{urllib.parse.quote(tt)}" if trevs else ""
    for u in author_idx:
        author_idx[u].sort()
    window = a.series_window_hours * 3600

    # pass 2 — flag the small-change band + enrich (revert, same-page neighbours, cross-page series)
    cands, scanned = [], 0
    for (wiki, title), revs in allrevs.items():
        host = host_of(wiki)
        scanned += len(revs)
        for i, rv in enumerate(revs):
            if i == 0:
                continue
            delta = rv["size"] - revs[i - 1]["size"]
            if not (a.min_bytes <= abs(delta) <= a.max_bytes):
                continue
            tags = rv.get("tags", []); u = rv.get("user", "(hidden)")
            prev_u = revs[i - 1].get("user")
            next_u = revs[i + 1].get("user") if i + 1 < len(revs) else None
            t = epoch(rv["timestamp"])
            sib = {et for (e, et) in author_idx.get(u, []) if et != title and abs(e - t) <= window}
            ti = talk_idx.get((wiki, title), [])
            to_talk = any(uu == u and abs(e - t) <= window for (e, uu) in ti)        # same author on talk
            talk_activity = any(abs(e - t) <= window for (e, _) in ti)               # any talk discussion
            cands.append({
                "wiki": wiki, "title": title, "ts": rv["timestamp"][:10],
                "user": u, "delta": delta,
                "summary": rv.get("comment", "") or "",
                "reverted": "mw-reverted" in tags,
                "is_revert": any(t2 in REVERTING for t2 in tags),
                "same_page_before": prev_u == u, "same_page_after": next_u == u,
                "series_n": len(sib),                       # same author, OTHER pages, within window
                "series_pages": "; ".join(sorted(sib)[:5]),
                "series_id": f"{u}@{rv['timestamp'][:10]}" if sib else "",
                "to_talk": to_talk, "talk_activity": talk_activity,
                "diff_url": f"https://{host}/wiki/Special:Diff/{rv['revid']}",
                "talk_url": talk_url.get((wiki, title), ""),
            })
    # sort series together (a series is one decision → review as a group), then loners by page/date
    cands.sort(key=lambda c: (c["series_id"] == "", c["series_id"], c["title"], c["ts"]))

    # CSV
    if a.out_csv:
        with open(a.out_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(cands[0].keys()) if cands else
                               ["wiki", "title", "ts", "user", "delta", "summary", "reverted",
                                "is_revert", "same_before", "same_after", "diff_url"])
            w.writeheader(); w.writerows(cands)

    # HTML
    def chip(b, t, c):
        return f'<span style="background:{c};color:#222;padding:0 5px;border-radius:3px;font-size:11px">{t}</span>' if b else ""
    H = ['<div style="font-family:var(--font-sans);font-size:13px;color:var(--text-primary)">']
    H.append(f'<div style="font-size:16px;font-weight:600">Small-change review queue — {len(cands)} '
             f'candidate edits ({a.min_bytes}–{a.max_bytes} B) across {len(pages)} pages, {scanned} revisions scanned</div>')
    H.append('<div style="font-size:12px;color:var(--text-secondary);margin:2px 0 8px">'
             'the band a human would check for "typo/reword vs real change". '
             'reverted / same-author-adjacent edits are usually auto-resolvable.</div>')
    H.append('<table style="border-collapse:collapse;width:100%"><thead><tr style="text-align:left;border-bottom:1px solid var(--border)">'
             '<th>page</th><th>date</th><th>author</th><th>Δ</th><th>summary</th><th>flags</th><th>diff</th></tr></thead><tbody>')
    for c in cands:
        talk = (f' <a href="{c["talk_url"]}" target="_blank" style="text-decoration:none">'
                f'<span style="background:#bfe6b0;color:#222;padding:0 5px;border-radius:3px;font-size:11px">→ talk</span></a>'
                if c["to_talk"] else chip(c["talk_activity"], "talk activity", "#e0efd8"))
        flags = " ".join(filter(None, [
            chip(c["series_n"] > 0, f'series ×{c["series_n"]}', "#d9c2f0"), talk,
            chip(c["reverted"], "reverted", "#f4b8b8"),
            chip(c["is_revert"], "is-revert", "#f7d9a0"),
            chip(c["same_page_before"] or c["same_page_after"], "same-page run", "#cfe3f7")]))
        H.append('<tr style="border-bottom:1px solid var(--border-subtle)">'
                 f'<td style="font-size:11px">{html.escape(c["title"][:38])}</td>'
                 f'<td>{c["ts"]}</td><td>{html.escape(str(c["user"])[:18])}</td>'
                 f'<td style="text-align:right;color:{"#087443" if c["delta"]>0 else "#b3261e"}">{c["delta"]:+d}</td>'
                 f'<td style="font-size:11px;max-width:280px">{html.escape(c["summary"][:120])}</td>'
                 f'<td>{flags}</td>'
                 f'<td><a href="{c["diff_url"]}" target="_blank">view</a></td></tr>')
    H.append('</tbody></table></div>')
    open(a.out, "w", encoding="utf-8").write("\n".join(H))
    print(f"wrote {a.out}"
          + (f" + {a.out_csv}" if a.out_csv else "")
          + f" | {len(cands)} candidates / {scanned} revisions / {len(pages)} pages")


if __name__ == "__main__":
    main()
