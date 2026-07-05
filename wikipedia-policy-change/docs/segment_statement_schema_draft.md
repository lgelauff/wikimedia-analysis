# DRAFT — segment + statement schema (revises #3, knock-ons to #2/#4/#5)

**Status: APPLIED** (this doc is the rationale/worked-example; the canonical schema now lives in
[`atomic_statements_design.md`](atomic_statements_design.md) §4, and the pipeline specs are GitHub
issues #3/#4/#5/#6). Resolves two things the exploration surfaced: (a) segmentation should *label*,
not *filter*; (b) statement identity is **meaning** (entity + occurrences), not text/position — so it
stays exact **and** doesn't explode.

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

## STATEMENT layer (#4) — identity is MEANING; text/position are evidence

**Core principle:** a statement's identity is its **meaning**, carried by a stable `entity_id`.
- **Same meaning ⇒ same statement** (one entity) — regardless of location on the page or minor
  wording. So two same-meaning occurrences collapse to one entity; ambiguous location is moot.
- **Different meaning ⇒ different statement.** If two near-duplicates won't merge, the residual
  difference *is* a distinct atomic claim (not a failure — that's what "atomic" guarantees).
- **Slightly different versions ⇒ overlapping occurrences of one entity** — evidence of one norm.

Text (a `source_quote`) and position are **not** the identity — they are *occurrences*: evidence of
where/when the meaning appears. Two tables:

`statement_entity` — the durable identity:
| field | notes |
|---|---|
| `entity_id` | `<wiki>:<page_id>:<seq>` — stable surrogate; **the** identity |
| `statement_en`, `deontic_type`, `governance_class` | the canonical meaning |
| `first_year`, `last_year`, `status` | lifespan (§2b) |

`statement_occurrence` — the evidence, many-to-one onto an entity:
| field | notes |
|---|---|
| `entity_id` | which meaning this is evidence for |
| `year` (or revid) | snapshot it appears in |
| `source_quote`, `quote_hash` | the verbatim text **as it appears that year** (may vary by typo/rewording) |
| `match_method` | `exact` \| `fuzzy` \| `semantic` — how this occurrence was attributed to the entity |
| *(derived, not stored)* `segment_type`, `prominence`, position | via the segment/text containing the quote |

**Attribution cascade** (how an occurrence is tied to an entity — cheap → expensive):
1. **exact** — the quote is a verbatim substring of the year's clean text → same entity (H2, free, ~90%).
2. **fuzzy** — normalized + small edit-distance/token-ratio ≤ τ_typo → same entity; a typo/whitespace
   fix **extends the run, does not spawn a version.** τ_typo is **conservative** (typo-tolerant, not
   meaning-tolerant — a loose threshold false-merges distinct rules and hides reform).
3. **semantic** (LLM) — the arbiter for the residue: same entity → new **version** (H3), new entity
   (birth), or entity ended (removal/reform). The `entity_id` carries continuity once text drifts.

**Scope of merging** — the one subtlety:
- **within a page/wiki: same meaning → merge** to one entity.
- **across wikis: same meaning → do NOT merge; record equivalence** (that's #7). The cross-wiki
  *comparison* is the goal, so the separate entities are kept and linked, never collapsed.

## Why it doesn't explode

- **Entities ≈ distinct norms** (small); **occurrences are linear** and mostly exact-matched (free).
- Overlapping/duplicate statements (completeness > minimality) **merge by meaning** into one entity,
  so the *entity* set stays close to the true rule count; raw occurrences are the audit trail.
- No positions stored as identity, no segment×statement join — attribution is the cheap cascade above.
- Snapshot ≈ 1,143 pages × ~50–150 raw statements → far fewer entities after meaning-merge. All-years
  bounded by version-on-change (§2b), not a per-year copy.

## What this really changes (vs the current issues)

- **#2 clean text** — *tiny*: pin "char offsets are Unicode code points into NFC-normalised clean text."
- **#3 segmentation** — *the real change*: `is_core` (binary filter) → **segments tile the text** with
  `segment_type` + `prominence` + `candidate` + `exclusion` route. Adds the structural pre-pass that
  routes votes/chrome/signals out (logged). Nothing dropped un-logged.
- **#4 extraction** — the big reframe: identity is **meaning** (`entity_id`), not position or exact
  text. Split into `statement_entity` (the meaning) + `statement_occurrence` (verbatim text per year,
  attributed by the exact→fuzzy→semantic cascade). No stored offsets; `source_quote` + `exists_in`
  (occurrence years) give H1/H2 for free. `prominence` is a *prior* (weight, don't skip).
- **#5 rating** — `prominence` is now a first-class field (the "location/context weight" metric),
  available via the containing segment; the exploration's `salience` column renames to `prominence`.
- **page-level `confidence`** (core_definition) — **unchanged**; explicitly *not* the same axis as prominence.
- **Exploration data** — `salience` → `prominence` rename; otherwise already consistent.

## Still open (your call)
- Is `prominence` a property of the **segment** (location; cheap default) or the **statement** (how
  central the norm is)? Lean: segment default, LLM overrides at statement level when they diverge
  (a throwaway line stating a load-bearing rule).
- 3- vs 4-point `prominence` scale; whether `context` and `scaffolding` collapse.
- **τ_typo** (the fuzzy band): how much edit-distance counts as "same text, typo" before it must go to
  the semantic arbiter. Conservative default; tuned against the identity-precision metric (false merge =
  hidden reform = the dangerous error).
- Whether same-meaning merge is **automatic** (fuzzy/semantic decides) or **proposed-then-confirmed**
  (a review step), given false-merges are costly.
