# DRAFT — segment + statement schema (revises #3, knock-ons to #2/#4/#5)

**Status: DRAFT for review.** Not yet applied to the GitHub issues. Resolves two things the
exploration surfaced: (a) segmentation should *label*, not *filter*; (b) statement↔text linkage must
be many-to-many-with-a-primary so it stays exact **and** doesn't explode.

## The key idea: two independent span-layers over one clean text (no join table)

Everything anchors to the **clean text** of a page-revid (#2). Two *separate* annotation layers sit on
top of it, each just a list of spans — they are **not** joined to each other in storage:

```
clean_text(revid)                      ← #2, the substrate (char offsets = code points into NFC text)
 ├─ SEGMENT layer  (#3)   spans that TILE the text, each labelled — "what kind of text is here"
 └─ STATEMENT layer (#4)  spans that point INTO the text — "the norms we read out of it"
```

A statement's segment-type/prominence is found by **which segment contains its primary span**
(spatial lookup, computed on demand) — never stored twice, never an N×M join. This is the whole
anti-explosion move.

## SEGMENT layer (#3) — a labelling pass, not a filter

Segments **tile** the clean text (every char belongs to exactly one segment; minimal overlap). Each:

| field | values |
|---|---|
| `char_start`, `char_end` | span into clean text |
| `segment_type` | rule · procedure · summary · meta · scaffolding |
| `prominence` | **central · supporting · context** — text-level weight (lead/qualifier/etc.), *not* page confidence |
| `candidate` | bool — is this a candidate for statement extraction? |
| `exclusion` | for non-candidates: `deliberation` → deliberation corpus · `chrome` → drop · `signal` → node facet |

- **Nothing is dropped as a filter.** "Exclusion" = `candidate=false` + a logged `exclusion` route.
  The only truly-out categories are structurally identifiable (votes, layout, `{{status}}`/category
  signals). Everything a reader would call policy prose is `candidate=true`, weighted by `prominence`.
- **`prominence` ≠ `confidence`.** Page-level `confidence` (confirmed/candidate, from `core_definition`)
  is untouched and means "is this page policy." `prominence` is within-page weight. Orthogonal.
- Because segments tile, **coverage/inclusion is exact** (fixes the fuzzy-match false positives).

## STATEMENT layer (#4) — one-to-one primary, rare secondary

| field | notes |
|---|---|
| `statement_id` | `<wiki>:<page_id>:<seq>` (unchanged) |
| `primary_char_start`, `primary_char_end` | **the one frontrunner span** — inline, one-to-one (the common case) |
| `statement_orig`, `statement_en`, `deontic_type`, `governance_class` | as before |
| *(derived, not stored)* `segment_type`, `prominence` | = the segment containing the primary span |

`statement_extra_span(statement_id, char_start, char_end)` — a **side table, used only for the rare
multi-span statement** (a rule whose exception lives elsewhere). Empty for ~all statements, so it
stays tiny. This is the "enforced one-to-one with optional secondary" you asked for: every statement
*must* have exactly one primary; secondaries are the exception, not the rule.

## Why it doesn't explode

- Storage is **O(#statements)** — one small row each. No segment×statement pairing is ever materialised.
- Overlapping/duplicate statements (completeness > minimality) are allowed but each is *one* row;
  the raw count is linear, not combinatorial.
- Secondary spans are rare → the side table is near-empty.
- The **deduplicated norm** (#7 cluster) is the *analytical* unit; the raw statements are the audit
  trail. So "many overlapping statements" is cheap to store and collapses for analysis.
- Snapshot ≈ 1,143 pages × ~50–150 statements ≈ 60k–170k rows. All-years stays bounded by
  version-on-change (§2b), not a per-year copy.

## What this really changes (vs the current issues)

- **#2 clean text** — *tiny*: pin "char offsets are Unicode code points into NFC-normalised clean text."
- **#3 segmentation** — *the real change*: `is_core` (binary filter) → **segments tile the text** with
  `segment_type` + `prominence` + `candidate` + `exclusion` route. Adds the structural pre-pass that
  routes votes/chrome/signals out (logged). Nothing dropped un-logged.
- **#4 extraction** — statement carries a **primary span** (+ rare secondary side table) instead of a
  segment foreign key; `prominence` is a *prior* (weight, don't skip low-prominence text). `statement_id`
  and the store are otherwise unchanged.
- **#5 rating** — `prominence` is now a first-class field (the "location/context weight" metric),
  available via the containing segment; the exploration's `salience` column renames to `prominence`.
- **page-level `confidence`** (core_definition) — **unchanged**; explicitly *not* the same axis as prominence.
- **Exploration data** — `salience` → `prominence` rename; otherwise already consistent.

## Still open (your call)
- Is `prominence` a property of the **segment** (location; cheap default) or the **statement** (how
  central the norm is)? Lean: segment default, LLM overrides at statement level when they diverge
  (a throwaway line stating a load-bearing rule).
- 3- vs 4-point `prominence` scale; whether `context` and `scaffolding` collapse.
