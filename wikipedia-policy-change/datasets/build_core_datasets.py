# /// script
# dependencies = []
# ///
"""
build_core_datasets.py — emit one per-wiki core-policy dataset folder under datasets/,
parallel to the hand-authored datasets/enwiki_core_policies_2026/.

Source of truth: ../data/network/{nodes,edges,governance_class}.csv (the 2026 6-wiki
network snapshot). For each wiki it writes:
  datasets/<wiki>_core_policies_2026/<wiki>_2026_core.csv   (one column: page_title)
  datasets/<wiki>_core_policies_2026/README.md              (counts, governance split, method)

enwiki is SKIPPED by default (it already has a hand-authored README from an earlier build,
316 rows vs 347 here) — pass --include-en to regenerate it too for a uniform family.

Usage:  uv run --script build_core_datasets.py [--include-en]
"""

import argparse
import collections
import csv
from pathlib import Path

NS_NAME = {"enwiki": "Wikipedia:", "dewiki": "Wikipedia:", "nlwiki": "Wikipedia:",
           "frwiki": "Wikipédia:", "eswiki": "Wikipedia:", "jawiki": "Wikipedia:"}
LONG = {"enwiki": "English", "dewiki": "German", "nlwiki": "Dutch",
        "frwiki": "French", "eswiki": "Spanish", "jawiki": "Japanese"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--include-en", action="store_true")
    a = ap.parse_args()
    root = Path(__file__).parent
    netdir = root.parent / "data" / "network"

    nodes = list(csv.DictReader(open(netdir / "nodes.csv")))
    gov = {r["node_id"]: r["governance_class"]
           for r in csv.DictReader(open(netdir / "governance_class.csv"))}
    links = collections.Counter()
    for r in csv.DictReader(open(netdir / "edges.csv")):
        if r["type"] == "wikilink":
            links[r["wiki"]] += 1

    bywiki = collections.defaultdict(list)
    for r in nodes:
        bywiki[r["wiki"]].append(r)

    for wiki, rows in sorted(bywiki.items()):
        if wiki == "enwiki" and not a.include_en:
            print(f"skip {wiki} (hand-authored; use --include-en to regenerate)")
            continue
        rows.sort(key=lambda r: r["title"])
        d = root / f"{wiki}_core_policies_2026"
        d.mkdir(exist_ok=True)
        # core CSV (parallel to enwiki: single page_title column)
        with open(d / f"{wiki}_2026_core.csv", "w", newline="") as f:
            w = csv.writer(f); w.writerow(["page_title"])
            for r in rows:
                w.writerow([r["title"]])
        # stats
        n = len(rows)
        nqid = sum(1 for r in rows if r["qid"])
        gsplit = collections.Counter(gov.get(r["node_id"], "?") for r in rows)
        style = sum(1 for r in rows if r["title"].startswith(("Manual_of_Style", "Naming_conventions",
                    "Wikipedia:Manual")) )  # en-style heuristic; other wikis use other prefixes
        gline = " · ".join(f"{k} {gsplit.get(k,0)} ({100*gsplit.get(k,0)//n}%)"
                           for k in ["content", "user-user", "user-admin", "Other"])
        readme = f"""# Dataset — {LONG[wiki]} Wikipedia core policies & guidelines (2026)

**`{wiki}_2026_core.csv`** — the {n} pages that constitute the **core** policy/guideline
body of {LONG[wiki]} Wikipedia as of the 2026 snapshot.

| field | |
|---|---|
| wiki | {NS_NAME[wiki].rstrip(':').lower()}.wikipedia (ns 4, the `{NS_NAME[wiki]}` project namespace) |
| snapshot year | 2026 |
| rows | {n} |
| `page_title` | MediaWiki `page_title` (underscores, no `{NS_NAME[wiki]}` prefix) |

These are the *confirmed* core nodes only. Wikidata coverage: {nqid}/{n}
(~{100*nqid//n}%) carry a Wikidata item. Internal structure: {links[wiki]:,} core→core
in-body wikilinks among these pages (the {LONG[wiki]} slice of the policy network).

## Governance-object split (provisional)

Heaberlin–DeDeo (2016) typology, assigned structurally (see
[`../../net/classify_governance.py`](../../net/classify_governance.py) and FINDINGS #5):

**{gline}**

## Method

Built from the 6-wiki 2026 network snapshot in [`../../data/network/`](../../data/network/)
(`net/net_build_current.py` → `nodes.csv`), filtered to `wiki = {wiki}`. Core membership,
the per-wiki indicator reconstruction, and the namespace-4 page-routing rule (policy vs.
venue vs. deliberation) are defined in
[`../../docs/core_definition.md`](../../docs/core_definition.md). Categories/templates are
admission *signals*, never graph edges; the network is the in-body wikilink graph.

Regenerate: `uv run --script ../build_core_datasets.py`.
"""
        (d / "README.md").write_text(readme, encoding="utf-8")
        print(f"wrote {d.name}: {n} pages, {nqid} qid, {links[wiki]} links  [{gline}]")


if __name__ == "__main__":
    main()
