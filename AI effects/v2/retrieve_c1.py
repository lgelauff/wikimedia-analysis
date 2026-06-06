"""
retrieve_c1.py — Full-text retrieval for Cycle 1 triage output.

Selects the top-N papers from the combined triage by priority tier, then
tries to obtain open-access PDFs via:
  1. arXiv direct download (for arxiv DOIs / arXiv URLs)
  2. Unpaywall API (email from environment or hardcoded)
  3. Semantic Scholar open-access link

PDFs are saved to research-vault/inbox/{citekey}.pdf; failures are logged
to fetch_errors_c1.log and added to needs_download.md.

Usage:
  uv run retrieve_c1.py                        # top 200, high+medium priority
  uv run retrieve_c1.py --top 100              # top 100 only
  uv run retrieve_c1.py --input triage_c1_combined.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

_HERE       = Path(__file__).parent
_VAULT      = Path(__file__).parent.parent.parent.parent / "research-vault"
_INBOX      = _VAULT / "inbox"
_ERRORS_LOG = _HERE / "fetch_errors_c1.log"
_NEEDS_DL   = _HERE / "needs_download.md"

UNPAYWALL_EMAIL = "lodewijk@stanford.edu"
USER_AGENT = "WikimediaAnalysis/1.0 (personal research project; https://github.com/lgelauff/wikimedia-analysis)"

PRIORITY_TIER = {
    ("relevant",  "high"):   1,
    ("relevant",  "medium"): 2,
    ("relevant",  "low"):    3,
    ("marginal",  "high"):   4,
    ("marginal",  "medium"): 5,
    ("marginal",  "low"):    6,
    ("irrelevant","high"):   7,
    ("irrelevant","medium"): 8,
    ("irrelevant","low"):    9,
}


def log_error(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with _ERRORS_LOG.open("a") as f:
        f.write(f"{ts} | retrieve | {msg}\n")


def needs_download(title: str, url: str | None, doi: str | None) -> None:
    line = f"- [ ] {title}"
    if doi:
        line += f"  DOI:{doi}"
    if url:
        line += f"  URL:{url}"
    with _NEEDS_DL.open("a") as f:
        f.write(line + "\n")


def make_citekey(paper: dict) -> str:
    authors = paper.get("authors") or []
    first_author = (authors[0] if authors else "unknown").split()[-1].lower()
    first_author = re.sub(r"[^a-z0-9]", "", first_author)
    year = str(paper.get("year") or "0000")
    words = re.sub(r"[^a-z0-9 ]", "", (paper.get("title") or "").lower()).split()
    first_word = next((w for w in words if len(w) > 3 and w not in
                       {"with","from","that","this","they","been","have","were","will","into",
                        "about","after","using","based","large","model","models","study","paper",
                        "effect","effects","impact","impacts","analysis","generative"}), words[0] if words else "x")
    return f"{first_author}{year}{first_word}"


def arxiv_id_from_paper(paper: dict) -> str | None:
    doi = (paper.get("doi") or "").lower()
    url = (paper.get("url") or "").lower()
    m = re.search(r"arxiv\.org/abs/([0-9]+\.[0-9]+)", url)
    if m:
        return m.group(1)
    m = re.search(r"10\.48550/arxiv\.([0-9]+\.[0-9]+)", doi)
    if m:
        return m.group(1)
    m = re.search(r"arxiv[:/]([0-9]{4}\.[0-9]+)", doi + url)
    if m:
        return m.group(1)
    return None


def try_arxiv(client: httpx.Client, arxiv_id: str) -> bytes | None:
    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
    try:
        r = client.get(pdf_url, follow_redirects=True, timeout=30)
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("application/pdf"):
            return r.content
        log_error(f"arXiv {arxiv_id} — HTTP {r.status_code}")
    except Exception as exc:
        log_error(f"arXiv {arxiv_id} — {type(exc).__name__}: {exc}")
    return None


def try_unpaywall(client: httpx.Client, doi: str) -> bytes | None:
    api_url = f"https://api.unpaywall.org/v2/{doi}?email={UNPAYWALL_EMAIL}"
    try:
        r = client.get(api_url, timeout=15)
        if r.status_code != 200:
            log_error(f"Unpaywall {doi} — HTTP {r.status_code}")
            return None
        data = r.json()
        best = data.get("best_oa_location") or {}
        pdf_url = best.get("url_for_pdf") or best.get("url")
        if not pdf_url:
            return None
        time.sleep(0.5)
        r2 = client.get(pdf_url, follow_redirects=True, timeout=30)
        if r2.status_code == 200 and "pdf" in r2.headers.get("content-type", ""):
            return r2.content
        log_error(f"Unpaywall PDF fetch {doi} — HTTP {r2.status_code} from {pdf_url[:80]}")
    except Exception as exc:
        log_error(f"Unpaywall {doi} — {type(exc).__name__}: {exc}")
    return None


def try_semantic_scholar(client: httpx.Client, doi: str) -> bytes | None:
    try:
        api_url = f"https://api.semanticscholar.org/graph/v1/paper/{doi}?fields=openAccessPdf"
        r = client.get(api_url, timeout=15)
        if r.status_code != 200:
            return None
        data = r.json()
        pdf_info = data.get("openAccessPdf") or {}
        pdf_url = pdf_info.get("url")
        if not pdf_url:
            return None
        time.sleep(0.5)
        r2 = client.get(pdf_url, follow_redirects=True, timeout=30)
        if r2.status_code == 200 and "pdf" in r2.headers.get("content-type", ""):
            return r2.content
        log_error(f"S2 PDF fetch {doi} — HTTP {r2.status_code} from {pdf_url[:80]}")
    except Exception as exc:
        log_error(f"S2 {doi} — {type(exc).__name__}: {exc}")
    return None


def retrieve_paper(client: httpx.Client, paper: dict) -> bool:
    """Try to download PDF. Returns True if successful."""
    citekey  = make_citekey(paper)
    dest     = _INBOX / f"{citekey}.pdf"

    if dest.exists():
        print(f"  already in inbox: {citekey}")
        return True

    # Also check if already in vault index
    vault_index = _VAULT / "index.json"
    if vault_index.exists():
        idx = json.loads(vault_index.read_text(encoding="utf-8"))
        doi = (paper.get("doi") or "").lower()
        title_lower = (paper.get("title") or "").lower()
        for entry in idx:
            if doi and (entry.get("DOI") or "").lower() == doi:
                print(f"  already in vault (DOI match): {citekey}")
                return True
            if title_lower and (entry.get("title") or "").lower() == title_lower:
                print(f"  already in vault (title match): {citekey}")
                return True

    doi      = paper.get("doi") or ""
    pdf_data = None

    arxiv_id = arxiv_id_from_paper(paper)
    if arxiv_id:
        pdf_data = try_arxiv(client, arxiv_id)
        if pdf_data:
            print(f"  ✓ arXiv", end=" ")

    if not pdf_data and doi:
        time.sleep(1)
        pdf_data = try_unpaywall(client, doi)
        if pdf_data:
            print(f"  ✓ Unpaywall", end=" ")

    if not pdf_data and doi:
        time.sleep(1)
        pdf_data = try_semantic_scholar(client, doi)
        if pdf_data:
            print(f"  ✓ S2", end=" ")

    if pdf_data:
        _INBOX.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(pdf_data)
        return True

    needs_download(paper.get("title", ""), paper.get("url"), doi or None)
    return False


def load_combined_triage(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def select_top(papers: list[dict], n: int, min_relevance: set[str], max_priority: set[str]) -> list[dict]:
    eligible = [
        p for p in papers
        if p.get("relevance") in min_relevance
        and p.get("priority") in max_priority
    ]
    eligible.sort(key=lambda p: (
        PRIORITY_TIER.get((p.get("relevance","irrelevant"), p.get("priority","low")), 99),
        (p.get("title") or "").lower()
    ))
    return eligible[:n]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="triage_c1_combined.json")
    parser.add_argument("--top", type=int, default=200)
    parser.add_argument("--relevance", nargs="+", default=["relevant", "marginal"],
                        help="Which relevance tiers to include")
    parser.add_argument("--priority", nargs="+", default=["high", "medium"],
                        help="Which priority tiers to include")
    args = parser.parse_args()

    triage_path = _HERE / args.input
    if not triage_path.exists():
        print(f"ERROR: {triage_path} not found. Run consolidate first.", file=sys.stderr)
        sys.exit(1)

    all_papers = load_combined_triage(triage_path)
    to_retrieve = select_top(all_papers, args.top, set(args.relevance), set(args.priority))

    print(f"Total triaged: {len(all_papers)}")
    print(f"Selected for retrieval: {len(to_retrieve)} (top {args.top}, relevance={args.relevance}, priority={args.priority})")
    print(f"Inbox: {_INBOX}")
    print()

    ok = 0
    fail = 0
    with httpx.Client(headers={"User-Agent": USER_AGENT}) as client:
        for i, paper in enumerate(to_retrieve, 1):
            title = (paper.get("title") or "")[:65]
            rel   = paper.get("relevance", "?")
            pri   = paper.get("priority", "?")
            print(f"[{i}/{len(to_retrieve)}] [{rel}/{pri}] {title}…", end=" ", flush=True)
            success = retrieve_paper(client, paper)
            if success:
                ok += 1
                print("OK")
            else:
                fail += 1
                print("FAILED → needs_download.md")
            time.sleep(0.3)

    print(f"\n{'─'*60}")
    print(f"Retrieved:  {ok}")
    print(f"Failed:     {fail} → {_NEEDS_DL.name}")
    print(f"Errors log: {_ERRORS_LOG.name}")
    print(f"\nNext step: uv run ingest.py --inbox  (in research-vault/)")


if __name__ == "__main__":
    main()
