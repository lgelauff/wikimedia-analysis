# Issue 03 — Atomic-statement data model + store

## Objective
Design and implement the storage for atomic statements. Each statement records its **identifier**,
the **source quote** it came from (the closest quote that fully describes it), the **atomic
statement** itself, its **language**, and **both** the original-language and an English rendering
of the statement. Plus provenance back to the page/segment so a statement is always traceable.

This gates Issue 04 (extraction writes into this store) and Issue 06 (similarity reads from it).

## Scope
6 wikis; current snapshot. (Time-versioning / lifespans — `atomic_statements_design.md` §2 — are a
**later extension**; v1 stores the current snapshot only.)

## Inputs
- Requirements in this issue.
- [`../atomic_statements_design.md`](../atomic_statements_design.md) — the fuller model (adopt the
  span-anchoring + by-reference-to-cache ideas; **defer** lifespans/versioning).
- [`../data_architecture.md`](../data_architecture.md) — storage tiers (structure → SQLite/ToolsDB; text by reference; embeddings in a vector store).

## Outputs
- `statement_schema.sql` (or equivalent) + a thin storage/IO layer + a short README.
- Required fields per statement:

| field | notes |
|---|---|
| `statement_id` | stable id (hash-seeded on wiki+page+span+text) |
| `wiki`, `page_id`, `revid` | provenance |
| `segment_id` / `char_start`, `char_end` | span back into Issue 01 clean text (the anchor) |
| `source_quote` | the **closest quote that fully describes** the statement, original language |
| `statement_orig` | the atomic statement, **original language** |
| `statement_en` | the atomic statement, **English** |
| `language` | source language code |
| `segment_type`, `governance_class` | carried from Issue 02 / the page (content/user/admin) |
| `created_by`, `model_id`, `prompt_version` | reproducibility (which agent/model/rubric produced it) |
| *(reserved)* `ratings`, `cluster_id` | filled by Issues 05 / 06 |

## Approach
1. Decide store: SQLite locally → ToolsDB for serving (consistent with the network tables). Text is
   stored **inline here** (statements are short) but the *source* text stays by-reference to the
   Issue 01 cache via the span anchor.
2. Define `statement_id` so re-extraction of an unchanged span yields the same id (hash of
   `wiki|page_id|char_start|char_end|statement_orig`).
3. Provide insert/query/dedupe-by-id helpers and a tiny validation (non-empty `statement_en`, valid span).

## Context documents
- [`../atomic_statements_design.md`](../atomic_statements_design.md), [`../data_architecture.md`](../data_architecture.md), [`../classification.md`](../classification.md) §2.

## Acceptance criteria
- Schema round-trips a hand-authored sample (≥10 statements across ≥2 languages) with all required fields.
- `statement_id` is stable across re-insertion of identical input; collisions across distinct spans = 0 on the sample.
- README documents every field + the by-reference-to-cache convention.

## Dependencies
None (parallel with 01/02). **Gates Issue 04.**

## Open questions
- One row per statement (overlap allowed → many rows per span) — confirm overlap is represented by
  distinct `statement_id`s over possibly-overlapping spans. (Default: yes; completeness > minimality.)
- Store `statement_en` for English-source statements too (identity), for a uniform cross-lingual key? (Default: yes.)
