#!/usr/bin/env python3
# /// script
# dependencies = ["matplotlib"]
# ///
"""
page_inclusion_viz.py — over the REAL rendered page text, mark which blocks are
INCLUDED (become atomic statements) vs EXCLUDED (dropped before extraction).

Fetches the page via the MediaWiki API (action=parse → HTML), strips markup to reader-text
blocks (the way the page looks, no wikicode), then shades each block:
  green  = included (a statement maps onto it)
  red    = excluded (no statement — deliberation / meta / scaffolding)
Match = content-word overlap between a block and any statement's source_quote/statement_orig.
Output: a self-contained HTML over the actual page text. Pure stdlib.

Usage:
  uv run python page_inclusion_viz.py --wiki nl.wikipedia.org \
     --title "Wikipedia:Stemlokaal/Stemgerechtigde gebruikers" \
     --statements nlwiki_stemgerechtigde_gebruikers/04_statements.csv \
     --out nlwiki_stemgerechtigde_gebruikers/page_inclusion.html
"""
import argparse, csv, html, json, re, urllib.parse, urllib.request
from html.parser import HTMLParser
from pathlib import Path

UA = "WikimediaAnalysis/1.0 (research; https://github.com/lgelauff/wikimedia-analysis)"
STOP = set("de het een en van op te in is dat die der den voor met als zijn er aan ook of dan "
           "wordt worden mag moet kan deze dit daar over hun zo uit nog wel geen heeft had hij "
           "zij men je naar bij niet om".split())
BLOCK = {"p", "li", "dd", "dt", "h1", "h2", "h3", "h4", "blockquote", "th", "td"}
SKIP = {"style", "script"}                       # plus class-based: mw-editsection, reference


class Strip(HTMLParser):
    def __init__(self):
        super().__init__()
        self.blocks, self.buf, self.stack = [], [], []   # stack = open skip-triggering tags
    def handle_starttag(self, tag, attrs):
        if tag in BLOCK:
            self._flush()
        cls = dict(attrs).get("class", "")
        if tag in SKIP or "mw-editsection" in cls or "reference" in cls:
            self.stack.append(tag)
    def handle_endtag(self, tag):
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        if tag in BLOCK:
            self._flush()
    def handle_data(self, data):
        if not self.stack:
            self.buf.append(data)
    def _flush(self):
        t = re.sub(r"\s+", " ", "".join(self.buf)).strip()
        if t:
            self.blocks.append(t)
        self.buf = []
    def close(self):
        self._flush(); super().close()


def toks(s):
    return {w for w in re.findall(r"[a-zà-ÿ0-9%]+", s.lower()) if w not in STOP and len(w) > 1}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wiki", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--statements", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--out-png", default=None)
    ap.add_argument("--floor", type=float, default=0.40)
    a = ap.parse_args()

    url = (f"https://{a.wiki}/w/api.php?action=parse&prop=text&formatversion=2&format=json&"
           f"page={urllib.parse.quote(a.title)}")
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as r:
        page_html = json.loads(r.read())["parse"]["text"]
    p = Strip(); p.feed(page_html); p.close()
    blocks = [b for b in p.blocks if len(b) > 1]

    rows = list(csv.DictReader(open(a.statements, encoding="utf-8")))
    col = "source_quote" if rows and rows[0].get("source_quote") else "statement_orig"
    stoks = [toks(r.get(col, "")) for r in rows]

    marks, inc_chars, tot_chars = [], 0, 0
    for b in blocks:
        bt = toks(b)
        best = 0.0
        for st in stoks:
            if st and bt:
                best = max(best, len(bt & st) / min(len(bt), len(st)))
        included = best >= a.floor
        marks.append(included)
        tot_chars += len(b); inc_chars += len(b) if included else 0
    n = len(blocks); inc = sum(marks)
    pct_b = 100 * inc // n if n else 0
    pct_c = 100 * inc_chars // tot_chars if tot_chars else 0

    G, Rd = "#bfe6b0", "#f4b8b8"
    H = ['<div style="font-family:var(--font-sans);max-width:860px;font-size:14px;line-height:1.55">']
    H.append(f'<div style="font-weight:500;font-size:17px;color:var(--text-primary)">{html.escape(a.title)}</div>')
    H.append(f'<div style="font-size:13px;color:var(--text-secondary);margin:2px 0 6px">real rendered page · '
             f'{n} text blocks · included {inc} ({pct_b}% of blocks, {pct_c}% of text) · rest excluded before extraction</div>')
    H.append(f'<div style="font-size:12px;margin-bottom:12px">'
             f'<span style="background:{G};color:#1c3a14;padding:1px 8px;border-radius:3px;margin-right:6px">included → statements</span>'
             f'<span style="background:{Rd};color:#4a1414;padding:1px 8px;border-radius:3px">excluded (deliberation / meta / scaffolding)</span></div>')
    for b, ok in zip(blocks, marks):
        bg, fg = (G, "#1c3a14") if ok else (Rd, "#4a1414")
        H.append(f'<div style="background:{bg};color:{fg};padding:3px 8px;margin:2px 0;border-radius:3px">{html.escape(b)}</div>')
    H.append('</div>')
    Path(a.out).write_text("\n".join(H), encoding="utf-8")

    if a.out_png:                                   # compact minimap: one bar per block
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import Patch
        fig, ax = plt.subplots(figsize=(5.2, max(3.0, n * 0.058)))
        for i, ok in enumerate(marks):
            ax.add_patch(plt.Rectangle((0, n - i - 1), 1, 1, facecolor=(G if ok else Rd), edgecolor="none"))
        ax.set_xlim(0, 1); ax.set_ylim(0, n); ax.axis("off")
        ax.set_title(f"{a.title}\nincluded {pct_b}% of blocks · {pct_c}% of text "
                     f"(top→bottom = page order)", fontsize=10, loc="left")
        ax.legend(handles=[Patch(facecolor=G, label="included → statements"),
                           Patch(facecolor=Rd, label="excluded before extraction")],
                  loc="lower center", bbox_to_anchor=(0.5, -0.04), ncol=2, fontsize=9, frameon=False)
        fig.tight_layout(); fig.savefig(a.out_png, dpi=150, bbox_inches="tight"); plt.close(fig)

    print(f"wrote {a.out} | {n} blocks, included {inc} ({pct_b}% blocks / {pct_c}% text)")


if __name__ == "__main__":
    main()
