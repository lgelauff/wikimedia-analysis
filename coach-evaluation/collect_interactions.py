"""Collect how the subject has interacted with mentor/coach and community
since the most recent ArbCom unblock.

Gathers, from the public record on nl.wikipedia.org:
  1. the subject's edits outside the mainspace (talk pages, project pages,
     user talk) since the unblock — outgoing interaction;
  2. edits by others on the subject's own talk page — incoming interaction;
  3. when MENTOR_USERS is set in config.py, traffic to/from those users is
     split out as mentor interaction.

Outputs a provenance-stamped JSON snapshot in data/ and regenerates
interactions_since_unblock.md as a chronological digest.
"""

import argparse
import time
from pathlib import Path

import config
from wiki_api import api_get, paginate, save_snapshot, utc_now_iso

TALK_PAGE = f"Overleg gebruiker:{config.SUBJECT_USER}"


def detect_last_unblock() -> str:
    """Return the timestamp of the most recent unblock in the public block log."""
    params = {
        "action": "query",
        "list": "logevents",
        "letype": "block",
        "letitle": f"Gebruiker:{config.SUBJECT_USER}",
        "lelimit": "50",
    }
    for ev in paginate(params, "logevents"):
        if ev.get("action") == "unblock":
            print(f"last unblock: {ev['timestamp']} by {ev.get('user', '?')}")
            return ev["timestamp"]
    raise SystemExit(
        f"No unblock found in the block log for {config.SUBJECT_USER}; "
        "pass --since explicitly."
    )


def subject_edits_since(since: str) -> tuple[list[dict], dict]:
    params = {
        "action": "query",
        "list": "usercontribs",
        "ucuser": config.SUBJECT_USER,
        "uclimit": "500",
        "ucend": since,  # newer→older listing stops at the unblock timestamp
        "ucprop": "ids|title|timestamp|sizediff|comment|flags",
    }
    return list(paginate(params, "usercontribs")), params


def talk_page_revisions_since(since: str) -> tuple[list[dict], dict]:
    params = {
        "action": "query",
        "prop": "revisions",
        "titles": TALK_PAGE,
        "rvlimit": "500",
        "rvend": since,
        "rvprop": "ids|timestamp|user|comment|size",
    }
    revs, cont = [], {}
    while True:
        data = api_get({**params, **cont})
        for page in data.get("query", {}).get("pages", []):
            revs.extend(page.get("revisions", []))
        if "continue" not in data:
            break
        cont = data["continue"]
        time.sleep(config.REQUEST_DELAY)
    return revs, params


def venue(title: str) -> str:
    if title == TALK_PAGE:
        return "eigen overlegpagina"
    if any(title == f"Overleg gebruiker:{m}" for m in config.MENTOR_USERS):
        return "overlegpagina mentor"
    if title.startswith("Overleg gebruiker:"):
        return "overlegpagina andere gebruiker"
    if title.startswith("Overleg:"):
        return "artikeloverleg"
    if title.startswith("Wikipedia:"):
        return "projectnaamruimte"
    if ":" not in title.split("/")[0]:
        return "artikel (hoofdnaamruimte)"
    return "overig"


def diff_url(revid: int) -> str:
    return f"https://{config.WIKI}/w/index.php?diff={revid}"


def write_markdown(since: str, outgoing: list[dict], incoming: list[dict]) -> Path:
    for e in outgoing:
        e["venue"] = venue(e["title"])
    mentor_out = [e for e in outgoing if e["venue"] == "overlegpagina mentor"]
    mentor_in = [r for r in incoming if r.get("user") in config.MENTOR_USERS]
    other_in = [r for r in incoming if r.get("user") not in config.MENTOR_USERS
                and r.get("user") != config.SUBJECT_USER]

    lines = [
        "# Interacties sinds deblokkade — 10Guillot (Gio)",
        "",
        f"Gegenereerd door `collect_interactions.py` op {utc_now_iso()}.",
        f"Periode: sinds {since} (laatste deblokkade volgens het blokkeerlogboek).",
        "",
        "## Samenvatting",
        "",
        f"- Bewerkingen door Gio sinds deblokkade: **{len(outgoing)}**",
    ]
    by_venue: dict[str, int] = {}
    for e in outgoing:
        by_venue[e["venue"]] = by_venue.get(e["venue"], 0) + 1
    for v, n in sorted(by_venue.items(), key=lambda kv: -kv[1]):
        lines.append(f"  - {v}: {n}")
    lines += [
        f"- Berichten van anderen op zijn overlegpagina: **{len(other_in)}**",
    ]
    if config.MENTOR_USERS:
        lines += [
            f"- Mentorverkeer ({', '.join(config.MENTOR_USERS)}): "
            f"**{len(mentor_out)}** uitgaand / **{len(mentor_in)}** inkomend",
        ]
    else:
        lines += [
            "- Mentorverkeer: *`MENTOR_USERS` is nog niet ingevuld in `config.py`;*",
            "  *vul de gebruikersnaam van de coach/mentor in en draai opnieuw.*",
        ]

    def table(rows: list[str]) -> list[str]:
        return [
            "| Tijdstip | Wie | Waar | Samenvatting | Diff |",
            "|---|---|---|---|---|",
            *rows,
        ]

    def out_row(e: dict) -> str:
        comment = (e.get("comment") or "").replace("|", "\\|")[:120]
        return (
            f"| {e['timestamp']} | Gio | {e['title']} ({e['venue']}) "
            f"| {comment} | [diff]({diff_url(e['revid'])}) |"
        )

    def in_row(r: dict) -> str:
        comment = (r.get("comment") or "").replace("|", "\\|")[:120]
        return (
            f"| {r['timestamp']} | {r.get('user', '?')} | {TALK_PAGE} "
            f"| {comment} | [diff]({diff_url(r['revid'])}) |"
        )

    if config.MENTOR_USERS:
        mentor_rows = sorted(
            [out_row(e) for e in mentor_out] + [in_row(r) for r in mentor_in]
        )
        lines += ["", "## Interactie met mentor/coach", ""] + table(mentor_rows)

    community_out = [e for e in outgoing if e["venue"] not in
                     ("artikel (hoofdnaamruimte)", "overlegpagina mentor")]
    lines += ["", "## Interactie met de gemeenschap (uitgaand)", ""]
    lines += table([out_row(e) for e in sorted(community_out, key=lambda e: e["timestamp"])])
    lines += ["", "## Berichten op zijn overlegpagina (inkomend)", ""]
    lines += table([in_row(r) for r in sorted(other_in, key=lambda r: r["timestamp"])])
    lines += [
        "",
        "## Inhoudelijk werk",
        "",
        f"Bewerkingen in de hoofdnaamruimte sinds deblokkade: "
        f"**{by_venue.get('artikel (hoofdnaamruimte)', 0)}** "
        "(zie `articles_under_review.md` voor de artikelbeoordeling).",
        "",
    ]

    path = Path(__file__).parent / config.INTERACTIONS_MD
    path.write_text("\n".join(lines))
    return path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", help="ISO timestamp override for the unblock moment")
    args = ap.parse_args()

    since = args.since or detect_last_unblock()
    outgoing, p1 = subject_edits_since(since)
    incoming, p2 = talk_page_revisions_since(since)

    snapshot = save_snapshot(
        "interactions",
        {
            "subject": config.SUBJECT_USER,
            "since": since,
            "outgoing": outgoing,
            "talk_page_revisions": incoming,
        },
        [p1, p2],
    )
    md = write_markdown(since, outgoing, incoming)
    print(f"{len(outgoing)} edits by Gio, {len(incoming)} talk-page revisions since {since}")
    print(f"snapshot: {snapshot}\nreport: {md}")


if __name__ == "__main__":
    main()
