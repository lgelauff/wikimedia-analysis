# Wikimania Deadlines Dataset — Final Design

## Purpose

A structured dataset of organisational deadlines for every Wikimania edition
(2005–2026), covering four process tracks: conference dates, program,
scholarship, and registration.

---

## Output Files

| File | Description |
|------|-------------|
| `editions/wikimania_YYYY.json` | One file per edition (22 files) |
| `wikimania_all.json` | All editions merged into one array |
| `deadline_availability.png` | Coverage heatmap |

---

## JSON Schema

Each edition file has this top-level shape:

```json
{
  "year": 2017,
  "city": "Montreal",
  "buckets": {
    "conference": { "deadlines": [...] },
    "program":    { "deadlines": [...] },
    "scholarship": { "deadlines": [...] },
    "registration": { "deadlines": [...] }
  }
}
```

Each deadline entry:

```json
{
  "type": "program_submission_open",
  "date": "2017-02-02",
  "date_confidence": "confirmed",
  "notes": "Parsed from: '...'",
  "sources": [
    {
      "url": "https://...",
      "source_type": "conference_site",
      "verified": true,
      "verified_date": "2017-02-02",
      "verified_text_found": "Call for proposals opens: February 2, 2017"
    }
  ]
}
```

### Deadline Types

**Conference**
- `conference_start` — first day of the event
- `conference_end` — last day of the event

**Program**
- `program_submission_open` — call for submissions opens
- `program_submission_deadline` — original proposal deadline
- `program_submission_deadline_extended` — extended deadline if pushed back
- `program_acceptance_notification` — when accepted speakers are notified
- `program_speaker_confirmation` — deadline for speakers to confirm
- `program_schedule_published` — full schedule goes public

**Scholarship**
- `scholarship_applications_open` — scholarship window opens
- `scholarship_deadline` — original scholarship deadline
- `scholarship_deadline_extended` — extended scholarship deadline
- `scholarship_results_notification` — decisions sent out
- `scholarship_acceptance_confirmation` — awardees confirm

**Registration**
- `registration_open` — public registration opens
- `registration_earlybird_deadline` — end of early-bird pricing
- `registration_deadline` — last day for online registration
- `registration_late_deadline` — on-site / late registration cutoff

### `date_confidence` Values

| Value | Meaning |
|-------|---------|
| `confirmed` | Exact date explicitly stated (≤1-day accuracy) |
| `approximate` | Month-only or inferred from context (≤7-day range) |
| `not_applicable` | This deadline did not exist for this edition |
| `unknown` | Searched; no conclusion found |

### `source_type` Values

| Value | Meaning |
|-------|---------|
| `conference_site` | `wikimaniaNNNN.wikimedia.org` or `wikimania.wikimedia.org` |
| `meta_wiki` | `meta.wikimedia.org` |
| `mailing_list` | `lists.wikimedia.org/pipermail/` archive |
| `other` | External source (blog, Diff, Eventyay, etc.) |

---

## Data Collection Pipeline

### Phase 1 — Edition scaffolding (`fetch_editions.py`)
Creates the 22 per-edition JSON files with conference dates from Meta-Wiki.

### Phase 2a — Wiki page scraping (`fetch_program.py`, `fetch_scholarships.py`, `fetch_registration.py`)
For each edition, fetches the relevant wiki page via the Wikimedia API
(`action=query&prop=revisions&rvprop=content`) and applies keyword-based
line classification to extract deadline dates.

### Phase 2b — Revision history (`fetch_revision_history.py`)
For the same wiki pages, fetches the revision that existed ~3 months before
the conference (`rvdir=older&rvstart=YYYY-05-01`). Uses `action=parse` for
rendered HTML to avoid template-parsing issues. This recovers dates that were
later overwritten with "submissions closed" text.

### Phase 2c — Email archives (`fetch_email_deadlines.py`)
Downloads monthly mbox archives from `lists.wikimedia.org/pipermail/`
(wikimania-l and wikimedia-l), covering 9 months before each conference.
Filters messages by deadline-related keywords, then batches them to
**Mistral** (`mistral-large-latest`) for structured date extraction.

### Phase 2d — Curated notes ingestion
Dates from a manually-compiled reference CSV are ingested as `approximate`
(month-only) or `confirmed` (day-level) entries, flagged "Pending quality
check" in the notes field.

### Phase 3 — Blind validation (`validate_deadlines.py`)
For each unverified entry:
1. Fetches the source page/archive content (without revealing the stored date).
2. Sends content + deadline type to **Mistral** for independent extraction.
3. Compares Mistral's answer to the stored date.
4. Marks `verified=true/false` and records `verified_text_found`.

### Phase 4 — Export
`wikimania_all.json` — flat combined file.
CSV export TBD (Phase 4).

---

## Merge Rules

When multiple sources provide dates for the same deadline type, the pipeline
applies these precedence rules (never overwrites a higher-confidence entry):

1. `not_applicable` — never overwritten
2. `confirmed` + date present — never overwritten
3. `approximate` → upgraded to `confirmed` if a confirmed source is found
4. `unknown` / missing — filled by any source

---

## Coverage (as of March 2026)

| Bucket | Coverage |
|--------|----------|
| Conference dates | 100% |
| Program | 79% |
| Scholarship | 59% |
| Registration | 51% |

Known gaps:
- **2022–2025 program/scholarship**: moved off wiki to external platforms
  (Pretalx, Eventyay); email archives also unavailable post-2019.
- **Registration 2005–2010**: early editions had minimal online registration
  infrastructure; pages are sparse or absent.
- **Speaker confirmation / schedule published**: rarely mentioned explicitly
  in wiki pages or email archives.

---

## Technical Notes

- All wiki fetches use the Wikimedia API (never HTML scraping).
- User-Agent: `WikimaniaDeadlinesResearch/1.0 (https://github.com/lgelauff/wikimedia-analysis; research project)`
- Downloaded content cached in `tmp/` (excluded from git via `.gitignore`).
- Past-edition cache is treated as immutable; current/future editions
  re-fetched after 7 days.
- Mistral API key loaded from `.env` file (excluded from git).
