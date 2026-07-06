#!/usr/bin/env python3
"""fetch_clean.py — #2 clean-text stage: fetch the real rendered page (action=parse),
strip to reader text (no markup), write one file per page. Pure stdlib.

Usage: uv run python fetch_clean.py --pages "en.wikipedia.org:Wikipedia:Neutral point of view,..." --outdir runs
"""
import argparse, json, re, unicodedata, urllib.parse, urllib.request
from html.parser import HTMLParser
from pathlib import Path

UA = "WikimediaAnalysis/1.0 (research; https://github.com/lgelauff/wikimedia-analysis)"
BLOCK = {"p", "li", "dd", "dt", "h1", "h2", "h3", "h4", "blockquote", "th", "td", "caption"}
SKIP = {"style", "script"}


class Strip(HTMLParser):
    def __init__(self):
        super().__init__(); self.blocks, self.buf, self.stack = [], [], []
    def handle_starttag(self, tag, attrs):
        if tag in BLOCK: self._flush()
        cls = dict(attrs).get("class", "")
        if tag in SKIP or "mw-editsection" in cls or "reference" in cls: self.stack.append(tag)
    def handle_endtag(self, tag):
        if self.stack and self.stack[-1] == tag: self.stack.pop()
        if tag in BLOCK: self._flush()
    def handle_data(self, d):
        if not self.stack: self.buf.append(d)
    def _flush(self):
        t = re.sub(r"\s+", " ", "".join(self.buf)).strip()
        if t: self.blocks.append(t)
        self.buf = []
    def close(self): self._flush(); super().close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", required=True)
    ap.add_argument("--outdir", default="runs")
    a = ap.parse_args()
    out = Path(a.outdir); out.mkdir(parents=True, exist_ok=True)
    for spec in a.pages.split(","):
        host, title = spec.split(":", 1)
        url = (f"https://{host}/w/api.php?action=parse&prop=text&formatversion=2&format=json&"
               f"page={urllib.parse.quote(title)}")
        h = json.loads(urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": UA}), timeout=90).read())["parse"]["text"]
        p = Strip(); p.feed(h); p.close()
        text = unicodedata.normalize("NFC", "\n".join(p.blocks))     # NFC per #2 offset contract
        lang = host.split(".")[0]
        slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")[:40]
        f = out / f"{lang}__{slug}.clean.txt"
        f.write_text(f"# {host} :: {title}\n\n{text}\n", encoding="utf-8")
        print(f"{f}  ({len(p.blocks)} blocks, {len(text):,} chars)")


if __name__ == "__main__":
    main()
