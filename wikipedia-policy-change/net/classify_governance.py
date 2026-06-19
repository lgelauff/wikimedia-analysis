# /// script
# dependencies = ["networkx", "scipy"]
# ///
"""
classify_governance.py — does the Heaberlin-DeDeo (2016) governance-object typology
(user-content | user-user | user-admin) extend to our 6-wiki network?

Method (no LLM, structure only):
  1. Seed three anchor sets by EN title (content/user/admin core pages).
  2. Propagate the seeds cross-lingually via interwiki clusters — an anchor's
     equivalents in de/fr/es/ja/nl become anchors too (language-agnostic: the
     scheme keys on what's governed, which every edition has).
  3. Within each wiki, run personalized PageRank from each anchor set over the
     intra-wiki wikilink graph; assign each page to its argmax category.
     Pages unreachable from every anchor (isolates etc.) -> Other (the residual).
  4. Louvain communities per wiki -> measure how well structure agrees with the
     three-way assignment (community purity), the DeDeo "norm bundles" check.

Usage:  uv run --script classify_governance.py [--dir ../data/network]
"""

import argparse
import collections
import csv
from pathlib import Path

ANCHORS = {  # EN titles (nodes.csv form); propagated to other wikis via clusters
    "content": ["Neutral_point_of_view", "Verifiability", "No_original_research",
                "Citing_sources", "What_Wikipedia_is_not"],
    "user-user": ["Civility", "Consensus", "No_personal_attacks", "Etiquette",
                  "Edit_warring", "Assume_good_faith", "Dispute_resolution"],
    "user-admin": ["Administrators", "Blocking_policy", "Deletion_policy",
                   "Protection_policy", "Banning_policy", "Username_policy"],
}
CATS = list(ANCHORS)


def load(d):
    nodes = {r["node_id"]: r for r in csv.DictReader(open(d / "nodes.csv"))}
    intra = collections.defaultdict(set)
    iw = []
    for r in csv.DictReader(open(d / "edges.csv")):
        s, t, ty = r["source"], r["target"], r["type"]
        if s not in nodes or t not in nodes:
            continue
        if ty == "wikilink":
            intra[s].add(t); intra[t].add(s)
        elif ty == "interwiki":
            iw.append((s, t))
    return nodes, intra, iw


def clusters(nodes, iw):
    par = {n: n for n in nodes}
    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]; x = par[x]
        return x
    for a, b in iw:
        par[find(a)] = find(b)
    return {n: find(n) for n in nodes}


def main():
    import networkx as nx
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(Path(__file__).parent.parent / "data" / "network"))
    a = ap.parse_args()
    d = Path(a.dir)
    nodes, intra, iw = load(d)
    cl_of = clusters(nodes, iw)

    # EN anchor node_ids -> their clusters -> seeds in every wiki
    en_by_title = {r["title"]: nid for nid, r in nodes.items() if r["wiki"] == "enwiki"}
    seed_clusters = {c: set() for c in CATS}
    for c, titles in ANCHORS.items():
        for t in titles:
            nid = en_by_title.get(t)
            if nid:
                seed_clusters[c].add(cl_of[nid])
    anchors = {c: {n for n in nodes if cl_of[n] in seed_clusters[c]} for c in CATS}

    bywiki = collections.defaultdict(list)
    for n, r in nodes.items():
        bywiki[r["wiki"]].append(n)
    wikis = sorted(bywiki, key=lambda w: -len(bywiki[w]))

    assign = {}                      # node -> category|Other
    purity_rows = []
    print("per-wiki governance-object split (personalized PageRank, argmax; "
          "Other = unreachable from all anchors):\n")
    print(f"  {'wiki':6} {'content':>9} {'user-user':>10} {'user-admin':>11} {'Other':>7} "
          f"{'anchors c/u/a':>14}  {'Louvain purity':>14}")
    for w in wikis:
        sub = nx.Graph()
        sub.add_nodes_from(bywiki[w])
        for u in bywiki[w]:
            for v in intra[u]:
                if nodes[v]["wiki"] == w:
                    sub.add_edge(u, v)
        ppr = {}
        nanch = {}
        for c in CATS:
            seeds = [n for n in anchors[c] if n in sub]
            nanch[c] = len(seeds)
            if seeds:
                pers = {n: (1.0 if n in seeds else 0.0) for n in sub}
                ppr[c] = nx.pagerank(sub, alpha=0.85, personalization=pers)
            else:
                ppr[c] = {n: 0.0 for n in sub}
        cnt = collections.Counter()
        for n in bywiki[w]:
            scores = {c: ppr[c][n] for c in CATS}
            tot = sum(scores.values())
            if tot <= 0:
                assign[n] = "Other"
            else:
                assign[n] = max(scores, key=scores.get)
            cnt[assign[n]] += 1
        # Louvain purity: each community's dominant-category share
        comms = nx.community.louvain_communities(sub, seed=42) if sub.number_of_edges() else []
        sizes, pure = 0, 0
        for com in comms:
            labs = collections.Counter(assign[n] for n in com)
            sizes += len(com); pure += labs.most_common(1)[0][1]
        purity = pure / sizes if sizes else 0
        purity_rows.append((w, purity, len(comms)))
        N = len(bywiki[w])
        print(f"  {w[:6]:6} {cnt['content']:4}/{100*cnt['content']//N:>2}% "
              f"{cnt['user-user']:4}/{100*cnt['user-user']//N:>2}% "
              f"{cnt['user-admin']:4}/{100*cnt['user-admin']//N:>2}% "
              f"{cnt['Other']:3}/{100*cnt['Other']//N:>2}% "
              f"{nanch['content']:>3}/{nanch['user-user']}/{nanch['user-admin']:<4} "
              f"  {purity:.2f} ({len(comms)} comms)")

    print("\nLouvain purity = fraction of nodes whose community's majority category "
          "matches their own.\nHigh purity => structural 'norm bundles' agree with the "
          "governance-object scheme (DeDeo's separate-derivation check).")

    # write per-node assignment for downstream use
    out = d / "governance_class.csv"
    with open(out, "w", newline="") as f:
        wr = csv.writer(f); wr.writerow(["node_id", "wiki", "title", "governance_class"])
        for n in sorted(nodes, key=lambda n: (nodes[n]["wiki"], assign.get(n, "Other"))):
            wr.writerow([n, nodes[n]["wiki"], nodes[n]["title"], assign.get(n, "Other")])
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
