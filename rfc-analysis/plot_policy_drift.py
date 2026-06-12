# /// script
# dependencies = ["certifi", "matplotlib", "pandas"]
# ///
"""
plot_policy_drift.py — visualise policy page drift metrics across languages.

Usage:
    uv run python plot_policy_drift.py          # enwiki only
    uv run python plot_policy_drift.py --langs  # fetch + plot de/fr/es/ja too
"""

import argparse
import csv
import glob
import json
import re
import ssl
import time
import urllib.parse
import urllib.request
from pathlib import Path

import certifi
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DRIFT_DIR = Path(__file__).parent / "data" / "policy_drift"
PLOT_DIR  = Path(__file__).parent / "data" / "policy_drift" / "plots"
PLOT_DIR.mkdir(parents=True, exist_ok=True)

OTHER_LANGS = ["de", "fr", "es", "ja"]
ENWIKI_POLICIES = [
    "Wikipedia:Ownership of content",
    "Wikipedia:Banning policy",
    "Wikipedia:Policies and guidelines",
    "Wikipedia:Proposed deletion of biographies of living people",
    "Wikipedia:Copyright violations",
    "Wikipedia:Clean start",
    "Wikipedia:Biographies of living persons",
    "Wikipedia:Volunteer Response Team",
    "Wikipedia:Attack page",
    "Wikipedia:Arbitration Committee/Conflict of interest reports",
]

SHORT = {
    "Wikipedia:Ownership of content":                                    "Ownership",
    "Wikipedia:Banning policy":                                          "Banning",
    "Wikipedia:Policies and guidelines":                                 "Policies & guidelines",
    "Wikipedia:Proposed deletion of biographies of living people":       "Proposed del. BLP",
    "Wikipedia:Copyright violations":                                    "Copyright violations",
    "Wikipedia:Clean start":                                             "Clean start",
    "Wikipedia:Biographies of living persons":                           "BLP",
    "Wikipedia:Volunteer Response Team":                                 "VRT",
    "Wikipedia:Attack page":                                             "Attack page",
    "Wikipedia:Arbitration Committee/Conflict of interest reports":      "ArbCom/COI",
}

_SSL_CTX = ssl.create_default_context(cafile=certifi.where())
UA = "WikimediaAnalysis/1.0 (personal research project; https://github.com/lgelauff/wikimedia-analysis)"
RATE_DELAY = 1.0


# ---------------------------------------------------------------------------
# API helpers (duplicated from policy_drift to keep this script self-contained)
# ---------------------------------------------------------------------------

def _api_get(wiki: str, params: dict) -> dict:
    url = f"https://{wiki}.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(5):
        time.sleep(RATE_DELAY * (2 ** attempt) if attempt else RATE_DELAY)
        try:
            with urllib.request.urlopen(req, timeout=30, context=_SSL_CTX) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(30 * (2 ** attempt))
            else:
                raise
    raise RuntimeError(f"Failed: {url}")


def get_langlinks(enwiki_title: str, langs: list[str]) -> dict[str, str]:
    """Return {lang: title} for the given enwiki page across requested languages."""
    # Fetch ALL langlinks and filter locally to avoid pipe encoding issues
    data = _api_get("en.wikipedia", {
        "action": "query", "titles": enwiki_title,
        "prop": "langlinks", "lllimit": "max",
        "format": "json", "formatversion": "2", "redirects": "1",
    })
    pages = data.get("query", {}).get("pages", [])
    if not pages:
        return {}
    lang_set = set(langs)
    result = {}
    for ll in pages[0].get("langlinks", []):
        if ll["lang"] in lang_set:
            result[ll["lang"]] = ll["title"]
    return result


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

def load_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["year"] = df["year"].astype(int)
    for col in ["cosine_vs_prev", "containment_old_in_new", "containment_new_in_old", "word_count"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def load_all(wiki: str = "en.wikipedia") -> dict[str, pd.DataFrame]:
    """Load all CSVs for a given wiki. Returns {title: df}."""
    pattern = DRIFT_DIR / f"{re.sub(r'[^\w]+', '_', wiki)}__*.csv"
    result = {}
    for f in sorted(glob.glob(str(pattern))):
        df = load_csv(Path(f))
        if len(df) == 0:
            continue
        title = df["title"].iloc[0]
        result[title] = df
    return result


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

METRICS = [
    ("word_count",             "Word count",                    False),
    ("cosine_vs_prev",         "Cosine similarity (vs prev yr)",True),
    ("containment_old_in_new", "Old content retained in new",   True),
    ("containment_new_in_old", "New content already in old",    True),
]


def plot_metric(metric: str, ylabel: str, is_ratio: bool,
                wiki_data: dict[str, dict[str, pd.DataFrame]],
                suffix: str = "") -> Path:
    """
    One graph: X=year, Y=metric. One line per policy (enwiki).
    If wiki_data has multiple wikis, use separate subplots per wiki.
    """
    wikis = list(wiki_data.keys())
    n = len(wikis)
    fig, axes = plt.subplots(1, n, figsize=(7 * n, 5), sharey=True)
    if n == 1:
        axes = [axes]

    all_titles = sorted({t for w in wiki_data.values() for t in w})
    colors = cm.tab10(np.linspace(0, 1, len(all_titles)))
    color_map = {t: colors[i] for i, t in enumerate(all_titles)}

    for ax, wiki in zip(axes, wikis):
        policy_dfs = wiki_data[wiki]
        for title, df in sorted(policy_dfs.items()):
            series = df[["year", metric]].dropna()
            if series.empty:
                continue
            label = SHORT.get(title, title.split(":")[-1][:30])
            ax.plot(series["year"], series[metric],
                    marker="o", markersize=3, linewidth=1.5,
                    color=color_map.get(title, "grey"),
                    label=label, alpha=0.85)
        ax.set_title(wiki, fontsize=11)
        ax.set_xlabel("Year")
        if is_ratio:
            ax.set_ylim(0, 1.05)
        ax.grid(axis="y", alpha=0.3)
        ax.tick_params(axis="x", rotation=45)

    axes[0].set_ylabel(ylabel)

    # Single legend outside
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center",
               ncol=3, fontsize=8, bbox_to_anchor=(0.5, -0.18))

    fig.suptitle(ylabel, fontsize=13, fontweight="bold", y=1.01)
    fig.tight_layout()

    slug = re.sub(r"\W+", "_", metric).strip("_")
    out = PLOT_DIR / f"{slug}{suffix}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out.name}")
    return out


def make_plots(wiki_data: dict[str, dict[str, pd.DataFrame]], suffix: str = "") -> None:
    print("\nGenerating plots …")
    for metric, ylabel, is_ratio in METRICS:
        plot_metric(metric, ylabel, is_ratio, wiki_data, suffix)


# ---------------------------------------------------------------------------
# Fetch other-language data
# ---------------------------------------------------------------------------

def fetch_other_langs(langs: list[str]) -> None:
    """For each enwiki policy, get interwiki titles and run policy_drift."""
    import subprocess, sys

    for en_title in ENWIKI_POLICIES:
        print(f"\nLanglinks for: {en_title}")
        ll = get_langlinks(en_title, langs)
        for lang, title in ll.items():
            wiki = f"{lang}.wikipedia"
            slug = re.sub(r"[^\w]+", "_", f"{wiki}__{title}").strip("_")[:100]
            out_csv = DRIFT_DIR / f"{slug}.csv"
            if out_csv.exists():
                print(f"  [{lang}] already done: {title}")
                continue
            print(f"  [{lang}] fetching: {title}")
            result = subprocess.run(
                ["uv", "run", "--script",
                 str(Path(__file__).parent / "policy_drift.py"),
                 "--wiki", wiki, "--title", title],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                print(f"    ERROR: {result.stderr[-200:]}")
            else:
                print(f"    OK")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--langs", action="store_true",
                        help="Fetch + plot de/fr/es/ja too")
    args = parser.parse_args()

    if args.langs:
        fetch_other_langs(OTHER_LANGS)

    # enwiki only plot
    en_data = load_all("en.wikipedia")
    print(f"\nLoaded {len(en_data)} enwiki policies")
    make_plots({"en.wikipedia": en_data}, suffix="_en")

    if args.langs:
        # Combined plot: one subplot per wiki
        combined: dict[str, dict[str, pd.DataFrame]] = {"en.wikipedia": en_data}
        for lang in OTHER_LANGS:
            wiki = f"{lang}.wikipedia"
            data = load_all(wiki)
            if data:
                combined[wiki] = data
                print(f"Loaded {len(data)} policies for {wiki}")
        make_plots(combined, suffix="_all")


if __name__ == "__main__":
    main()
