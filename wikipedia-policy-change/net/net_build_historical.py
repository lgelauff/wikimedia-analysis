#!/usr/bin/env python3
"""
net_build_historical.py — M4 Phase 1: walk the locked core back through time.

Seeds from the current (2026) core in ToolsDB and reconstructs, for each year
2005..2025, the 1-Jan snapshot of every seed page:
  * existence that year (no revision before 1-Jan-Y -> page absent -> no row)
  * is_core that year (EXPANSIVE: core unless absent or positively demoted by an
    essay/proposed/historical banner — never reduced by mere regex misses)
  * the in-body wikilink graph among the seed set (edges-over-time)

Writes year-keyed rows into the SAME schema (node, link) as the current build,
so 2005..2025 sit alongside the 2026 slice. Resumable per year (skips years
already present). Raw wikitext cached by revid (reproducibility substrate).

Phase 2 (later): expand the node set with pages that were core historically but
aren't in the 2026 seed (fill-back via the year-Y link graph).

Snapshot rule: the revision in effect at Y-01-01T00:00:00Z.
Run on Toolforge (needs ToolsDB seed + outbound API). Creds from ~/replica.my.cnf.

Usage:
  python3 net_build_historical.py --wiki enwiki --from-year 2005 --to-year 2025
"""

import argparse
import configparser
import json
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

try:
    import pymysql
except ImportError:
    pymysql = None
try:
    import mwparserfromhell as mwp
except ImportError:
    mwp = None

UA = "WikimediaAnalysis/1.0 (research; https://github.com/lgelauff/wikimedia-analysis)"
_SSL = ssl.create_default_context()
CACHE = Path.home() / "policy_cache" / "raw"

# Approximate banner detection from raw wikitext (Phase 1). Template renames/aliases
# across 20 years mean this is a first approximation; refine with redirect resolution later.
CORE_BANNER = re.compile(
    r"\{\{\s*(policy|guideline|mos[ _]?guideline|style[ _-]?guideline|manual of style|"
    r"naming[ _]conventions?|subcat[ _]guideline|notability[ _]guideline|"
    r"procedural[ _]policy|content[ _]guideline|conduct[ _]guideline|editing[ _]guideline)\b",
    re.I)
ESSAY_BANNER = re.compile(
    r"\{\{\s*(essay|supplement|information[ _]page|wikipedia[ _]how-?to|wikiproject[ _]advice|"
    r"humorous[ _]essay|historical|proposed|failed[ _]proposal|rejected)\b", re.I)


# --------------------------------------------------------------------------- DB
def creds():
    p = Path.home() / "replica.my.cnf"
    if not p.exists(): return None
    c = configparser.ConfigParser(); c.read(p)
    return c["client"]["user"].strip("'\""), c["client"]["password"].strip("'\"")


def connect_toolsdb():
    if pymysql is None: sys.exit("pip install pymysql")
    if mwp is None: sys.exit("pip install mwparserfromhell")
    cr = creds()
    if cr is None:
        print("No ~/replica.my.cnf — run on Toolforge. Exiting cleanly."); sys.exit(0)
    u, pw = cr
    return pymysql.connect(host="tools.db.svc.wikimedia.cloud", user=u, password=pw,
                           database=f"{u}__policies", charset="utf8mb4", autocommit=True)


def connect_replica(wiki):
    cr = creds()
    if cr is None: return None
    u, pw = cr
    try:
        return pymysql.connect(host=f"{wiki}.analytics.db.svc.wikimedia.cloud",
                               user=u, password=pw, database=f"{wiki}_p",
                               charset="utf8mb4", autocommit=True)
    except Exception as e:
        print(f"  replica unreachable ({e}) — redirect resolution disabled", flush=True)
        return None


def redirect_aliases(rep, pages_by_key):
    """{(ns,title) of a redirect: target_page_id} for redirects pointing at the seed pages."""
    if rep is None: return {}
    alias = {}; keys = list(pages_by_key)
    for i in range(0, len(keys), 500):
        ch = keys[i:i+500]
        vals = ",".join(["(%s,%s)"] * len(ch))
        params = [x for k in ch for x in k]
        with rep.cursor() as cur:
            cur.execute(f"""
                SELECT r.rd_namespace, r.rd_title, p.page_namespace, p.page_title
                FROM redirect r JOIN page p ON p.page_id = r.rd_from
                WHERE (r.rd_namespace, r.rd_title) IN ({vals})""", params)
            for (rd_ns, rd_title, redir_ns, redir_title) in cur.fetchall():
                tgt = pages_by_key.get((rd_ns, dec(rd_title)))
                if tgt: alias[(redir_ns, dec(redir_title))] = tgt
    return alias


def dec(x): return x.decode() if isinstance(x, bytes) else x


# -------------------------------------------------------------------------- API
def api(wiki, params):
    lang = wiki[:-4] if wiki.endswith("wiki") else wiki
    params = {**params, "format": "json", "formatversion": "2", "maxlag": "5"}
    url = f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60, context=_SSL) as r:
                return json.loads(r.read())
        except Exception as e:
            wait = 5 * (2 ** attempt)
            print(f"    api retry ({e}) {wait}s", flush=True); time.sleep(wait)
    raise RuntimeError("API failed: " + url)


def siteinfo_ns(wiki):
    d = api(wiki, {"action": "query", "meta": "siteinfo",
                   "siprop": "namespaces|namespacealiases"})
    m = {}
    for ns in d["query"]["namespaces"].values():
        if ns["id"] < 0: continue
        for k in (ns.get("name", ""), ns.get("canonical", "")):
            if k: m[k.replace(" ", "_").lower()] = ns["id"]
    for a in d["query"].get("namespacealiases", []):
        m[a["alias"].replace(" ", "_").lower()] = a["id"]
    return m


def norm_title(s):
    s = s.split("#")[0].strip().lstrip(":").strip()
    if not s: return ""
    s = s.replace(" ", "_")
    return s[0].upper() + s[1:]


def parse_link(raw, nsmap):
    raw = raw.split("#")[0].strip().lstrip(":")
    if ":" in raw:
        pre, rest = raw.split(":", 1)
        ns = nsmap.get(pre.replace(" ", "_").lower())
        if ns is not None:
            return ns, norm_title(rest)
    return 0, norm_title(raw)


def year_revision(wiki, pid, year):
    """Return (revid, wikitext) in effect at Y-01-01, or (None, None) if absent."""
    data = api(wiki, {"action": "query", "pageids": str(pid), "prop": "revisions",
                      "rvstart": f"{year}-01-01T00:00:00Z", "rvdir": "older",
                      "rvlimit": "1", "rvprop": "ids|content", "rvslots": "main"})
    pages = data.get("query", {}).get("pages", [])
    if not pages or "revisions" not in pages[0]:
        return None, None
    rev = pages[0]["revisions"][0]
    revid = rev["revid"]
    cf = CACHE / wiki / f"{revid}.txt"
    if cf.exists():
        return revid, cf.read_text(encoding="utf-8")
    text = rev.get("slots", {}).get("main", {}).get("content", "")
    cf.parent.mkdir(parents=True, exist_ok=True)
    cf.write_text(text, encoding="utf-8")
    return revid, text


# ------------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wiki", default="enwiki")
    ap.add_argument("--seed-year", type=int, default=2026)
    ap.add_argument("--from-year", type=int, default=2005)
    ap.add_argument("--to-year", type=int, default=2025)
    ap.add_argument("--no-toolsdb", action="store_true")
    ap.add_argument("--sqlite", default=str(Path.home() / "policy_net_hist.db"))
    a = ap.parse_args()
    wiki = a.wiki
    db = connect_toolsdb()

    # seed = current core (page_id, title, namespace) from ToolsDB
    with db.cursor() as cur:
        cur.execute("SELECT page_id, title, namespace FROM node "
                    "WHERE wiki=%s AND year=%s AND confidence='core'", (wiki, a.seed_year))
        seed = [(pid, dec(t), ns) for pid, t, ns in cur.fetchall()]
    if not seed:
        sys.exit(f"no {a.seed_year} core in ToolsDB for {wiki} — run net_build_current first")
    seed_key = {(ns, t): pid for pid, t, ns in seed}
    rep = connect_replica(wiki)
    n_aliases = 0
    if rep is not None:
        aliases = redirect_aliases(rep, dict(seed_key))   # links via a redirect of a core page count
        seed_key.update(aliases); n_aliases = len(aliases)
    print(f"seed core ({a.seed_year}) = {len(seed):,} pages (+{n_aliases} redirect aliases)")
    nsmap = siteinfo_ns(wiki)

    import sqlite3
    sdb = sqlite3.connect(a.sqlite)
    sdb.executescript(
        "CREATE TABLE IF NOT EXISTS node(wiki,page_id,year,title,namespace,is_redirect,"
        "wikidata_qid,confidence,admitted_via,status_tier,PRIMARY KEY(wiki,year,page_id));"
        "CREATE TABLE IF NOT EXISTS link(wiki,year,from_page,to_ns,to_title,to_page,to_admitted);")

    def year_done(year):
        if not a.no_toolsdb:
            with db.cursor() as cur:
                cur.execute("SELECT 1 FROM node WHERE wiki=%s AND year=%s LIMIT 1", (wiki, year))
                return cur.fetchone() is not None
        return sdb.execute("SELECT 1 FROM node WHERE wiki=? AND year=? LIMIT 1",
                           (wiki, year)).fetchone() is not None

    for year in range(a.to_year, a.from_year - 1, -1):
        if year_done(year):
            print(f"{year}: already done — skip"); continue
        print(f"{year}: reconstructing …", flush=True)
        nodes, links = [], []
        n_exist = n_core = 0
        for i, (pid, title, ns) in enumerate(seed):
            revid, wt = year_revision(wiki, pid, year)
            if revid is None:
                continue                                  # page absent that year
            n_exist += 1
            # EXPANSIVE rule: every seed page is core NOW (2026, by construction), so
            # walking back it stays core unless there's POSITIVE counter-evidence that it
            # wasn't policy that year — i.e. it carried an essay/proposed/historical banner.
            # Mere absence of a detected policy banner is regex noise, NOT a demotion.
            demote = ESSAY_BANNER.search(wt)
            is_core = not demote
            if is_core: n_core += 1
            banner_seen = bool(CORE_BANNER.search(wt))     # explicit banner -> promotion signal
            tier = demote.group(1).lower().replace(" ", "_").replace("-", "") if demote else None
            nodes.append((wiki, pid, year, title, ns, 0, None,
                          "core" if is_core else "candidate",
                          ("status_template" if banner_seen else "inherited") if is_core else "demoted",
                          tier))
            seen = set()
            for wl in mwp.parse(wt).filter_wikilinks():
                lns, lt = parse_link(str(wl.title), nsmap)
                # MediaWiki titles are <=255 bytes; longer = parse artifact from malformed
                # wikitext (a stray [[ swallowing text). Skip empties/over-long.
                if not lt or len(lt.encode("utf-8")) > 255: continue
                if (lns, lt) in seen: continue
                seen.add((lns, lt))
                to_pid = seed_key.get((lns, lt))
                links.append((wiki, year, pid, lns, lt, to_pid, 1 if to_pid else 0))
            if (i + 1) % 50 == 0:
                print(f"    {i+1}/{len(seed)} pages", flush=True)

        # write the year (atomic-ish: delete then insert)
        sdb.execute("DELETE FROM node WHERE wiki=? AND year=?", (wiki, year))
        sdb.execute("DELETE FROM link WHERE wiki=? AND year=?", (wiki, year))
        sdb.executemany("INSERT INTO node VALUES(?,?,?,?,?,?,?,?,?,?)", nodes)
        sdb.executemany("INSERT INTO link VALUES(?,?,?,?,?,?,?)", links)
        sdb.commit()
        if not a.no_toolsdb:
            # atomic per-year write: node+link in ONE transaction so a mid-write
            # failure leaves the year empty (resume redoes it cleanly), never a
            # node-only partial that the year_done check would mistake for complete.
            db.begin()
            try:
                with db.cursor() as cur:
                    cur.execute("DELETE FROM node WHERE wiki=%s AND year=%s", (wiki, year))
                    cur.execute("DELETE FROM link WHERE wiki=%s AND year=%s", (wiki, year))
                    cur.executemany("INSERT INTO node VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", nodes)
                    for j in range(0, len(links), 1000):
                        cur.executemany("INSERT INTO link VALUES(%s,%s,%s,%s,%s,%s,%s)", links[j:j+1000])
                db.commit()
            except Exception:
                db.rollback(); raise
        core_links = sum(1 for l in links if l[6])
        print(f"  {year}: exist {n_exist} · core {n_core} · core->core links {core_links}", flush=True)

    print("\n=== done ===")
    print("year | existed | core | core->core links")
    src = sdb
    for year in range(a.from_year, a.to_year + 1):
        ex = src.execute("SELECT COUNT(*) FROM node WHERE wiki=? AND year=?", (wiki, year)).fetchone()[0]
        co = src.execute("SELECT COUNT(*) FROM node WHERE wiki=? AND year=? AND confidence='core'", (wiki, year)).fetchone()[0]
        cl = src.execute("SELECT COUNT(*) FROM link WHERE wiki=? AND year=? AND to_admitted=1", (wiki, year)).fetchone()[0]
        if ex:
            print(f"  {year}  {ex:>5}  {co:>5}  {cl:>6}")


if __name__ == "__main__":
    main()
