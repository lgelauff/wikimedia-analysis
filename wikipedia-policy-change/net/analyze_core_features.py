#!/usr/bin/env python3
"""
analyze_core_features.py — exploratory: what category/template signals associate with
core membership, per wiki, and which candidates "look core" (potential misses).

NOT a hypothesis test. Core is defined by banner/overview/iw, NOT by these features, so
treat this as an AUDIT + DISCOVERY tool:
  1. per-feature LIFT = P(core | has feature) / base-core-rate  (univariate, honest first cut)
  2. optional logistic "kitchen sink" (one-hot categories+templates) — multivariate, top coeffs
  3. candidates whose feature profile most resembles core -> potential under-admissions (misses)
  4. cross-wiki: compare the top discriminating features

Reads the local SQLite mirror (~/policy_net.db) which holds node / node_category /
node_template for all built wikis. No replica/API needed. Pure pandas; sklearn optional.

Usage:  python3 analyze_core_features.py --db ~/policy_net.db --year 2026 --min-support 3
"""
import argparse, sqlite3, math
from collections import defaultdict
from pathlib import Path


def load(db, wiki, year):
    con = sqlite3.connect(db)
    nodes = {pid: conf for pid, conf in con.execute(
        "SELECT page_id, confidence FROM node WHERE wiki=? AND year=?", (wiki, year))}
    feats = defaultdict(set)   # page_id -> {feature}
    for pid, cat in con.execute(
            "SELECT page_id, category_title FROM node_category WHERE wiki=? AND year=?", (wiki, year)):
        feats[pid].add("cat:" + (cat.decode() if isinstance(cat, bytes) else cat))
    for pid, t, role in con.execute(
            "SELECT page_id, template_title, role FROM node_template WHERE wiki=? AND year=?", (wiki, year)):
        t = t.decode() if isinstance(t, bytes) else t
        feats[pid].add(f"tmpl[{role}]:" + t)
    con.close()
    return nodes, feats


def known_indicators(db, wiki, year):
    """Features already flagged as indicators in the registries -> 'seed' (tautological);
    anything else high-lift is 'NEW' (a signal we didn't encode)."""
    con = sqlite3.connect(db); k = set()
    for (c,) in con.execute("SELECT category_title FROM category_registry "
                            "WHERE wiki=? AND year=? AND is_indicator=1", (wiki, year)):
        k.add("cat:" + (c.decode() if isinstance(c, bytes) else c))
    for (t,) in con.execute("SELECT template_title FROM template_registry "
                            "WHERE wiki=? AND year=? AND is_indicator=1", (wiki, year)):
        t = t.decode() if isinstance(t, bytes) else t
        k.update({f"tmpl[status]:{t}", f"tmpl[navigation]:{t}", f"tmpl[noise]:{t}"})
    con.close(); return k


def enrichment(nodes, feats, min_support):
    n = len(nodes); ncore = sum(1 for c in nodes.values() if c == "core")
    base = ncore / n if n else 0
    # per-feature: how many nodes have it, how many of those are core
    has = defaultdict(int); has_core = defaultdict(int)
    for pid, conf in nodes.items():
        for f in feats.get(pid, ()):
            has[f] += 1
            if conf == "core": has_core[f] += 1
    rows = []
    for f, h in has.items():
        if h < min_support: continue
        p = has_core[f] / h
        rows.append((f, h, has_core[f], p, p / base if base else 0))
    rows.sort(key=lambda r: (-r[4], -r[1]))
    return base, n, ncore, rows


def potential_misses(nodes, feats, top_feats):
    """candidates carrying >=2 high-lift core-features = look core but weren't admitted."""
    hi = {f for f, *_ in top_feats[:40]}
    out = []
    for pid, conf in nodes.items():
        if conf != "core":
            k = len(feats.get(pid, set()) & hi)
            if k >= 2: out.append((pid, k))
    out.sort(key=lambda x: -x[1])
    return out


def logistic(nodes, feats, min_support):
    try:
        import numpy as np
        from sklearn.linear_model import LogisticRegression
        from sklearn.feature_extraction import DictVectorizer
    except ImportError:
        print("  (sklearn not installed — skipping multivariate logistic; pip install scikit-learn)")
        return
    pids = list(nodes); y = [1 if nodes[p] == "core" else 0 for p in pids]
    if sum(y) < 10 or sum(y) == len(y): print("  (too few/all core — skip logistic)"); return
    dv = DictVectorizer(sparse=True)
    X = dv.fit_transform([{f: 1 for f in feats.get(p, ())} for p in pids])
    clf = LogisticRegression(max_iter=1000, C=1.0).fit(X, y)
    coef = sorted(zip(dv.get_feature_names_out(), clf.coef_[0]), key=lambda x: -x[1])
    print("  top + (predict core):")
    for f, c in coef[:12]: print(f"     {c:+.2f}  {f}")
    print("  top - (predict candidate):")
    for f, c in coef[-6:]: print(f"     {c:+.2f}  {f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(Path.home() / "policy_net.db"))
    ap.add_argument("--year", type=int, default=2026)
    ap.add_argument("--wikis", default="enwiki,dewiki,nlwiki")
    ap.add_argument("--min-support", type=int, default=3)
    ap.add_argument("--logistic", action="store_true")
    a = ap.parse_args()

    top_by_wiki = {}
    for wiki in a.wikis.split(","):
        nodes, feats = load(a.db, wiki, a.year)
        if not nodes: print(f"\n=== {wiki}: no data ==="); continue
        base, n, ncore, rows = enrichment(nodes, feats, a.min_support)
        known = known_indicators(a.db, wiki, a.year)
        # the interesting rows are NEW (not already an encoded indicator) — surface those
        new_rows = [r for r in rows if r[0] not in known]
        top_by_wiki[wiki] = rows
        print(f"\n=== {wiki} ===  admitted {n:,}  core {ncore:,}  base-core-rate {base:.3f}")
        print(f"  top features by lift  ([seed]=already an indicator, tautological; [NEW]=surprise):")
        for f, h, hc, p, lift in rows[:20]:
            tag = "[seed]" if f in known else "[NEW] "
            print(f"    {tag} lift {lift:5.1f}  core {hc:>4}/{h:<4}  {f[:64]}")
        print(f"  --- NEW high-lift features (not in our indicator set) — the actual discoveries:")
        for f, h, hc, p, lift in new_rows[:12]:
            print(f"     lift {lift:5.1f}  core {hc:>4}/{h:<4}  {f[:64]}")
        # off-diagonal residuals (the informative cases, not the confident center)
        miss = potential_misses(nodes, feats, rows)
        print(f"  candidates with >=2 top-40 core-features (potential MISSES): {len(miss)}")
        for pid, k in miss[:8]: print(f"     page_id {pid}  ({k} core-features)")
        hi = {f for f, *_ in rows[:40]}
        poor = [p for p, c in nodes.items() if c == "core" and not (feats.get(p, set()) & hi)]
        print(f"  CORE pages with NO top-40 feature (overview/iw-only, structurally odd): {len(poor)}")
        if a.logistic:
            print("  --- logistic kitchen sink ---"); logistic(nodes, feats, a.min_support)

    # cross-wiki: do the top discriminating features differ?
    if len(top_by_wiki) > 1:
        print("\n=== cross-wiki: top-10 lift features per wiki (do signals differ?) ===")
        for wiki, rows in top_by_wiki.items():
            print(f"  {wiki}:", [f.split(':',1)[-1][:24] for f,*_ in rows[:10]])


if __name__ == "__main__":
    main()
