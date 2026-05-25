"""
fetch.py — director script for research source fetching.

Reads sources.txt, fetches each entry through a configurable pipeline,
and writes cleaned text to cache/<citekey>.md.

Default pipeline (tried in order until one succeeds):
  wikimedia → arxiv → wayback → spn2

Override per-run:  --pipeline wayback,spn2
Override per-entry: add `strategy: wayback,spn2` to the entry in sources.txt

Rate limits default to ethical documented values (see lib/ratelimits.py).
Override per-run: --rate-override arxiv.org=5

Usage:
    python fetch.py [--dry-run] [--citekey KEY] [--force]
                   [--pipeline STAGE,...] [--no-spn2]
                   [--rate-override DOMAIN=SECS ...]

sources.txt format (--- separated blocks):
    ---
    citekey: small2021polis
    title: Some Paper Title
    url: https://example.com/paper.pdf
    access: open
    notes: Optional notes.

Credentials (from environment variables):
    IA_ACCESS_KEY / IA_SECRET_KEY   — Internet Archive (SPN2)
    WIKIMEDIA_ENTERPRISE_KEY        — optional, for Wikimedia Enterprise API
"""

import argparse
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# Resolve lib/ relative to this script so it works when called from any cwd.
sys.path.insert(0, str(Path(__file__).parent))

from lib.ratelimits import RateLimitRegistry
from lib.http import get as http_get
from lib.text import html_to_text, pdf_to_text
from lib.sources import parse as parse_sources, max_age_days
from lib import wikimedia, wayback as wb, spn2 as spn2_mod

_HERE      = Path(__file__).parent
_CACHE_DIR = _HERE / "cache"
_RAW_DIR   = _HERE / "raw"
_SOURCES   = _HERE / "sources.txt"

DEFAULT_PIPELINE = ["wikimedia", "arxiv", "wayback", "spn2"]
_SKIP_ACCESS = {"paywall", "login", "blocked"}

_ARXIV_RE = re.compile(r"arxiv\.org/(?:abs|pdf|html)/([0-9]+\.[0-9v]+)")


# ---------------------------------------------------------------------------
# Per-stage handlers
# Each returns (text, snapshot_date, method) or None to try the next stage.
# ---------------------------------------------------------------------------

def _stage_wikimedia(entry, url, rl, spn2, raw_dir):
    if not wikimedia.is_wikimedia(url):
        return None
    text = wikimedia.fetch(url, rl)
    return text, "live", "wikimedia-api"


def _stage_arxiv(entry, url, rl, spn2, raw_dir):
    arxiv_id = entry.get("arxiv", "").strip()
    if not arxiv_id or arxiv_id == "—":
        m = _ARXIV_RE.search(url)
        if not m:
            return None
        arxiv_id = m.group(1)
    text = _fetch_arxiv(arxiv_id, rl)
    return text, "live", "arxiv"


def _stage_wayback(entry, url, rl, spn2, raw_dir):
    snap = wb.availability(url, rl)
    if snap is None:
        return None
    age = wb.snapshot_age_days(snap["timestamp"])
    max_age = max_age_days(url)
    if age > max_age:
        print(f"    snapshot is {age}d old (max {max_age}d)", end=" ", flush=True)
        return None
    text = wb.fetch_snapshot(snap["url"], rl)
    date = datetime.strptime(snap["timestamp"][:8], "%Y%m%d").strftime("%Y-%m-%d")
    return text, date, "wayback"


def _stage_spn2(entry, url, rl, spn2, raw_dir):
    if spn2 is None:
        return None
    age_str = f"{max_age_days(url)}d"
    try:
        print("    SPN2 submitting…", end=" ", flush=True)
        result = spn2.capture(url, if_not_archived_within=age_str)
    except Exception as e:
        print(f"SPN2 error: {e}", end=" ", flush=True)
        return None
    if result.get("status") != "success":
        return None
    # Re-query Wayback for the freshly archived snapshot URL
    snap = wb.availability(url, rl)
    if snap is None:
        return None
    text = wb.fetch_snapshot(snap["url"], rl)
    date = datetime.strptime(snap["timestamp"][:8], "%Y%m%d").strftime("%Y-%m-%d")
    return text, date, "spn2+wayback"


def _stage_pdf(entry, url, rl, spn2, raw_dir):
    """Explicit opt-in stage — not in DEFAULT_PIPELINE.
    Detects PDF via Content-Type, not URL extension (avoids landing-page traps).
    """
    body, ct = http_get(url, rl, accept="application/pdf")
    if "application/pdf" not in ct:
        print(f"    PDF URL returned {ct!r} (landing page?) — skipping", end=" ")
        return None
    dest = raw_dir / f"{entry['citekey']}.pdf"
    dest.write_bytes(body)
    text = pdf_to_text(body)
    return text, "live", "direct-pdf"


def _stage_direct(entry, url, rl, spn2, raw_dir):
    """Explicit opt-in stage — not in DEFAULT_PIPELINE.
    Respects robots.txt; handles both HTML and PDF responses.
    """
    if not rl.is_allowed(url):
        raise PermissionError(f"blocked by robots.txt: {url}")
    body, ct = http_get(url, rl)
    if "application/pdf" in ct:
        dest = raw_dir / f"{entry['citekey']}.pdf"
        dest.write_bytes(body)
        return pdf_to_text(body), "live", "direct-pdf"
    return html_to_text(body.decode("utf-8", errors="replace")), "live", "direct"


_STAGES = {
    "wikimedia": _stage_wikimedia,
    "arxiv":     _stage_arxiv,
    "wayback":   _stage_wayback,
    "spn2":      _stage_spn2,
    "pdf":       _stage_pdf,
    "direct":    _stage_direct,
}


# ---------------------------------------------------------------------------
# Core fetch logic
# ---------------------------------------------------------------------------

def fetch_entry(
    entry: dict,
    rl: RateLimitRegistry,
    spn2,
    pipeline: list[str],
    raw_dir: Path,
) -> tuple[str, str, str]:
    """
    Try each stage in pipeline until one returns content.
    Returns (text, snapshot_date, method).
    Raises RuntimeError if all stages fail.
    """
    url = entry.get("url", "").strip()

    # Per-entry pipeline override via `strategy: wayback,spn2` in sources.txt
    if entry.get("strategy"):
        pipeline = [s.strip() for s in entry["strategy"].split(",")]

    for stage_name in pipeline:
        handler = _STAGES.get(stage_name)
        if handler is None:
            print(f"    unknown pipeline stage '{stage_name}' — skipping", end=" ")
            continue
        result = handler(entry, url, rl, spn2, raw_dir)
        if result is not None:
            return result

    raise RuntimeError(f"all pipeline stages failed for {url}")


def _fetch_arxiv(arxiv_id: str, rl: RateLimitRegistry) -> str:
    """Try arXiv HTML full text, fall back to abstract page."""
    try:
        body, _ = http_get(f"https://arxiv.org/html/{arxiv_id}", rl)
        text = html_to_text(body.decode("utf-8", errors="replace"))
        if len(text) > 2000:
            return text
    except Exception:
        pass
    body, _ = http_get(f"https://arxiv.org/abs/{arxiv_id}", rl)
    return html_to_text(body.decode("utf-8", errors="replace"))


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run(
    sources_path: Path = _SOURCES,
    cache_dir: Path = _CACHE_DIR,
    raw_dir: Path = _RAW_DIR,
    dry_run: bool = False,
    only_citekey: str | None = None,
    force: bool = False,
    pipeline: list[str] = DEFAULT_PIPELINE,
    rate_overrides: dict[str, float] | None = None,
    use_spn2: bool = True,
):
    entries = parse_sources(sources_path)
    if only_citekey:
        entries = [e for e in entries if e.get("citekey") == only_citekey]
        if not entries:
            print(f"citekey not found: {only_citekey}", file=sys.stderr)
            sys.exit(1)

    to_fetch = [
        e for e in entries
        if e.get("citekey")
        and e.get("access", "").lower() not in _SKIP_ACCESS
        and (force or not (cache_dir / f"{e['citekey']}.md").exists())
    ]

    rl = RateLimitRegistry(overrides=rate_overrides)

    spn2 = None
    if use_spn2:
        try:
            spn2 = spn2_mod.SPN2Client()
        except EnvironmentError as e:
            print(f"SPN2 disabled: {e}")

    print(
        f"Sources to fetch: {len(to_fetch)}  "
        f"pipeline={','.join(pipeline)}  "
        f"spn2={'yes' if spn2 else 'no'}  "
        f"dry_run={dry_run}"
    )
    cache_dir.mkdir(exist_ok=True)
    raw_dir.mkdir(exist_ok=True)

    ok = skip = err = 0
    for i, e in enumerate(to_fetch, 1):
        citekey = e["citekey"]
        url = e.get("url", "(no url)")
        effective_pipeline = (
            [s.strip() for s in e["strategy"].split(",")]
            if e.get("strategy") else pipeline
        )
        ref = rl.reference_for(url) or ""
        print(
            f"  [{i}/{len(to_fetch)}] {citekey}"
            f"  [{','.join(effective_pipeline)}]"
            f"  {url[:55]}",
            end=" … ", flush=True,
        )

        if dry_run:
            print("(dry run)")
            continue

        try:
            text, snapshot_date, method = fetch_entry(e, rl, spn2, pipeline, raw_dir)
            if not text.strip():
                print("EMPTY — skipped")
                skip += 1
                continue
            header = (
                f"# {e.get('title', citekey)}\n"
                f"Source: {url}\n"
                f"Fetched: {time.strftime('%Y-%m-%d')}  "
                f"Snapshot: {snapshot_date}  "
                f"Method: {method}"
                + (f"  RateLimit-ref: {ref}" if ref else "")
                + "\n\n"
            )
            (cache_dir / f"{citekey}.md").write_text(header + text, encoding="utf-8")
            print(f"ok ({len(text):,} chars, snapshot={snapshot_date}, method={method})")
            ok += 1
        except Exception as exc:
            print(f"ERROR: {exc}")
            err += 1

    print(f"\nDone: {ok} fetched, {skip} empty/skipped, {err} errors")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description="Fetch research sources via Wayback / SPN2.")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--citekey", help="Process only this citekey")
    p.add_argument("--force", action="store_true", help="Re-fetch even if cache exists")
    p.add_argument(
        "--pipeline",
        default=",".join(DEFAULT_PIPELINE),
        help=f"Comma-separated stages (default: {','.join(DEFAULT_PIPELINE)})",
    )
    p.add_argument("--no-spn2", action="store_true", help="Disable SavePageNow")
    p.add_argument(
        "--rate-override",
        action="append",
        metavar="DOMAIN=SECS",
        help="Override delay for a domain, e.g. --rate-override arxiv.org=5",
    )
    a = p.parse_args()

    rate_overrides: dict[str, float] = {}
    for override in a.rate_override or []:
        domain, _, secs = override.partition("=")
        rate_overrides[domain.strip()] = float(secs.strip())

    run(
        dry_run=a.dry_run,
        only_citekey=a.citekey,
        force=a.force,
        pipeline=[s.strip() for s in a.pipeline.split(",")],
        rate_overrides=rate_overrides or None,
        use_spn2=not a.no_spn2,
    )


if __name__ == "__main__":
    main()
