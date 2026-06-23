# Issue 05 — Atomic-statement criteria + rating

> **Scope: `wikipedia-policy-change/` only** — all paths/context are within this project of the `wikimedia-analysis` repo; do not touch other folders.

## Objective
The criteria **already exist** — the wiki-polis guide §3 set (atomicity / declarative / concrete /
scoped / faithful framing) plus the extraction-faithfulness additions already written into Issue 04.
So this issue does **not** invent criteria; it **consolidates them into a versioned rubric and
applies them**. Two steps, in order:
1. **Verify the rating agent can actually judge accurately** — calibrate it against a small
   human-rated set *before* trusting it at scale. If the agent can't reliably tell a good statement
   from a bad one, its ratings are worthless and the whole step is.
2. **Apply** the (verified) rating agent to every extracted statement and flag ones needing revision.

This is the **independent-check** step — a *different* agent than the one that extracted (Issue 04),
to avoid self-grading bias.

## Scope
6 wikis; all statements from Issue 04. Current snapshot.

## Inputs
- **Issue 04** statement store (populated).
- The wiki-polis guide §3 criteria (atomicity, declarative, concrete, scoped, neutral framing).
- [`../atomic_statements_design.md`](../atomic_statements_design.md) §8 (eval metrics — diagnostic for now, not gates) for the evaluation discipline.

## Outputs
- `statement_criteria.md` — the **already-established** criteria *consolidated* into one versioned
  rubric (each criterion: definition, pass/fail bar, an example pass + fail). Not re-invented — these
  come from wiki-polis §3 + Issue 04's faithfulness additions:

| criterion | passes if… |
|---|---|
| `atomicity` | exactly one claim; no un-split and/but/because |
| `declarative` | a statement, not a question/heading |
| `concreteness` | names a specific obligation/permission, not a vague generality |
| `scope` | neither trivially-broad nor a single obscure detail |
| `faithfulness` | matches the source rule's meaning + deontic force; no editorializing/inversion |
| `translation_fidelity` | `statement_en` faithfully renders `statement_orig` |
| `source_grounding` | `source_quote` actually contains/supports the statement |

- A **rater-validation report** (produced *before* the full run): agreement between the rating agent
  and a small human-rated gold set, per criterion — establishing whether the agent judges accurately
  enough to apply.
- Per-statement ratings written back to the store (`ratings` field per Issue 03): each criterion
  scored (pass/fail or 0–2) + an overall flag `{ok | revise | reject}` + a one-line reason.
- A rating summary: pass-rate per criterion per wiki; the revise/reject worklist.

## Approach
1. **Consolidate** the existing criteria into `statement_criteria.md`; version it (content-hash).
2. **Verify the rater first.** Build a small human-rated gold set (~30–50 statements spanning clear
   passes, clear fails, and hard cases, ≥2 languages). Run the rating agent on it and measure
   agreement with the human labels per criterion. Proceed to the full run only if the agent judges
   accurately enough to be useful (report the agreement — this is validation, not a hard gate yet).
3. Apply the verified rating agent to every statement; cache keyed by `(statement_id, rubric_version, model_id)`.
4. Emit the worklist; `revise` items can loop back to Issue 04 for re-extraction.

## Context documents
- wiki-polis guide §3; [`../atomic_statements_design.md`](../atomic_statements_design.md) §8; [`../classification.md`](../classification.md) §4.

## Acceptance criteria
- `statement_criteria.md` exists, versioned, with examples per criterion (consolidated, not re-invented).
- **Rater verified first:** agent-vs-human agreement on the gold set is reported per criterion, per
  language (never pooled-only), *before* the full run — so we know the rater can actually judge.
- Every statement has a rating row; the summary reports per-criterion pass-rates per language.

The ratings themselves are **diagnostic** — their purpose is to flag bad statements (so they can be
fixed/revised) and to help us understand how the extraction is working, not to gate the pipeline.

## Dependencies
Issue 04. (Consolidating the criteria + building the rater-validation gold set can start immediately, in parallel with 04.)

## Parallelism
Per-statement; fan out. Consolidating criteria + validating the rater are the up-front tasks that gate the full rating run.

## Open questions
- Numeric scores vs pass/fail per criterion? (Default: pass/fail + overall flag; numeric later if needed.)
- Should `reject`ed statements be deleted or kept with a flag? (Default: keep, flagged — never silently delete.)
