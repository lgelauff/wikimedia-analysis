# Issue 03 — Atomic-statement data model + store

> **Scope: `wikipedia-policy-change/` only** — all paths/context are within this project of the `wikimedia-analysis` repo; do not touch other folders.

## Objective
Design and implement the storage for atomic statements. Each statement records its **identifier**,
the **source quote** it came from (the closest quote that fully describes it), the **atomic
statement** itself, its **language**, and **both** the original-language text and an English
translation of the statement. The English text is an **interpretation aid** (so a researcher who
doesn't read the language can understand the statement) — **not** a canonical or matching key; how
languages are mapped to each other is undetermined (Issue 06). Plus provenance back to the
page/segment so a statement is always traceable.

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
| `statement_id` | **surrogate** unique id (UUID or autoincrement), assigned once at insert — an opaque reference handle, **not** derived from content/spans (those move on re-run) |
| `wiki`, `page_id`, `revid` | provenance |
| `segment_id` / `char_start`, `char_end` | span back into Issue 01 clean text (the anchor) |
| `source_quote` | the **closest quote that fully describes** the statement, original language |
| `statement_orig` | the atomic statement, **original language** |
| `statement_en` | the atomic statement translated to **English** — interpretation aid for non-speakers; **not** a matching/canonical key |
| `language` | source language code |
| `segment_type`, `governance_class` | carried from Issue 02 / the page (content/user/admin) |
| `created_by`, `model_id`, `prompt_version` | reproducibility (which agent/model/rubric produced it) |
| *(reserved)* `ratings`, `cluster_id` | filled by Issues 05 / 06 |

## Approach
1. Decide store: SQLite locally → ToolsDB for serving (consistent with the network tables). Text is
   stored **inline here** (statements are short) but the *source* text stays by-reference to the
   Issue 01 cache via the span anchor.
2. `statement_id` is a **surrogate key** — assign an opaque unique id (UUID or autoincrement) once,
   at insert. Do **not** derive identity from content or char-offsets: the cleaned-text cache can be
   regenerated (offsets shift) and `statement_orig` is LLM output (paraphrase varies on re-run), so a
   content-hash id would churn for statements that didn't really change; and policy boilerplate
   repeats verbatim across pages, so content can't be a unique key anyway. The surrogate id is purely
   a stable reference handle. (Detecting that two statements are *the same / overlap* is a separate
   concern — the dedup/overlap layer, Issue 06 — not the job of this id.)
3. Provide insert/query helpers and a tiny validation (non-empty `statement_en`, valid span).

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
- Store `statement_en` for English-source statements too (i.e. `statement_en` = `statement_orig`), so every row has a uniform English interpretation field? (Default: yes — purely an interpretation convenience; **not** a cross-lingual matching key. The mapping method is undetermined — Issue 06.)
