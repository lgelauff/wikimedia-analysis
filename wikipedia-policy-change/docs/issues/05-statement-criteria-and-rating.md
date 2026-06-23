# Issue 05 — Atomic-statement criteria + rating

> **Scope: `wikipedia-policy-change/` only** — all paths/context are within this project of the `wikimedia-analysis` repo; do not touch other folders.

## Objective
Two deliverables: **(a)** define an explicit, versioned set of **criteria** for what makes a good
atomic statement (so quality is measurable, not vibes); **(b)** run a **rating agent** that scores
every extracted statement (Issue 04) against those criteria and flags ones needing revision.

This is the **independent-check** step — a *different* agent than the one that extracted, to avoid
self-grading bias.

## Scope
6 wikis; all statements from Issue 04. Current snapshot.

## Inputs
- **Issue 04** statement store (populated).
- The wiki-polis guide §3 criteria (atomicity, declarative, concrete, scoped, neutral framing).
- [`../atomic_statements_design.md`](../atomic_statements_design.md) §8 (eval metrics — diagnostic for now, not gates) for the evaluation discipline.

## Outputs
- `statement_criteria.md` — the versioned criteria/rubric (each criterion: definition, pass/fail
  bar, an example pass + fail). Suggested criteria:

| criterion | passes if… |
|---|---|
| `atomicity` | exactly one claim; no un-split and/but/because |
| `declarative` | a statement, not a question/heading |
| `concreteness` | names a specific obligation/permission, not a vague generality |
| `scope` | neither trivially-broad nor a single obscure detail |
| `faithfulness` | matches the source rule's meaning + deontic force; no editorializing/inversion |
| `translation_fidelity` | `statement_en` faithfully renders `statement_orig` |
| `source_grounding` | `source_quote` actually contains/supports the statement |

- Per-statement ratings written back to the store (`ratings` field per Issue 03): each criterion
  scored (pass/fail or 0–2) + an overall flag `{ok | revise | reject}` + a one-line reason.
- A rating summary: pass-rate per criterion per wiki; the revise/reject worklist.

## Approach
1. Draft `statement_criteria.md` from the guide §3 + the extraction needs; version it (content-hash).
2. Rating agent scores each statement against the rubric; cache keyed by `(statement_id, rubric_version, model_id)`.
3. Emit the worklist; `revise` items can loop back to Issue 04 for re-extraction.

## Context documents
- wiki-polis guide §3; [`../atomic_statements_design.md`](../atomic_statements_design.md) §8; [`../classification.md`](../classification.md) §4.

## Acceptance criteria
- `statement_criteria.md` exists, versioned, with examples per criterion.
- Every statement has a rating row; the summary reports per-criterion pass-rates per language (never pooled-only).
- **Inter-rater check:** on a sample (≥50 statements), report how often a second rater (or human)
  agrees with the rating agent — a **metric** to gauge rating quality, not a blocking floor (yet).

The ratings themselves are **diagnostic** — their purpose is to flag bad statements (so they can be
fixed/revised) and to help us understand how the extraction is working, not to gate the pipeline.

## Dependencies
Issue 04. (Criteria definition (a) can start immediately, in parallel with 04.)

## Parallelism
Per-statement; fan out. Criteria definition is a single small design task that gates the rating run.

## Open questions
- Numeric scores vs pass/fail per criterion? (Default: pass/fail + overall flag; numeric later if needed.)
- Should `reject`ed statements be deleted or kept with a flag? (Default: keep, flagged — never silently delete.)
