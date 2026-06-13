#!/usr/bin/env python3
"""
net_build_current.py — M1: build the CURRENT (2026) structural policy network for
one wiki from the Toolforge replica link tables. No dumps, no LLM.

Pipeline (Tier-1 structural, rule-gate only):
  A. BFS the category tree from the seed root ('Wikipedia policies and guidelines'),
     bounded by --max-depth, to discover indicator categories (language-agnostic:
     names are discovered, not hardcoded).
  B. Admit pages: members (cl_type='page') of any indicator category, UNION pages
     transcluding a seed status template. Exclude mainspace (ns 0).
  C. Edges for admitted nodes: category membership, template transclusion, wikilinks.
     Resolve targets -> page_id (and redirects -> canonical); flag policy->policy.
  D. QIDs from page_props (wikibase_item).
  E. Write node / edge / *_registry / build_run to ToolsDB (REPLACE) + a local SQLite mirror.

Schema confirmed live (Jun 2026): categorylinks.cl_target_id / templatelinks.tl_target_id /
pagelinks.pl_target_id -> linktarget(lt_id, lt_namespace, lt_title). cl_to is gone.

Runs on Toolforge (replica access is Toolforge-only). Locally it detects the missing
replica and exits cleanly. Resumable-ish: writes are idempotent (REPLACE INTO);
re-running rebuilds the slice. Reads DB creds from ~/replica.my.cnf — never hardcoded.

Usage (on the bastion, in a venv with pymysql):
  python3 net_build_current.py --wiki enwiki --year 2026 --max-depth 4
  python3 net_build_current.py --wiki enwiki --year 2026 --no-toolsdb --sqlite /tmp/net.db
"""

import argparse
import configparser
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import pymysql
except ImportError:
    pymysql = None

# Seed indicators (BOOTSTRAP only — the operative set is discovered from the tree).
# Per-wiki root category (resolved from enwiki langlinks; ns-14 title WITHOUT the
# localized "Category:" prefix). Category-BFS admission is language-agnostic from here.
WIKI_ROOTS = {
    "enwiki": "Wikipedia policies and guidelines",
    "dewiki": "Wikipedia:Richtlinien",
    "nlwiki": "Wikipedia:Beleid",
}
SEED_ROOT_CATEGORY = WIKI_ROOTS["enwiki"]

# Status-template seeds are en-only for now; on other wikis these find nothing and
# admission falls back to category-BFS (the primary, language-agnostic path).
# Localized status templates will be discovered later (M6 / registry bootstrap).
WIKI_STATUS_TEMPLATES = {
    "enwiki": ["Policy", "Guideline", "MoS_guideline", "Subcat_guideline",
               "Naming_conventions", "Notability_guideline", "Procedural_policy"],
}
SEED_STATUS_TEMPLATES = WIKI_STATUS_TEMPLATES["enwiki"]
EXCLUDE_NS = {0}                    # exclusion-based: drop only mainspace
BATCH = 500


# ---------------------------------------------------------------------------
# DB plumbing
# ---------------------------------------------------------------------------

def creds():
    cfg = configparser.ConfigParser()
    p = Path.home() / "replica.my.cnf"
    if not p.exists():
        return None
    cfg.read(p)
    return cfg["client"]["user"].strip("'\""), cfg["client"]["password"].strip("'\"")


def connect_replica(wiki):
    if pymysql is None:
        sys.exit("pymysql not installed — create a venv and `pip install pymysql`.")
    c = creds()
    if c is None:
        print("No ~/replica.my.cnf found — this script must run on Toolforge. Exiting cleanly.")
        sys.exit(0)
    user, pw = c
    try:
        return pymysql.connect(
            host=f"{wiki}.analytics.db.svc.wikimedia.cloud",
            user=user, password=pw, database=f"{wiki}_p",
            charset="utf8mb4", autocommit=True,
        )
    except Exception as e:
        print(f"Cannot reach replica ({e}) — must run on Toolforge. Exiting cleanly.")
        sys.exit(0)


def connect_toolsdb():
    user, pw = creds()
    return pymysql.connect(host="tools.db.svc.wikimedia.cloud", user=user, password=pw,
                           database=f"{user}__policies", charset="utf8mb4", autocommit=True)


def q(conn, sql, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchall()


def batched(seq, n=BATCH):
    seq = list(seq)
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


# ---------------------------------------------------------------------------
# A. Category-tree BFS  (discover indicator categories)
# ---------------------------------------------------------------------------

def discover_categories(rep, root, max_depth):
    """BFS subcategories from root. Returns {category_title: depth}. Handles cycles."""
    root = root.replace(" ", "_")
    seen = {root: 0}
    frontier = [root]
    depth = 0
    while frontier and depth < max_depth:
        depth += 1
        nxt = []
        for chunk in batched(frontier):
            # subcategories: pages (ns14) linked to a frontier category with cl_type='subcat'
            ph = ",".join(["%s"] * len(chunk))
            rows = q(rep, f"""
                SELECT lt.lt_title AS parent, sub.page_title AS child
                FROM linktarget lt
                JOIN categorylinks cl ON cl.cl_target_id = lt.lt_id AND cl.cl_type='subcat'
                JOIN page sub ON sub.page_id = cl.cl_from AND sub.page_namespace = 14
                WHERE lt.lt_namespace = 14 AND lt.lt_title IN ({ph})
            """, chunk)
            for _parent, child in rows:
                child = child.decode() if isinstance(child, bytes) else child
                if child not in seen:
                    seen[child] = depth
                    nxt.append(child)
        frontier = nxt
        print(f"  BFS depth {depth}: +{len(nxt)} categories (total {len(seen)})")
    return seen


def pages_in_categories(rep, cats):
    """Admitted page_ids that are members (cl_type='page') of any indicator category."""
    admitted = {}   # page_id -> set(category_title)
    for chunk in batched(list(cats)):
        ph = ",".join(["%s"] * len(chunk))
        rows = q(rep, f"""
            SELECT cl.cl_from AS pid, lt.lt_title AS cat
            FROM linktarget lt
            JOIN categorylinks cl ON cl.cl_target_id = lt.lt_id AND cl.cl_type='page'
            WHERE lt.lt_namespace = 14 AND lt.lt_title IN ({ph})
        """, chunk)
        for pid, cat in rows:
            cat = cat.decode() if isinstance(cat, bytes) else cat
            admitted.setdefault(pid, set()).add(cat)
    return admitted


# ---------------------------------------------------------------------------
# B. Template-transclusion admission
# ---------------------------------------------------------------------------

def template_page_ids(rep, names):
    rows = []
    for chunk in batched(names):
        ph = ",".join(["%s"] * len(chunk))
        rows += q(rep, f"SELECT page_id, page_title FROM page "
                       f"WHERE page_namespace=10 AND page_title IN ({ph})", chunk)
    return {(t.decode() if isinstance(t, bytes) else t): pid for pid, t in rows}


def pages_transcluding(rep, template_titles):
    """Admitted page_ids transcluding any seed status template (via templatelinks)."""
    admitted = set()
    for chunk in batched(template_titles):
        ph = ",".join(["%s"] * len(chunk))
        rows = q(rep, f"""
            SELECT tl.tl_from AS pid
            FROM linktarget lt
            JOIN templatelinks tl ON tl.tl_target_id = lt.lt_id
            WHERE lt.lt_namespace = 10 AND lt.lt_title IN ({ph})
        """, chunk)
        admitted.update(r[0] for r in rows)
    return admitted


# ---------------------------------------------------------------------------
# Page metadata, redirects, QIDs
# ---------------------------------------------------------------------------

def page_meta(rep, page_ids):
    meta = {}
    for chunk in batched(list(page_ids)):
        ph = ",".join(["%s"] * len(chunk))
        for pid, ns, title, isred in q(rep,
                f"SELECT page_id,page_namespace,page_title,page_is_redirect "
                f"FROM page WHERE page_id IN ({ph})", chunk):
            meta[pid] = {"ns": ns,
                         "title": title.decode() if isinstance(title, bytes) else title,
                         "is_redirect": int(isred)}
    return meta


def resolve_titles_to_pageids(rep, ns_title_pairs):
    """Map (ns,title) -> page_id for edge-target resolution."""
    out = {}
    by_ns = {}
    for ns, title in ns_title_pairs:
        by_ns.setdefault(ns, set()).add(title)
    for ns, titles in by_ns.items():
        for chunk in batched(list(titles)):
            ph = ",".join(["%s"] * len(chunk))
            for pid, t in q(rep, f"SELECT page_id,page_title FROM page "
                                 f"WHERE page_namespace=%s AND page_title IN ({ph})",
                            [ns, *chunk]):
                t = t.decode() if isinstance(t, bytes) else t
                out[(ns, t)] = pid
    return out


def qids(rep, page_ids):
    out = {}
    for chunk in batched(list(page_ids)):
        ph = ",".join(["%s"] * len(chunk))
        for pid, val in q(rep, f"SELECT pp_page,pp_value FROM page_props "
                               f"WHERE pp_propname='wikibase_item' AND pp_page IN ({ph})", chunk):
            out[pid] = val.decode() if isinstance(val, bytes) else val
    return out


# ---------------------------------------------------------------------------
# C. Edges
# ---------------------------------------------------------------------------

def collect_edges(rep, admitted_ids):
    """For each admitted page, its category/template/wikilink targets (ns,title)."""
    edges = []   # (from_page, edge_type, to_ns, to_title)
    specs = [
        ("category", "categorylinks", "cl_from", "cl_target_id"),
        ("template", "templatelinks", "tl_from", "tl_target_id"),
        ("wikilink", "pagelinks",     "pl_from", "pl_target_id"),
    ]
    for etype, table, fromcol, targetcol in specs:
        for chunk in batched(list(admitted_ids)):
            ph = ",".join(["%s"] * len(chunk))
            rows = q(rep, f"""
                SELECT t.{fromcol} AS frm, lt.lt_namespace AS ns, lt.lt_title AS title
                FROM {table} t
                JOIN linktarget lt ON t.{targetcol} = lt.lt_id
                WHERE t.{fromcol} IN ({ph})
            """, chunk)
            for frm, ns, title in rows:
                title = title.decode() if isinstance(title, bytes) else title
                edges.append((frm, etype, ns, title))
        print(f"  edges[{etype}]: {sum(1 for e in edges if e[1]==etype):,}")
    return edges


# ---------------------------------------------------------------------------
# E. Writers
# ---------------------------------------------------------------------------

DDL_SQLITE = """
CREATE TABLE IF NOT EXISTS node(wiki,page_id,year,title,namespace,is_redirect,wikidata_qid,admitted_via,
  PRIMARY KEY(wiki,year,page_id));
CREATE TABLE IF NOT EXISTS edge(wiki,year,from_page,edge_type,to_ns,to_title,to_page,to_admitted);
CREATE TABLE IF NOT EXISTS category_registry(wiki,year,category_title,n_members,depth_from_root,is_indicator,
  PRIMARY KEY(wiki,year,category_title));
CREATE TABLE IF NOT EXISTS template_registry(wiki,year,template_title,n_transclusions,is_indicator,
  PRIMARY KEY(wiki,year,template_title));
CREATE TABLE IF NOT EXISTS build_run(wiki,year,built_at,source,root_category,max_depth,n_nodes,n_edges);
"""


def write_sqlite(path, wiki, year, nodes, edges, cat_reg, tmpl_reg, run):
    db = sqlite3.connect(path)
    db.executescript(DDL_SQLITE)
    db.execute("DELETE FROM node WHERE wiki=? AND year=?", (wiki, year))
    db.execute("DELETE FROM edge WHERE wiki=? AND year=?", (wiki, year))
    db.execute("DELETE FROM category_registry WHERE wiki=? AND year=?", (wiki, year))
    db.execute("DELETE FROM template_registry WHERE wiki=? AND year=?", (wiki, year))
    db.executemany("INSERT OR REPLACE INTO node VALUES(?,?,?,?,?,?,?,?)", nodes)
    db.executemany("INSERT INTO edge VALUES(?,?,?,?,?,?,?,?)", edges)
    db.executemany("INSERT OR REPLACE INTO category_registry VALUES(?,?,?,?,?,?)", cat_reg)
    db.executemany("INSERT OR REPLACE INTO template_registry VALUES(?,?,?,?,?)", tmpl_reg)
    db.execute("INSERT INTO build_run VALUES(?,?,?,?,?,?,?,?)", run)
    db.commit(); db.close()
    print(f"  wrote SQLite -> {path}")


def write_toolsdb(wiki, year, nodes, edges, cat_reg, tmpl_reg, run):
    conn = connect_toolsdb()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM node WHERE wiki=%s AND year=%s", (wiki, year))
        cur.execute("DELETE FROM edge WHERE wiki=%s AND year=%s", (wiki, year))
        cur.execute("DELETE FROM category_registry WHERE wiki=%s AND year=%s", (wiki, year))
        cur.execute("DELETE FROM template_registry WHERE wiki=%s AND year=%s", (wiki, year))
        cur.executemany("REPLACE INTO node VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
                        [(n[0], n[1], n[2], n[3], n[4], n[5], n[6], n[7]) for n in nodes])
        for ch in batched(edges, 1000):
            cur.executemany("INSERT INTO edge VALUES(%s,%s,%s,%s,%s,%s,%s,%s)", ch)
        cur.executemany("REPLACE INTO category_registry VALUES(%s,%s,%s,%s,%s,%s)", cat_reg)
        cur.executemany("REPLACE INTO template_registry VALUES(%s,%s,%s,%s,%s)", tmpl_reg)
        cur.execute("REPLACE INTO build_run VALUES(%s,%s,%s,%s,%s,%s,%s,%s)", run)
    conn.close()
    print("  wrote ToolsDB")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wiki", default="enwiki")
    ap.add_argument("--year", type=int, default=2026)
    ap.add_argument("--max-depth", type=int, default=4)
    ap.add_argument("--root", default=None,
                    help="ns-14 root category title (no 'Category:' prefix). "
                         "Defaults to the per-wiki value in WIKI_ROOTS.")
    ap.add_argument("--no-toolsdb", action="store_true")
    ap.add_argument("--sqlite", default=str(Path.home() / "policy_net.db"))
    args = ap.parse_args()
    wiki, year = args.wiki, args.year
    if args.root is None:
        if wiki not in WIKI_ROOTS:
            sys.exit(f"No default root for {wiki}; pass --root explicitly.")
        args.root = WIKI_ROOTS[wiki]
    seed_templates = WIKI_STATUS_TEMPLATES.get(wiki, [])

    rep = connect_replica(wiki)
    print(f"=== M1 build: {wiki} year={year} root='{args.root}' depth<={args.max_depth} ===")

    # A. discover indicator categories
    print("A. category BFS …")
    cats = discover_categories(rep, args.root, args.max_depth)

    # B. admit
    print("B. admission …")
    by_cat = pages_in_categories(rep, cats.keys())
    tmpl_ids = template_page_ids(rep, seed_templates) if seed_templates else {}
    by_tmpl = pages_transcluding(rep, list(tmpl_ids.keys())) if tmpl_ids else set()
    print(f"  via category: {len(by_cat):,} pages · via template: {len(by_tmpl):,} pages")

    admitted = set(by_cat) | set(by_tmpl)
    meta = page_meta(rep, admitted)
    # exclusion-based namespace filter (drop only mainspace)
    admitted = {pid for pid in admitted
                if pid in meta and meta[pid]["ns"] not in EXCLUDE_NS}
    print(f"  admitted (excl. ns0): {len(admitted):,} nodes")

    qid = qids(rep, admitted)

    def admitted_via(pid):
        c, t = pid in by_cat, pid in by_tmpl
        return "both" if c and t else "category" if c else "template"

    nodes = [(wiki, pid, year, meta[pid]["title"], meta[pid]["ns"],
              meta[pid]["is_redirect"], qid.get(pid), admitted_via(pid))
             for pid in admitted]

    # C. edges
    print("C. edges …")
    raw_edges = collect_edges(rep, admitted)
    targets = {(ns, title) for _f, _t, ns, title in raw_edges}
    tgt_pid = resolve_titles_to_pageids(rep, targets)
    edges = []
    for frm, etype, ns, title in raw_edges:
        to_page = tgt_pid.get((ns, title))
        edges.append((wiki, year, frm, etype, ns, title, to_page,
                      1 if (to_page in admitted) else 0))

    # registries
    cat_member_counts = {}
    for cset in by_cat.values():
        for c in cset:
            cat_member_counts[c] = cat_member_counts.get(c, 0) + 1
    cat_reg = [(wiki, year, c, cat_member_counts.get(c, 0), cats.get(c, -1), 1) for c in cats]
    tmpl_counts = {}
    for _f, etype, ns, title in raw_edges:
        if etype == "template" and ns == 10:
            tmpl_counts[title] = tmpl_counts.get(title, 0) + 1
    tmpl_reg = [(wiki, year, t, n, 1 if t in seed_templates else 0)
                for t, n in tmpl_counts.items()]

    built_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    run = (wiki, year, built_at, "replica:current",
           args.root.replace(" ", "_"), args.max_depth, len(nodes), len(edges))

    # E. write
    print("E. writing …")
    write_sqlite(args.sqlite, wiki, year, nodes, edges, cat_reg, tmpl_reg, run)
    if not args.no_toolsdb:
        write_toolsdb(wiki, year, nodes, edges, cat_reg, tmpl_reg, run)

    # summary (M1 gate: node count, fan-out, namespace spread)
    print(f"\n=== summary ===")
    print(f"  nodes:        {len(nodes):,}")
    print(f"  edges:        {len(edges):,}  "
          f"(policy->policy: {sum(1 for e in edges if e[7]):,})")
    print(f"  categories:   {len(cats):,} (depth<= {args.max_depth})")
    ns_spread = {}
    for n in nodes:
        ns_spread[n[4]] = ns_spread.get(n[4], 0) + 1
    print(f"  namespace spread: {dict(sorted(ns_spread.items()))}")
    print(f"  with QID:     {sum(1 for n in nodes if n[6]):,}")


if __name__ == "__main__":
    main()
