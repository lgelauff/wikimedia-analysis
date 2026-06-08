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

Pre-flight enrichment (runs before the fetch loop):
  Citoid  — fills missing title/year/url from Wikipedia's citation resolver.
  OpenAlex — fills missing url (OA PDF), year, abstract from the scholarly graph.
  Both run only for entries missing the relevant fields; existing values are never overwritten.

Usage:
    python fetch.py [--dry-run] [--citekey KEY] [--force]
                   [--pipeline STAGE,...] [--no-spn2] [--ignore-robots]
                   [--no-enrich] [--rate-override DOMAIN=SECS ...]

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
import json
import os
import re
import sys
import time
from datetime import date, datetime
from pathlib import Path

import requests

from .lib.ratelimits import RateLimitRegistry
from .lib.http import get as http_get, _UA
from .lib.text import html_to_text, pdf_to_text
from .lib.sources import parse as parse_sources, max_age_days
from .lib import (
    wikimedia, wayback as wb, spn2 as spn2_mod, citoid, openalex,
    unpaywall, memento, archivetoday,
)

# One shared HTTP session (keep-alive) reused across stages and the whole run.
_SESSION = None


def _session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
        _SESSION.headers.update({"User-Agent": _UA})
    return _SESSION

from . import __version__

# Package lives at <repo>/source_collection/; default data dirs stay at <repo>/.
_HERE      = Path(__file__).resolve().parent.parent
_CACHE_DIR = _HERE / "cache"
_RAW_DIR   = _HERE / "raw"
_SOURCES   = _HERE / "sources.txt"
# Failed fetches are logged here by default — cwd-local, inside the project.
# Point elsewhere (e.g. a shared research-vault inbox) with --pending-file.
_PENDING_DEFAULT = _HERE / "fetch_errors.txt"


def _log_failed(entry: dict, reason: str, pending_path: Path, project: str = "") -> None:
    """Append a failed fetch to the pending-downloads file."""
    if not pending_path.parent.exists():
        return  # target directory not present; skip silently
    existing = pending_path.read_text(encoding="utf-8") if pending_path.exists() else ""
    effective_project = entry.get("project", "") or project
    block = "\n---\n"
    block += f"query:     {json.dumps(entry.get('title', entry.get('citekey', '')))}\n"
    if entry.get("url"):
        block += f"url:       {entry['url']}\n"
    if effective_project:
        block += f"project:   {effective_project}\n"
    block += f"status:    failed\n"
    block += f"added:     {date.today()}\n"
    block += f"failure:   {reason}\n"
    pending_path.write_text(existing + block, encoding="utf-8")

# Cheapest / most-canonical sources first; live capture and robots-respecting
# direct fetch last. `direct` only runs if everything archived failed.
DEFAULT_PIPELINE = [
    "wikimedia", "arxiv", "unpaywall", "wayback",
    "memento", "archivetoday", "spn2", "direct",
]
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
    # Pull several recent clean snapshots so we can skip a soft-404/empty capture.
    snaps = wb.recent_snapshots(url, rl, _session(), n=5)
    if not snaps:
        return None
    max_age = max_age_days(url)
    for snap in snaps:
        age = wb.snapshot_age_days(snap["timestamp"])
        # Too old AND we still have live-capture (SPN2) to try → let SPN2 get a
        # fresh copy. If SPN2 is disabled, accept the stale snapshot — better a
        # stale capture than no collection at all.
        if age > max_age and spn2 is not None:
            continue
        text = wb.fetch_snapshot(snap["url"], rl)  # raw (id_) by default
        if text and text.strip():
            date = datetime.strptime(snap["timestamp"][:8], "%Y%m%d").strftime("%Y-%m-%d")
            return text, date, "wayback"
    return None


def _stage_unpaywall(entry, url, rl, spn2, raw_dir):
    """OA-PDF resolution for scholarly DOIs — preferred over archive HTML."""
    doi = (entry.get("doi") or "").strip()
    if not doi:
        return None
    res = unpaywall.fetch_text(doi, rl, _session())
    if res is None:
        return None
    text, pdf_url = res
    return text, "live", "unpaywall"


def _stage_memento(entry, url, rl, spn2, raw_dir):
    """Memento aggregator — best archived copy across many web archives."""
    if not url:
        return None
    res = memento.fetch_text(url, rl, _session())
    if res is None:
        return None
    text, memento_url = res
    return text, "archived", "memento"


def _stage_archivetoday(entry, url, rl, spn2, raw_dir):
    """archive.today — captures many pages the Internet Archive misses."""
    if not url:
        return None
    res = archivetoday.fetch_text(url, rl, _session())
    if res is None:
        return None
    text, snap_url = res
    return text, "archived", "archive.today"


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
    Respects robots.txt unless ignore_robots: true is set on the entry.
    Handles both HTML and PDF responses.
    """
    entry_ignores = str(entry.get("ignore_robots", "")).lower() in ("true", "yes", "1")
    if not entry_ignores and not rl.is_allowed(url):
        raise PermissionError(f"blocked by robots.txt: {url}")
    body, ct = http_get(url, rl)
    if "application/pdf" in ct:
        dest = raw_dir / f"{entry['citekey']}.pdf"
        dest.write_bytes(body)
        return pdf_to_text(body), "live", "direct-pdf"
    return html_to_text(body, content_type=ct), "live", "direct"


_STAGES = {
    "wikimedia":     _stage_wikimedia,
    "arxiv":         _stage_arxiv,
    "unpaywall":     _stage_unpaywall,
    "wayback":       _stage_wayback,
    "memento":       _stage_memento,
    "archivetoday":  _stage_archivetoday,
    "spn2":          _stage_spn2,
    "pdf":           _stage_pdf,
    "direct":        _stage_direct,
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

    # A direct .pdf URL → try the direct-PDF stage first (it's not in the default).
    if url.lower().split("?")[0].endswith(".pdf") and "pdf" not in pipeline:
        pipeline = ["pdf", *pipeline]

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
        body, ct = http_get(f"https://arxiv.org/html/{arxiv_id}", rl)
        text = html_to_text(body, content_type=ct)
        if len(text) > 2000:
            return text
    except Exception:
        pass
    body, ct = http_get(f"https://arxiv.org/abs/{arxiv_id}", rl)
    return html_to_text(body, content_type=ct)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def _enrich_entries(entries: list[dict], rl: RateLimitRegistry) -> None:
    """
    Pre-flight enrichment: fill missing metadata via Citoid and OpenAlex.

    Runs only for entries that lack a url or have a doi but no url.
    Modifies entries in-place; existing values are never overwritten.
    """
    needs_enrich = [
        e for e in entries
        if e.get("citekey") and (not e.get("url") or e.get("doi"))
    ]
    if not needs_enrich:
        return

    print(f"Pre-flight enrichment: {len(needs_enrich)} entries via Citoid + OpenAlex…")
    session = requests.Session()
    for e in needs_enrich:
        citekey = e.get("citekey", "?")
        before_url = e.get("url")
        citoid.enrich(e, rl, session)
        openalex.enrich(e, rl, session)
        if not before_url and e.get("url"):
            print(f"  {citekey}: resolved url → {e['url'][:70]}")


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
    ignore_robots: bool = False,
    enrich: bool = True,
    project: str = "",
    pending_file: Path | None = None,
):
    pending_path = pending_file or _PENDING_DEFAULT
    entries = parse_sources(sources_path)
    if only_citekey:
        entries = [e for e in entries if e.get("citekey") == only_citekey]
        if not entries:
            print(f"citekey not found: {only_citekey}", file=sys.stderr)
            sys.exit(1)

    rl = RateLimitRegistry(overrides=rate_overrides, ignore_robots=ignore_robots)

    if enrich and not dry_run:
        _enrich_entries(entries, rl)

    to_fetch = [
        e for e in entries
        if e.get("citekey")
        and e.get("access", "").lower() not in _SKIP_ACCESS
        and (force or not (cache_dir / f"{e['citekey']}.md").exists())
    ]

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
    cache_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

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
                print("EMPTY — logged as failed")
                _log_failed(e, "empty extraction (all stages returned no text)",
                            pending_path, project=project)
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
            _log_failed(e, str(exc), pending_path, project=project)
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
        "--sources",
        default=str(_SOURCES),
        help="Input sources.txt to read (default: ./sources.txt)",
    )
    p.add_argument("--out", default="", help="Directory for cleaned text output (default: ./cache)")
    p.add_argument("--raw-dir", default="", help="Directory for raw PDF downloads (default: ./raw)")
    p.add_argument("--version", action="store_true", help="Print package/script version and exit")
    p.add_argument("--selfcheck", action="store_true", help="Print resolved script path + version and exit")
    p.add_argument(
        "--pipeline",
        default=",".join(DEFAULT_PIPELINE),
        help=f"Comma-separated stages (default: {','.join(DEFAULT_PIPELINE)})",
    )
    p.add_argument("--no-spn2", action="store_true", help="Disable SavePageNow")
    p.add_argument("--no-enrich", action="store_true", help="Skip Citoid/OpenAlex pre-flight enrichment")
    p.add_argument("--project", default="", help="Project name recorded alongside failed fetches")
    p.add_argument(
        "--pending-file",
        default="",
        help="Where to log failed fetches (default: ./fetch_errors.txt). "
             "Point at a shared inbox, e.g. ../../research-vault/inbox/pending.txt",
    )
    p.add_argument(
        "--ignore-robots",
        action="store_true",
        help="Skip robots.txt checks (use only when site explicitly permits automated access)",
    )
    p.add_argument(
        "--rate-override",
        action="append",
        metavar="DOMAIN=SECS",
        help="Override delay for a domain, e.g. --rate-override arxiv.org=5",
    )
    a = p.parse_args()

    if a.version:
        print(__version__)
        return
    if a.selfcheck:
        print(f"source_collection.fetch {__version__}")
        print(f"script:  {Path(__file__).resolve()}")
        print(f"lib:     {(Path(__file__).resolve().parent / 'lib')}")
        print(f"data:    {_HERE}")
        return

    rate_overrides: dict[str, float] = {}
    for override in a.rate_override or []:
        domain, _, secs = override.partition("=")
        rate_overrides[domain.strip()] = float(secs.strip())

    run(
        sources_path=Path(a.sources),
        cache_dir=Path(a.out) if a.out else _CACHE_DIR,
        raw_dir=Path(a.raw_dir) if a.raw_dir else _RAW_DIR,
        dry_run=a.dry_run,
        only_citekey=a.citekey,
        force=a.force,
        pipeline=[s.strip() for s in a.pipeline.split(",")],
        rate_overrides=rate_overrides or None,
        use_spn2=not a.no_spn2,
        ignore_robots=a.ignore_robots,
        enrich=not a.no_enrich,
        project=a.project,
        pending_file=Path(a.pending_file) if a.pending_file else None,
    )


if __name__ == "__main__":
    main()
