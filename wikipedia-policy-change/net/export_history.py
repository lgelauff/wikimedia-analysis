#!/usr/bin/env python3
"""
export_history.py — dump the year-keyed ToolsDB tables to CSV for the repo.

ToolsDB is Toolforge-only, quota-bound, and the per-build SQLite archives aren't in
git — so this writes the compact, year-keyed derived tables to data/network/history/
as the durable, committable copy of the historical (and current) network.

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

# year-keyed tables worth committing (small, derived). Facets are larger but still
# compact; include them by default so the export is self-contained.
TABLES = ["node", "link", "node_category", "node_template", "navbox_member",
          "category_registry", "template_registry", "provenance", "build_run"]

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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT_DEFAULT))
    ap.add_argument("--tables", default=",".join(TABLES),
                    help="comma-separated subset to export")
    ap.add_argument("--wiki", default=None, help="restrict to one wiki (default: all)")
    a = ap.parse_args()

    cr = creds()
    if cr is None:
        print("No ~/replica.my.cnf — run on Toolforge. Nothing to do."); sys.exit(0)
    user, pw = cr
    db = pymysql.connect(host="tools.db.svc.wikimedia.cloud", user=user, password=pw,
                         database=f"{user}__policies", charset="utf8mb4", autocommit=True)

    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    where = ("WHERE wiki=%s", (a.wiki,)) if a.wiki else ("", ())

    for tbl in a.tables.split(","):
        tbl = tbl.strip()
        if not tbl:
            continue
        with db.cursor() as cur:
            try:
                cur.execute(f"SELECT * FROM {tbl} {where[0]} ORDER BY 1", where[1])
            except pymysql.err.ProgrammingError as e:
                print(f"  {tbl}: skip ({e})"); continue
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
        fpath = out / f"{tbl}.csv"
        with fpath.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(cols)
            for r in rows:
                w.writerow([dec(v) for v in r])
        print(f"  {tbl}: {len(rows):,} rows -> {fpath}")

    # quick year coverage summary so you can see what's actually populated
    print("\nyear coverage (node):")
    with db.cursor() as cur:
        cur.execute("SELECT wiki, year, COUNT(*) c, "
                    "SUM(confidence='core') core FROM node "
                    f"{where[0]} GROUP BY wiki, year ORDER BY wiki, year", where[1])
        for wiki, year, c, core in cur.fetchall():
            print(f"  {dec(wiki):14s} {year}  rows {c:>6}  core {core or 0:>6}")


if __name__ == "__main__":
    main()
