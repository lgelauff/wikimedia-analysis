# Atomic-statement data model + store

> **Scope: `wikipedia-policy-change/` only** — all paths/context are within this project of the `wikimedia-analysis` repo; do not touch other folders.

## Objective
Design and implement the storage for atomic statements. Each statement records its **identifier**,
the **source quote** it came from (the closest quote that fully describes it), the **atomic
statement** itself, its **language**, and **both** the original-language text and an English
translation of the statement. The English text is an **interpretation aid** (so a researcher who
doesn't read the language can understand the statement) — **not** a canonical or matching key; how
languages are mapped to each other is undetermined (#7). Plus provenance back to the
page/segment so a statement is always traceable.

This gates #5 (extraction writes into this store) and #7 (similarity reads from it).

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
| `statement_id` | **`<wiki>:<page_id>:<seq>`** — the page's `node_id` plus an incremental per-page sequence number assigned at insert. A stable, legible reference handle; **not** derived from content/spans (those move on re-run) |
| `wiki`, `page_id`, `revid` | provenance |
| `segment_id` / `char_start`, `char_end` | span back into #2 clean text (the anchor) |
| `source_quote` | the **closest quote that fully describes** the statement, original language |
| `statement_orig` | the atomic statement, **original language** |
| `statement_en` | the atomic statement translated to **English** — interpretation aid for non-speakers; **not** a matching/canonical key |
| `language` | source language code |
| `segment_type`, `governance_class` | carried from #3 / the page (content/user/admin) |
| `created_by`, `model_id`, `prompt_version` | reproducibility (which agent/model/rubric produced it) |
| *(reserved)* `ratings`, `cluster_id` | filled by Issues #6/#7 |

## Approach
1. Decide store: SQLite locally → ToolsDB for serving (consistent with the network tables). Text is
   stored **inline here** (statements are short) but the *source* text stays by-reference to the
   #2 cache via the span anchor.
2. `statement_id = <wiki>:<page_id>:<seq>` — the page's `node_id` plus an incremental per-page
   sequence number assigned at insert. It is a **surrogate** reference handle: do **not** derive
   identity from content or char-offsets (the cleaned-text cache can be regenerated → offsets shift;
   `statement_orig` is LLM output → paraphrase varies on re-run; and policy boilerplate repeats
   verbatim across pages → content can't be a unique key anyway). The id stays legible (you can see
   which page a statement came from) without being content-stable. (Detecting that two statements are
   *the same / overlap* is a separate concern — the dedup/overlap layer, #7 — not the job of
   this id.)
3. Provide insert/query helpers and a tiny validation (non-empty `statement_en`, valid span).

## Context documents
- [`../atomic_statements_design.md`](../atomic_statements_design.md), [`../data_architecture.md`](../data_architecture.md), [`../classification.md`](../classification.md) §2.

## Acceptance criteria
- Schema round-trips a hand-authored sample (≥10 statements across ≥2 languages) with all required fields.
- `statement_id` is stable across re-insertion of identical input; collisions across distinct spans = 0 on the sample.
- README documents every field + the by-reference-to-cache convention.

## Dependencies
None (parallel with #2/#3). **Gates #5.**

## Open questions
- One row per statement (overlap allowed → many rows per span) — confirm overlap is represented by
  distinct `statement_id`s over possibly-overlapping spans. (Default: yes; completeness > minimality.)
- Store `statement_en` for English-source statements too (i.e. `statement_en` = `statement_orig`), so every row has a uniform English interpretation field? (Default: yes — purely an interpretation convenience; **not** a cross-lingual matching key. The mapping method is undetermined — #7.)
