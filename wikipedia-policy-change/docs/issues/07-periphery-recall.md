# Periphery review (recall-on-demand, selective)

> **Scope: `wikipedia-policy-change/` only** — all paths/context are within this project of the `wikimedia-analysis` repo; do not touch other folders.

> 🚧 **Status: very ill-defined — placeholder, needs substantial work.** This issue depends entirely
> on what the earlier stages surface and on a clearer picture of *what else has happened* (the shape
> of the periphery, where the gaps actually are, how much recall the core missed). Treat everything
> below as a **rough placeholder**; it must be rewritten once #2–#7 are done and we can see the real
> situation. Do not build to this spec.

## Objective
The pipeline (#2–#7) runs on the **core only**. This issue is the **follow-up** that, *after* the
core pipeline is complete, goes through the **periphery** (candidate/suspect tier — pages outside
the confirmed core) and pulls in **only** what's worth adding. It is **not** a re-run of the whole
pipeline on the periphery — it is **gap-driven and selective**: a periphery page earns its way in
only if it would fill a real gap found at #7.

This is the M9 *"unmatched element → targeted net expansion"* mechanism, and it also yields the
**recall-miss estimate** (capture–recapture): the fraction of cross-lingual gaps that turn out to
have an answer sitting in the periphery.

> Note on the word "periphery": here it means **candidate-tier pages outside the core** — *not* the
> within-page non-core text segments of #3 (`summary`/`meta`/`scaffolding`). Different thing.

## Scope
6 wikis; the candidate/suspect tier. Runs once the core pipeline (#2–#7) is accepted.

## Inputs
- **#7** gap report — statements/norms with no cross-lingual match (the queries).
- The **candidate/suspect tier**: pages outside the core. *Not in the committed repo* — export from
  the ToolsDB `node` table (`confidence='suspect'`) or rebuild the candidate set; this export is the
  first task of this issue.
- The #5 statement store + #7 embeddings/index (to search periphery against the gaps).

## Outputs
- For each gap: the periphery page(s) (if any) that contain a matching norm — search the periphery
  wide (CirrusSearch / embedding-NN over the candidate pool) for the gap's content.
- A **promotion list**: periphery pages worth pulling into the core for this analysis, each with the
  gap it answers. Those pages are then run through #2–#7 *individually* (not the whole tier).
- A **recall-miss report**: per language, fraction of gaps resolved by expansion = the capture–
  recapture estimate (feeds M5's open capture–recapture item).
- Remaining gaps after expansion = **genuine** cross-lingual divergences (the real finding).

## Approach
1. Export the candidate tier (one-off).
2. For each Issue-#7 gap, query the periphery (broad search bounded to policy-plausible namespaces);
   stop widening when results turn non-policy (scope widens, the element definition does not).
3. If a periphery page answers a gap → add to the promotion list; run it through #2–#7.
4. Re-align (#7) with the newly promoted statements; recompute the gap report.
5. Report recall-miss rate + the residual genuine gaps.

## Context documents
- [`../related_work.md`](../related_work.md) — M9 net-expansion + capture–recapture.
- [`../ROADMAP.md`](../ROADMAP.md) M9 (targeted net expansion) and M5 (capture–recapture miss-rate, currently open).
- `../../data/network/FINDINGS.md` #4 — hidden-equivalents as a structural prior for where to look.
- [`../core_definition.md`](../core_definition.md) — confirmed vs candidate tiers; `core_audit.csv` disposition.

## Acceptance criteria
- Candidate tier exported and documented.
- Every Issue-#7 gap is searched against the periphery; promotion list produced with the gap each page answers.
- Recall-miss rate reported per language.
- Residual genuine-gap list produced (gaps that survive expansion).

## Dependencies
#7 (its gap report is the input). Loops back through #2–#7 for promoted pages only.

## Parallelism
Per-gap search; per-promoted-page pipeline run.

## Open questions
- Promotion bar: how strong must the match be to promote a periphery page? (Default: Issue-#7-grade verified equivalence.)
- Do promoted pages become permanent core or analysis-only? (Default: tag as analysis-promoted, audit-visible; don't silently rewrite the core.)
