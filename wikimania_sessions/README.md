# Wikimania session overview

Session-level companion to `wikimania_deadlines/` (when) and `wikimania_attendees/` (who attended).

Generated **2026-10-18** from the pipeline in `lgelauff/schroedinger1000 → wikimania-recordings/` (the authoritative scripts + full evidence live there).

## What a session is here

- **records** = one per media file/page (a session can have several: Commons + YouTube + IA, or language variants).
- **identified_sessions** = distinct sessions we can name from *any* source — recording, delivered program, or slide deck — merged where titles match.
- **delivered** = on the official program (eventyay API, **2023–2026 only** so far).
- Records and sessions are different aggregates; **don't** compare them 1:1.

## Per-year

| Year | Records | Identified sessions | w/ recording | w/ slide | Delivered (eventyay) | Slides | Posters (PDF/all) | Hours rec/session |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2005 | 3 | 15 | 3 | 12 | — | 13 | — | 2/2 |
| 2006 | 56 | 60 | 56 | 4 | — | 5 | — | 2/2 |
| 2007 | — | 20 | 0 | 5 | — | — | — | —/— |
| 2008 | 83 | 89 | 82 | 6 | — | 6 | — | 1/1 |
| 2009 | 85 | 129 | 85 | 23 | — | 25 | — | 61/61 |
| 2010 | 3 | 61 | 3 | 38 | — | 41 | 1/1 | 0/0 |
| 2011 | 204 | 232 | 201 | 39 | — | 41 | — | 110/109 |
| 2012 | 232 | 283 | 229 | 65 | — | 70 | — | 92/91 |
| 2013 | 392 | 439 | 390 | 68 | — | 84 | — | 101/100 |
| 2014 | 263 | 333 | 261 | 89 | — | 100 | 8/11 | 101/100 |
| 2015 | 93 | 176 | 84 | 95 | — | 116 | — | 52/50 |
| 2016 | 101 | 159 | 98 | 53 | — | 77 | 7/65 | 40/38 |
| 2017 | 105 | 229 | 102 | 134 | — | 153 | 21/48 | 39/37 |
| 2018 | 101 | 202 | 98 | 96 | — | 120 | 34/93 | 23/21 |
| 2019 | 191 | 356 | 177 | 180 | — | 204 | 42/116 | 128/126 |
| 2021 | 213 | 240 | 208 | 58 | — | 67 | — | 95/89 |
| 2022 | 165 | 178 | 157 | 36 | — | 47 | — | 146/62 |
| 2023 | 762 | 731 | 584 | 225 | 301 | 235 | 33/209 | 490/327 |
| 2024 | 264 | 397 | 253 | 89 | 212 | 107 | 35/83 | 373/123 |
| 2025 | 335 | 449 | 305 | 109 | 195 | 146 | 78/367 | 313/309 |
| 2026 | 256 | 492 | 252 | 139 | 291 | 176 | 98/334 | 451/242 |
| 2027 | 3 | 5 | 3 | 2 | — | 5 | — | 2/0 |
| **total** | **3910** | **5275** | **3631** | **1565** | **999** | **1,872** | **~358/all** | **~2,640/~1,890** |

## Caveats (read before quoting)

- **2020 did not happen** (cancelled) — excluded; some 2020-dated files are misfiled.
- **2010** has almost no recordings — a *recording gap*, not a missing edition (a poster category exists).
- **Session/recording matching is title-based** and therefore a **lower bound**; `with_slide` and `identified` will rise with better matching.
- **Posters never have recordings** by default (a live-streamed 2026 poster hall is the rare exception) — they're counted from poster PDFs/photos, not video.
- **Delivered** program data exists only for **2023–2026**; pre-2023 schedules are being reconstructed (wiki pages; Remo/Pheedloop platforms are hardest).
- `identified_sessions` is a heuristic union, **not** a certified count — pending human review.

## Files

- `yearly_sessions.csv` — per year: identified sessions, with_recording, with_slide, with_both, posters, unrecorded_nonposter, poster_no_media
- `yearly_stats.csv` — per year: records, hours (rec vs session), delivered, speakers, slides, missing duration
- `posters_by_year.csv` — poster files per year, PDF vs image
- `wikimania_org_sessions.csv` — the curated 1,085-session index parsed from `wikimania.wikimedia.org` playlists (8 editions)
