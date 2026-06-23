# Issue 04 — Atomic-statement extraction

> **Scope: `wikipedia-policy-change/` only** — all paths/context are within this project of the `wikimedia-analysis` repo; do not touch other folders.

## Objective
From the **core policy text** (the `is_core` segments from Issue 02), extract **all** atomic
statements and write them into the store (Issue 03). For each statement, also produce its
**English** rendering and capture the **closest source quote that fully describes it**.

**Completeness > minimality. Statements may overlap.** It is better to emit a rule twice (e.g. once
narrowly, once with its exception) than to miss it. Do not try to minimize statement count.

**One segment/sentence → possibly many statements.** A segment is a *container*, not a unit, and a
single sentence often packs several propositions (coordination, subordinate clauses, embedded
exceptions). Decompose to **propositions, not sentences** — emit every distinct statement a span
supports, even when they share the **same `source_quote`** (multiple statement rows may point at one
quote; that's expected, not a bug). See [`../atomic_statements_design.md`](../atomic_statements_design.md) §1.

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

## Why an LLM here (and its guardrails)
This stage is where an LLM genuinely shines: decomposing dense policy prose into atomic
propositions requires reading for **meaning** — resolving coordination, subordinate clauses,
embedded exceptions, anaphora, and cross-references, and rendering across six languages. That is
exactly what marker/regex segmentation cannot do, and it's why the unit is deontic-*informed* (not
-required) and the statement is an *interpretation* (not a span). The same step naturally produces
the original + English renderings.

"Shines" ≠ "unchecked." The interpretive freedom is bounded by four grounding mechanisms so the
output stays measurable: (1) every statement is anchored to a `source_quote` (provenance —
confirmable against the page); (2) an **independent** agent rates quality (Issue 05); (3) dedup /
clustering (Issue 06) absorbs the deliberate over-generation; (4) the §5/§8 **metrics** (diagnostic,
not gates yet) track how the extractor is behaving. So the LLM does the decomposition; anchoring,
rating, and dedup keep it honest.

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
   language-aware. `statement_en` is an **English translation for interpretation only** — so a
   researcher who doesn't read the source language can understand the statement. It is **NOT** the
   cross-lingual matching key, and **how** statements are mapped across languages is **not yet
   determined** (an open question — see Issue 06). Do not build anything that assumes `statement_en`
   is the match substrate.

## Context documents
- wiki-polis guide §3 (above) — the definition.
- [`../atomic_statements_design.md`](../atomic_statements_design.md) §1 — extractive/span-anchored unit; §1a segment mixing.
- [`../classification.md`](../classification.md) §2a/2b — segment type + governance object per statement.

## Quality metrics (diagnostic — report to find bad statements, not blocking gates yet)
- **Coverage:** fraction of core-policy text covered by ≥1 statement (report it; completeness is the goal).
- **Atomicity:** sampled audit — statements contain a single claim (no un-split "and/but/because").
- **Translation present + faithful:** every row has a non-empty `statement_en`; sampled bilingual check that `statement_en` matches `statement_orig`.
- **Run-to-run stability:** two runs on the same page produce alignable statement sets (report
  Jaccard over source spans).

These are **metrics to understand how the system is working and surface bad statements**, not
pass/fail gates — they may be promoted to gates before any formal claim (see
[`../atomic_statements_design.md`](../atomic_statements_design.md) §8).

## Dependencies
Issues 02 (input text) and 03 (store). **Feeds 05 and 06.**

## Parallelism
Per-page / per-wiki — the primary fan-out stage for many agents.

## Open questions
- Granularity of overlap (how aggressively to emit narrow + broad variants)? (Default: lean inclusive.)
- Translate at extraction time or as a separate pass? (Default: at extraction — the agent already has full context.)
