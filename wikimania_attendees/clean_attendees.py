"""
Post-process collected attendance figures for every Wikimania edition.

Step 1 — Auto-exclude:
    Mark figures as excluded=True (with a reason) when they are clearly NOT
    conference headcounts: money amounts, presentation counts, Wikipedia-wide
    stats, date strings, web traffic, etc.
    Figures are NOT deleted — they stay in the JSON with excluded=True so the
    exclusion decision is auditable and reversible.

Step 2 — Flag for review:
    Set needs_review=True on figures that are ambiguous: geographic counts
    (countries), scholarship/volunteer counts, figures that couldn't be parsed
    to a number, suspiciously small figures, etc.

Step 3 — Regenerate combined files:
    Rewrites attendance_all.json and attendance_report.md, skipping excluded
    figures.  Flagged figures are shown with a ❓ marker.

Run:
    uv run clean_attendees.py           # all editions
    uv run clean_attendees.py 2006      # specific year(s)
"""

import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths — reuse write_combined / write_markdown from the fetcher
# ---------------------------------------------------------------------------
ATTENDEES_DIR = Path(__file__).parent
EDITIONS_DIR  = ATTENDEES_DIR / "editions"
sys.path.insert(0, str(ATTENDEES_DIR.parent / "wikimania_deadlines"))

from fetch_attendees import write_combined  # noqa: E402 (reuse combined-output logic)

# ---------------------------------------------------------------------------
# Rule sets
# ---------------------------------------------------------------------------

# Substrings that, if found anywhere in definition_as_reported (lowercased),
# trigger auto-exclusion.  Checked in order; first match wins.
EXCLUDE_DEFINITION_RULES: list[tuple[str, str]] = [
    # Money / prizes
    ("euro",            "money amount, not a headcount"),
    ("dollar",          "money amount, not a headcount"),
    (" usd",            "money amount, not a headcount"),
    ("prize",           "prize/award, not a headcount"),
    ("budget",          "budget figure, not a headcount"),
    ("amount in",       "money amount, not a headcount"),
    # Dates / deadlines
    ("deadline",        "submission deadline, not a headcount"),
    ("registration deadline", "deadline, not a headcount"),
    # Presentation / programme counts
    ("presentations",   "programme item count, not a headcount"),
    ("workshops",       "programme item count, not a headcount"),
    ("lightning",       "programme item count, not a headcount"),
    ("posters",         "programme item count, not a headcount"),
    ("accepted presentations", "programme item count, not a headcount"),
    ("submissions",     "submission count, not a headcount"),
    # Wikipedia / Wikimedia-wide statistics
    ("active editors",  "Wikipedia-wide stat, not conference attendance"),
    ("active registered", "Wikipedia-wide stat, not conference attendance"),
    ("contributors to meta", "Wikipedia-wide stat, not conference attendance"),
    ("wikimedia foundation wikis", "Wikipedia-wide stat, not conference attendance"),
    ("machine-readable","unrelated Wikipedia stat"),
    ("french population","unrelated demographic stat"),
    ("french voters",   "unrelated demographic stat"),
    ("using it daily",  "unrelated usage stat"),
    ("internet users",  "internet-wide stat, not conference attendance"),
    ("reach in ",       "internet reach stat, not conference attendance"),
    ("users accessed",  "internet-wide stat, not conference attendance"),
    # Web / media traffic
    ("hits",            "web traffic metric, not a headcount"),
    ("unique visitors", "web traffic metric (unless conference livestream)"),
    ("total unique visitors", "web traffic metric, not a headcount"),
    ("page views",      "web traffic metric, not a headcount"),
    # Email list / community stats
    ("subscribed to this list", "mailing-list subscriber count, not conference attendance"),
    ("people subscribed", "mailing-list subscriber count, not conference attendance"),
    # Conference ordinals / edition labels
    ("year of wikimania", "ordinal edition label, not a headcount"),
    ("wikimania conference", "ordinal edition label, not a headcount"),
    ("annual wikimedia conference", "ordinal edition label, not a headcount"),
    ("international wikimedia conference", "ordinal edition label, not a headcount"),
    # Visa / individual-person anecdotes
    ("couldn't get visas", "anecdote about individuals, not a headcount"),
    ("was explicitly rejected", "anecdote about individuals, not a headcount"),
    # Seat capacity (not actual attendance)
    ("seat auditorium", "venue capacity, not actual attendance"),
    ("capacity",        "venue capacity, not actual attendance"),
    # Wikipedia language/project counts
    (" wikis",          "count of wikis, not a headcount"),
    ("wikinews projects", "count of projects, not a headcount"),
    # Clearly non-attendance definitions
    (" projects",       "count of projects, not a headcount"),
    # Website traffic to non-conference sites
    ("wikigadugi",      "website traffic to personal/unrelated site"),
]

# figure_raw patterns that are obviously not headcounts
EXCLUDE_RAW_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r'^\d{1,2}%$'),              "percentage, not a headcount"),
    (re.compile(r'^\d+\.\d+%'),              "percentage, not a headcount"),
    (re.compile(r'^(January|February|March|April|May|June|July|August|'
                r'September|October|November|December)\s+\d', re.I),
                                             "date string, not a headcount"),
    (re.compile(r'^\d{1,2}\s+(January|February|March|April|May|June|'
                r'July|August|September|October|November|December)', re.I),
                                             "date string, not a headcount"),
    (re.compile(r'^a quarter', re.I),        "fraction, not a specific count"),
    (re.compile(r'^a third', re.I),          "fraction, not a specific count"),
    (re.compile(r'^half\b', re.I),           "fraction, not a specific count"),
    (re.compile(r'^\d{1,3}[Mm]$'),           "millions figure (web traffic?)"),
    (re.compile(r'^\d+,\d{3},\d{3}'),        "figure in millions, likely not conference headcount"),
    # Question strings extracted as figure_raw
    (re.compile(r'\?'),                      "looks like a question, not a figure"),
]

# Definitions that are valid conference stats but NOT attendance headcounts
# → keep, but flag needs_review so they appear with ❓ in the report
FLAG_DEFINITION_RULES: list[tuple[str, str]] = [
    ("countries",       "geographic count, not a person headcount"),
    ("continents",      "geographic count, not a person headcount"),
    ("scholarship",     "scholarship count, not total attendance"),
    ("scholars",        "scholarship count, not total attendance"),
    ("volunteer",       "volunteer count, not total attendance"),
    ("journalists",     "press/media count, not total attendance"),
    ("press",           "press count, not total attendance"),
    ("speakers",        "speaker count, not total attendance"),
    ("applications",    "application count, not actual attendance"),
    ("languages",       "language count, not a person headcount"),
    ("global unique visitors", "may be web traffic rather than in-person count"),
]

# Flag any figure that could not be parsed to a number (figure_numeric is None)
FLAG_IF_NO_NUMERIC = True

# Flag figures < this threshold from mailing-list sources (very small numbers
# from emails are often about something else entirely)
FLAG_IF_NUMERIC_BELOW = 20


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def classify_figure(f: dict) -> tuple[bool, str | None, bool, str | None]:
    """
    Returns (excluded, exclude_reason, needs_review, review_reason).
    """
    defn_lower    = (f.get("definition_as_reported") or "").lower()
    raw           = (f.get("figure_raw") or "").strip()
    numeric       = f.get("figure_numeric")
    context_lower = (f.get("context") or "").lower()

    # --- Auto-exclude checks ---
    for substring, reason in EXCLUDE_DEFINITION_RULES:
        if substring in defn_lower:
            return True, reason, False, None

    for pattern, reason in EXCLUDE_RAW_PATTERNS:
        if pattern.search(raw):
            return True, reason, False, None

    # Context-based exclusions: figures that appear only in hypothetical,
    # opinion, or unrelated context
    EXCLUDE_CONTEXT_FRAGMENTS = [
        ("opening the conference to",  "hypothetical/opinion about conference size, not reported attendance"),
        ("makes it, in my opinion",    "hypothetical/opinion statement, not reported attendance"),
        ("visitors and",               "website traffic, not conference attendance"),  # "1720 visitors and 50,000+ hits"
    ]
    for fragment, reason in EXCLUDE_CONTEXT_FRAGMENTS:
        if fragment in context_lower:
            return True, reason, False, None

    # Already verified → never flag / exclude
    if f.get("verified"):
        return False, None, False, None

    # --- Flag checks ---
    for substring, reason in FLAG_DEFINITION_RULES:
        if substring in defn_lower:
            return False, None, True, reason

    if FLAG_IF_NO_NUMERIC and numeric is None:
        return False, None, True, "figure could not be parsed to a number"

    if FLAG_IF_NUMERIC_BELOW and numeric is not None and numeric < FLAG_IF_NUMERIC_BELOW:
        return False, None, True, f"suspiciously small figure ({numeric}) — may not be a conference headcount"

    # Flag mailing-list figures that are implausibly high for the era.
    # Pre-2012 conferences never exceeded ~1,400; anything much higher in an email
    # is probably about something else (Wikipedia traffic, list subscribers, etc.)
    year = f.get("_year")  # set by clean_edition before calling classify_figure
    if (year and year <= 2011
            and numeric is not None and numeric > 2000
            and f.get("source_type") == "mailing_list"):
        return False, None, True, (
            f"figure ({numeric}) seems implausibly high for a pre-2012 conference "
            f"— may refer to something other than conference attendance"
        )

    return False, None, False, None


def clean_edition(year: int) -> dict:
    """
    Load the edition JSON, apply classification, save back, and return a
    summary dict with counts.
    """
    path = EDITIONS_DIR / f"wikimania_{year}.json"
    if not path.exists():
        return {"year": year, "error": "file not found"}

    data = json.loads(path.read_text())
    figures = data.get("reported_figures", [])
    # Stamp year on each figure so classify_figure can use era-based rules
    for f in figures:
        f["_year"] = year

    n_excluded = n_flagged = n_cleared = 0

    for f in figures:
        excluded, ex_reason, needs_review, rv_reason = classify_figure(f)

        if excluded:
            f["excluded"]        = True
            f["excluded_reason"] = ex_reason
            f["needs_review"]    = False
            f.pop("review_reason", None)
            n_excluded += 1
        else:
            f.pop("excluded", None)
            f.pop("excluded_reason", None)
            if needs_review:
                f["needs_review"]  = True
                f["review_reason"] = rv_reason
                n_flagged += 1
            else:
                f["needs_review"] = False
                f.pop("review_reason", None)
                n_cleared += 1

    for f in figures:
        f.pop("_year", None)
    data["reported_figures"] = figures
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return {
        "year":      year,
        "total":     len(figures),
        "excluded":  n_excluded,
        "flagged":   n_flagged,
        "clean":     n_cleared,
    }


# ---------------------------------------------------------------------------
# Patched write_combined that skips excluded figures
# ---------------------------------------------------------------------------
# We monkey-patch write_markdown to honour excluded / needs_review flags.

from fetch_attendees import write_markdown as _orig_write_markdown  # noqa: E402


def write_markdown_with_flags(all_data: list[dict]) -> None:
    """
    Extended version of write_markdown that:
    - Skips figures with excluded=True
    - Marks figures with needs_review=True as ❓ instead of ⬜
    - Shows review_reason inline
    """
    from datetime import date
    TODAY = date.today().isoformat()

    lines = [
        "# Wikimania Attendance Figures — Collected Data",
        "",
        f"*Generated: {TODAY}*",
        "",
        "This document collects every reported attendance or participation figure "
        "for each Wikimania edition, preserving the exact definition used by each "
        "source. Figures are **not** normalised.",
        "",
        "Verification status: ✅ verified | ❓ needs review | ⬜ unverified",
        "",
        "---",
        "",
    ]

    source_type_labels = {
        "wikipedia":       "Wikipedia",
        "meta_wiki":       "Meta-wiki",
        "conference_wiki": "Conference wiki",
        "mailing_list":    "Mailing list",
        "blog":            "Wikimedia blog",
        "other":           "Other",
    }

    for edition in all_data:
        year     = edition["year"]
        location = edition.get("location", "N/A")
        notes    = edition.get("notes", "")
        all_figs = edition.get("reported_figures", [])
        figures  = [f for f in all_figs if not f.get("excluded")]

        lines.append(f"## {year} — {location}")
        if notes:
            lines.append(f"*{notes}*")
        lines.append("")

        n_excluded = sum(1 for f in all_figs if f.get("excluded"))
        if n_excluded:
            lines.append(f"*({n_excluded} figure(s) auto-excluded as non-attendance data.)*")
            lines.append("")

        if not figures:
            lines.append("*No figures collected yet.*")
            lines.append("")
            lines.append("---")
            lines.append("")
            continue

        def sort_key(f):
            type_order = {"wikipedia": 0, "meta_wiki": 1, "conference_wiki": 2,
                          "mailing_list": 3, "blog": 4, "other": 5}
            return (type_order.get(f.get("source_type", "other"), 9),
                    -(f.get("figure_numeric") or 0))
        figures_sorted = sorted(figures, key=sort_key)

        for f in figures_sorted:
            if f.get("verified"):
                status_icon = "✅"
            elif f.get("needs_review"):
                status_icon = "❓"
            else:
                status_icon = "⬜"

            figure_raw    = f.get("figure_raw", "?")
            defn          = f.get("definition_as_reported", "")
            context       = f.get("context", "").strip()
            source_url    = f.get("source_url", "")
            source_type   = source_type_labels.get(f.get("source_type", ""), "Other")
            author        = f.get("author")
            author_role   = f.get("author_role")
            email_subject = f.get("email_subject", "")
            retrieved     = f.get("retrieved", "")
            review_reason = f.get("review_reason", "")

            lines.append(f"### {figure_raw} — {defn}")
            lines.append("")
            if context:
                lines.append(f"> {context}")
                lines.append("")

            meta_parts = [f"**Source:** [{source_type}]({source_url})"]
            if author:
                author_str = author
                if author_role:
                    author_str += f" *({author_role})*"
                meta_parts.append(f"**Author:** {author_str}")
            if email_subject:
                meta_parts.append(f"**Subject:** {email_subject}")
            if retrieved:
                meta_parts.append(f"**Retrieved:** {retrieved}")
            meta_parts.append(f"**Status:** {status_icon}")
            if review_reason:
                meta_parts.append(f"**Note:** {review_reason}")

            lines.append(" · ".join(meta_parts))
            lines.append("")

        lines.append("---")
        lines.append("")

    out = ATTENDEES_DIR / "attendance_report.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Markdown report written:  {out}")


def write_combined_with_flags() -> None:
    """Rewrite attendance_all.json and the Markdown report."""
    import fetch_attendees as fa
    all_data = []
    for path in sorted(EDITIONS_DIR.glob("wikimania_*.json")):
        if "all" in path.name:
            continue
        all_data.append(json.loads(path.read_text()))

    out = ATTENDEES_DIR / "attendance_all.json"
    out.write_text(json.dumps(all_data, indent=2, ensure_ascii=False))
    print(f"Combined JSON written:    {out}")

    write_markdown_with_flags(all_data)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    target_years = None
    if len(sys.argv) > 1:
        target_years = [int(a) for a in sys.argv[1:]]

    paths = sorted(EDITIONS_DIR.glob("wikimania_*.json"))
    if target_years:
        paths = [p for p in paths if any(str(y) in p.name for y in target_years)]

    print(f"Cleaning {len(paths)} edition(s)...\n")
    totals = {"total": 0, "excluded": 0, "flagged": 0, "clean": 0}
    for p in paths:
        year = int(re.search(r'(\d{4})', p.name).group(1))
        result = clean_edition(year)
        if "error" in result:
            print(f"  {year}: {result['error']}")
            continue
        print(f"  {result['year']:4d}: "
              f"{result['total']:3d} total  "
              f"{result['excluded']:3d} excluded  "
              f"{result['flagged']:3d} flagged  "
              f"{result['clean']:3d} clean")
        for k in totals:
            totals[k] += result.get(k, 0)

    print(f"\n  {'TOTAL':4s}: "
          f"{totals['total']:3d} total  "
          f"{totals['excluded']:3d} excluded  "
          f"{totals['flagged']:3d} flagged  "
          f"{totals['clean']:3d} clean")

    print()
    write_combined_with_flags()


if __name__ == "__main__":
    main()
