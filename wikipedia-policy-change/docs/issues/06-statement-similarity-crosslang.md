# Statement similarity, dedup, and cross-lingual mapping

> **Scope: `wikipedia-policy-change/` only** — all paths/context are within this project of the `wikimedia-analysis` repo; do not touch other folders.

> 🚧 **Status: preliminary / under-specified — needs another pass.** *How* we actually find statement
> overlap and map equivalents across languages is still an open problem (see
> [`../OPEN_QUESTIONS.md`](../OPEN_QUESTIONS.md) OQ-1; cross-lingual mapping method is undetermined).
> This issue is a **sketch** — rework it once Issues #5/#6 land and we can see what the real
> statements look like. Do not over-build to this spec yet.

## Objective
Find similarities between statements: **(a)** deduplicate near-identical statements *within* a
language (overlap was allowed at extraction by design, so duplicates are expected and fine — here we
cluster them); **(b)** map each statement to its **equivalents across the 6 languages**; and **(c)**
produce a **gap report** — statements with no cross-lingual match are candidate points of divergence
(the payoff: what one edition has codified that another hasn't).

This is the project's core unit of comparison — *atomic policy elements compared across languages* —
realized. It is **M9 at the statement level**.

> **Method status — UNDETERMINED.** *How* statements are mapped across languages is an **open
> research question**, not decided here. In particular, `statement_en` is an English **translation
> for interpretation** (Issues #4/#5) — it is **not** the matching substrate; do **not** build the
> cross-lingual mapping on it. The approaches in "Approach" below are **candidate options to
> evaluate**, not a chosen pipeline. Settling the mapping method is itself a deliverable of this
> issue (see Open questions).

## Scope
All six languages (en/de/nl/fr/es/ja). All rated statements (Issue #5/#6). Current snapshot.

## Inputs
- **#5** statement store. (`statement_en` is an English **translation for interpretation**,
  NOT a match key — the mapping method is open, see the status note above.)
- **#6** ratings (optionally restrict to `ok` statements, or weight by quality).
- Structural priors: `../../data/network/` interwiki clusters + the **hidden-equivalents** method
  (FINDINGS #4 / `../../net/analyze_network.py` §5) — pages already aligned cross-wiki are strong
  priors for where statement matches should concentrate.

## Outputs
- Within-language dedup clusters (`cluster_id` written back per #4).
- A cross-lingual statement-equivalence map: clusters of statements (across languages) expressing
  the same norm, with a `relationship` tag where inferable (genetic/translated vs convergent).
- A **gap report**: per language, statements with no match elsewhere — disaggregated (genuine gap
  vs. likely-missed). Ties to the M9 "unmatched element → targeted net expansion" idea.

## Approach — candidate options to evaluate (method not yet chosen)
First task of this issue: **decide and justify the mapping method.** Candidate building blocks to
weigh (and likely combine), none mandated, and **`statement_en` is not assumed as the substrate**:
- multilingual sentence embeddings over the **original-language** `statement_orig` (shared space
  without an English pivot);
- structural priors — the interwiki/QID page alignment + the hidden-equivalents method (FINDINGS #4);
- LLM equivalence verification performed on the **original-language** texts (not their English glosses);
- `statement_en` used only as an *interpretation aid* for the human researcher reviewing candidates.
Then:
1. Embed/represent statements by the chosen method (embeddings in a vector store —
   [`../data_architecture.md`](../data_architecture.md); reuse keys per `statement_id`).
2. **Block, never O(n²):** candidate pairs from (QID ∪ langlink page-alignment ∪ embedding-ANN),
   then **verify** the top-k for genuine equivalence vs mere topical similarity — verification on
   original-language text.
3. Within-language: dedup/cluster first; cross-language: align clusters.
4. Known translations (the translated-page work) as a **positive control** for the matcher.
5. Gap = no match after blocking + verify. **Do not search the periphery here** — emit the gap
   report; the periphery search (recall-on-demand) is **#8**, which consumes this report. A
   gap is only "genuine" after #8's expand-and-re-search fails.

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
#5 and #6. The capstone — everything feeds here.

## Parallelism
Embedding + ANN per-statement; verification per candidate pair (fan out).

## Open questions
- **The core open question: what is the cross-lingual mapping method?** (Undetermined — deciding it
  is part of this issue.) `statement_en` (a translation for interpretation) must **not** be assumed
  as the matching key; favour original-language representation + verification.
- Equivalence threshold / how strict is "the same norm"? (Default: LLM-verified semantic equivalence, not paraphrase similarity — set on the control.)
