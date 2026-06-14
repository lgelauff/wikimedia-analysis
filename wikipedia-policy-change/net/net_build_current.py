#!/usr/bin/env python3
"""
net_build_current.py — clean-base build of the CURRENT policy network for one wiki.

Model (see docs/CLEAN_BASE_PROPOSAL.md):
  * ONE graph = in-body wikilinks parsed from WIKITEXT (not pagelinks — which is
    navbox-inflated). Categories/templates are node-level FACETS, never edges.
  * Confirmed/suspect tiers. Confirmed = status-template transclusion OR core-category
    membership OR Wikidata P31=Q4656150. Suspects = reached via SCORED indicator
    categories/navboxes (support/density vs the confirmed set), promotable later.

Pipeline:
  A. confirmed seed C  (core categories + status templates; Wikidata promotes later)
  B. scored category discovery -> indicator cats -> suspect members
  C. scored navbox discovery   -> indicator navboxes -> suspect targets + navbox_member
  D. admitted = C ∪ suspects (excl. ns0); page meta; QIDs; Wikidata P31 promotion
  E. link graph from wikitext (API + mwparserfromhell), matched against admitted
  F. facets: node_category, node_template(role), navbox_member
  G. write ToolsDB + SQLite

Admission/scoring use SQL (fast). Link graph uses the API (wikitext). Creds from
~/replica.my.cnf (never hardcoded). Runs on Toolforge; exits cleanly off-Toolforge.
"""

import argparse
import configparser
import json
from collections import Counter
import re
import sqlite3
import ssl
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

try:
    import pymysql
except ImportError:
    pymysql = None
try:
    import mwparserfromhell as mwp
except ImportError:
    mwp = None

WIKI_ROOTS = {
    "enwiki": "Wikipedia policies and guidelines",
    "dewiki": "Wikipedia:Richtlinien",
    "nlwiki": "Wikipedia:Beleid",
}
# Policy/guideline status banners → CORE (the "this IS policy/guideline" templates).
CORE_STATUS_TEMPLATES = {
    "enwiki": ["Policy", "Guideline", "MoS_guideline", "Subcat_guideline",
               "Naming_conventions", "Notability_guideline", "Procedural_policy",
               "Content_guideline", "Conduct_guideline", "Editing_guideline"],
}
# Essay / non-binding banners → demote to CANDIDATE (maybe), never core. An essay
# tag OVERRIDES policy-category membership (the page says "this is not policy").
ESSAY_MAYBE_TEMPLATES = {
    "enwiki": ["Essay", "Supplement", "Information_page", "Wikipedia_how-to",
               "WikiProject_advice", "Humorous_essay", "Historical", "Proposed",
               "Failed_proposal", "Rejected"],
}
ESSAY_TIER = {"Essay": "essay", "Humorous_essay": "essay", "Supplement": "supplement",
              "Information_page": "info", "Wikipedia_how-to": "howto",
              "WikiProject_advice": "advice", "Historical": "historical",
              "Proposed": "proposed", "Failed_proposal": "rejected", "Rejected": "rejected"}
EXCLUDE_NS = {0}
# Sandbox/archive subpages inherit a policy banner but aren't policy pages.
NOISE_SUBPAGE = re.compile(r"/(sandbox\d*|archive)", re.I)
Q_POLICY_PAGE = "Q4656150"      # Wikimedia project policies and guidelines page
Q_NAVBOX      = "Q11753321"     # Wikimedia navigational template
BATCH = 500
UA = "WikimediaAnalysis/1.0 (research; https://github.com/lgelauff/wikimedia-analysis)"
_SSL = ssl.create_default_context()


# --------------------------------------------------------------------------- DB
def creds():
    p = Path.home() / "replica.my.cnf"
    if not p.exists():
        return None
    c = configparser.ConfigParser(); c.read(p)
    return c["client"]["user"].strip("'\""), c["client"]["password"].strip("'\"")


def connect_replica(wiki):
    if pymysql is None: sys.exit("pip install pymysql")
    if mwp is None: sys.exit("pip install mwparserfromhell")
    cr = creds()
    if cr is None:
        print("No ~/replica.my.cnf — run on Toolforge. Exiting cleanly."); sys.exit(0)
    u, pw = cr
    try:
        return pymysql.connect(host=f"{wiki}.analytics.db.svc.wikimedia.cloud",
                               user=u, password=pw, database=f"{wiki}_p",
                               charset="utf8mb4", autocommit=True)
    except Exception as e:
        print(f"Replica unreachable ({e}) — run on Toolforge. Exiting cleanly."); sys.exit(0)


def connect_toolsdb():
    u, pw = creds()
    return pymysql.connect(host="tools.db.svc.wikimedia.cloud", user=u, password=pw,
                           database=f"{u}__policies", charset="utf8mb4", autocommit=True)


def q(conn, sql, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params or ()); return cur.fetchall()


def batched(seq, n=BATCH):
    seq = list(seq)
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def dec(x):
    return x.decode() if isinstance(x, bytes) else x


def git_commit():
    """Short HEAD of the repo this script lives in (pins the build for reproduction)."""
    try:
        import subprocess
        return subprocess.check_output(
            ["git", "-C", str(Path(__file__).resolve().parent), "rev-parse", "--short", "HEAD"],
            text=True, timeout=5).strip()
    except Exception:
        return "unknown"


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
            print(f"    api retry ({e}) in {wait}s"); time.sleep(wait)
    raise RuntimeError("API failed: " + url)


# ------------------------------------------------------------ category helpers
def subcats(rep, cat_titles):
    out = set()
    for ch in batched(list(cat_titles)):
        ph = ",".join(["%s"] * len(ch))
        for (_p, child) in q(rep, f"""
            SELECT lt.lt_title, sub.page_title
            FROM linktarget lt
            JOIN categorylinks cl ON cl.cl_target_id=lt.lt_id AND cl.cl_type='subcat'
            JOIN page sub ON sub.page_id=cl.cl_from AND sub.page_namespace=14
            WHERE lt.lt_namespace=14 AND lt.lt_title IN ({ph})""", ch):
            out.add(dec(child))
    return out


def cat_members(rep, cat_titles):
    """{category_title: set(page_id)} for cl_type='page'."""
    res = {}
    for ch in batched(list(cat_titles)):
        ph = ",".join(["%s"] * len(ch))
        for (pid, cat) in q(rep, f"""
            SELECT cl.cl_from, lt.lt_title
            FROM linktarget lt
            JOIN categorylinks cl ON cl.cl_target_id=lt.lt_id AND cl.cl_type='page'
            WHERE lt.lt_namespace=14 AND lt.lt_title IN ({ph})""", ch):
            res.setdefault(dec(cat), set()).add(pid)
    return res


def cat_member_counts(rep, cat_titles):
    """{category_title: total member pages} via grouped COUNT (no member lists — avoids OOM)."""
    res = {}
    for ch in batched(list(cat_titles)):
        ph = ",".join(["%s"] * len(ch))
        for (cat, n) in q(rep, f"""
            SELECT lt.lt_title, COUNT(*)
            FROM linktarget lt
            JOIN categorylinks cl ON cl.cl_target_id=lt.lt_id AND cl.cl_type='page'
            WHERE lt.lt_namespace=14 AND lt.lt_title IN ({ph})
            GROUP BY lt.lt_title""", ch):
            res[dec(cat)] = n
    return res


def cats_of(rep, page_ids):
    """{page_id: set(category_title)} for the given pages."""
    res = {}
    for ch in batched(list(page_ids)):
        ph = ",".join(["%s"] * len(ch))
        for (pid, cat) in q(rep, f"""
            SELECT cl.cl_from, lt.lt_title
            FROM categorylinks cl JOIN linktarget lt ON cl.cl_target_id=lt.lt_id
            WHERE lt.lt_namespace=14 AND cl.cl_from IN ({ph})""", ch):
            res.setdefault(pid, set()).add(dec(cat))
    return res


# ------------------------------------------------------------ template helpers
def templates_of(rep, page_ids):
    """{page_id: set(template_title ns10)}."""
    res = {}
    for ch in batched(list(page_ids)):
        ph = ",".join(["%s"] * len(ch))
        for (frm, t) in q(rep, f"""
            SELECT tl.tl_from, lt.lt_title
            FROM templatelinks tl JOIN linktarget lt ON tl.tl_target_id=lt.lt_id
            WHERE lt.lt_namespace=10 AND tl.tl_from IN ({ph})""", ch):
            res.setdefault(frm, set()).add(dec(t))
    return res


def transcluding(rep, template_titles, ns=None):
    """{page_id: set(matched template titles)} for hosts transcluding any ns10 template.
    Optional ns filter restricts the HOST namespace."""
    res = {}
    if not template_titles:
        return res
    for ch in batched(list(template_titles)):
        ph = ",".join(["%s"] * len(ch))
        nsf = " AND p.page_namespace=%s" if ns is not None else ""
        params = ([*ch, ns] if ns is not None else ch)
        for (frm, t) in q(rep, f"""
            SELECT tl.tl_from, lt.lt_title
            FROM templatelinks tl
            JOIN linktarget lt ON tl.tl_target_id=lt.lt_id
            JOIN page p ON p.page_id=tl.tl_from
            WHERE lt.lt_namespace=10 AND lt.lt_title IN ({ph}){nsf}""", params):
            res.setdefault(frm, set()).add(dec(t))
    return res


def title_to_pageid(rep, ns, titles):
    out = {}
    for ch in batched(list(titles)):
        ph = ",".join(["%s"] * len(ch))
        for (pid, t) in q(rep, f"SELECT page_id,page_title FROM page "
                               f"WHERE page_namespace=%s AND page_title IN ({ph})", [ns, *ch]):
            out[dec(t)] = pid
    return out


def template_targets(rep, template_pageids):
    """{template_page_id: set(target page_id)} — what each template links to (pagelinks)."""
    res = {}
    for ch in batched(list(template_pageids)):
        ph = ",".join(["%s"] * len(ch))
        for (frm, ns, t) in q(rep, f"""
            SELECT pl.pl_from, lt.lt_namespace, lt.lt_title
            FROM pagelinks pl JOIN linktarget lt ON pl.pl_target_id=lt.lt_id
            WHERE pl.pl_from IN ({ph})""", ch):
            res.setdefault(frm, []).append((ns, dec(t)))
    return res


# ------------------------------------------------------------ page meta / qids
def page_meta(rep, page_ids):
    meta = {}
    for ch in batched(list(page_ids)):
        ph = ",".join(["%s"] * len(ch))
        for pid, ns, title, isred in q(rep,
                f"SELECT page_id,page_namespace,page_title,page_is_redirect "
                f"FROM page WHERE page_id IN ({ph})", ch):
            meta[pid] = {"ns": ns, "title": dec(title), "is_redirect": int(isred)}
    return meta


def qids(rep, page_ids):
    out = {}
    for ch in batched(list(page_ids)):
        ph = ",".join(["%s"] * len(ch))
        for pid, val in q(rep, f"SELECT pp_page,pp_value FROM page_props "
                               f"WHERE pp_propname='wikibase_item' AND pp_page IN ({ph})", ch):
            out[pid] = dec(val)
    return out


def wikidata_p31(qid_list):
    """{qid: set(P31 Q-ids)} via wbgetentities (batches of 50)."""
    out = {}
    base = "https://www.wikidata.org/w/api.php"
    for ch in batched(qid_list, 50):
        url = base + "?" + urllib.parse.urlencode(
            {"action": "wbgetentities", "ids": "|".join(ch),
             "props": "claims", "format": "json"})
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=60, context=_SSL) as r:
                data = json.loads(r.read())
        except Exception as e:
            print(f"    wikidata retry skip ({e})"); continue
        for qid, ent in data.get("entities", {}).items():
            vals = set()
            for c in ent.get("claims", {}).get("P31", []):
                try: vals.add(c["mainsnak"]["datavalue"]["value"]["id"])
                except (KeyError, TypeError): pass
            out[qid] = vals
        time.sleep(0.5)
    return out


# ------------------------------------------------------------- wikitext links
def norm_title(s):
    s = s.strip().lstrip(":").strip()
    if not s: return ""
    s = s.replace(" ", "_")
    return s[0].upper() + s[1:]


def siteinfo_ns(wiki):
    data = api(wiki, {"action": "query", "meta": "siteinfo",
                      "siprop": "namespaces|namespacealiases"})
    m = {}
    for ns in data["query"]["namespaces"].values():
        if ns["id"] < 0: continue
        for key in (ns.get("name", ""), ns.get("canonical", "")):
            if key: m[key.replace(" ", "_").lower()] = ns["id"]
    for a in data["query"].get("namespacealiases", []):
        m[a["alias"].replace(" ", "_").lower()] = a["id"]
    return m


def parse_link(raw, nsmap):
    """raw wikilink title -> (ns, normalized_title)."""
    raw = raw.split("#")[0].strip().lstrip(":")
    if ":" in raw:
        pre, rest = raw.split(":", 1)
        ns = nsmap.get(pre.replace(" ", "_").lower())
        if ns is not None:
            return ns, norm_title(rest)
    return 0, norm_title(raw)


def fetch_wikitext(wiki, page_ids):
    """{page_id: wikitext} via API (batches of 50)."""
    out = {}
    for ch in batched(list(page_ids), 50):
        data = api(wiki, {"action": "query", "pageids": "|".join(map(str, ch)),
                          "prop": "revisions", "rvprop": "content", "rvslots": "main"})
        for pg in data.get("query", {}).get("pages", []):
            try:
                out[pg["pageid"]] = pg["revisions"][0]["slots"]["main"]["content"]
            except (KeyError, IndexError):
                pass
        time.sleep(0.3)
    return out


# --------------------------------------------------------------- role tagging
_STATUS_CAT = re.compile(r"polic|guideline|richtlin|beleid", re.I)
_NAV_CAT    = re.compile(r"navigat|navbox|sidebar|zijbalk", re.I)
_NOISE_NAME = re.compile(r"^(cite|citation|reflist|sfn|harv|infobox|navbar|"
                         r"shortcut|hatnote|cleanup|ambox|tmbox)", re.I)


def tag_role(name, own_cats, p31, is_scored_navbox):
    cats = " ".join(own_cats)
    if is_scored_navbox or p31 == Q_NAVBOX or _NAV_CAT.search(cats):
        return "navigation"
    if _STATUS_CAT.search(cats):
        return "status"
    if _NOISE_NAME.match(name):
        return "noise"
    return "noise"


# -------------------------------------------------------------------- writers
DDL_SQLITE = """
CREATE TABLE IF NOT EXISTS node(wiki,page_id,year,title,namespace,is_redirect,wikidata_qid,confidence,admitted_via,status_tier,PRIMARY KEY(wiki,year,page_id));
CREATE TABLE IF NOT EXISTS link(wiki,year,from_page,to_ns,to_title,to_page,to_admitted);
CREATE TABLE IF NOT EXISTS node_category(wiki,year,page_id,category_title);
CREATE TABLE IF NOT EXISTS node_template(wiki,year,page_id,template_title,role);
CREATE TABLE IF NOT EXISTS navbox_member(wiki,year,page_id,navbox_title);
CREATE TABLE IF NOT EXISTS category_registry(wiki,year,category_title,support,n_members,density,is_indicator,PRIMARY KEY(wiki,year,category_title));
CREATE TABLE IF NOT EXISTS template_registry(wiki,year,template_title,role,support,density,is_indicator,PRIMARY KEY(wiki,year,template_title));
CREATE TABLE IF NOT EXISTS provenance(wiki,year,page_id,role,evidence_type,evidence_title,support,density);
CREATE TABLE IF NOT EXISTS build_run(wiki,year,built_at,git_commit,source,n_confirmed,n_suspect,n_links,s_min,d_min);
"""
TABLES = ["node", "link", "node_category", "node_template", "navbox_member",
          "category_registry", "template_registry", "provenance", "build_run"]


def write_sqlite(path, wiki, year, data):
    db = sqlite3.connect(path)
    # auto-heal a stale-schema mirror: if `node` exists with the wrong column count,
    # drop ALL tables and recreate (the file is a disposable latest mirror; the
    # immutable per-build archive preserves history).
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='node'").fetchone():
        ncols = len(db.execute("PRAGMA table_info(node)").fetchall())
        if ncols != 10:
            print(f"  (stale SQLite schema: node has {ncols} cols, expected 10 — recreating)")
            for (t,) in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
                db.execute(f"DROP TABLE IF EXISTS {t}")
    db.executescript(DDL_SQLITE)
    for t in TABLES:
        db.execute(f"DELETE FROM {t} WHERE wiki=? AND year=?", (wiki, year))
    db.executemany("INSERT INTO node VALUES(?,?,?,?,?,?,?,?,?,?)", data["node"])
    db.executemany("INSERT INTO link VALUES(?,?,?,?,?,?,?)", data["link"])
    db.executemany("INSERT INTO node_category VALUES(?,?,?,?)", data["node_category"])
    db.executemany("INSERT INTO node_template VALUES(?,?,?,?,?)", data["node_template"])
    db.executemany("INSERT INTO navbox_member VALUES(?,?,?,?)", data["navbox_member"])
    db.executemany("INSERT INTO category_registry VALUES(?,?,?,?,?,?,?)", data["category_registry"])
    db.executemany("INSERT INTO template_registry VALUES(?,?,?,?,?,?,?)", data["template_registry"])
    db.executemany("INSERT INTO provenance VALUES(?,?,?,?,?,?,?,?)", data["provenance"])
    db.execute("INSERT INTO build_run VALUES(?,?,?,?,?,?,?,?,?,?)", data["build_run"])
    db.commit(); db.close(); print(f"  wrote SQLite -> {path}")


def write_toolsdb(wiki, year, data):
    conn = connect_toolsdb()
    with conn.cursor() as cur:
        for t in TABLES:
            cur.execute(f"DELETE FROM {t} WHERE wiki=%s AND year=%s", (wiki, year))
        cur.executemany("INSERT INTO node VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", data["node"])
        for ch in batched(data["link"], 1000):
            cur.executemany("INSERT INTO link VALUES(%s,%s,%s,%s,%s,%s,%s)", ch)
        for ch in batched(data["node_category"], 1000):
            cur.executemany("INSERT INTO node_category VALUES(%s,%s,%s,%s)", ch)
        for ch in batched(data["node_template"], 1000):
            cur.executemany("INSERT INTO node_template VALUES(%s,%s,%s,%s,%s)", ch)
        for ch in batched(data["navbox_member"], 1000):
            cur.executemany("INSERT INTO navbox_member VALUES(%s,%s,%s,%s)", ch)
        cur.executemany("INSERT INTO category_registry VALUES(%s,%s,%s,%s,%s,%s,%s)", data["category_registry"])
        cur.executemany("INSERT INTO template_registry VALUES(%s,%s,%s,%s,%s,%s,%s)", data["template_registry"])
        for ch in batched(data["provenance"], 1000):
            cur.executemany("INSERT INTO provenance VALUES(%s,%s,%s,%s,%s,%s,%s,%s)", ch)
        cur.execute("INSERT INTO build_run VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", data["build_run"])
    conn.close(); print("  wrote ToolsDB")


# ----------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wiki", default="enwiki")
    ap.add_argument("--year", type=int, default=2026)
    ap.add_argument("--root", default=None)
    ap.add_argument("--s-min", type=int, default=3)
    ap.add_argument("--d-min", type=float, default=0.10)
    ap.add_argument("--no-toolsdb", action="store_true")
    ap.add_argument("--no-wikidata", action="store_true")
    ap.add_argument("--sqlite", default=str(Path.home() / "policy_net.db"))
    a = ap.parse_args()
    wiki, year = a.wiki, a.year
    root = a.root or WIKI_ROOTS.get(wiki)
    if not root: sys.exit(f"no root for {wiki}; pass --root")
    core_t = CORE_STATUS_TEMPLATES.get(wiki, [])
    essay_t = ESSAY_MAYBE_TEMPLATES.get(wiki, [])
    rep = connect_replica(wiki)
    print(f"=== clean build: {wiki} {year} root='{root}' s_min={a.s_min} d_min={a.d_min} ===")

    # A. CORE seed — project-ns pages carrying a policy/guideline status banner,
    #    minus essay-tagged (an essay/supplement/historical tag OVERRIDES -> candidate).
    print("A. core seed …")
    core_host = transcluding(rep, core_t, ns=4)      # {pid: {tmpl}} in project ns
    essay_host = transcluding(rep, essay_t)          # {pid: {tmpl}} any ns
    essay_pids = set(essay_host)
    core = set(core_host) - essay_pids
    via = {pid: "status_template" for pid in core}
    tier_of = {}
    for pid, ts in essay_host.items():
        tier_of[pid] = next((ESSAY_TIER[t] for t in ts if t in ESSAY_TIER), "essay")
    print(f"  core (policy/guideline banner, ns4, non-essay) = {len(core):,}; essay-tagged = {len(essay_pids):,}")

    # B. scored category discovery -> expansion candidates (anchored on core)
    print("B. category scoring …")
    support_by_cat = Counter()
    for cs in cats_of(rep, core).values():
        for c in cs:
            support_by_cat[c] += 1
    cand_cats = list(support_by_cat)
    ncounts = cat_member_counts(rep, cand_cats)      # cheap COUNT, no member lists
    cat_reg, ind_cats, cat_score = [], set(), {}
    for cat in cand_cats:
        supp = support_by_cat[cat]; n = ncounts.get(cat, 0)
        dens = supp / n if n else 0
        is_ind = supp >= a.s_min and dens >= a.d_min
        if is_ind: ind_cats.add(cat); cat_score[cat] = (supp, round(dens, 4))
        cat_reg.append((wiki, year, cat, supp, n, round(dens, 4), int(is_ind)))
    ind_members = cat_members(rep, ind_cats)         # member lists ONLY for indicators
    susp_cat, prov = set(), []                        # prov = per-node evidence trail
    for cat in ind_cats:
        for pid in ind_members.get(cat, set()) - core:
            susp_cat.add(pid)
            prov.append([pid, "candidate", "scored_category", cat, *cat_score[cat]])
    print(f"  candidate cats {len(cand_cats):,} · indicators {len(ind_cats):,} · territory {len(susp_cat):,}")

    # C. scored navbox discovery -> expansion candidates
    print("C. navbox scoring …")
    tcount = Counter()
    for s in templates_of(rep, core).values():
        for t in s: tcount[t] += 1
    cand_nav_titles = [t for t, n in tcount.items() if n >= 2]
    nav_pid = title_to_pageid(rep, 10, cand_nav_titles)
    tgt = template_targets(rep, set(nav_pid.values()))
    tmpl_reg, ind_navbox_titles, susp_nav, navbox_members_rows = [], set(), set(), []
    nav_score = {}
    cmeta = page_meta(rep, core)
    c_key = {(m["ns"], m["title"]): pid for pid, m in cmeta.items()}
    for tt, tp in nav_pid.items():
        targets = tgt.get(tp, [])
        tpids = {c_key.get(k) for k in targets if k in c_key}; tpids.discard(None)
        supp = len(tpids); n = len(targets); dens = supp / n if n else 0
        is_ind = supp >= a.s_min and dens >= a.d_min
        if is_ind: ind_navbox_titles.add(tt); nav_score[tt] = (supp, round(dens, 4))
        tmpl_reg.append((wiki, year, tt, "navigation" if is_ind else "noise",
                         supp, round(dens, 4), int(is_ind)))
    # resolve indicator-navbox targets -> page_ids; attribute each to its navbox(es)
    target_to_navboxes = {}
    for tt in ind_navbox_titles:
        for key in tgt.get(nav_pid[tt], []):
            target_to_navboxes.setdefault(key, set()).add(tt)
    for ns in {k[0] for k in target_to_navboxes}:
        tpid = title_to_pageid(rep, ns, [t for (n, t) in target_to_navboxes if n == ns])
        for t, pid in tpid.items():
            if pid in core: continue
            susp_nav.add(pid)
            for tt in target_to_navboxes[(ns, t)]:
                prov.append([pid, "candidate", "scored_navbox", tt, *nav_score[tt]])
    print(f"  candidate navboxes {len(cand_nav_titles):,} · indicators {len(ind_navbox_titles):,} · territory {len(susp_nav):,}")

    # D. candidates (expansion territory) + admitted set
    candidates = (susp_cat | susp_nav | essay_pids) - core
    admitted = core | candidates
    meta = page_meta(rep, admitted)
    admitted = {p for p in admitted if p in meta and meta[p]["ns"] not in EXCLUDE_NS
                and not NOISE_SUBPAGE.search(meta[p]["title"])}
    core &= admitted; candidates = admitted - core
    qid = qids(rep, admitted)

    # Wikidata: P31=Q4656150 promotes a candidate into CORE (project-ns, non-essay)
    if not a.no_wikidata and qid:
        print("D. wikidata P31 promotion …")
        p31 = wikidata_p31(list(qid.values()))
        for pid in list(candidates):
            if (Q_POLICY_PAGE in p31.get(qid.get(pid, ""), set())
                    and meta[pid]["ns"] == 4 and pid not in essay_pids):
                core.add(pid); candidates.discard(pid); via[pid] = "wikidata"
    for pid in candidates:
        via.setdefault(pid, "essay" if pid in essay_pids else
                       "scored_navbox" if pid in susp_nav else "scored_category")
    # evidence trail for core nodes + essays (scored evidence already in prov)
    for pid in core:
        et = via.get(pid, "status_template")
        title = (Q_POLICY_PAGE if et == "wikidata"
                 else next(iter(core_host.get(pid, {"?"})), "?"))
        prov.append([pid, "core", et, title, None, None])
    for pid in (essay_pids & admitted) - core:
        prov.append([pid, "candidate", "essay",
                     next(iter(essay_host.get(pid, {"?"})), "?"), None, None])
    prov = [[wiki, year, *r] for r in prov if r[0] in admitted]
    print(f"  admitted {len(admitted):,}  (core {len(core):,} · candidate {len(candidates):,}) · prov rows {len(prov):,}")

    # E. link graph from wikitext — CORE only (the live graph is core->core)
    print("E. wikitext links (core) …")
    nsmap = siteinfo_ns(wiki)
    core_key = {(meta[p]["ns"], meta[p]["title"]): p for p in core}
    wikitext = fetch_wikitext(wiki, core)
    links = []
    for pid in core:
        wt = wikitext.get(pid)
        if not wt: continue
        seen = set()
        for wl in mwp.parse(wt).filter_wikilinks():
            ns, title = parse_link(str(wl.title), nsmap)
            if (ns, title) in seen: continue
            seen.add((ns, title))
            to_pid = core_key.get((ns, title))
            links.append((wiki, year, pid, ns, title, to_pid, 1 if to_pid else 0))
    print(f"  links {len(links):,} (core->core {sum(1 for l in links if l[6]):,})")

    # F. facets — for CORE (the live set)
    print("F. facets …")
    nc = [(wiki, year, p, c) for p, cs in cats_of(rep, core).items() for c in cs]
    tpl_all = templates_of(rep, core)
    all_tmpl_titles = {t for s in tpl_all.values() for t in s}
    tmpl_pid = title_to_pageid(rep, 10, all_tmpl_titles)
    tmpl_owncats = cats_of(rep, set(tmpl_pid.values()))
    tmpl_qid = qids(rep, set(tmpl_pid.values())) if not a.no_wikidata else {}
    tmpl_qp31 = wikidata_p31(list(tmpl_qid.values())) if tmpl_qid else {}
    role_of = {}
    for t in all_tmpl_titles:
        tp = tmpl_pid.get(t)
        owncats = tmpl_owncats.get(tp, set()) if tp else set()
        p31 = next(iter(tmpl_qp31.get(tmpl_qid.get(tp, ""), set())), None) if tp else None
        role_of[t] = tag_role(t, owncats, p31, t in ind_navbox_titles)
    nt = [(wiki, year, p, t, role_of.get(t, "noise"))
          for p, ts in tpl_all.items() for t in ts]
    for tt in ind_navbox_titles:
        for (ns, title) in tgt.get(nav_pid[tt], []):
            mp = core_key.get((ns, title))
            if mp: navbox_members_rows.append((wiki, year, mp, tt))

    built_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    commit = git_commit()
    nodes = [(wiki, p, year, meta[p]["title"], meta[p]["ns"], meta[p]["is_redirect"],
              qid.get(p), "core" if p in core else "candidate",
              via.get(p, "scored_category"), tier_of.get(p)) for p in admitted]
    data = {
        "node": nodes, "link": links, "node_category": nc, "node_template": nt,
        "navbox_member": navbox_members_rows,
        "category_registry": cat_reg, "template_registry": tmpl_reg, "provenance": prov,
        "build_run": (wiki, year, built_at, commit, "replica+api:current",
                      len(core), len(candidates), len(links), a.s_min, a.d_min),
    }

    print("G. writing …")
    write_sqlite(a.sqlite, wiki, year, data)
    if not a.no_toolsdb: write_toolsdb(wiki, year, data)
    # immutable per-build dump (audit / backtrace) — never overwritten
    try:
        import shutil
        arch = Path.home() / "policy_net_archive"; arch.mkdir(exist_ok=True)
        stamp = built_at.replace(":", "").replace("-", "")
        dst = arch / f"{wiki}_{year}_{stamp}_{commit}.sqlite"
        shutil.copy(a.sqlite, dst); print(f"  archived -> {dst}")
    except Exception as e:
        print(f"  archive skipped ({e})")

    print("\n=== summary ===")
    print(f"  CORE {len(core):,} · candidate(territory) {len(candidates):,} · total {len(admitted):,}")
    print(f"  core links {len(links):,} (core->core {sum(1 for l in links if l[6]):,})")
    print(f"  indicator cats {len(ind_cats):,} · indicator navboxes {len(ind_navbox_titles):,}")
    nsp = {}
    for n in nodes:
        if n[7] == "core": nsp[n[4]] = nsp.get(n[4], 0) + 1
    print(f"  CORE namespace spread {dict(sorted(nsp.items()))}")
    roles = Counter(r[3] for r in tmpl_reg)
    print(f"  template roles (registry) {dict(roles)}")
    print(f"  essay-tagged (-> candidate) {len(essay_pids & admitted):,}")
    print(f"  core with QID {sum(1 for n in nodes if n[7]=='core' and n[6]):,}")


if __name__ == "__main__":
    main()
