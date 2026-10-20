# Wikimania session overview

Session-level companion to `wikimania_deadlines/` (when) and `wikimania_attendees/` (who): **what ran, and what media exists for it** — recordings, delivered programme, slide decks, posters.

_Generated 2026-10-20._

## How these files were produced (provenance)

- **Sources** (all public):
  - **Wikimedia Commons** – `action=query` category members + `prop=imageinfo` (durations via `videoinfo`); slide decks via `list=search` `wikimania filetype:pdf`; posters via the per-edition poster categories.
  - **eventyay / pretalx public schedule JSON** – `wikimedia.eventyay.com/wm/wikimaniaYYYY/schedule/export/schedule.json` for the **delivered programme, 2023–2026** (talks, speakers, room, track).
  - **`wikimania.wikimedia.org` `YYYY:Videos`** curated playlist pages (2011–2022 subset) — the recorded-session index.
  - **Per-edition wikis** (`wikimaniaYYYY.wikimedia.org`) `File:` namespaces — for locally hosted decks.
- **Method:** harvest → normalise titles → deduplicate within/across platforms (title + near-identical duration) → classify recording type → match slide decks by title stem → join the delivered programme → count. Deterministic and snapshot-cached, so re-runs are byte-identical.
- **Scripts** (pipeline names): `stage_commons.py`, `stage_youtube.py`, `stage_archive.py`, `stage_usage.py`, `stage_compile.py`, `stage_dedupe.py`, `parse_videos_pages.py`, `parse_eventyay.py`, `parse_eventyay_full.py`, `stage_slides.py`, `match_slides.py`, `poster_inventory.py`, `make_session_set.py`, `yearly_stats.py`, `identified_sessions.py`, `make_session_overview.py`.
- The full pipeline **with evidence and a decision log** lives in a companion repository (`lgelauff/schroedinger1000 → wikimania-recordings/`), private at time of writing; the four CSVs here are a direct projection of it. Ask @lgelauff for access, or re-derive from the public sources above.

## Column definitions

**`yearly_stats.csv`**
- `records` — platform records (one per media file/page; a session can have several).
- `recorded_sessions` — distinct **recorded** sessions (deduped by `session_key`). This is *not* the cross-source union (that is `yearly_sessions.identified_sessions`).
- `rec_hours` — runtime of all media with a known duration; `session_hours` — single-session recordings only; `full_day_h` — full-day room streams.
- `delivered` — sessions on the official programme (eventyay, **2023–2026 only**).
- `speakers` — speaker-edition records from eventyay (same years).
- `slides` — Commons slide PDFs dated to that year.
- `missing_duration` — records with no known duration (mostly Internet Archive items).

**`yearly_sessions.csv`**
- `identified_sessions` — distinct sessions nameable from *any* source (recording, delivered programme, or slide deck), union-merged by title.
- `with_recording` / `with_slide` / `with_both` — has a recording / a slide deck / both.
- `posters` — poster sessions (**flag that overlaps** the columns above: a poster with a deck counts in both).
- `unrecorded_nonposter` — real talks with no recording and no slide.
- `poster_no_media` — poster sessions with no recording or slide (expected — posters are rarely recorded).
- **These partition the total:** `identified_sessions = with_recording + with_slide − with_both + unrecorded_nonposter + poster_no_media`. (`posters` is a cross-cutting flag, not part of the sum.)

**`posters_by_year.csv`** — `files` = poster files (PDFs + photos), split into `pdf` / `image` / `other`.
**`wikimania_org_sessions.csv`** — the curated index: `year`, `commons_file`, `session_title`, `program_page`, `speakers` (names only), `track` (session track/label), `in_dataset`.

## Per-year

| Year | Records | Recorded sessions | Identified sessions | with recording | with slide | Delivered | Slides | Posters (PDF/all) | Hours rec/session |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2005 | 3 | 3 | 15 | 3 | 12 | — | 13 | — | 2/2 |
| 2006 | 56 | 56 | 60 | 56 | 4 | — | 5 | — | 2/2 |
| 2007 | — | — | 20 | 0 | 5 | — | — | — | —/— |
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
| **Σ table** | **3910** | **3631** | **5275** | — | — | **999** | **1838** | **1327** | **2622/1890** |

**Totals reconciliation.** The table sums only records with a known conference year. Dataset-wide totals include what the per-year rows cannot: 4015 records (+105 with no conference year), 1872 Wikimania-related slide PDFs (+34 un-year'd), ≈2,642 recording-hours (+≈20 un-year'd), and 1947 poster files (+620 un-year'd). These are listed, not distributed across years.

## Caveats (please don't quote without these)

- **2020 did not happen** (cancelled) — excluded; some 2020-dated files are misfiled.
- **2010** has almost no recordings — a *recording gap*, not a missing edition (a poster category exists).
- Matching is **title-based → a lower bound**; `identified` / `with_slide` will rise with better matching.
- `identified_sessions` is a **heuristic union**, not a certified count — pending human review.
- **Posters are not "missing recordings"**; they are counted from poster PDFs/photos. (A rare live-streamed 2026 poster hall is recorded.)
- **Delivered** programme exists only for **2023–2026**; pre-2023 schedules are being reconstructed.

## Curated index accuracy (the `in_dataset` column)

**1,084 of 1,085** curated sessions are in the recorded dataset. The single exception is `File:Podcast PhD thesis Imagine a world Wikimania 2021.ogg` — it **exists on Commons** (page id 108369907) but was **missed by the v1.8.0 harvest**, so it is neither in the dataset nor in the exclusion list. It is a known **harvest miss**, not a deliberate exclusion; it should be added in the next dataset build.

## Files

- `yearly_stats.csv` · `yearly_sessions.csv` · `posters_by_year.csv` · `wikimania_org_sessions.csv`
