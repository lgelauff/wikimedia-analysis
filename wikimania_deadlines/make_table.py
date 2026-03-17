"""
Generate a compact date table for all Wikimania editions.

Columns: year, conf start/end, program open/deadline/extended/total-open,
         scholarship open/deadline/extended/total-open,
         registration open/online deadline/in-person deadline/in-person-open.
"""

import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime

EDITIONS_DIR = Path(__file__).parent / "editions"

COLUMNS = [
    # (bucket, type, header line 1, header line 2)
    ("conference",  "conference_start",                     "Conf",   "Start"),
    ("conference",  "conference_end",                       "Conf",   "End"),
    ("program",     "program_submission_open",              "Prog",   "Open"),
    ("program",     "program_submission_deadline",          "Prog",   "Deadline"),
    ("program",     "program_submission_deadline_extended", "Prog",   "Extended"),
    ("program",     "_prog_total_open",                     "Prog",   "Days open"),
    ("scholarship", "scholarship_applications_open",        "Schol",  "Open"),
    ("scholarship", "scholarship_deadline",                 "Schol",  "Deadline"),
    ("scholarship", "scholarship_deadline_extended",        "Schol",  "Extended"),
    ("scholarship", "_schol_total_open",                    "Schol",  "Days open"),
    ("registration","registration_open",                    "Reg",    "Open"),
    ("registration","registration_deadline_online",         "Reg",    "Online"),
    ("registration","registration_deadline_inperson",       "Reg",    "In-person"),
    ("registration","_reg_inperson_open",                   "Reg",    "Days open"),
]

BUCKET_COLORS = {
    "conference":  "#1565c0",
    "program":     "#6a1b9a",
    "scholarship": "#e65100",
    "registration":"#00695c",
}

COMPUTED = {"_prog_total_open", "_schol_total_open", "_reg_inperson_open"}


def parse_date(date_str):
    if not date_str:
        return None
    try:
        if len(date_str) == 7:
            return datetime.strptime(date_str, "%Y-%m")
        return datetime.strptime(date_str[:10], "%Y-%m-%d")
    except Exception:
        return None


def fmt_date(date_str, confidence):
    if not date_str or confidence == "not_applicable":
        return "—"
    if confidence == "unknown":
        return "?"
    try:
        if len(date_str) == 7:
            y, m = date_str.split("-")
            label = f"{int(m):02d}/{y[2:]}"
        else:
            dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
            label = f"{dt.day:02d}/{dt.month:02d}"
        return f"~{label}" if confidence == "approximate" else label
    except Exception:
        return date_str[:10]


def days_between(entry_from, entry_to_main, entry_to_ext=None):
    """Return day-delta string between open and last deadline (extended if available)."""
    if not entry_from or not entry_to_main:
        return "?"
    conf_from = entry_from.get("date_confidence", "unknown")
    if conf_from in ("not_applicable", "unknown"):
        return "—" if conf_from == "not_applicable" else "?"

    # Use extended deadline if available and not n/a or unknown
    end_entry = entry_to_main
    if entry_to_ext:
        c = entry_to_ext.get("date_confidence", "unknown")
        if c not in ("not_applicable", "unknown") and entry_to_ext.get("date"):
            end_entry = entry_to_ext

    conf_to = end_entry.get("date_confidence", "unknown")
    if conf_to in ("not_applicable", "unknown"):
        return "—" if conf_to == "not_applicable" else "?"

    d_from = parse_date(entry_from.get("date"))
    d_to   = parse_date(end_entry.get("date"))
    if not d_from or not d_to:
        return "?"

    delta = (d_to - d_from).days
    if delta < 0:
        return "?"
    approx = (entry_from.get("date_confidence") == "approximate" or
              end_entry.get("date_confidence") == "approximate")
    return f"~{delta}d" if approx else f"{delta}d"


def load_data():
    rows = []
    for year in range(2005, 2027):
        fp = EDITIONS_DIR / f"wikimania_{year}.json"
        if not fp.exists():
            continue
        data = json.loads(fp.read_text())
        lookup = {}
        for bname, bucket in data["buckets"].items():
            for d in bucket.get("deadlines", []):
                lookup[(bname, d["type"])] = d

        row = [str(year)]
        for bucket, dtype, _, _ in COLUMNS:
            if dtype in COMPUTED:
                if dtype == "_prog_total_open":
                    val = days_between(
                        lookup.get(("program", "program_submission_open")),
                        lookup.get(("program", "program_submission_deadline")),
                        lookup.get(("program", "program_submission_deadline_extended")),
                    )
                elif dtype == "_schol_total_open":
                    val = days_between(
                        lookup.get(("scholarship", "scholarship_applications_open")),
                        lookup.get(("scholarship", "scholarship_deadline")),
                        lookup.get(("scholarship", "scholarship_deadline_extended")),
                    )
                elif dtype == "_reg_inperson_open":
                    val = days_between(
                        lookup.get(("registration", "registration_open")),
                        lookup.get(("registration", "registration_deadline_inperson")),
                    )
                row.append(val)
            else:
                entry = lookup.get((bucket, dtype))
                if entry is None:
                    row.append("?")
                else:
                    row.append(fmt_date(entry.get("date"), entry.get("date_confidence", "unknown")))
        rows.append(row)
    return rows


def draw_table(rows):
    n_rows = len(rows)
    n_cols = len(COLUMNS) + 1   # +1 for year

    # Column widths
    duration_w = 0.58
    date_w     = 0.68
    year_w     = 0.45
    col_widths = [year_w]
    for _, dtype, _, _ in COLUMNS:
        col_widths.append(duration_w if dtype in COMPUTED else date_w)

    row_height    = 0.22
    header_height = 0.22
    fig_w = sum(col_widths) + 0.2
    fig_h = (n_rows + 2) * row_height + 0.35

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.axis("off")

    x_positions = [0]
    for w in col_widths[:-1]:
        x_positions.append(x_positions[-1] + w)
    total_w = sum(col_widths)
    total_h = (n_rows + 2) * row_height

    bucket_spans = {}
    for ci, (bucket, _, _, _) in enumerate(COLUMNS):
        bucket_spans.setdefault(bucket, []).append(ci + 1)

    def cell_rect(col, row, w, h, fc, ec="white", lw=0.5):
        x = x_positions[col]
        y = total_h - (row + 1) * h
        rect = plt.Rectangle((x, y), w, h,
                              facecolor=fc, edgecolor=ec, linewidth=lw,
                              transform=ax.transData, clip_on=False)
        ax.add_patch(rect)

    # Header row 0: bucket labels
    drawn_buckets = set()
    for ci, (bucket, _, _, _) in enumerate(COLUMNS):
        col = ci + 1
        color = BUCKET_COLORS[bucket]
        cell_rect(col, 0, col_widths[col], header_height, fc=color + "30", ec=color, lw=0.8)
        if bucket not in drawn_buckets:
            span_cols = bucket_spans[bucket]
            span_w = sum(col_widths[c] for c in span_cols)
            span_x = x_positions[span_cols[0]]
            ax.text(span_x + span_w / 2, total_h - header_height / 2,
                    {"conference": "CONFERENCE", "program": "PROGRAM",
                     "scholarship": "SCHOLARSHIP", "registration": "REGISTRATION"}[bucket],
                    ha="center", va="center", fontsize=6.5, fontweight="bold", color=color)
            drawn_buckets.add(bucket)

    # Year header (spans both header rows)
    cell_rect(0, 0, col_widths[0], header_height * 2, fc="#eeeeee", ec="#aaa", lw=0.8)
    ax.text(x_positions[0] + col_widths[0] / 2, total_h - header_height,
            "Year", ha="center", va="center", fontsize=7.5, fontweight="bold")

    # Header row 1: column labels
    for ci, (bucket, dtype, _, h2) in enumerate(COLUMNS):
        col = ci + 1
        color = BUCKET_COLORS[bucket]
        fc = color + "40" if dtype in COMPUTED else color + "18"
        cell_rect(col, 1, col_widths[col], header_height, fc=fc, ec=color, lw=0.8)
        ax.text(x_positions[col] + col_widths[col] / 2, total_h - 1.5 * header_height,
                h2, ha="center", va="center", fontsize=6, color=color, fontweight="bold")

    # Data rows
    for ri, row in enumerate(rows):
        dr  = ri + 2
        y_c = total_h - (dr + 0.5) * row_height
        bg  = "#f9f9f9" if ri % 2 == 0 else "#ffffff"

        for ci, val in enumerate(row):
            _, dtype, _, _ = ("year", "year", "", "") if ci == 0 else COLUMNS[ci - 1]
            w = col_widths[ci]
            is_dur = (ci > 0 and dtype in COMPUTED)
            cell_fc = bg if not is_dur else (bg if ri % 2 == 0 else "#f5f5f5")
            cell_rect(ci, dr, w, row_height, fc=cell_fc, ec="#ddd", lw=0.4)

            if ci == 0:
                color, fw = "#333", "bold"
            elif val == "—":
                color, fw = "#bbb", "normal"
            elif val == "?":
                color, fw = "#ccc", "normal"
            elif val.startswith("~"):
                color, fw = "#777", "normal"
            elif is_dur:
                color, fw = BUCKET_COLORS[COLUMNS[ci-1][0]], "bold"
            else:
                color, fw = "#222", "normal"

            ax.text(x_positions[ci] + w / 2, y_c, val,
                    ha="center", va="center", fontsize=6.5,
                    color=color, fontweight=fw)

    ax.set_xlim(0, total_w)
    ax.set_ylim(0, total_h)
    fig.suptitle("Wikimania 2005–2026  ·  Key Deadline Dates",
                 fontsize=10, fontweight="bold", y=0.99)

    out_path = Path(__file__).parent / "deadline_table.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Table saved to: {out_path}")


def write_csv(rows):
    import csv
    header = ["Year"] + [f"{h1} {h2}".strip() for _, _, h1, h2 in COLUMNS]
    out_path = Path(__file__).parent / "deadline_table.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    print(f"CSV saved to:   {out_path}")


if __name__ == "__main__":
    rows = load_data()
    write_csv(rows)
    draw_table(rows)
