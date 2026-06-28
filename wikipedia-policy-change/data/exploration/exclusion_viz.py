# /// script
# dependencies = ["matplotlib"]
# ///
"""
exclusion_viz.py — mark which page text is EXCLUDED from the statement set, by kind.

Input: an annotated page (JSONL of {"text","kind"}), where kind is one of
  included | deliberation | meta | scaffolding | summary   (anything != "included" is excluded).
Output: a self-contained HTML and a PNG, each line shaded by its kind — so it's instantly visible
how much of the page becomes policy statements vs. what is dropped (and why).

Usage:
  uv run --script exclusion_viz.py --in nlwiki_stemgerechtigde_gebruikers/02b_text_annotated.jsonl \
      --out-html ... --out-png ... --title "..."
"""
import argparse, json, html
from pathlib import Path

KIND = {  # kind -> (color, label, excluded?)
    "included":     ("#9fe0a0", "included (becomes statements)", False),
    "deliberation": ("#f3a0a0", "excluded · deliberation (votes/arguments)", True),
    "meta":         ("#f6c98a", "excluded · meta / rationale / outcome", True),
    "scaffolding":  ("#d3d0c8", "excluded · scaffolding / layout / nav", True),
    "summary":      ("#fff1a8", "excluded · summary (linked, not counted)", True),
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out-html", required=True)
    ap.add_argument("--out-png", required=True)
    ap.add_argument("--title", default="excluded text")
    a = ap.parse_args()
    rows = [json.loads(l) for l in Path(a.inp).read_text(encoding="utf-8").splitlines() if l.strip()]
    n = len(rows)
    n_excl = sum(1 for r in rows if KIND.get(r["kind"], KIND["meta"])[2])
    pct = 100 * n_excl // n if n else 0

    # ---- HTML ----
    H = ['<div style="font-family:var(--font-sans);max-width:840px;font-size:14px;line-height:1.5">']
    H.append(f'<div style="font-weight:500;font-size:17px">{html.escape(a.title)}</div>')
    H.append(f'<div style="color:#555;font-size:13px;margin:2px 0 10px">{n} text blocks · '
             f'{n_excl} excluded ({pct}%) · {n-n_excl} kept</div>')
    H.append('<div style="font-size:12px;margin-bottom:10px">' + " ".join(
        f'<span style="background:{c};color:#2c2c2a;padding:1px 7px;border-radius:3px;margin-right:4px">{l}</span>'
        for c, l, _ in dict.fromkeys(KIND.values()) and KIND.values()) + '</div>')
    for r in rows:
        c, _, _ = KIND.get(r["kind"], KIND["meta"])
        H.append(f'<div style="background:{c};color:#2c2c2a;padding:3px 8px;margin:2px 0;'
                 f'border-radius:3px">{html.escape(r["text"])}</div>')
    H.append('</div>')
    Path(a.out_html).write_text("\n".join(H), encoding="utf-8")

    # ---- PNG ----
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    fig, ax = plt.subplots(figsize=(12, 0.42 * n + 1.2))
    for i, r in enumerate(rows):
        c, _, _ = KIND.get(r["kind"], KIND["meta"])
        y = n - i - 1
        ax.add_patch(plt.Rectangle((0, y), 1, 0.9, facecolor=c, edgecolor="white", linewidth=1))
        t = r["text"]
        if len(t) > 104:
            t = t[:101] + "…"
        ax.text(0.008, y + 0.45, t, va="center", ha="left", fontsize=9, color="#222")
    ax.set_xlim(0, 1); ax.set_ylim(0, n); ax.axis("off")
    ax.set_title(f"{a.title}   —   {pct}% of the page text is excluded ({n_excl}/{n} blocks)",
                 fontsize=12, loc="left")
    seen, handles = set(), []
    for r in rows:
        k = r["kind"]
        if k in seen: continue
        seen.add(k); c, l, _ = KIND.get(k, KIND["meta"]); handles.append(Patch(facecolor=c, label=l))
    ax.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, -0.06 - 0.6 / n),
              ncol=2, fontsize=9, frameon=False)
    fig.tight_layout()
    fig.savefig(a.out_png, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {a.out_html} and {a.out_png} | {pct}% excluded ({n_excl}/{n} blocks)")

if __name__ == "__main__":
    main()
