# /// script
# dependencies = ["pandas", "matplotlib", "numpy"]
# ///
"""
pilot_ossification.py — cheap first read on the policy-change thesis, run on the
EXISTING mwparserfromhell-cleaned drift CSVs (no build, no Toolforge, no LLM).

Tests, directionally:
  H2 (ossification): does per-policy change magnitude decline with year / age?
  H1 (additive-not-reform): are transitions mostly additive (old text retained)
      rather than reformative (old text replaced)?
  RQ2 (reform candidates): rank node-year transitions by a reform score and emit
      the shortlist worth case-studying.
  RQ3 (inflection, RAW proxy): aggregate change magnitude per year — eyeball
      regime shifts. NB: raw, not M5-normalized; directional only.

CAVEATS (this is a pilot, not a result): non-random 10-policy sample, en-heavy,
raw un-normalized series, yearly snapshots only. Uses the cleaned CSVs — the old
regex cleaner manufactured phantom change that would fake anti-ossification.
"""

import glob
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

DRIFT = Path(__file__).parent / "data" / "policy_drift"
OUT = DRIFT / "pilot"
OUT.mkdir(parents=True, exist_ok=True)

REFORM_OLD_IN_NEW = 0.80   # below this, old text was substantially replaced = reform-ish
SHORT = {  # tidy labels
    "en": "en", "de": "de", "fr": "fr", "es": "es", "ja": "ja", "nl": "nl",
}


def load() -> pd.DataFrame:
    frames = []
    for f in sorted(glob.glob(str(DRIFT / "*.csv"))):
        df = pd.read_csv(f)
        if df.empty:
            continue
        df["lang"] = df["wiki"].iloc[0].split(".")[0]
        df["policy"] = df["title"].iloc[0]
        for c in ["year", "word_count", "cosine_vs_prev",
                  "containment_old_in_new", "containment_new_in_old",
                  "words_added", "words_removed"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        frames.append(df)
    d = pd.concat(frames, ignore_index=True)
    d["change"] = 1.0 - d["cosine_vs_prev"]          # change magnitude (0=identical)
    d["age"] = d.groupby(["wiki", "policy"])["year"].transform(lambda s: s - s.min())
    return d


def h2_ossification(d: pd.DataFrame) -> None:
    """Change magnitude vs calendar year and vs policy age."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    # vs year (en only, per policy translucent + mean solid)
    en = d[(d["lang"] == "en") & d["change"].notna()]
    for _, g in en.groupby("policy"):
        axes[0].plot(g["year"], g["change"], color="#1f77b4", alpha=0.20, lw=0.9)
    m = en.groupby("year")["change"].mean()
    axes[0].plot(m.index, m.values, color="#1f77b4", lw=2, marker="o", ms=3, label="en mean")
    axes[0].set_title("H2: change magnitude (1−cosine) vs year — enwiki")
    axes[0].set_xlabel("year"); axes[0].set_ylabel("change magnitude"); axes[0].legend()
    axes[0].grid(alpha=0.3)
    # vs age (all langs, mean by age)
    for lang, g in d[d["change"].notna()].groupby("lang"):
        ma = g.groupby("age")["change"].mean()
        axes[1].plot(ma.index, ma.values, marker="o", ms=3, lw=1.5, label=SHORT.get(lang, lang))
    axes[1].set_title("H2: change magnitude vs policy age — by language")
    axes[1].set_xlabel("years since first snapshot"); axes[1].set_ylabel("mean change")
    axes[1].legend(); axes[1].grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(OUT / "h2_ossification.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # trend stats
    rows = []
    for lang, g in d[d["change"].notna()].groupby("lang"):
        if len(g) > 3:
            r_year = np.corrcoef(g["year"], g["change"])[0, 1]
            r_age = np.corrcoef(g["age"], g["change"])[0, 1]
            rows.append((lang, len(g), round(r_year, 3), round(r_age, 3),
                         round(g["change"].mean(), 3)))
    t = pd.DataFrame(rows, columns=["lang", "n_transitions", "corr_change_year",
                                    "corr_change_age", "mean_change"])
    t.to_csv(OUT / "h2_trends.csv", index=False)
    print("\nH2 — ossification trends (negative corr = freezing over time/age):")
    print(t.to_string(index=False))


def h1_additive(d: pd.DataFrame) -> None:
    """Are transitions additive (old retained) or reformative (old replaced)?"""
    sub = d[d["containment_old_in_new"].notna()].copy()
    sub["is_reform"] = sub["containment_old_in_new"] < REFORM_OLD_IN_NEW
    by_lang = sub.groupby("lang").agg(
        n=("is_reform", "size"),
        reform_rate=("is_reform", "mean"),
        mean_old_in_new=("containment_old_in_new", "mean"),
        mean_added=("words_added", "mean"),
        mean_removed=("words_removed", "mean"),
    ).round(3)
    by_lang.to_csv(OUT / "h1_additive.csv")
    print(f"\nH1 — additive-vs-reform (reform = old_in_new < {REFORM_OLD_IN_NEW}):")
    print(by_lang.to_string())

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(sub["containment_old_in_new"].dropna(), bins=30, color="#1f77b4", alpha=0.8)
    ax.axvline(REFORM_OLD_IN_NEW, color="red", ls="--", label=f"reform threshold {REFORM_OLD_IN_NEW}")
    ax.set_title("H1: distribution of old-content-retained (low = reform)")
    ax.set_xlabel("containment_old_in_new"); ax.set_ylabel("node-year transitions")
    ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(OUT / "h1_additive_hist.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def rq2_reform_candidates(d: pd.DataFrame) -> None:
    """Rank transitions by reform score = (1-old_in_new) * change."""
    sub = d[d["containment_old_in_new"].notna() & d["change"].notna()].copy()
    sub["reform_score"] = (1 - sub["containment_old_in_new"]) * sub["change"]
    cols = ["lang", "policy", "year", "word_count", "cosine_vs_prev",
            "containment_old_in_new", "containment_new_in_old", "reform_score"]
    top = sub.sort_values("reform_score", ascending=False)[cols].head(25).round(3)
    top.to_csv(OUT / "rq2_reform_candidates.csv", index=False)
    print("\nRQ2 — top reform candidates (case-study shortlist):")
    print(top.head(15).to_string(index=False))


def rq3_inflection(d: pd.DataFrame) -> None:
    """RAW aggregate change magnitude per year (en) — eyeball inflection."""
    en = d[(d["lang"] == "en") & d["change"].notna()]
    agg = en.groupby("year").agg(mean_change=("change", "mean"),
                                 n=("change", "size"),
                                 total_words=("word_count", "sum"))
    agg.to_csv(OUT / "rq3_aggregate_by_year.csv")
    fig, ax1 = plt.subplots(figsize=(9, 5))
    ax1.plot(agg.index, agg["mean_change"], color="#d62728", marker="o", ms=3, label="mean change")
    ax1.set_xlabel("year"); ax1.set_ylabel("mean change magnitude", color="#d62728")
    ax2 = ax1.twinx()
    ax2.plot(agg.index, agg["total_words"], color="#1f77b4", lw=1.5, alpha=0.6, label="total words")
    ax2.set_ylabel("total words (corpus size)", color="#1f77b4")
    ax1.set_title("RQ3: enwiki aggregate change + size by year (RAW — not M5-normalized)")
    ax1.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(OUT / "rq3_inflection_raw.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("\nRQ3 — enwiki aggregate by year (raw proxy; eyeball regime shifts):")
    print(agg.round(3).to_string())


def main() -> None:
    d = load()
    print(f"Loaded {d['policy'].nunique()} policies across {d['lang'].nunique()} langs, "
          f"{len(d)} node-years.")
    h2_ossification(d)
    h1_additive(d)
    rq2_reform_candidates(d)
    rq3_inflection(d)
    print(f"\nOutputs → {OUT}")


if __name__ == "__main__":
    main()
