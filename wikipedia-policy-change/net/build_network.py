#!/usr/bin/env python3
"""
build_network.py — export the multi-wiki policy CORE as one network.

Nodes  = core pages across the wikis (node id = "<wiki>:<page_id>").
Edges  = (a) intra-wiki in-body wikilinks, core->core (from ToolsDB `link`);
         (b) INTER-wiki links from the replica `langlinks` table DIRECTLY
             (no Wikidata) — kept only when the langlink target is itself a core
             node on the target wiki.

Outputs (repeatable): nodes.csv, edges.csv, policy_network.graphml.

Runs on Toolforge (ToolsDB for cores+links, replica for langlinks, API for the
per-wiki namespace map). Creds from ~/replica.my.cnf.

Usage:
  python3 build_network.py --year 2026 --wikis enwiki,dewiki,nlwiki,frwiki,eswiki,jawiki
"""

import argparse
import configparser
import json
import ssl
import sys
import urllib.parse
import urllib.request
import xml.sax.saxutils as sx
from pathlib import Path

try:
    import pymysql
except ImportError:
    pymysql = None

UA = "WikimediaAnalysis/1.0 (research; https://github.com/lgelauff/wikimedia-analysis)"
_SSL = ssl.create_default_context()
BATCH = 500


def creds():
    p = Path.home() / "replica.my.cnf"
    if not p.exists(): return None
    c = configparser.ConfigParser(); c.read(p)
    return c["client"]["user"].strip("'\""), c["client"]["password"].strip("'\"")


def toolsdb():
    u, pw = creds()
    return pymysql.connect(host="tools.db.svc.wikimedia.cloud", user=u, password=pw,
                           database=f"{u}__policies", charset="utf8mb4", autocommit=True)


def replica(wiki):
    u, pw = creds()
    return pymysql.connect(host=f"{wiki}.analytics.db.svc.wikimedia.cloud", user=u, password=pw,
                           database=f"{wiki}_p", charset="utf8mb4", autocommit=True)


def dec(x): return x.decode() if isinstance(x, bytes) else x


def api(wiki, params):
    lang = wiki[:-4] if wiki.endswith("wiki") else wiki
    params = {**params, "format": "json", "formatversion": "2"}
    url = f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}),
                                timeout=60, context=_SSL) as r:
        return json.loads(r.read())


def nsmap(wiki):
    """{lowercased prefix: ns_id} for resolving langlink titles on the target wiki."""
    d = api(wiki, {"action": "query", "meta": "siteinfo",
                   "siprop": "namespaces|namespacealiases"})
    m = {}
    for ns in d["query"]["namespaces"].values():
        if ns["id"] < 0: continue
        for k in (ns.get("name", ""), ns.get("canonical", "")):
            if k: m[k.replace(" ", "_").lower()] = ns["id"]
    for a in d["query"].get("namespacealiases", []):
        m[a["alias"].replace(" ", "_").lower()] = a["id"]
    return m


def norm(s):
    s = s.split("#")[0].strip().lstrip(":").replace(" ", "_")
    return (s[0].upper() + s[1:]) if s else s


def parse_title(raw, nsm):
    raw = raw.strip().lstrip(":")
    if ":" in raw:
        pre, rest = raw.split(":", 1)
        ns = nsm.get(pre.replace(" ", "_").lower())
        if ns is not None:
            return ns, norm(rest)
    return 0, norm(raw)


def batched(seq, n=BATCH):
    seq = list(seq)
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2026)
    ap.add_argument("--wikis", default="enwiki,dewiki,nlwiki,frwiki,eswiki,jawiki")
    ap.add_argument("--out", default=str(Path.home() / "policy_network"))
    a = ap.parse_args()
    wikis = a.wikis.split(",")
    if pymysql is None: sys.exit("pip install pymysql")
    if creds() is None:
        print("No ~/replica.my.cnf — run on Toolforge. Exiting cleanly."); sys.exit(0)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    td = toolsdb()

    # 1. nodes + per-wiki (ns,title)->node_id and core page_id sets
    print("nodes …")
    nodes = []                       # (node_id, wiki, page_id, title, ns, qid, confidence, admitted_via, native)
    core_key = {w: {} for w in wikis}
    core_pids = {w: set() for w in wikis}
    NATIVE_VIA = {"status_template", "overview", "core_category", "wikidata"}
    for w in wikis:
        with td.cursor() as cur:
            cur.execute("SELECT page_id,title,namespace,wikidata_qid,confidence,admitted_via,status_tier "
                        "FROM node WHERE wiki=%s AND year=%s AND confidence='core'", (w, a.year))
            for pid, title, ns, qid, conf, via, tier in cur.fetchall():
                title = dec(title); nid = f"{w}:{pid}"
                native = 1 if (dec(via) in NATIVE_VIA) else 0
                nodes.append((nid, w, pid, title, ns, dec(qid) or "", dec(conf), dec(via), native, dec(tier) or ""))
                core_key[w][(ns, title)] = nid
                core_pids[w].add(pid)
        print(f"  {w}: {len(core_pids[w]):,} core")

    # 2. intra-wiki edges: core->core wikilinks (from ToolsDB link)
    print("intra-wiki edges …")
    edges = []                       # (src, tgt, type, wiki)
    for w in wikis:
        with td.cursor() as cur:
            cur.execute("SELECT from_page,to_page FROM link "
                        "WHERE wiki=%s AND year=%s AND to_admitted=1 AND to_page IS NOT NULL",
                        (w, a.year))
            cp = core_pids[w]
            for f, t in cur.fetchall():
                if f in cp and t in cp:
                    edges.append((f"{w}:{f}", f"{w}:{t}", "wikilink", w))
        print(f"  {w}: {sum(1 for e in edges if e[3]==w and e[2]=='wikilink'):,} core->core")

    # 3. inter-wiki edges from langlinks (NO wikidata)
    print("inter-wiki edges (langlinks) …")
    lang2wiki = {w[:-4]: w for w in wikis}
    nsm = {w: nsmap(w) for w in wikis}
    iw = set()                       # frozenset({src,tgt}) to dedup symmetric langlinks
    for w in wikis:
        rep = replica(w)
        for ch in batched(list(core_pids[w])):
            ph = ",".join(["%s"] * len(ch))
            with rep.cursor() as cur:
                cur.execute(f"SELECT ll_from, ll_lang, ll_title FROM langlinks "
                            f"WHERE ll_from IN ({ph})", ch)
                rows = cur.fetchall()
            for frm, lang, title in rows:
                lang = dec(lang); tw = lang2wiki.get(lang)
                if not tw: continue
                ns, t = parse_title(dec(title), nsm[tw])
                tgt = core_key[tw].get((ns, t))
                if tgt:
                    iw.add(frozenset((f"{w}:{frm}", tgt)))
        rep.close()
    for pair in iw:
        s, t = tuple(pair) if len(pair) == 2 else (next(iter(pair)),) * 2
        edges.append((s, t, "interwiki", ""))
    print(f"  interwiki edges: {len(iw):,}")

    # 4. write nodes.csv, edges.csv, GraphML
    import csv
    with (out / "nodes.csv").open("w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["node_id", "wiki", "page_id", "title", "namespace", "qid",
                     "confidence", "admitted_via", "native", "status_tier"])
        wr.writerows(nodes)
    with (out / "edges.csv").open("w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["source", "target", "type", "wiki"])
        wr.writerows(edges)

    nkeys = [("wiki", "string"), ("title", "string"), ("namespace", "long"),
             ("qid", "string"), ("confidence", "string"), ("admitted_via", "string"),
             ("native", "long"), ("status_tier", "string")]
    with (out / "policy_network.graphml").open("w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<graphml xmlns="http://graphml.graphdrawing.org/xmlns">\n')
        for k, ty in nkeys:
            f.write(f'  <key id="{k}" for="node" attr.name="{k}" attr.type="{ty}"/>\n')
        f.write('  <key id="etype" for="edge" attr.name="type" attr.type="string"/>\n')
        f.write('  <key id="ewiki" for="edge" attr.name="wiki" attr.type="string"/>\n')
        f.write('  <graph edgedefault="directed">\n')
        for nd in nodes:
            nid, w, pid, title, ns, qid, conf, via, native, tier = nd
            f.write(f'    <node id={sx.quoteattr(nid)}>\n')
            for (k, _), v in zip(nkeys, (w, title, ns, qid, conf, via, native, tier)):
                f.write(f'      <data key="{k}">{sx.escape(str(v))}</data>\n')
            f.write('    </node>\n')
        for i, (s, t, ty, w) in enumerate(edges):
            f.write(f'    <edge id="e{i}" source={sx.quoteattr(s)} target={sx.quoteattr(t)}>\n')
            f.write(f'      <data key="etype">{ty}</data>\n')
            if w: f.write(f'      <data key="ewiki">{w}</data>\n')
            f.write('    </edge>\n')
        f.write('  </graph>\n</graphml>\n')

    print(f"\n=== network ===")
    print(f"  nodes: {len(nodes):,}  ({', '.join(f'{w} {len(core_pids[w])}' for w in wikis)})")
    print(f"  edges: {len(edges):,}  (wikilink {sum(1 for e in edges if e[2]=='wikilink'):,} · "
          f"interwiki {sum(1 for e in edges if e[2]=='interwiki'):,})")
    print(f"  wrote {out}/nodes.csv, edges.csv, policy_network.graphml")


if __name__ == "__main__":
    main()
