# Wikimania Deadlines — Executed Plan

This document describes the data collection and validation pipeline as it was actually built and run, including deviations from the original plan and lessons learned.

---

## Objective

Collect structured data on organisational deadlines for every Wikimania edition (2005–2026), covering four buckets: **Conference dates**, **Program**, **Scholarship**, and **Registration**. All deadlines must be traceable to a verified source.

---

## Scope

- **Editions**: Wikimania 2005 through 2026 (21 editions; 2020 cancelled)
- **Out of scope**: volunteer applications, conference announcement dates, call for host city proposals

---

## Output files

| File | Description |
|------|-------------|
| `editions/wikimania_YYYY.json` | One JSON file per edition |
| `deadline_availability.png` | Heatmap of data coverage across all editions and deadline types |
| `deadline_table.png` | Compact date table (DD/MM format) with duration columns |
| `deadline_table.csv` | Same table exported as CSV |

---

## JSON schema

Each edition JSON contains:
- Edition metadata: year, location, meta_wiki_url, conference_site_url
- Four buckets: `conference`, `program`, `scholarship`, `registration`
- Each bucket contains a list of deadline entries with:
  - `type` — deadline identifier
  - `date` — ISO 8601 date string (YYYY-MM-DD or YYYY-MM for month-only)
  - `date_confidence` — `confirmed`, `approximate`, `not_applicable`, or `unknown`
  - `notes` — provenance notes and original quoted text
  - `sources` — list of source records with URL, source_type, verified flag, and verified text found

### `date_confidence` values
- `confirmed` — exact date found verbatim in a source
- `approximate` — inferred or found only in a secondary source
- `not_applicable` — actively confirmed that this deadline did not exist for this edition
- `unknown` — searched but no conclusion reached

---

## Deadline types collected

### Conference
| Type | Description |
|------|-------------|
| `conference_start` | First day of the conference |
| `conference_end` | Last day of the conference |

### Program
| Type | Description |
|------|-------------|
| `program_submission_open` | Call for submissions opens |
| `program_submission_deadline` | Original submission deadline |
| `program_submission_deadline_extended` | Extended deadline (only if announced) |
| `program_acceptance_notification` | First acceptance notifications sent |
| `program_speaker_confirmation` | Deadline for accepted speakers to confirm |
| `program_schedule_published` | Full programme published |

### Scholarship
| Type | Description |
|------|-------------|
| `scholarship_applications_open` | Applications open |
| `scholarship_deadline` | Original application deadline |
| `scholarship_deadline_extended` | Extended deadline (only if announced) |
| `scholarship_results_notification` | First results notifications sent |
| `scholarship_acceptance_confirmation` | Deadline for awardees to confirm |

### Registration
| Type | Description |
|------|-------------|
| `registration_open` | Registration opens |
| `registration_earlybird_deadline` | Early bird rate deadline |
| `registration_deadline_online` | Online registration deadline |
| `registration_deadline_inperson` | In-person / on-site registration deadline |
| `registration_late_deadline` | Late / on-site registration close |

**Note:** `registration_deadline` was originally a single field. During execution it was split into `registration_deadline_online` and `registration_deadline_inperson` to reflect the hybrid nature of post-2020 editions. For editions up to 2019 (in-person only), `registration_deadline_online` is `not_applicable`. For 2021–2022 (virtual only), `registration_deadline_inperson` is `not_applicable`.

---

## Pipeline phases

### Phase 1 — Setup and initial population
- Created `editions/wikimania_YYYY.json` for all editions
- Pre-populated metadata and conference dates from Meta-wiki
- Scripts: `fetch_editions.py`

### Phase 2 — Data collection

#### 2a — Wiki pages
Fetched programme, scholarship, and registration pages from each edition's conference website via the Wikimedia API (`action=parse`, `prop=wikitext`). Used `action=query&prop=revisions` to access historical revisions when the current page showed post-event state only.

- Scripts: `fetch_program.py`, `fetch_scholarships.py`, `fetch_registration.py`
- API rule: always used the Wikimedia API; never scraped HTML directly

#### 2b — Mailing list archives
Downloaded monthly mbox archives from `lists.wikimedia.org/pipermail/wikimania-l/` and `wikimedia-l/` (9 months before conference through conference month). Filtered messages by deadline-related keywords, then sent batches to Mistral for structured date extraction.

- Script: `fetch_email_deadlines.py`
- Coverage: 2006–2021 (2022–2025 archives unavailable — lists migrated away from pipermail)
- SSL fix: `cache.py` updated to use `certifi` for SSL verification

#### 2c — Curated notes
Manually collected dates from a `notes.txt` file for editions where automated extraction was incomplete.

### Phase 3 — Validation

For each deadline entry with `verified=false`:
1. Fetched the source URL content
2. Sent to Mistral **blind** (without the stored date) to independently extract a date
3. Compared:
   - **Match** → `verified=true`
   - **Not found** → left unverified, skipped
   - **Mismatch** → triggered binary search through wiki revision history at offsets of 5, 3, and 1 months before the conference

Binary search logic:
- Bisect confirms stored date → `verified=true`
- Bisect confirms found date → stored date corrected and `verified=true`
- Three-way discrepancy → flagged for human review
- Conference start/end mismatches → noted but not auto-corrected (pre-conf days vary)

Script: `validate_deadlines.py`

**Resumability:** The validator writes the edition JSON after every source processed, and maintains a checkpoint at `/tmp/wikimania_validate_checkpoint.json` to skip completed editions on re-run.

### Phase 3b — Human review of flagged discrepancies

Several entries flagged by the automated validator were reviewed manually:

| Year | Field | Issue | Resolution |
|------|-------|-------|------------|
| 2007 | `scholarship_deadline` | Three-way discrepancy (Apr 1 / Apr 15 / Mar 26) | Kept Apr 1 — confirmed as original deadline by email evidence |
| 2017 | `program_submission_deadline` | Stored Apr 10, bisect found Mar 30, wiki shows May 1 | Corrected to Mar 30 (original); May 1 set as extended |
| 2017 | `program_submission_deadline_extended` | Stored Jun 10 (lightning talks track, not main) | Corrected to May 1 (main track) |
| 2016 | `program_*` | Mixed data from multiple tracks (Critical Issues, Training, Posters) | Rebuilt from wiki pages: CfP open Dec 11 2015, deadline Jan 17 2016, notification Feb 1 2016 |
| 2017 | `scholarship_deadline_extended` | May 6 date was from WMF Board Recruitment email | Set to `not_applicable`; confirmed by three wiki revisions |
| 2017 | `registration_open` | Nov 2016 date was from a Wikimedia Conference (Berlin) email | Reset to unknown |
| 2025 | `scholarship_applications_open` | Dec 8 corrected by bisect was the *close* date, not open | Reverted to Nov 7 (original open date) |
| 2021–2022 | `registration_deadline` | Date was approximate end-of-conference | Corrected to confirmed dates from registration pages |

Extended deadlines equal to the original deadline (same date) were set to `not_applicable` for editions 2005, 2006, 2008, and 2009.

### Phase 4 — Export and visualisation

**Heatmap** (`visualize_deadlines.py`): shows data availability per edition per deadline type using four confidence levels (confirmed / approximate / unknown / not_applicable), with per-column coverage percentages.

**Table** (`make_table.py`): shows actual dates in DD/MM format per edition. Includes computed duration columns:
- **Program "Days open"**: days from `program_submission_open` to last submission deadline (extended if available)
- **Scholarship "Days open"**: days from `scholarship_applications_open` to last scholarship deadline
- **Registration "Days open"**: days from `registration_open` to `registration_deadline_inperson`

Output: `deadline_table.png` and `deadline_table.csv`

---

## Coverage achieved

| Bucket | Coverage |
|--------|----------|
| Conference | 100% |
| Program | 78% |
| Scholarship | 64% |
| Registration | 59% |

---

## Sources used (priority order)

1. **Conference wiki pages** — `wikimaniaYYYY.wikimedia.org` or `wikimania.wikimedia.org/YYYY:*` — accessed via Wikimedia API
2. **Meta-wiki** — `meta.wikimedia.org/wiki/Wikimania_YYYY` — for conference dates and overview
3. **Mailing lists** — `lists.wikimedia.org/pipermail/wikimania-l/` and `wikimedia-l/` — downloaded as mbox, parsed and extracted by Mistral
4. **Wiki revision history** — used for binary search validation and for editions where current page showed only post-event state
5. **Wikimedia Diff blog** — for 2022–2025 editions where mailing lists were unavailable

---

## Known data quality issues

| Issue | Affected editions | Status |
|-------|------------------|--------|
| Early editions (2005–2010) have sparse online records | 2005–2010 | Many fields remain `unknown` |
| Mailing list archives unavailable post-2021 | 2022–2025 | No email-sourced data; wiki-only |
| Some conference websites offline | Pre-2013 | Many mailing list sources cannot be re-fetched |
| 2016 had multiple parallel submission tracks with different timelines | 2016 | Program fields reflect Critical Issues track (main presentations) only |
| Registration deadline split (online vs in-person) retroactively applied | All | Pre-2021 editions have `not_applicable` for online; 2021–2022 for in-person |
