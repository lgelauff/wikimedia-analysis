#!/usr/bin/env python3
"""
coverage_viz.py — visualize how well a set of atomic statements covers a page's text.

For each sentence of the page text, count how many statements map onto it (by content-word
overlap with the statement's source_quote / statement_orig), and colour it by that count:
  0 = uncovered (gap)   1 = yellow   2 = green   3+ = blue
Reveals topics that are skipped (gaps) or piled-up (over-covered) — a sanity check on extraction.

Pure stdlib. Emits a self-contained HTML fragment (style + content).

Usage:
  uv run python coverage_viz.py --text nlwiki_stemprocedure/01_clean_text.txt \
      --statements nlwiki_stemprocedure/04_statements_v2_inclusive.csv \
      --out coverage_stemprocedure_v2.html --title "Stemprocedure — v2 (43 statements)"
"""
import argparse, csv, html, re
from pathlib import Path

STOP = set("de het een en van op te in is dat die der den voor met als zijn er aan ook "
           "naar bij niet om of dan wordt worden mag moet kan deze dit daar over hun zo "
           "uit nog wel geen heeft had hij zij men je men's the a of to".split())
COLORS = {0: "#f3c0c0", 1: "#fff1a8", 2: "#9fe0a0", 3: "#9ec9f5"}  # gap / yellow / green / blue
LABEL  = {0: "0 (gap)", 1: "1", 2: "2", 3: "3+"}

def toks(s):
    return {w for w in re.findall(r"[a-zà-ÿ0-9%]+", s.lower()) if w not in STOP and len(w) > 1}

def split_sentences(text):
    units = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if re.match(r"(Artikel \d|Wikipedia:|\[)", line):       # header / annotation line
            units.append((line, True)); continue
        for s in re.split(r"(?<=[.!?:])\s+", line):
            s = s.strip()
            if s:
                units.append((s, False))
    return units

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True)
    ap.add_argument("--statements", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="statement coverage")
    ap.add_argument("--floor", type=float, default=0.34)   # overlap-coefficient threshold
    a = ap.parse_args()

    text = Path(a.text).read_text(encoding="utf-8")
    units = split_sentences(text)
    sent_idx = [i for i, (_, hdr) in enumerate(units) if not hdr]
    sent_tok = {i: toks(units[i][0]) for i in sent_idx}

    rows = list(csv.DictReader(open(a.statements, encoding="utf-8")))
    col = "source_quote" if rows and rows[0].get("source_quote") else "statement_orig"
    counts = {i: 0 for i in sent_idx}
    for r in rows:
        q = toks(r.get(col, ""))
        if not q:
            continue
        best, bi = 0.0, None
        for i in sent_idx:
            st = sent_tok[i]
            if not st:
                continue
            ov = len(q & st) / min(len(q), len(st))     # overlap coefficient
            if ov > best:
                best, bi = ov, i
        if bi is not None and best >= a.floor:
            counts[bi] += 1

    covered = sum(1 for i in sent_idx if counts[i] > 0)
    n = len(sent_idx)
    pct = 100 * covered // n if n else 0

    # render self-contained HTML fragment
    out = []
    out.append('<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:820px;'
               'line-height:1.9;color:#222;font-size:15px">')
    out.append(f'<div style="font-weight:700;font-size:17px;margin-bottom:4px">{html.escape(a.title)}</div>')
    out.append(f'<div style="color:#555;font-size:13px;margin-bottom:10px">{len(rows)} statements · '
               f'{n} sentences · <b>{pct}% covered</b> · {n-covered} gaps · '
               'matched by content-word overlap</div>')
    # legend
    leg = " ".join(f'<span style="background:{COLORS[k]};padding:1px 8px;border-radius:3px;'
                   f'margin-right:4px">{LABEL[k]}</span>' for k in (0, 1, 2, 3))
    out.append(f'<div style="margin-bottom:12px;font-size:13px">coverage: {leg}</div>')
    for i, (txt, hdr) in enumerate(units):
        if hdr:
            out.append(f'<div style="font-weight:700;margin:12px 0 2px;color:#333">{html.escape(txt)}</div>')
            continue
        c = counts[i]; col_c = COLORS[min(c, 3)]
        out.append(f'<span title="covered by {c}" style="background:{col_c};padding:1px 3px;'
                   f'border-radius:2px;margin:0 1px">{html.escape(txt)}'
                   f'<sup style="color:#666;font-size:9px">&nbsp;{c}</sup></span> ')
    out.append('</div>')
    Path(a.out).write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {a.out} | {n} sentences, {pct}% covered, {n-covered} gaps, "
          f"max coverage {max(counts.values()) if counts else 0}")

if __name__ == "__main__":
    main()
