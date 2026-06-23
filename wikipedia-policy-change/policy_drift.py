# /// script
# dependencies = ["certifi", "mwparserfromhell"]
# ///
"""
policy_drift.py — measure how much a policy page has changed over time.

For a single wiki + policy page:
  1. Fetch the full revision index (IDs + timestamps) via MediaWiki API
  2. Select one snapshot per year (last revision of each calendar year)
  3. Fetch wikitext for each snapshot via API
  4. Strip wiki markup to plain text
  5. Compute per-year metrics:
     - word_count
     - words_added / words_removed vs previous year
     - cosine_similarity vs previous year
     - containment_forward: fraction of old sentences still in new version
     - containment_backward: fraction of new sentences already in old version
  6. Write results to data/policy_drift/<wiki>__<title>.csv

Usage:
    uv run python policy_drift.py
    uv run python policy_drift.py --wiki en.wikipedia --title "Wikipedia:Neutral_point_of_view"
"""

import argparse
import json
import math
import re
import ssl
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

import certifi

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_WIKI  = "en.wikipedia"
DEFAULT_TITLE = "Wikipedia:Neutral_point_of_view"

OUT_DIR    = Path(__file__).parent / "data" / "policy_drift"
CACHE_DIR  = Path(__file__).parent / "tmp" / "revisions"
RATE_DELAY = 1.0  # seconds between API calls

UA = (
    "WikimediaAnalysis/1.0 "
    "(personal research project; https://github.com/lgelauff/wikimedia-analysis)"
)

_SSL_CTX = ssl.create_default_context(cafile=certifi.where())


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def _api_base(wiki: str) -> str:
    return f"https://{wiki}.org/w/api.php"


def _get(wiki: str, params: dict) -> dict:
    url = _api_base(wiki) + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": UA, "Accept": "application/json"},
    )
    for attempt in range(5):
        time.sleep(RATE_DELAY * (2 ** attempt) if attempt else RATE_DELAY)
        try:
            with urllib.request.urlopen(req, timeout=30, context=_SSL_CTX) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 30 * (2 ** attempt)
                print(f"  429 rate-limited, waiting {wait}s …", flush=True)
                time.sleep(wait)
            else:
                raise
    raise RuntimeError(f"Failed after 5 attempts: {url}")


def fetch_revision_index(wiki: str, title: str) -> list[dict]:
    """
    Return list of {revid, timestamp} for all revisions of a page,
    oldest first. Uses rvdir=newer + continuation to page through all results.
    """
    revisions = []
    params = {
        "action":        "query",
        "titles":        title,
        "prop":          "revisions",
        "rvprop":        "ids|timestamp",
        "rvlimit":       "max",
        "rvdir":         "newer",
        "format":        "json",
        "formatversion": "2",
        "redirects":     "1",
        "maxlag":        "5",
    }
    while True:
        data = _get(wiki, params)
        pages = data.get("query", {}).get("pages", [])
        if not pages:
            break
        revisions.extend(pages[0].get("revisions", []))
        cont = data.get("continue", {})
        if not cont:
            break
        params.update(cont)

    print(f"  {len(revisions):,} total revisions")
    return revisions


def fetch_revision_text(wiki: str, revid: int) -> str:
    """Fetch wikitext for a specific revision ID."""
    cache_file = CACHE_DIR / wiki / f"{revid}.txt"
    if cache_file.exists():
        return cache_file.read_text(encoding="utf-8")

    data = _get(wiki, {
        "action":        "query",
        "revids":        str(revid),
        "prop":          "revisions",
        "rvprop":        "content",
        "rvslots":       "main",
        "format":        "json",
        "formatversion": "2",
        "maxlag":        "5",
    })
    pages = data.get("query", {}).get("pages", [])
    if not pages:
        raise RuntimeError(f"revid {revid} not found")
    rev = pages[0]["revisions"][0]
    text = rev["slots"]["main"]["content"]

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(text, encoding="utf-8")
    return text


# ---------------------------------------------------------------------------
# Text processing
# ---------------------------------------------------------------------------

# Category and interwiki links (e.g. [[Category:…]], [[de:…]]) are scaffolding,
# not policy text. Strip them before parsing so they don't leak in as link labels.
# The leading-letter requirement skips in-text links like [[:Category:…]] and
# ordinary wikilinks (no namespace/lang prefix).
_NS_LINK = re.compile(r"\[\[[A-Za-z][A-Za-z\-]*:[^\]]*\]\]", re.S)


def strip_markup(wikitext: str) -> str:
    """
    Strip wiki markup to plain policy text using mwparserfromhell.

    mwparserfromhell parses the wikitext into a node tree and `strip_code()`
    removes templates (at any nesting depth), ref tags, HTML, file embeds,
    and heading/format markers while keeping link display text. This replaces
    the previous single-level regex template stripper, which mangled nested
    templates and produced phantom year-over-year discontinuities (see
    .claude/discontinuity/FINDING.md).
    """
    import mwparserfromhell

    text = _NS_LINK.sub(" ", wikitext)
    code = mwparserfromhell.parse(text)
    text = code.strip_code(normalize=True, collapse=True)
    # collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text: str) -> list[str]:
    return re.findall(r"\b\w+\b", text.lower())


def sentences(text: str) -> list[str]:
    """Split into sentences; normalize whitespace."""
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in parts if len(s.strip()) > 20]


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def cosine_similarity(a: list[str], b: list[str]) -> float:
    ca, cb = Counter(a), Counter(b)
    vocab = set(ca) | set(cb)
    dot  = sum(ca[w] * cb[w] for w in vocab)
    na   = math.sqrt(sum(v * v for v in ca.values()))
    nb   = math.sqrt(sum(v * v for v in cb.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def containment(src_sentences: list[str], tgt_text: str) -> float:
    """
    Fraction of src_sentences that appear (case-insensitive substring match)
    in tgt_text. A sentence 'contains' if its first 60 chars appear in tgt.
    Uses a 60-char prefix to be robust to minor trailing punctuation changes.
    """
    if not src_sentences:
        return 1.0
    tgt_lower = tgt_text.lower()
    found = sum(
        1 for s in src_sentences
        if s[:60].lower() in tgt_lower
    )
    return found / len(src_sentences)


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------

def select_yearly_snapshots(revisions: list[dict]) -> dict[int, int]:
    """
    Return {year: revid} — the last revision ID in each calendar year.
    """
    yearly = {}
    for rev in revisions:
        year = int(rev["timestamp"][:4])
        yearly[year] = rev["revid"]   # later revisions overwrite earlier ones
    return dict(sorted(yearly.items()))


def analyse(wiki: str, title: str) -> list[dict]:
    print(f"\n=== {wiki} / {title} ===")

    print("Fetching revision index …")
    revisions = fetch_revision_index(wiki, title)
    yearly    = select_yearly_snapshots(revisions)
    print(f"  Yearly snapshots: {list(yearly.keys())}")

    rows = []
    prev_tokens    = None
    prev_sentences = None
    prev_text      = None

    for year, revid in yearly.items():
        print(f"  {year}  revid={revid} …", end=" ", flush=True)
        wikitext = fetch_revision_text(wiki, revid)
        text     = strip_markup(wikitext)
        tokens   = tokenize(text)
        sents    = sentences(text)

        row = {
            "wiki":        wiki,
            "title":       title,
            "year":        year,
            "revid":       revid,
            "word_count":  len(tokens),
            "sent_count":  len(sents),
        }

        if prev_tokens is not None:
            prev_set = Counter(prev_tokens)
            cur_set  = Counter(tokens)
            added    = sum((cur_set - prev_set).values())
            removed  = sum((prev_set - cur_set).values())
            row["words_added"]             = added
            row["words_removed"]           = removed
            row["cosine_vs_prev"]          = round(cosine_similarity(prev_tokens, tokens), 4)
            row["containment_old_in_new"]  = round(containment(prev_sentences, text), 4)
            row["containment_new_in_old"]  = round(containment(sents, prev_text), 4)
        else:
            row["words_added"]             = None
            row["words_removed"]           = None
            row["cosine_vs_prev"]          = None
            row["containment_old_in_new"]  = None
            row["containment_new_in_old"]  = None

        rows.append(row)
        prev_tokens    = tokens
        prev_sentences = sents
        prev_text      = text
        print(f"{len(tokens):,} words")

    return rows


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def write_csv(rows: list[dict], wiki: str, title: str) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^\w]+", "_", f"{wiki}__{title}").strip("_")[:100]
    out  = OUT_DIR / f"{slug}.csv"

    cols = [
        "wiki", "title", "year", "revid",
        "word_count", "sent_count",
        "words_added", "words_removed",
        "cosine_vs_prev",
        "containment_old_in_new",
        "containment_new_in_old",
    ]

    import csv
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    print(f"\nWrote {len(rows)} rows → {out}")
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Measure policy page drift over time")
    parser.add_argument("--wiki",  default=DEFAULT_WIKI,  help="e.g. en.wikipedia")
    parser.add_argument("--title", default=DEFAULT_TITLE, help="MediaWiki page title")
    args = parser.parse_args()

    rows = analyse(args.wiki, args.title)
    write_csv(rows, args.wiki, args.title)

    # Print a quick summary table
    print("\nYear | Words | Cosine | Old-in-New | New-in-Old")
    print("-----|-------|--------|------------|----------")
    for r in rows:
        cos = f"{r['cosine_vs_prev']:.3f}" if r["cosine_vs_prev"] is not None else "  —  "
        oin = f"{r['containment_old_in_new']:.3f}" if r["containment_old_in_new"] is not None else "  —  "
        nio = f"{r['containment_new_in_old']:.3f}" if r["containment_new_in_old"] is not None else "  —  "
        print(f"{r['year']} | {r['word_count']:>5} | {cos} | {oin} | {nio}")


if __name__ == "__main__":
    main()
