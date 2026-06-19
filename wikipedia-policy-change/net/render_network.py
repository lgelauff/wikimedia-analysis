# /// script
# dependencies = ["matplotlib", "networkx", "scipy"]
# ///
"""
render_network.py — regenerate the exploratory graphs from the current CSVs.

Reproducible replacement for the one-off renders in commit 462f786. Reads
data/network/nodes.csv + edges.csv and writes, into the same dir:

  policy_network_overview.svg  — per-wiki summary: circle = #core pages,
                                 bar = mean within-core degree; pure stdlib.
  policy_network_layout.png    — node-link spring layout, nodes coloured by wiki,
                                 interwiki edges drawn faintly; needs matplotlib+networkx.

Metric note: "internal density" here = mean **undirected** within-core degree
(unique core neighbours per page) — the same number reported in FINDINGS.md §3
(en 23.3 …). edges.csv stores directed core->core wikilinks; we dedupe to
undirected for degree.

Usage:  uv run --script render_network.py [--dir ../data/network]
"""

import argparse
import collections
import csv
import statistics as st
from pathlib import Path

WIKI_COLORS = {  # stable per-wiki palette
    "enwiki": "#2b8a9e", "jawiki": "#7b3294", "frwiki": "#d95f02",
    "dewiki": "#1b9e77", "eswiki": "#e7298a", "nlwiki": "#66a61e",
}


def load(d):
    nodes = {r["node_id"]: r for r in csv.DictReader(open(d / "nodes.csv"))}
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


def stats(nodes, nbr, iw):
    bywiki = collections.defaultdict(list)
    for n, r in nodes.items():
        bywiki[r["wiki"]].append(n)
    wikis = sorted(bywiki, key=lambda w: -len(bywiki[w]))
    count = {w: len(bywiki[w]) for w in wikis}
    dens = {w: st.mean(len(nbr[n]) for n in bywiki[w]) for w in wikis}
    return wikis, count, dens, len(iw)


def render_svg(out, wikis, count, dens, n_iw):
    """per-wiki summary chart — pure stdlib, no deps."""
    short = {"enwiki": "en", "jawiki": "ja", "frwiki": "fr",
             "dewiki": "de", "eswiki": "es", "nlwiki": "nl"}
    xs = [95 + 100 * i for i in range(len(wikis))]
    cmax = max(count.values()); dmax = max(dens.values())
    L = []
    L.append('<svg width="100%" viewBox="0 0 680 230" role="img" '
             'xmlns="http://www.w3.org/2000/svg" '
             'font-family="-apple-system, Segoe UI, Roboto, sans-serif">')
    L.append('<style>.c-teal{fill:#2b8a9e}.c-purple{fill:#7b3294}'
             '.th{fill:#fff;font-weight:700;font-size:13px}'
             '.t{fill:#222;font-weight:600;font-size:14px}.ts{fill:#555;font-size:11px}</style>')
    L.append('<title>Policy core by wiki</title>')
    top = wikis[0]
    L.append(f'<desc>Six Wikipedia editions: circle size = core policy pages, '
             f'purple bar = mean within-core degree. {short[top]} largest '
             f'({count[top]}) and densest ({dens[top]:.1f}).</desc>')
    L.append('<g class="c-teal">')
    for x, w in zip(xs, wikis):
        r = 14 + 25 * (count[w] / cmax)
        L.append(f'<circle cx="{x}" cy="95" r="{r:.0f}"/>'
                 f'<text class="th" x="{x}" y="95" text-anchor="middle" '
                 f'dominant-baseline="central">{count[w]}</text>')
    L.append('</g>')
    for x, w in zip(xs, wikis):
        L.append(f'<text class="t" x="{x}" y="152" text-anchor="middle">{short[w]}</text>')
    for x, w in zip(xs, wikis):
        bw = 100 * (dens[w] / dmax)
        L.append(f'<rect class="c-purple" x="{x-50:.0f}" y="164" width="{bw:.0f}" height="8" rx="2"/>')
        L.append(f'<text class="ts" x="{x}" y="186" text-anchor="middle">{dens[w]:.1f}</text>')
    L.append('<circle class="c-teal" cx="48" cy="212" r="6"/>'
             '<text class="ts" x="60" y="212" text-anchor="start" '
             'dominant-baseline="central">core pages</text>')
    L.append('<rect class="c-purple" x="170" y="207" width="18" height="9" rx="2"/>'
             '<text class="ts" x="194" y="212" text-anchor="start" '
             'dominant-baseline="central">mean within-core degree</text>')
    L.append(f'<text class="ts" x="450" y="212" text-anchor="start" '
             f'dominant-baseline="central">+ {n_iw:,} interwiki links across cores</text>')
    L.append('</svg>')
    (out).write_text("\n".join(L), encoding="utf-8")


def render_layout(out, nodes, nbr, iw):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import networkx as nx
    G = nx.Graph()
    for n in nodes:
        G.add_node(n)
    for u, ns in nbr.items():
        for v in ns:
            if u < v:
                G.add_edge(u, v, kind="wikilink")
    for u, v in iw:
        G.add_edge(u, v, kind="interwiki")
    pos = nx.spring_layout(G, seed=42, k=0.25, iterations=60)
    fig, ax = plt.subplots(figsize=(13, 13))
    wl = [(u, v) for u, v, k in G.edges(data="kind") if k == "wikilink"]
    il = [(u, v) for u, v, k in G.edges(data="kind") if k == "interwiki"]
    nx.draw_networkx_edges(G, pos, edgelist=wl, edge_color="#cccccc", width=0.3, alpha=0.5, ax=ax)
    nx.draw_networkx_edges(G, pos, edgelist=il, edge_color="#d62728", width=0.6, alpha=0.5, ax=ax)
    cols = [WIKI_COLORS.get(nodes[n]["wiki"], "#888") for n in G.nodes]
    deg = dict(G.degree())
    sizes = [8 + 1.3 * deg[n] for n in G.nodes]
    nx.draw_networkx_nodes(G, pos, node_color=cols, node_size=sizes,
                           linewidths=0, ax=ax)
    handles = [plt.Line2D([0], [0], marker="o", color="w", label=w[:-4],
                          markerfacecolor=c, markersize=9)
               for w, c in WIKI_COLORS.items()]
    handles.append(plt.Line2D([0], [0], color="#d62728", label="interwiki", lw=1.5))
    ax.legend(handles=handles, loc="lower left", fontsize=11, framealpha=0.9)
    ax.set_title("Multi-wiki policy core — node-link (spring layout); "
                 "red = interwiki langlink edges", fontsize=13)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(out, dpi=130, bbox_inches="tight")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(Path(__file__).parent.parent / "data" / "network"))
    a = ap.parse_args()
    d = Path(a.dir)
    nodes, nbr, iw = load(d)
    wikis, count, dens, n_iw = stats(nodes, nbr, iw)
    print("per-wiki: " + " · ".join(f"{w[:2]} {count[w]}/{dens[w]:.1f}" for w in wikis)
          + f"  · interwiki {n_iw}")
    render_svg(d / "policy_network_overview.svg", wikis, count, dens, n_iw)
    print(f"wrote {d/'policy_network_overview.svg'}")
    render_layout(d / "policy_network_layout.png", nodes, nbr, iw)
    print(f"wrote {d/'policy_network_layout.png'}")


if __name__ == "__main__":
    main()
