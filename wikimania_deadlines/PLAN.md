# Wikimania Deadlines Data Collection Plan

## Objective

Collect structured data on organizational deadlines for every Wikimania edition (2005–2026),
covering four buckets: **Conference dates**, **Program**, **Scholarship**, and **Registration**.
All deadlines must be traceable to a verified source.

---

## Scope

- **Editions**: Wikimania 2005 through Wikimania 2026 (all editions)
- **Out of scope**: volunteer applications, conference announcement dates, call for host city proposals

---

## Output format

One JSON file per edition (e.g., `wikimania_2019.json`), plus a combined `wikimania_all.json`.
Later: a flattened CSV export derived from the JSON.

### JSON schema (per edition)

```json
{
  "edition": "Wikimania 2019",
  "year": 2019,
  "location": "Stockholm, Sweden",
  "conference_dates": "2019-08-14 to 2019-08-18",
  "buckets": {
    "conference": {
      "deadlines": [
        {
          "type": "conference_start",
          "date": "2019-08-14",
          "date_confidence": "confirmed | approximate | unknown",
          "notes": "",
          "sources": []
        },
        {
          "type": "conference_end",
          "date": "2019-08-18",
          "date_confidence": "confirmed | approximate | unknown",
          "notes": "",
          "sources": []
        }
      ]
    },
    "program": {
      "deadlines": [
        {
          "type": "submission_open",
          "date": "2019-01-15",
          "date_confidence": "confirmed | approximate | unknown",
          "notes": "",
          "sources": [
            {
              "url": "https://meta.wikimedia.org/wiki/...",
              "source_type": "meta_wiki | conference_site | mailing_list | wikipedia | blog | other",
              "verified": false,
              "verified_date": null,
              "verified_text_found": null
            }
          ]
        }
      ]
    },
    "scholarship": { "deadlines": [] },
    "registration": { "deadlines": [] }
  }
}
```

`date_confidence` values:
- `confirmed` — exact date found verbatim in a verified source
- `approximate` — inferred (e.g., "early March") or only found in a secondary source
- `not_applicable` — actively confirmed that this deadline did not exist for this edition
  (e.g., no early bird tier was offered; set `date` to `null` and note the source that confirms absence)
- `unknown` — searched but could not determine whether deadline existed; no conclusion reached

---

## Deadline types to collect (exhaustive list)

### Conference bucket
| ID | Deadline type | Notes |
|----|--------------|-------|
| `conference_start` | First day of the conference | |
| `conference_end` | Last day of the conference | |

### Program bucket
| ID | Deadline type | Notes |
|----|--------------|-------|
| `program_submission_open` | Call for submissions opens | |
| `program_submission_deadline` | Submission deadline (original announced date) | |
| `program_submission_deadline_extended` | Extended submission deadline | Only if an extension was announced |
| `program_acceptance_notification` | First acceptance/rejection notifications sent | Capture first wave only; later batches not tracked |
| `program_speaker_confirmation` | Deadline for accepted speakers to confirm | |
| `program_schedule_published` | Full program/schedule published | |

### Scholarship bucket
| ID | Deadline type | Notes |
|----|--------------|-------|
| `scholarship_applications_open` | Scholarship applications open | |
| `scholarship_deadline` | Application deadline (original) | |
| `scholarship_deadline_extended` | Extended application deadline | Only if announced |
| `scholarship_results_notification` | First scholarship results notifications sent | Capture first wave only; later batches not tracked |
| `scholarship_acceptance_confirmation` | Deadline for awardees to confirm acceptance | |

### Registration bucket
| ID | Deadline type | Notes |
|----|--------------|-------|
| `registration_open` | Registration opens to the public | |
| `registration_earlybird_deadline` | Early bird rate deadline | |
| `registration_deadline` | General registration deadline | |
| `registration_late_deadline` | Late / on-site registration close | |

---

## Sources (priority order)

### API usage rule
**Always use the Wikimedia API** when fetching data from any Wikimedia website. Never scrape HTML pages directly.
- Meta-wiki API: `https://meta.wikimedia.org/w/api.php`
- English Wikipedia API: `https://en.wikipedia.org/w/api.php`
- Get wikitext: `action=query&titles=PAGE_NAME&prop=revisions&rvprop=content&format=json`
- Parse a page: `action=parse&page=PAGE_NAME&prop=wikitext&format=json`

### Tier 1 — Primary, versioned, most reliable
1. **Wikimedia Meta-wiki** (`meta.wikimedia.org/wiki/Wikimania_YYYY`)
   - Main coordination hub for each edition
   - Revision history allows checking when information was posted
   - Often has sub-pages: `.../Scholarships`, `.../Program`, `.../Registration`
   - Access via API: `https://meta.wikimedia.org/w/api.php?action=query&titles=Wikimania_YYYY&prop=revisions&rvprop=content&format=json`

2. **Individual conference websites**
   - Pattern varies by year: `wikimaniaYYYY.wikimedia.org`, `wikimania.wikimedia.org/YYYY`, or custom domains
   - These are wiki-based — access via their respective API endpoints
   - May have gone offline → see Wayback Machine note

### Tier 2 — Announcement channels
3. **Wikimedia mailing lists** (via `lists.wikimedia.org`)
   - `wikimania-l` — Wikimania-specific, highest priority for deadline announcements
   - `wikimedia-l` — General Wikimedia, used for major announcements
   - `foundation-l` — Older list, relevant for 2005–2012 editions
   - Search via: list archives at `lists.wikimedia.org/pipermail/wikimania-l/`

4. **Wikimedia blog** (`blog.wikimedia.org`)
   - Deadline announcements are sometimes posted here, especially for scholarships

### Tier 3 — Encyclopedic / cross-reference
5. **Wikipedia articles on Wikimania**
   - English: `en.wikipedia.org/wiki/Wikimania`
   - Non-English: especially useful for host-country languages — may contain deadline tables
     or link to local coverage with additional detail
   - Check language versions for host countries: e.g., Arabic (2018 Cape Town was English;
     2022 was online; check each year's host country)

### Tier 4 — Deferred
6. **Internet Archive / Wayback Machine** — to recover offline conference sites
   - Defer until Tier 1–3 are exhausted for a given edition

---

## Collection instructions (step by step)

### Phase 1 — Setup
- [ ] Create the `wikimania_deadlines/` directory with one JSON file per edition
- [ ] Pre-populate each file with edition metadata (year, location, conference dates) from a
      reliable list of all Wikimania editions — this itself should be sourced and noted

### Phase 2 — Data collection (per edition)
For each edition, in this order:

1. Go to `meta.wikimedia.org/wiki/Wikimania_YYYY` and its sub-pages
2. Record every deadline found, with the exact URL and the text as found on the page
3. Check the conference website (if known/live)
4. Search mailing list archives for that year's edition (search: `wikimania YYYY deadline`)
5. Check Wikimedia blog for that year
6. Check Wikipedia article for any tabular data

### Phase 3 — Validation (see below)

### Phase 4 — CSV export
Flatten JSON into rows: one row per deadline per edition.

---

## Validation plan

### Goal
Every deadline entry with `verified: false` must be independently confirmed before the
dataset is considered complete. Verification means: a human or agent visits the URL,
finds the specific text on the page, and records what was found.

### Validation agent instructions (for each source record)

**Critical: the validation agent must work blind.** It receives only the `url` and the
`deadline_type` label — it does NOT receive the `expected_date` collected in Phase 2.
This ensures the two passes are genuinely independent.

Given:
- `url` — the source URL
- `deadline_type` — what we're looking for (e.g., `scholarship_deadline`)

Steps:
1. Fetch the URL
2. Locate the section of the page relevant to `deadline_type` (e.g., the scholarships section)
3. Independently determine what date (if any) is stated for that deadline type
4. Record:
   - Whether the page loaded successfully
   - The date found (or `null` if none)
   - The exact surrounding sentence or table row where the date appears
   - The date the verification was run
5. Compare the independently found date against `expected_date` from Phase 2:
   - Match → set `verified: true`, fill `verified_text_found` with the quoted context
   - Mismatch → set `verified: false`, record both dates and flag for human review
   - Not found → set `verified: false`, note that no relevant date was found in that section

For `not_applicable` entries: the agent must read the full relevant section and explicitly
confirm no deadline of that type was mentioned — not just that the date string was absent.

### Confidence rules after validation
- A deadline is `confirmed` only if the blind validation matches at a Tier 1 or Tier 2 source
- A deadline from Wikipedia or blog only rises to `confirmed` if corroborated by a Tier 1/2 source
- Mismatches and unverifiable deadlines are flagged in the CSV for human review
- Unresolvable deadlines remain `approximate` or `unknown`

---

## Known challenges

| Challenge | Mitigation |
|-----------|-----------|
| Early editions (2005–2009) have sparse online records | Accept `unknown` more liberally; note in dataset |
| Conference websites go offline | Wayback Machine (Phase 4) |
| Extended deadlines may overwrite originals on wiki pages | Check page revision history for original date |
| Non-English sources | Prioritize host-country Wikipedia language edition |
| Mailing list archives are flat text — hard to search | Use year + keyword filters; accept lower coverage |
