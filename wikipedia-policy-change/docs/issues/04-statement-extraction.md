# Issue 04 — Atomic-statement extraction

## Objective
From the **core policy text** (the `is_core` segments from Issue 02), extract **all** atomic
statements and write them into the store (Issue 03). For each statement, also produce its
**English** rendering and capture the **closest source quote that fully describes it**.

**Completeness > minimality. Statements may overlap.** It is better to emit a rule twice (e.g. once
narrowly, once with its exception) than to miss it. Do not try to minimize statement count.

## What an atomic statement is (from the wiki-polis organizer guide §3)
A good atomic statement is:
- **Atomic — a single claim.** Never join two claims with "and / but / because"; split compounds.
  (*"Require reliable sources AND disclose COI"* → two statements.)
- **Declarative.** A claim, not a question or a heading.
- **Concrete, not vague.** Name the specific obligation, not "Wikipedia should be good."
- **Appropriately scoped.** Not so broad it's trivially true, not a single obscure detail.
- **Faithfully framed.** For *our* extractive use, this means: represent the rule as the policy
  states it, without editorializing or inverting its force (the analogue of the guide's "neutral,
  non-leading framing"). Preserve the deontic force (must / should / may / must not).

Source: https://github.com/lgelauff/wiki-polis/blob/main/guidance/guide_organizer.md#3-writing-good-statements

## Scope
6 wikis; the `is_core` segments of every page. Current snapshot.

## Inputs
- **Issue 02** core segments (`segments/<wiki>/<page_id>.jsonl`, `is_core=true`).
- **Issue 03** statement store + schema (write target).

## Outputs
- Populated statement store: one row per atomic statement with `source_quote`, `statement_orig`,
  `statement_en`, `language`, span anchor, provenance, `model_id`/`prompt_version` (per Issue 03).
- A per-page extraction report: #statements, #per-segment, coverage (fraction of core text under ≥1 statement).

## Approach
1. For each core segment, prompt an extraction agent to emit the atomic statements it contains
   (1..n; overlap allowed), each with: the statement (original language), the closest fully-
   describing source quote, and an English rendering.
2. Enforce the criteria above in the prompt (atomic/declarative/concrete/scoped/faithful); split
   compounds; keep deontic force.
3. Anchor each statement to its source span; write via the Issue 03 layer (idempotent on `statement_id`).
4. Per-wiki: the deontic markers and phrasing differ by language — the extraction prompt is
   language-aware; the **English rendering is the shared key** used downstream (Issue 06).

## Context documents
- wiki-polis guide §3 (above) — the definition.
- [`../atomic_statements_design.md`](../atomic_statements_design.md) §1 — extractive/span-anchored unit; §1a segment mixing.
- [`../classification.md`](../classification.md) §2a/2b — segment type + governance object per statement.

## Acceptance criteria
- **Coverage:** ≥ a pre-registered fraction of core-policy text is covered by ≥1 statement (report it; completeness is the goal).
- **Atomicity:** sampled audit — statements contain a single claim (no un-split "and/but/because").
- **Translation present + faithful:** every row has a non-empty `statement_en`; sampled bilingual check that `statement_en` matches `statement_orig`.
- **Run-to-run stability:** two runs on the same page produce alignable statement sets (a precursor
  to the M8 boundary-stability gate — report Jaccard over source spans).

## Dependencies
Issues 02 (input text) and 03 (store). **Feeds 05 and 06.**

## Parallelism
Per-page / per-wiki — the primary fan-out stage for many agents.

## Open questions
- Granularity of overlap (how aggressively to emit narrow + broad variants)? (Default: lean inclusive.)
- Translate at extraction time or as a separate pass? (Default: at extraction — the agent already has full context.)
