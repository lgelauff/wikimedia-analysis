#!/usr/bin/env python3
"""
analyze_network.py — structural analysis of the exported multi-wiki policy network.

Reads data/network/nodes.csv + edges.csv (output of build_network.py) and computes,
with NO replica/ToolsDB access (pure local):
  1. cross-lingual clusters (connected components over interwiki langlink edges)
  2. per-node within-wiki degree, normalized by that wiki's mean (densities differ)
  3. consistently-peripheral vs consistently-central policies across languages
  4. the style/MoS apparatus per wiki (size + cross-lingual matchability)

Findings (2026 snapshot) are written up in data/network/FINDINGS.md.
Caveat: raw structural counts — no null model yet (M5 gate) before any claim.

Usage:  uv run python analyze_network.py [--dir ../data/network]
"""

import argparse
import collections
import csv
import statistics as st
from pathlib import Path


def load(d):
    nodes = {r["node_id"]: (r["wiki"], r["title"])
             for r in csv.DictReader(open(d / "nodes.csv"))}
    nbr = {n: set() for n in nodes}
    iw = []
    for r in csv.DictReader(open(d / "edges.csv")):
        s, t, ty = r["source"], r["target"], r["type"]
        if s not in nodes or t not in nodes:
            continue
        if ty == "wikilink":
            nbr[s].add(t); nbr[t].add(s)
        elif ty == "interwiki":
            iw.append((s, t))
    return nodes, nbr, iw


def components(nodes, iw):
    par = {n: n for n in nodes}
    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]; x = par[x]
        return x
    for a, b in iw:
        par[find(a)] = find(b)
    cl = collections.defaultdict(list)
    for n in nodes:
        cl[find(n)].append(n)
    return find, cl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(Path(__file__).parent.parent / "data" / "network"))
    a = ap.parse_args()
    d = Path(a.dir)
    nodes, nbr, iw = load(d)
    find, cl = components(nodes, iw)

    deg = {n: len(nbr[n]) for n in nodes}
    bywiki = collections.defaultdict(list)
    for n, (w, _) in nodes.items():
        bywiki[w].append(deg[n])
    mean = {w: st.mean(v) for w, v in bywiki.items()}
    nd = {n: deg[n] / mean[nodes[n][0]] for n in nodes}
    wikis = sorted(bywiki, key=lambda w: -len(bywiki[w]))

    def label(mem):
        en = [m for m in mem if nodes[m][0] == "enwiki"]
        return nodes[(en or mem)[0]][1]

    # 1. consistent periphery / centre across >=3 languages
    rows = []
    for mem in cl.values():
        langs = {nodes[m][0] for m in mem}
        if len(langs) >= 3:
            rows.append((round(st.mean(nd[m] for m in mem), 2), len(langs), label(mem)))
    rows.sort()
    print(f"cross-lingual clusters (>=3 wikis): {len(rows)}  (all-6: {sum(1 for r in rows if r[1]==6)})")
    print("\n=== consistently PERIPHERAL (low normalized degree across languages) ===")
    for avgnd, n, lab in rows[:20]:
        print(f"  {avgnd:4.2f}  {n}lg  {lab[:40]}")
    print("\n=== consistently CENTRAL ===")
    for avgnd, n, lab in rows[-8:]:
        print(f"  {avgnd:4.2f}  {n}lg  {lab[:40]}")

    # 2. style / MoS apparatus per wiki
    en_style = [n for n, (w, t) in nodes.items() if w == "enwiki"
                and (t.startswith("Manual_of_Style") or t.startswith("Naming_conventions"))]
    en_tot = len(bywiki["enwiki"])
    enonly = sum(1 for n in en_style if {nodes[m][0] for m in cl[find(n)]} == {"enwiki"})
    print(f"\n=== style/MoS apparatus ===")
    print(f"en MoS+NC pages: {len(en_style)} ({100*len(en_style)//en_tot}% of en core); "
          f"en-only (no cross-lingual match): {enonly} ({100*enonly//len(en_style)}%)")
    style_cl = {find(n) for n in en_style}
    for w in wikis:
        c = sum(1 for n, (ww, _) in nodes.items() if ww == w and find(n) in style_cl)
        print(f"  {w:7} style share: {c:3}/{len(bywiki[w]):3} ({100*c//len(bywiki[w])}%)")

    # 3. density with vs without the en-style cluster (does the en density lead survive?)
    print("\n=== internal density (links/node), full vs ex-MoS-cluster ===")
    for w in wikis:
        alln = [n for n in nodes if nodes[n][0] == w]
        keep = [n for n in alln if find(n) not in style_cl]
        d_all = st.mean(deg[n] for n in alln)
        d_ex = st.mean(deg[n] for n in keep) if keep else 0
        print(f"  {w:7} full {d_all:5.1f}  ex-MoS {d_ex:5.1f}  (n {len(alln)}->{len(keep)})")


if __name__ == "__main__":
    main()
