"""Collect mainspace articles started or significantly expanded by the subject.

Produces a provenance-stamped JSON snapshot in data/ and regenerates
articles_under_review.md, the working list for the coach evaluation. The
assessment columns in the Markdown are left blank on purpose — filling them
is the human part of the evaluation.
"""

import time
from pathlib import Path

import config
from wiki_api import api_get, paginate, save_snapshot, utc_now_iso


def collect_contribs() -> list[dict]:
    params = {
        "action": "query",
        "list": "usercontribs",
        "ucuser": config.SUBJECT_USER,
        "ucnamespace": "0",
        "uclimit": "500",
        "ucprop": "ids|title|timestamp|sizediff|flags|comment",
    }
    return list(paginate(params, "usercontribs")), params


def aggregate(contribs: list[dict]) -> dict[str, dict]:
    pages: dict[str, dict] = {}
    for c in contribs:
        p = pages.setdefault(
            c["title"],
            {
                "title": c["title"],
                "created_by_subject": False,
                "n_edits": 0,
                "net_bytes": 0,
                "max_single_add": 0,
                "first_edit": c["timestamp"],
                "last_edit": c["timestamp"],
            },
        )
        p["n_edits"] += 1
        diff = c.get("sizediff", 0) or 0
        p["net_bytes"] += diff
        p["max_single_add"] = max(p["max_single_add"], diff)
        p["first_edit"] = min(p["first_edit"], c["timestamp"])
        p["last_edit"] = max(p["last_edit"], c["timestamp"])
        if "new" in c or c.get("new"):
            p["created_by_subject"] = True
    return pages


def classify(pages: dict[str, dict]) -> list[dict]:
    selected = []
    for p in pages.values():
        if p["created_by_subject"]:
            p["role"] = "gestart"
        elif (
            p["max_single_add"] >= config.SINGLE_EDIT_BYTES
            or p["net_bytes"] >= config.CUMULATIVE_BYTES
        ):
            p["role"] = "significant uitgebreid"
        else:
            continue
        selected.append(p)
    return sorted(selected, key=lambda p: (p["role"] != "gestart", p["first_edit"]))


def add_page_status(selected: list[dict]) -> None:
    titles = [p["title"] for p in selected]
    for i in range(0, len(titles), 50):
        batch = titles[i : i + 50]
        data = api_get(
            {"action": "query", "prop": "info", "titles": "|".join(batch)}
        )
        for info in data.get("query", {}).get("pages", []):
            status = "bestaat"
            if info.get("missing"):
                status = "bestaat niet meer (verwijderd of hernoemd)"
            elif info.get("redirect"):
                status = "redirect"
            for p in selected:
                if p["title"] == info.get("title"):
                    p["status"] = status
        time.sleep(config.REQUEST_DELAY)
    for p in selected:
        p.setdefault("status", "onbekend")


def write_markdown(selected: list[dict], collected_utc: str) -> Path:
    def link(title: str) -> str:
        return f"[{title}](https://{config.WIKI}/wiki/{title.replace(' ', '_')})"

    started = [p for p in selected if p["role"] == "gestart"]
    expanded = [p for p in selected if p["role"] != "gestart"]

    lines = [
        "# Artikelen onder beoordeling — 10Guillot (Gio)",
        "",
        f"Gegenereerd door `collect_articles.py` op {collected_utc} uit de openbare",
        f"bijdragenlijst op {config.WIKI} (hoofdnaamruimte). De uitspraak in",
        "*Deblokkade 10Guillot (3)* stelt dat hij geen nieuwe artikelen mag aanmaken",
        '"totdat de problemen met al zijn oude, door hem gestarte artikelen zijn',
        'opgelost". De oorspronkelijke klacht betrof neutraliteit (NPOV), origineel',
        "onderzoek (OO) en verifieerbaarheid (VER).",
        "",
        "- **Door hem gestarte artikelen** vallen per definitie onder de voorwaarde.",
        "- **Significant uitgebreide artikelen** (één bewerking ≥ "
        f"{config.SINGLE_EDIT_BYTES:+} bytes of netto ≥ {config.CUMULATIVE_BYTES:+} bytes)",
        "  staan apart gelijst; of ze onder de klacht vallen is een beoordeling, geen",
        "  automatische conclusie.",
        "- Verwijderde artikelen verschijnen niet in de openbare bijdragenlijst;",
        "  een moderator-controle van verwijderde bijdragen is nodig voor volledigheid.",
        "",
        "De beoordelingskolommen worden handmatig ingevuld.",
        "",
    ]

    header = (
        "| Artikel | Eerste bewerking | Laatste bewerking | Netto bytes | Status | "
        "Valt onder klacht? | Problemen opgelost? | Notities |\n"
        "|---|---|---|---|---|---|---|---|"
    )

    def rows(pages: list[dict]) -> list[str]:
        return [
            f"| {link(p['title'])} | {p['first_edit'][:10]} | {p['last_edit'][:10]} "
            f"| {p['net_bytes']:+} | {p['status']} |  |  |  |"
            for p in pages
        ]

    lines += [f"## Door Gio gestarte artikelen ({len(started)})", "", header, *rows(started), ""]
    lines += [
        f"## Significant door Gio uitgebreide artikelen ({len(expanded)})",
        "",
        header,
        *rows(expanded),
        "",
    ]

    path = Path(__file__).parent / config.ARTICLES_MD
    path.write_text("\n".join(lines))
    return path


def main() -> None:
    contribs, params = collect_contribs()
    pages = aggregate(contribs)
    selected = classify(pages)
    add_page_status(selected)
    collected = utc_now_iso()
    snapshot = save_snapshot(
        "articles",
        {"subject": config.SUBJECT_USER, "n_contribs": len(contribs), "pages": selected},
        [params],
    )
    md = write_markdown(selected, collected)
    print(f"{len(contribs)} mainspace edits -> {len(selected)} pages under review")
    print(f"snapshot: {snapshot}\nworking list: {md}")


if __name__ == "__main__":
    main()
