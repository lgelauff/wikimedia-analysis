# Historical core network (2005–2026) — seeded from the 2026 baseline

The policy/guideline **core** of six Wikipedia editions as an annual network, 2005–2026.
Generated from ToolsDB by [`../../../net/export_history.py`](../../../net/export_history.py)
(M4 Phase 1). Also available as a public download:
`https://wikimedia-policies.toolforge.org/policy-net/`.

This is the **2026 core walked back through time**: 2026 is the baseline (the locked core,
identical to [`../nodes.csv`](../nodes.csv) / [`../edges.csv`](../edges.csv)); 2005–2025 are
reconstructed from it.

## Files

`nodes.csv` — one row per node per year.
| column | meaning |
|---|---|
| wiki, page_id, year, title, namespace | identity (year = state at 1 Jan) |
| is_redirect, wikidata_qid | flags |
| confidence | `core`, or `candidate` (see below) |
| admitted_via | status_template / inherited / demoted |
| status_tier | policy/guideline/essay/… where detected |

`links.csv` — core→core links, **both endpoints `core` that year** (`wiki, year, from_page,
to_ns, to_title, to_page, to_admitted`). Matches the 2026 `edges.csv` core wikilinks.

`build_run.csv` — provenance (`git_commit`, thresholds) per wiki-year.

## What `candidate` means (it differs by era — read this)

- **Historical years (2005–2025):** `candidate` = the page existed that year but carried an
  essay/proposed/historical banner, i.e. a genuine **per-year demotion**. These rows are kept —
  they are signal (when was a page *not yet* core).
- **2026 baseline:** kept **`core`-only**. The current build's large `candidate` frontier (the
  ~34k undiscovered suspects) is *not* a demotion and is **excluded** here, so `candidate` means
  one thing across the file.

## Provisional — caveats (M4 Phase 1)

1. **Survivorship bias.** Seeded from the 2026 core and walked back, so it contains only pages
   that survived to 2026. Pages that were core historically but later deleted/merged/renamed are
   missing — early-year core counts **undercount** the true historical core. (Phase 2 fill-back,
   not yet done, addresses this.)
2. **Regex-banner approximation.** `is_core` demotion is detected by regex on raw wikitext; 20
   years of template renames/aliases make this a first approximation.
3. **Inference-gated (M5).** No density/centrality/trend **claim** ships off these series until
   M5 detrending + size-normalization. The series is data, not yet a finding.

Regenerate: `python net/export_history.py` on Toolforge (needs `~/replica.my.cnf`).
License: Wikipedia-derived, **CC BY-SA** (attribution via wiki + page_id + revision).
