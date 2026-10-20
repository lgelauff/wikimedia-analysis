# Wikimania session overview

Session-level companion to `wikimania_deadlines/` (when) and `wikimania_attendees/` (who): **what ran, and what media exists for it** — recordings, delivered programme, slide decks, posters.

_Generated 2026-10-20. **JSON is canonical** (house convention); no CSVs in this folder._

## How these files were produced (provenance)

- **Sources** (all public):
  - **Wikimedia Commons** – `action=query` category members + `prop=imageinfo` (`videoinfo` durations); slide decks via `list=search` `wikimania filetype:pdf`; posters via the per-edition poster categories.
  - **eventyay / pretalx public schedule JSON** – `wikimedia.eventyay.com/wm/wikimaniaYYYY/schedule/export/schedule.json` for the **delivered programme, 2023–2026** (talks, speakers, room, track).
  - **`wikimania.wikimedia.org` `YYYY:Videos`** curated playlist pages (2011–2022) — the recorded-session index.
  - **Per-edition wikis** (`wikimaniaYYYY.wikimedia.org`) `File:` namespaces — locally hosted decks.
- **Method:** harvest → normalise titles → deduplicate within/across platforms (title + near-identical duration) → classify recording type → match slide decks by title stem → join the delivered programme → count. Deterministic and snapshot-cached (byte-identical re-runs).
- **Pipeline scripts** (private repo): `stage_commons.py`, `stage_youtube.py`, `stage_archive.py`, `stage_usage.py`, `stage_compile.py`, `stage_dedup.py`, `parse_videos_pages.py`, `parse_eventyay.py`, `parse_eventyay_full.py`, `stage_slides.py`, `match_slides.py`, `poster_inventory.py`, `make_session_set.py`, `yearly_stats.py`, `identified_sessions.py`.
- These JSON files are a **direct projection** of the companion repository (`lgelauff/schroedinger1000 → wikimania-recordings/`), kept in sync; the small table builder that emits them is not part of the numbered pipeline.

## Files & schema (JSON)

- **`yearly_sessions.json`** — `{meta, years:[{year, identified_sessions, with_recording, with_slide, with_both, posters, unrecorded_nonposter, poster_no_media}], totals}`. Partition identity: `identified_sessions = with_recording + with_slide − with_both + unrecorded_nonposter + poster_no_media`; `posters` is an **overlapping flag**, not part of the sum.
- **`yearly_stats.json`** — `{meta, years:[{year, records, recorded_sessions, rec_hours, session_hours, full_day_h, delivered, speakers, slides, missing_duration}], totals}`. `recorded_sessions` = distinct *recorded* sessions (by `session_key`), **not** the cross-source union (that is `yearly_sessions.identified_sessions`).
- **`posters_by_year.json`** — `{meta, years:[{year, files, pdf, image, other}]}`.
- **`wikimania_org_sessions.json`** — `{meta, sessions:[{year, commons_file, session_title, program_page, speakers, track, slides_link, in_dataset}]}`; `speakers` = names (+ roles/affiliations where the page gave them), `track` = the session track/label only, `slides_link` = a direct deck link when the page supplied one.

## Per-year

| Year | Records | Recorded sessions | Identified sessions | with recording | with slide | Delivered | Slides | Posters (PDF/all) | Hours rec/session |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2005 | 3 | 3 | 15 | 3 | 12 | — | 13 | — | 2/2 |
| 2006 | 56 | 56 | 60 | 56 | 4 | — | 5 | — | 2/2 |
| 2007 | — | — | 20 | 0 | 5 | — | 6 | — | —/— |
| 2008 | 83 | 82 | 89 | 82 | 6 | — | 6 | — | 1/1 |
| 2009 | 85 | 85 | 129 | 85 | 23 | — | 25 | — | 61/61 |
| 2010 | 3 | 3 | 61 | 3 | 38 | — | 41 | 1/1 | 0/0 |
| 2011 | 204 | 201 | 232 | 201 | 39 | — | 41 | — | 110/109 |
| 2012 | 232 | 229 | 283 | 229 | 65 | — | 70 | — | 92/91 |
| 2013 | 392 | 390 | 439 | 390 | 68 | — | 84 | — | 101/100 |
| 2014 | 263 | 261 | 333 | 261 | 89 | — | 100 | 8/11 | 101/100 |
| 2015 | 93 | 84 | 176 | 84 | 95 | — | 116 | — | 52/50 |
| 2016 | 101 | 98 | 159 | 98 | 53 | — | 77 | 7/65 | 40/38 |
| 2017 | 105 | 102 | 229 | 102 | 134 | — | 153 | 21/48 | 39/37 |
| 2018 | 101 | 98 | 202 | 98 | 96 | — | 120 | 34/93 | 23/21 |
| 2019 | 191 | 177 | 356 | 177 | 180 | — | 204 | 42/116 | 128/126 |
| 2021 | 213 | 208 | 240 | 208 | 58 | — | 67 | — | 95/89 |
| 2022 | 165 | 157 | 178 | 157 | 36 | — | 47 | — | 146/62 |
| 2023 | 762 | 584 | 731 | 584 | 225 | 301 | 235 | 33/209 | 490/327 |
| 2024 | 264 | 253 | 397 | 253 | 89 | 212 | 107 | 35/83 | 373/123 |
| 2025 | 335 | 305 | 449 | 305 | 109 | 195 | 146 | 78/367 | 313/309 |
| 2026 | 256 | 252 | 492 | 252 | 139 | 291 | 176 | 98/334 | 451/242 |
| 2027 | 3 | 3 | 5 | 3 | 2 | — | 5 | — | 2/0 |
| **Σ table** | **3910** | **3631** | **5275** | — | — | **999** | **1844** | **1327** | **2622/1890** |

**Totals reconciliation.** Per-year rows cover known conference year only. Dataset-wide totals add what rows cannot: 4015 records (+105 no-year), 1872 Wikimania-related slide PDFs (+28 un-year'd), ≈2,642 recording-hours (+≈20 un-year'd), 1947 poster files (+620 un-year'd).

- **Verbatim typo, kept on purpose:** two 2019 rows read `Libraties Ideation sessions` — the source page's own typo (its link target is `2019:Libraries`). Do not "fix" it silently.

## Caveats

- **2020 did not happen** (cancelled) — excluded; 2020-dated files are misfiled.
- **2027** counts are **not sessions**: 3 items are scholarship-orientation recordings and the Santiago announcement, for an edition not yet held. Treat as pre-event material.
- **2010** has almost no recordings — a *recording gap*, not a missing edition (a poster category exists).
- Matching is **title-based → a lower bound**; `identified_sessions` is a **heuristic union**, pending human review.
- **Posters are not "missing recordings"** — judged by poster artifacts (a rare live-streamed 2026 hall is recorded).
- **Delivered** programme exists only for **2023–2026**; pre-2023 schedules are being reconstructed.

## Curated index accuracy (`in_dataset`)

**1,084 of 1,085** curated sessions are in the recorded dataset. The one exception is `File:Podcast PhD thesis Imagine a world Wikimania 2021.ogg` — it **exists on Commons** (page id 108369907) but was **missed by the v1.8.0 harvest** (not in the dataset, not in the exclusion list). A known harvest miss to add next build, not a deliberate exclusion.
