# Issue 06 — Statement similarity, dedup, and cross-lingual mapping

> **Scope: `wikipedia-policy-change/` only** — all paths/context are within this project of the `wikimedia-analysis` repo; do not touch other folders.

## Objective
Find similarities between statements: **(a)** deduplicate near-identical statements *within* a
language (overlap was allowed at extraction by design, so duplicates are expected and fine — here we
cluster them); **(b)** map each statement to its **equivalents across the 6 languages**; and **(c)**
produce a **gap report** — statements with no cross-lingual match are candidate points of divergence
(the payoff: what one edition has codified that another hasn't).

This is the project's core unit of comparison — *atomic policy elements compared across languages* —
realized. It is **M9 at the statement level**.

## Scope
All six languages (en/de/nl/fr/es/ja). All rated statements (Issue 04/05). Current snapshot.

## Inputs
- **Issue 04** statement store (with `statement_en` — the shared cross-lingual key).
- **Issue 05** ratings (optionally restrict to `ok` statements, or weight by quality).
- Structural priors: `../../data/network/` interwiki clusters + the **hidden-equivalents** method
  (FINDINGS #4 / `../../net/analyze_network.py` §5) — pages already aligned cross-wiki are strong
  priors for where statement matches should concentrate.

## Outputs
- Within-language dedup clusters (`cluster_id` written back per Issue 03).
- A cross-lingual statement-equivalence map: clusters of statements (across languages) expressing
  the same norm, with a `relationship` tag where inferable (genetic/translated vs convergent).
- A **gap report**: per language, statements with no match elsewhere — disaggregated (genuine gap
  vs. likely-missed). Ties to the M9 "unmatched element → targeted net expansion" idea.

## Approach
1. Embed statements via `statement_en` (shared space) — embeddings in a vector store
   ([`../data_architecture.md`](../data_architecture.md); reuse keys per `statement_id`).
2. **Block, never O(n²):** candidate pairs from (QID ∪ langlink page-alignment ∪ embedding-ANN),
   then **LLM-verify** the top-k for genuine equivalence vs mere topical similarity.
3. Within-language: dedup/cluster first; cross-language: align clusters.
4. Known translations (the translated-page work) as a **positive control** for the matcher.
5. Gap = no match after blocking + verify. **Do not search the periphery here** — emit the gap
   report; the periphery search (recall-on-demand) is **Issue 07**, which consumes this report. A
   gap is only "genuine" after Issue 07's expand-and-re-search fails.

## Context documents
- [`../related_work.md`](../related_work.md) — M9 architecture, DeDeo typology, embedding approach.
- [`../atomic_statements_design.md`](../atomic_statements_design.md) §5 — embed uniques, vector store.
- [`../classification.md`](../classification.md) §2d — cross-wiki element alignment.
- `../../data/network/FINDINGS.md` #4 — the structural hidden-equivalents prior + its caveats (candidate generator, false positives → verify).

## Acceptance criteria
- **Dedup precision** on a sampled set (clusters really are the same statement).
- **Cross-lingual matching** validated on the known-translation positive control (report recall).
- Gap report produced per language, with genuine-vs-missed disaggregation on a sample.
- No O(n²) pass (blocking demonstrated).

## Dependencies
Issues 04 and 05. The capstone — everything feeds here.

## Parallelism
Embedding + ANN per-statement; verification per candidate pair (fan out).

## Open questions
- Match on `statement_en` only, or also use original-language embeddings as a check? (Default: en for blocking, original for verification.)
- Equivalence threshold / how strict is "the same norm"? (Default: LLM-verified semantic equivalence, not paraphrase similarity — set on the control.)
