#!/usr/bin/env python3
"""
null_model.py — M5 inference layer for the multi-wiki policy network.

Turns the descriptive FINDINGS into defensible claims by giving each reported
metric a null / size-normalization baseline. Pure-local (nodes.csv + edges.csv),
no replica/LLM, pure stdlib (matches analyze_network.py).

Three tests, one per outstanding finding:

  A. Density gap (FINDINGS #3, "en ~2x denser").
     Size-normalization + uncertainty: bootstrap each wiki's mean within-wiki
     degree (resample nodes with replacement) -> 95% CI. Non-overlapping CIs
     mean the ranking is not a sampling artifact. (Mean degree is scale-free in
     n, so this is the size-control: a bigger core does not mechanically raise
     links-per-page.)

  B. Cross-lingual consistency of periphery (FINDINGS #1, "peripheral in all 6").
     Null: peripherality independent across wikis. Within each wiki, permute the
     normalized-degree ranks; recompute how many all-6 clusters land in the
     bottom (top) quintile in ALL wikis. Empirical p = how often the null matches
     or beats the observed count of consistently-peripheral (central) clusters.

  C. Hidden equivalents (FINDINGS #4, "82 pairs at Jaccard>=0.45").
     The configuration-model test. Degree-preserving double-edge-swap of each
     wiki's within-wiki graph (interwiki edges FIXED, cluster membership fixed),
     then recompute the cross-lingual neighborhood-Jaccard. If the observed 82
     pairs far exceed the rewired null, the equivalence signal is real structure,
     not a by-product of the degree sequence (which the swap preserves exactly).

Navbox/complete-subgraph artifact note: the network already uses in-body
wikilinks (not pagelinks), so navbox cliques are largely excluded at build time;
the configuration model additionally destroys any residual clique structure, so
a surviving signal in C is not a template-transclusion artifact.

Usage:  uv run python null_model.py [--dir ../data/network] [--reps 500] [--seed 12345]
"""

import argparse
import collections
import csv
import itertools
import random
import statistics as st
from pathlib import Path

JACC = 0.45      # hidden-equivalent threshold (must match analyze_network.py §5)
FP_MIN = 6       # min fingerprint size (must match analyze_network.py §5)


def load(d):
    nodes = {r["node_id"]: (r["wiki"], r["title"])
             for r in csv.DictReader(open(d / "nodes.csv"))}
    nbr = collections.defaultdict(set)
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


def clusters(nodes, iw):
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
    return {n: find(n) for n in nodes}, cl


def fingerprints(adj, cl_of, crossling):
    """fp[n] = set of cross-lingual clusters n's neighbors belong to (|fp|>=FP_MIN)."""
    fp = {}
    for n, ns in adj.items():
        s = {cl_of[m] for m in ns if cl_of[m] in crossling}
        if len(s) >= FP_MIN:
            fp[n] = s
    return fp


def count_pairs(fp, nodes, cl_of, thresh=JACC):
    """# cross-wiki, NOT co-clustered pairs with neighborhood Jaccard >= thresh."""
    inv = collections.defaultdict(list)
    for n, s in fp.items():
        for c in s:
            inv[c].append(n)
    seen, hits = set(), []
    for members in inv.values():
        for x, y in itertools.combinations(members, 2):
            if nodes[x][0] == nodes[y][0] or cl_of[x] == cl_of[y]:
                continue
            key = (x, y) if x < y else (y, x)
            if key in seen:
                continue
            seen.add(key)
            j = len(fp[x] & fp[y]) / len(fp[x] | fp[y])
            if j >= thresh:
                hits.append((j, x, y))
    return hits


def wiki_edges(nodes, nbr):
    """undirected within-wiki edge list per wiki (dedup u<v)."""
    by = collections.defaultdict(list)
    for u, ns in nbr.items():
        for v in ns:
            if u < v and nodes[u][0] == nodes[v][0]:
                by[nodes[u][0]].append((u, v))
    return by


def rewire(edges, rng, passes=10):
    """degree-preserving double-edge-swap; returns adjacency sets. No multi/self-edge."""
    E = list(edges)
    adj = collections.defaultdict(set)
    eset = set()
    for u, v in E:
        adj[u].add(v); adj[v].add(u); eset.add((u, v) if u < v else (v, u))
    m = len(E)
    if m < 2:
        return adj
    for _ in range(passes * m):
        i, j = rng.randrange(m), rng.randrange(m)
        if i == j:
            continue
        a, b = E[i]; c, dd = E[j]
        if rng.random() < 0.5:
            c, dd = dd, c
        if len({a, b, c, dd}) < 4:
            continue
        e1 = (a, dd) if a < dd else (dd, a)
        e2 = (c, b) if c < b else (b, c)
        if e1 in eset or e2 in eset:
            continue
        o1 = (a, b) if a < b else (b, a)
        o2 = (c, dd) if c < dd else (dd, c)
        eset.discard(o1); eset.discard(o2); eset.add(e1); eset.add(e2)
        adj[a].discard(b); adj[b].discard(a); adj[c].discard(dd); adj[dd].discard(c)
        adj[a].add(dd); adj[dd].add(a); adj[c].add(b); adj[b].add(c)
        E[i] = (a, dd); E[j] = (c, b)
    return adj


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(Path(__file__).parent.parent / "data" / "network"))
    ap.add_argument("--reps", type=int, default=500)
    ap.add_argument("--seed", type=int, default=12345)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    d = Path(a.dir)
    nodes, nbr, iw = load(d)
    cl_of, cl = clusters(nodes, iw)
    cl_langs = {c: {nodes[m][0] for m in mem} for c, mem in cl.items()}
    crossling = {c for c, lg in cl_langs.items() if len(lg) >= 2}
    deg = {n: len(nbr[n]) for n in nodes}
    bywiki = collections.defaultdict(list)
    for n, (w, _) in nodes.items():
        bywiki[w].append(n)
    wikis = sorted(bywiki, key=lambda w: -len(bywiki[w]))

    # ---- A. density gap: bootstrap CI on mean within-wiki degree ----
    print(f"=== A. density gap — bootstrap 95% CI on mean within-wiki degree "
          f"({a.reps} resamples) ===")
    print("  wiki    mean   95% CI            n")
    ci = {}
    for w in wikis:
        ns = bywiki[w]; n = len(ns)
        boot = []
        for _ in range(a.reps):
            boot.append(st.mean(deg[rng.choice(ns)] for _ in range(n)))
        boot.sort()
        lo, hi = boot[int(.025 * a.reps)], boot[int(.975 * a.reps)]
        ci[w] = (lo, hi)
        print(f"  {w:7} {st.mean(deg[x] for x in ns):5.1f}  [{lo:5.1f}, {hi:5.1f}]   {n}")
    top, second = wikis[0], None
    order = sorted(wikis, key=lambda w: -st.mean(deg[x] for x in bywiki[w]))
    top, second = order[0], order[1]
    gap = "non-overlapping" if ci[top][0] > ci[second][1] else "OVERLAPPING"
    print(f"  -> {top} CI lower {ci[top][0]:.1f} vs next ({second}) CI upper "
          f"{ci[second][1]:.1f}: {gap} -> density lead is "
          f"{'robust' if gap[0]=='n' else 'NOT distinguishable'}")

    # ---- B. cross-lingual periphery consistency: rank-permutation null ----
    print(f"\n=== B. cross-lingual periphery/centre consistency — rank-permutation "
          f"null ({a.reps} perms) ===")
    # Test the SAME set analyze_network uses for the periphery claim: clusters
    # spanning >=3 wikis, consistency measured over each cluster's actual span.
    multi = [mem for mem in cl.values() if len(cl_langs[cl_of[mem[0]]]) >= 3]
    def consistent(qfn):
        lo = hi = 0
        for mem in multi:
            qs = [qfn(m) for m in mem]          # one quintile per member page
            if all(q == 0 for q in qs): lo += 1   # peripheral in EVERY wiki it appears in
            if all(q == 4 for q in qs): hi += 1   # central in every wiki it appears in
        return lo, hi
    # observed per-wiki quintile rank of each node (0=lowest, 4=highest)
    q_obs = {}
    for w in wikis:
        ranked = sorted(bywiki[w], key=lambda n: deg[n])
        for i, n in enumerate(ranked):
            q_obs[n] = min(4, i * 5 // len(ranked))
    obs_lo, obs_hi = consistent(lambda m: q_obs[m])
    ge_lo = ge_hi = 0
    for _ in range(a.reps):
        q = {}
        for w in wikis:
            order_w = bywiki[w][:]; rng.shuffle(order_w)
            L = len(order_w)
            for i, n in enumerate(order_w):
                q[n] = min(4, i * 5 // L)
        plo, phi = consistent(lambda m: q[m])
        ge_lo += (plo >= obs_lo); ge_hi += (phi >= obs_hi)
    print(f"  clusters spanning >=3 wikis: {len(multi)}")
    print(f"  peripheral in every wiki it appears (bottom quintile): observed {obs_lo}  "
          f"null mean {len(multi)*(0.2**3):.2f}  p={(ge_lo+1)/(a.reps+1):.4f}")
    print(f"  central in every wiki it appears    (top quintile):    observed {obs_hi}  "
          f"p={(ge_hi+1)/(a.reps+1):.4f}")

    # ---- C. hidden equivalents: configuration-model null ----
    print(f"\n=== C. hidden equivalents — degree-preserving rewire null "
          f"({a.reps} replicas) ===")
    obs_fp = fingerprints(nbr, cl_of, crossling)
    obs_hits = count_pairs(obs_fp, nodes, cl_of)
    obs_n = len(obs_hits)
    wedges = wiki_edges(nodes, nbr)
    null_counts = []
    for r in range(a.reps):
        adj = collections.defaultdict(set)
        for n in nodes:
            adj[n]  # touch
        for w in wikis:
            radj = rewire(wedges[w], rng)
            for n, s in radj.items():
                adj[n] = s
        fp = fingerprints(adj, cl_of, crossling)
        null_counts.append(len(count_pairs(fp, nodes, cl_of)))
    nm = st.mean(null_counts); nsd = st.pstdev(null_counts) or 1e-9
    ge = sum(1 for c in null_counts if c >= obs_n)
    print(f"  observed qualifying pairs (Jaccard>={JACC}): {obs_n}")
    print(f"  null: mean {nm:.1f}  sd {nsd:.1f}  max {max(null_counts)}")
    print(f"  z = {(obs_n - nm)/nsd:.1f}   empirical p = {(ge+1)/(a.reps+1):.4f}")
    print(f"  -> hidden-equivalent signal is "
          f"{'real structure (not a degree artifact)' if ge == 0 else 'NOT clearly above null'}")


if __name__ == "__main__":
    main()
