#!/usr/bin/env python3
"""
export_history.py — dump the year-keyed core network from ToolsDB to CSV for the repo.

The series is the 2026 core walked back through time (M4 Phase 1): 2026 is the BASELINE,
2005..2025 are reconstructed from it. This exports a compact, consistent slice:

  nodes.csv  — every `core` node (all years, incl. the 2026 baseline = the locked core),
               PLUS `candidate` nodes for historical years only (genuine per-year demotions:
               existed-but-essay/proposed/historical). The 2026 `candidate` frontier
               (the ~34k undiscovered suspects of the current build) is NOT a demotion and
               is dropped, so `candidate` means one thing throughout.
  links.csv  — core->core links: BOTH endpoints are `core` that year (a join, not the raw
               to_admitted flag), so the 2026 slice matches data/network/edges.csv rather
               than pulling in frontier targets.
  build_run.csv — provenance (git_commit per wiki-year).

ToolsDB is Toolforge-only and quota-bound; the per-build SQLite archives aren't in git —
so this is the durable, committable copy. Run on Toolforge (needs ~/replica.my.cnf):
  toolforge jobs run export-hist --image python3.13 --mem 2Gi --wait \
    --command "~/venv/bin/python -u ~/wikimedia-analysis/wikipedia-policy-change/net/export_history.py"

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
    return len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT_DEFAULT))
    ap.add_argument("--from-year", type=int, default=2005)
    ap.add_argument("--to-year", type=int, default=2026)
    ap.add_argument("--baseline-year", type=int, default=2026,
                    help="seed year: kept core-only (no candidate/frontier rows)")
    ap.add_argument("--wiki", default=None, help="restrict to one wiki (default: all)")
    ap.add_argument("--include-suspects", action="store_true",
                    help="keep ALL node rows incl. the baseline frontier — large, debug only")
    ap.add_argument("--all-links", action="store_true",
                    help="raw to_admitted links instead of strict both-endpoints-core — large")
    a = ap.parse_args()

    cr = creds()
    if cr is None:
        print("No ~/replica.my.cnf — run on Toolforge. Nothing to do."); sys.exit(0)
    user, pw = cr
    db = pymysql.connect(host="tools.db.svc.wikimedia.cloud", user=user, password=pw,
                         database=f"{user}__policies", charset="utf8mb4", autocommit=True)

    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    wp = [a.wiki] if a.wiki else []

    # --- nodes: all core + historical-only candidates (drop baseline-year candidates) ---
    if a.include_suspects:
        node_cond = ""
        node_params = [a.from_year, a.to_year] + wp
    else:
        node_cond = " AND (confidence='core' OR (confidence='candidate' AND year < %s))"
        node_params = [a.from_year, a.to_year] + wp + [a.baseline_year]
    dump(db, out, "nodes",
         "SELECT * FROM node WHERE year BETWEEN %s AND %s"
         + (" AND wiki=%s" if a.wiki else "") + node_cond
         + " ORDER BY wiki, year, page_id", node_params)

    # --- links: both endpoints core that year (matches data/network/ core edges) ---
    if a.all_links:
        dump(db, out, "links",
             "SELECT * FROM link WHERE year BETWEEN %s AND %s"
             + (" AND wiki=%s" if a.wiki else "") + " AND to_admitted=1"
             " ORDER BY wiki, year, from_page", [a.from_year, a.to_year] + wp)
    else:
        dump(db, out, "links",
             "SELECT l.* FROM link l "
             "JOIN node nf ON nf.wiki=l.wiki AND nf.year=l.year "
             "  AND nf.page_id=l.from_page AND nf.confidence='core' "
             "JOIN node nt ON nt.wiki=l.wiki AND nt.year=l.year "
             "  AND nt.page_id=l.to_page AND nt.confidence='core' "
             "WHERE l.year BETWEEN %s AND %s"
             + (" AND l.wiki=%s" if a.wiki else "")
             + " ORDER BY l.wiki, l.year, l.from_page", [a.from_year, a.to_year] + wp)

    dump(db, out, "build_run",
         "SELECT * FROM build_run WHERE year BETWEEN %s AND %s"
         + (" AND wiki=%s" if a.wiki else "")
         + " ORDER BY wiki, year, built_at", [a.from_year, a.to_year] + wp)

    # year coverage summary (same node filter)
    print("\nyear coverage (exported nodes):")
    with db.cursor() as cur:
        cur.execute("SELECT wiki, year, COUNT(*) AS n, SUM(confidence='core') AS core "
                    "FROM node WHERE year BETWEEN %s AND %s"
                    + (" AND wiki=%s" if a.wiki else "") + node_cond
                    + " GROUP BY wiki, year ORDER BY wiki, year", node_params)
        for wiki, year, n, core in cur.fetchall():
            print(f"  {dec(wiki):14s} {year}  n {n:>6}  core {core or 0:>6}")


if __name__ == "__main__":
    main()
