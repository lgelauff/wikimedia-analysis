"""Per-article evaluation pass for the coach evaluation.

For every article in the latest articles snapshot (run collect_articles.py
first), this script gathers the raw material for the four coach-prompt
questions:

  1. what Gio added since the ArbCom ruling  -> his diffs since --since
  2. whether improvements included sources   -> ref/citation counts before vs now
  3. policy alignment                        -> material for human judgement
  4. what people complained about            -> article talk activity since --since

Writes one Markdown sheet per article to evaluation/ plus an INDEX.md with
empty verdict columns. Judgement stays human; this collects evidence.
"""

import argparse
import json
import re
import time
from pathlib import Path

import config
from collect_interactions import detect_last_unblock
from wiki_api import api_get, save_snapshot, utc_now_iso

REF_RE = re.compile(r"<ref[ >]", re.IGNORECASE)
CITE_RE = re.compile(r"\{\{\s*(citeer|cite)", re.IGNORECASE)


def latest_articles_snapshot() -> dict:
    data_dir = Path(__file__).parent / config.DATA_DIR
    snaps = sorted(data_dir.glob("articles_*.json"))
    if not snaps:
        raise SystemExit("No articles snapshot found — run collect_articles.py first.")
    return json.loads(snaps[-1].read_text())


def revisions(title: str, since: str, user: str | None = None) -> list[dict]:
    """All revisions of `title` from `since` to now (oldest first)."""
    params = {
        "action": "query",
        "prop": "revisions",
        "titles": title,
        "rvlimit": "500",
        "rvdir": "newer",
        "rvstart": since,
        "rvprop": "ids|timestamp|user|comment|size",
    }
    if user:
        params["rvuser"] = user
    revs, cont = [], {}
    while True:
        data = api_get({**params, **cont})
        for page in data.get("query", {}).get("pages", []):
            revs.extend(page.get("revisions", []))
        if "continue" not in data:
            return revs
        cont = data["continue"]
        time.sleep(config.REQUEST_DELAY)


def wikitext_of(revid: int | None, title: str | None = None) -> str:
    """Wikitext of a specific revision, or of the current page when revid is None."""
    params = {"action": "parse", "prop": "wikitext"}
    if revid:
        params["oldid"] = revid
    else:
        params["page"] = title
    try:
        return api_get(params)["parse"]["wikitext"]
    except (RuntimeError, KeyError):
        return ""


def source_counts(text: str) -> dict:
    return {"refs": len(REF_RE.findall(text)), "cite_templates": len(CITE_RE.findall(text))}


def diff_url(revid: int) -> str:
    return f"https://{config.WIKI}/w/index.php?diff={revid}"


def evaluate_article(page: dict, since: str) -> dict:
    title = page["title"]
    gio_revs = revisions(title, since, user=config.SUBJECT_USER)

    baseline_revid = gio_revs[0].get("parentid") if gio_revs else None
    before = source_counts(wikitext_of(baseline_revid)) if baseline_revid else None
    now = source_counts(wikitext_of(None, title=title))

    talk = [
        r for r in revisions(f"Overleg:{title}", since)
        if r.get("user") != config.SUBJECT_USER
    ]
    time.sleep(config.REQUEST_DELAY)
    return {
        "title": title,
        "role": page.get("role", ""),
        "status": page.get("status", ""),
        "edits_since_ruling": gio_revs,
        "sources_before": before,
        "sources_now": now,
        "talk_since_ruling": talk,
    }


def sheet_name(title: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", title).strip("_") + ".md"


def write_sheet(ev: dict, since: str, out_dir: Path) -> None:
    lines = [
        f"# {ev['title']}",
        "",
        f"Rol: {ev['role']} · status: {ev['status']} · periode: sinds {since}",
        f"Artikel: https://{config.WIKI}/wiki/{ev['title'].replace(' ', '_')}",
        "",
        "## 1. Bewerkingen door Gio sinds de uitspraak",
        "",
    ]
    if ev["edits_since_ruling"]:
        lines += ["| Tijdstip | Samenvatting | Bytes | Diff |", "|---|---|---|---|"]
        for r in ev["edits_since_ruling"]:
            comment = (r.get("comment") or "").replace("|", "\\|")[:120]
            lines.append(
                f"| {r['timestamp']} | {comment} | {r.get('size', '?')} "
                f"| [diff]({diff_url(r['revid'])}) |"
            )
    else:
        lines.append("*Geen bewerkingen sinds de uitspraak.*")

    lines += ["", "## 2. Bronnen (voor eerste bewerking sinds uitspraak vs. nu)", ""]
    if ev["sources_before"] is not None:
        b, n = ev["sources_before"], ev["sources_now"]
        lines += [
            "| | `<ref>` | citatiesjablonen |",
            "|---|---|---|",
            f"| voor | {b['refs']} | {b['cite_templates']} |",
            f"| nu | {n['refs']} | {n['cite_templates']} |",
            f"| verschil | {n['refs'] - b['refs']:+} | {n['cite_templates'] - b['cite_templates']:+} |",
        ]
    else:
        n = ev["sources_now"]
        lines.append(
            f"*Geen bewerkingen sinds uitspraak; huidige stand: {n['refs']} refs, "
            f"{n['cite_templates']} citatiesjablonen.*"
        )

    lines += ["", "## 3. Overlegactiviteit door anderen sinds de uitspraak", ""]
    if ev["talk_since_ruling"]:
        lines += ["| Tijdstip | Wie | Samenvatting | Diff |", "|---|---|---|---|"]
        for r in ev["talk_since_ruling"]:
            comment = (r.get("comment") or "").replace("|", "\\|")[:120]
            lines.append(
                f"| {r['timestamp']} | {r.get('user', '?')} | {comment} "
                f"| [diff]({diff_url(r['revid'])}) |"
            )
    else:
        lines.append("*Geen overlegactiviteit van anderen sinds de uitspraak.*")

    lines += [
        "",
        "## 4. Beoordeling (handmatig)",
        "",
        "- Deugdelijkheid toegevoegde bronnen (onafhankelijk / gepubliceerd / dekkend):",
        "- Beleidsconformiteit (NPOV / geen OO / VER):",
        "- Oordeel: `opgelost` / `verbeterd, nog niet opgelost` / `onveranderd` / `verslechterd`",
        "- Motivering:",
        "",
    ]
    (out_dir / sheet_name(ev["title"])).write_text("\n".join(lines))


def write_index(evaluations: list[dict], since: str, out_dir: Path) -> None:
    lines = [
        "# Evaluatie-index",
        "",
        f"Gegenereerd op {utc_now_iso()}; periode sinds {since}.",
        "Volgorde: minst bewerkte artikelen eerst (daar is het minst gebeurd).",
        "",
        "| Artikel | Rol | Bewerkingen sinds uitspraak | Refs +/- | Overleg door anderen | Oordeel |",
        "|---|---|---|---|---|---|",
    ]
    def refdelta(ev: dict) -> str:
        if ev["sources_before"] is None:
            return "n.v.t."
        return f"{ev['sources_now']['refs'] - ev['sources_before']['refs']:+}"

    for ev in sorted(evaluations, key=lambda e: len(e["edits_since_ruling"])):
        lines.append(
            f"| [{ev['title']}]({sheet_name(ev['title'])}) | {ev['role']} "
            f"| {len(ev['edits_since_ruling'])} | {refdelta(ev)} "
            f"| {len(ev['talk_since_ruling'])} |  |"
        )
    (out_dir / "INDEX.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", help="ISO timestamp of the ArbCom ruling/unblock")
    args = ap.parse_args()
    since = args.since or detect_last_unblock()

    snapshot = latest_articles_snapshot()
    out_dir = Path(__file__).parent / "evaluation"
    out_dir.mkdir(exist_ok=True)

    evaluations = []
    for page in snapshot["pages"]:
        ev = evaluate_article(page, since)
        evaluations.append(ev)
        write_sheet(ev, since, out_dir)
        print(f"{ev['title']}: {len(ev['edits_since_ruling'])} edits, "
              f"{len(ev['talk_since_ruling'])} talk revisions")

    write_index(evaluations, since, out_dir)
    save_snapshot("evaluation", {"since": since, "articles": evaluations},
                  [{"note": "see per-call params in evaluate_articles.py"}])
    print(f"{len(evaluations)} sheets in {out_dir}/, index at {out_dir}/INDEX.md")


if __name__ == "__main__":
    main()
