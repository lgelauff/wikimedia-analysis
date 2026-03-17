"""
Visualize deadline data availability across all Wikimania editions.

Shows which deadline fields have a "good date" (confirmed or approximate,
accurate to at least a 7-day range) vs unknown, not_applicable, or missing.
"""

import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as ticker
import numpy as np
from pathlib import Path

# ---------------------------------------------------------------------------
# Data definitions
# ---------------------------------------------------------------------------

DEADLINE_COLUMNS = [
    # (bucket, field_key, short_label)
    ("conference",  "conference_start",                     "Start"),
    ("conference",  "conference_end",                       "End"),
    ("program",     "program_submission_open",              "Open"),
    ("program",     "program_submission_deadline",          "Deadline"),
    ("program",     "program_submission_deadline_extended", "Extended"),
    ("program",     "program_acceptance_notification",      "Notif"),
    ("program",     "program_speaker_confirmation",         "Speaker"),
    ("program",     "program_schedule_published",           "Schedule"),
    ("scholarship", "scholarship_applications_open",        "Open"),
    ("scholarship", "scholarship_deadline",                 "Deadline"),
    ("scholarship", "scholarship_deadline_extended",        "Extended"),
    ("scholarship", "scholarship_results_notification",     "Results"),
    ("scholarship", "scholarship_acceptance_confirmation",  "Confirm"),
    ("registration","registration_open",                    "Open"),
    ("registration","registration_earlybird_deadline",      "EarlyBird"),
    ("registration","registration_deadline_online",         "Online deadline"),
    ("registration","registration_deadline_inperson",       "In-person deadline"),
    ("registration","registration_late_deadline",           "Late"),
]

BUCKET_LABELS = {
    "conference":  "CONFERENCE",
    "program":     "PROGRAM",
    "scholarship": "SCHOLARSHIP",
    "registration":"REGISTRATION",
}
BUCKET_COLORS = {
    "conference":  "#1565c0",
    "program":     "#6a1b9a",
    "scholarship": "#e65100",
    "registration":"#00695c",
}

# Cell value codes
CONFIRMED      = 3
APPROXIMATE    = 2
UNKNOWN        = 1
NOT_APPLICABLE = 0

CELL_COLORS = {
    CONFIRMED:      np.array([0x2e, 0x7d, 0x32]) / 255,   # dark green
    APPROXIMATE:    np.array([0x81, 0xc7, 0x84]) / 255,   # light green
    UNKNOWN:        np.array([0xff, 0xec, 0xb3]) / 255,   # light amber
    NOT_APPLICABLE: np.array([0xb0, 0xbe, 0xc5]) / 255,  # blue-grey
}


def load_editions():
    editions_dir = Path(__file__).parent / "editions"
    editions = []
    for year in range(2005, 2027):
        fp = editions_dir / f"wikimania_{year}.json"
        if fp.exists():
            editions.append(json.loads(fp.read_text()))
    return editions


def build_matrix(editions):
    years = [e["year"] for e in editions]
    n_rows, n_cols = len(editions), len(DEADLINE_COLUMNS)
    matrix = np.full((n_rows, n_cols), UNKNOWN, dtype=int)

    for r, edition in enumerate(editions):
        lookup = {}
        for bucket_name, bucket in edition["buckets"].items():
            for d in bucket.get("deadlines", []):
                lookup[(bucket_name, d["type"])] = d

        for c, (bucket, field, _) in enumerate(DEADLINE_COLUMNS):
            entry = lookup.get((bucket, field))
            if entry is None:
                matrix[r][c] = UNKNOWN
                continue
            conf  = entry.get("date_confidence")
            date  = entry.get("date")
            if conf == "not_applicable":
                matrix[r][c] = NOT_APPLICABLE
            elif conf == "confirmed" and date:
                matrix[r][c] = CONFIRMED
            elif conf == "approximate" and date:
                matrix[r][c] = APPROXIMATE
            else:
                matrix[r][c] = UNKNOWN

    return years, matrix


def bucket_spans(columns):
    """Return list of (bucket_name, col_start, col_end) groups."""
    spans = []
    current, start = None, 0
    for c, (bucket, _, _) in enumerate(columns):
        if bucket != current:
            if current is not None:
                spans.append((current, start, c - 1))
            current, start = bucket, c
    spans.append((current, start, len(columns) - 1))
    return spans


def draw_heatmap(years, matrix):
    n_rows, n_cols = matrix.shape
    col_labels = [lbl for _, _, lbl in DEADLINE_COLUMNS]
    spans      = bucket_spans(DEADLINE_COLUMNS)

    # Build RGB image
    img = np.zeros((n_rows, n_cols, 3))
    for code, rgb in CELL_COLORS.items():
        img[matrix == code] = rgb

    # Figure: make it clearly wider than tall
    cell_w, cell_h = 0.72, 0.52          # inches per cell
    left_margin    = 0.6                  # year labels
    right_margin   = 0.2
    top_margin     = 1.5                  # bucket header + col labels
    bottom_margin  = 0.9                  # legend + pct row
    fig_w = left_margin + n_cols * cell_w + right_margin
    fig_h = top_margin + n_rows * cell_h + bottom_margin

    fig = plt.figure(figsize=(fig_w, fig_h))

    # Main axes: leave room at top for bucket headers
    ax_left   = left_margin / fig_w
    ax_bottom = bottom_margin / fig_h
    ax_width  = n_cols * cell_w / fig_w
    ax_height = n_rows * cell_h / fig_h
    ax = fig.add_axes([ax_left, ax_bottom, ax_width, ax_height])

    ax.imshow(img, aspect="auto", interpolation="none",
              extent=[-0.5, n_cols - 0.5, n_rows - 0.5, -0.5])

    # --- Cell grid lines ---
    for x in np.arange(-0.5, n_cols, 1):
        ax.axvline(x, color="white", lw=0.6)
    for y in np.arange(-0.5, n_rows, 1):
        ax.axhline(y, color="white", lw=0.6)

    # --- Thicker bucket separator lines ---
    for _, _, _, col_end in [(s[0], s[1], s[2], s[2]) for s in spans[:-1]]:
        ax.axvline(col_end + 0.5, color="white", lw=2.5)

    # --- Year labels (y axis) ---
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels([str(y) for y in years], fontsize=8.5)
    ax.tick_params(axis="y", length=0, pad=4)

    # --- Column labels (rotated, bottom of heatmap) ---
    ax.set_xticks(range(n_cols))
    ax.set_xticklabels(col_labels, rotation=45, ha="right", fontsize=8)
    ax.xaxis.set_ticks_position("bottom")
    ax.tick_params(axis="x", length=0, pad=2)

    # --- Percentage row below column labels ---
    pct_y = -0.55   # data coords below the heatmap bottom (-0.5)
    for c in range(n_cols):
        col        = matrix[:, c]
        good       = int(np.sum((col == CONFIRMED) | (col == APPROXIMATE)))
        n_relevant = int(np.sum(col != NOT_APPLICABLE))
        if n_relevant > 0:
            pct = f"{100 * good // n_relevant}%"
            ax.text(c, n_rows - 0.5 + 0.25, pct,
                    transform=ax.transData,
                    ha="center", va="top", fontsize=6.5, color="#555")

    ax.set_xlim(-0.5, n_cols - 0.5)
    ax.set_ylim(n_rows - 0.5, -0.5)

    # --- Bucket header band (drawn in figure coords above the main axes) ---
    header_h_in  = 0.38          # height of header band in inches
    gap_in       = 0.06          # gap between header band and heatmap top
    header_bot   = ax_bottom + ax_height + gap_in / fig_h
    header_h     = header_h_in / fig_h

    ax_header = fig.add_axes([ax_left, header_bot, ax_width, header_h])
    ax_header.set_xlim(0, n_cols)
    ax_header.set_ylim(0, 1)
    ax_header.axis("off")

    for bname, c_start, c_end in spans:
        color     = BUCKET_COLORS[bname]
        left_frac = c_start / n_cols
        width_frac= (c_end - c_start + 1) / n_cols
        rect = mpatches.FancyBboxPatch(
            (c_start + 0.08, 0.08),
            (c_end - c_start + 1) - 0.16, 0.84,
            boxstyle="round,pad=0.02",
            linewidth=0, facecolor=color, alpha=0.15,
            transform=ax_header.transData, clip_on=False,
        )
        ax_header.add_patch(rect)
        ax_header.text(
            (c_start + c_end + 1) / 2, 0.52,
            BUCKET_LABELS[bname],
            ha="center", va="center",
            fontsize=8, fontweight="bold", color=color,
            transform=ax_header.transData,
        )

    # --- Legend (in figure coords below the heatmap) ---
    legend_patches = [
        mpatches.Patch(facecolor=CELL_COLORS[CONFIRMED],
                       edgecolor="#ccc", linewidth=0.5,
                       label="Confirmed  (exact date, ≤1-day accuracy)"),
        mpatches.Patch(facecolor=CELL_COLORS[APPROXIMATE],
                       edgecolor="#ccc", linewidth=0.5,
                       label="Approximate  (≤7-day range)"),
        mpatches.Patch(facecolor=CELL_COLORS[UNKNOWN],
                       edgecolor="#ccc", linewidth=0.5,
                       label="Unknown  (searched; no date found)"),
        mpatches.Patch(facecolor=CELL_COLORS[NOT_APPLICABLE],
                       edgecolor="#ccc", linewidth=0.5,
                       label="Not applicable  (event/tier did not exist)"),
    ]
    fig.legend(
        handles=legend_patches,
        loc="lower left",
        bbox_to_anchor=(ax_left, 0.01),
        ncol=2, fontsize=8.5,
        frameon=True, framealpha=0.95,
        columnspacing=1.2, handlelength=1.2,
    )

    # --- Title ---
    fig.text(
        ax_left + ax_width / 2,
        ax_bottom + ax_height + (gap_in + header_h_in + 0.15) / fig_h,
        "Wikimania 2005–2026  ·  Deadline Data Availability\n"
        "% below each column = share of applicable editions with a good date",
        ha="center", va="bottom",
        fontsize=11, fontweight="bold", linespacing=1.5,
    )

    out_path = Path(__file__).parent / "deadline_availability.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_path


def print_text_summary(years, matrix):
    col_labels = [lbl for _, _, lbl in DEADLINE_COLUMNS]
    symbols = {CONFIRMED: "●", APPROXIMATE: "◐", UNKNOWN: "○", NOT_APPLICABLE: "—"}

    print(f"\n{'Year':<6}", end="")
    for lbl in col_labels:
        print(f" {lbl[:10]:<10}", end="")
    print()
    print("─" * (6 + 11 * len(col_labels)))

    for r, year in enumerate(years):
        print(f"{year:<6}", end="")
        for c in range(len(DEADLINE_COLUMNS)):
            print(f" {symbols[matrix[r][c]]:<10}", end="")
        print()

    print("\nLegend: ● confirmed  ◐ approximate  ○ unknown  — not applicable")

    print("\nCoverage by bucket (good dates / applicable edition-fields):")
    for bname, c_start, c_end in bucket_spans(DEADLINE_COLUMNS):
        cols      = matrix[:, c_start:c_end + 1]
        good      = int(np.sum((cols == CONFIRMED) | (cols == APPROXIMATE)))
        relevant  = int(np.sum(cols != NOT_APPLICABLE))
        pct       = 100 * good // relevant if relevant else 0
        print(f"  {bname:<14}: {good:>3}/{relevant:<3}  ({pct}%)")


def main():
    editions = load_editions()
    years, matrix = build_matrix(editions)
    print_text_summary(years, matrix)
    out_path = draw_heatmap(years, matrix)
    print(f"\nHeatmap saved to: {out_path}")


if __name__ == "__main__":
    main()
