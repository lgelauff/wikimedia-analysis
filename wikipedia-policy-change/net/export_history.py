#!/usr/bin/env python3
"""
export_history.py — dump the year-keyed core network from ToolsDB to CSV for the repo.

ToolsDB is Toolforge-only, quota-bound, and the per-build SQLite archives aren't in
git — so this writes the compact, year-keyed CORE network to data/network/history/
as the durable, committable copy of the historical (and 2026) network.

By default it exports the *core* network only — node rows that are core/candidate
(drops the 2026 'suspect' frontier) and core->core links (to_admitted=1) — so the
output matches the shape of data/network/ (core), NOT the full raw build (the enwiki
2026 raw node table alone is ~34k rows; the full link graph is far larger and belongs
in the SQLite archive, not git).

Run on Toolforge (needs ~/replica.my.cnf):
  toolforge jobs run export-hist --image python3.13 --mem 1Gi --wait \
    --command "~/venv/bin/python -u ~/wikimedia-analysis/wikipedia-policy-change/net/export_history.py"
Then on the bastion: git -C ~/wikimedia-analysis add -A && commit && push.

Local (no creds): exits cleanly, does nothing.
"""

import argparse
import configparser
import csv
import sys
from pathlib import Path

try:
    import pymysql
except ImportError:
    sys.exit("pip install pymysql")

OUT_DEFAULT = Path(__file__).parent.parent / "data" / "network" / "history"


def creds():
    p = Path.home() / "replica.my.cnf"
    if not p.exists():
        return None
    c = configparser.ConfigParser()
    c.read(p)
    return c["client"]["user"].strip("'\""), c["client"]["password"].strip("'\"")


def dec(x):
    return x.decode("utf-8", "replace") if isinstance(x, (bytes, bytearray)) else x


def dump(db, out, name, sql, params):
    with db.cursor() as cur:
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
    fpath = out / f"{name}.csv"
    with fpath.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow([dec(v) for v in r])
    print(f"  {name}: {len(rows):,} rows -> {fpath}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT_DEFAULT))
    ap.add_argument("--from-year", type=int, default=2005)
    ap.add_argument("--to-year", type=int, default=2026)
    ap.add_argument("--wiki", default=None, help="restrict to one wiki (default: all)")
    ap.add_argument("--include-suspects", action="store_true",
                    help="also export non-core (2026 frontier) nodes — large")
    ap.add_argument("--all-links", action="store_true",
                    help="export every wikilink, not just core->core — large")
    a = ap.parse_args()

    cr = creds()
    if cr is None:
        print("No ~/replica.my.cnf — run on Toolforge. Nothing to do."); sys.exit(0)
    user, pw = cr
    db = pymysql.connect(host="tools.db.svc.wikimedia.cloud", user=user, password=pw,
                         database=f"{user}__policies", charset="utf8mb4", autocommit=True)

    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    yr = "year BETWEEN %s AND %s"
    pr = [a.from_year, a.to_year]
    wclause = " AND wiki=%s" if a.wiki else ""
    wp = [a.wiki] if a.wiki else []

    node_filter = "" if a.include_suspects else " AND confidence IN ('core','candidate')"
    dump(db, out, "nodes",
         f"SELECT * FROM node WHERE {yr}{wclause}{node_filter} ORDER BY wiki, year, page_id",
         pr + wp)

    link_filter = "" if a.all_links else " AND to_admitted=1"
    dump(db, out, "links",
         f"SELECT * FROM link WHERE {yr}{wclause}{link_filter} ORDER BY wiki, year, from_page",
         pr + wp)

    dump(db, out, "build_run",
         f"SELECT * FROM build_run WHERE {yr}{wclause} ORDER BY wiki, year, built_at",
         pr + wp)

    # year coverage summary
    print("\nyear coverage (exported nodes):")
    with db.cursor() as cur:
        cur.execute(f"SELECT wiki, year, COUNT(*) AS n, SUM(confidence='core') AS core "
                    f"FROM node WHERE {yr}{wclause}{node_filter} "
                    f"GROUP BY wiki, year ORDER BY wiki, year", pr + wp)
        for wiki, year, n, core in cur.fetchall():
            print(f"  {dec(wiki):14s} {year}  n {n:>6}  core {core or 0:>6}")


if __name__ == "__main__":
    main()
