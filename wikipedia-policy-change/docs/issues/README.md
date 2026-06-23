# Pipeline issues — clean text → atomic statements → cross-lingual alignment

A pipeline of discrete, agent-runnable work units that take the **current, complete 6-wiki
policy network** and turn each page into **rated, cross-lingually-aligned atomic statements**.
Each issue has an objective, identified inputs/outputs, context docs, and acceptance criteria.

> ⚠️ **All issues here apply to the `wikipedia-policy-change/` project ONLY** (inside the
> `wikimedia-analysis` repo). Every path, dataset, and context doc is within this folder; this work
> must not touch or depend on any other project folder in the repo.

**Scope (shared by all issues):**
- **Project:** `wikipedia-policy-change/` only (see banner above).
- **Wikis:** en, de, nl, fr, es, ja (all six).
- **Pages: the confirmed core only** (`../../data/network/nodes.csv`, 1,143 pages). The pipeline
  (01–06) does **not** run on the periphery/candidate tier. Periphery is handled **after** the
  pipeline, selectively and gap-driven, in **Issue 07** (recall-on-demand: only pull in a periphery
  page if it fills a real gap found at Issue 06).
- **Current snapshot first — but all years is the goal.** These issues (01–06) build the
  **current-year** statement set, which is the **anchor/reference spine**. The full intent is to
  atomize **all years** (the time series powers H1/H2/H3 + reform) — done as **Phase 2**, anchored
  on this snapshot and walked back, matching by *meaning* (see
  [`../atomic_statements_design.md`](../atomic_statements_design.md) §2b). So the snapshot is Phase 1
  of the statement work, not the whole of it. Rendered HTML / `action=parse` is fine for the current
  snapshot (and cached); the historical walk-back uses raw wikitext, and because identity is semantic
  the two substrates need not byte-align.
- **Principle:** statements may **overlap**; **completeness > minimality**. Better to capture a
  rule twice than miss it.

**Pipeline & dependencies:**

```
01 clean-text  ──►  02 core/periphery  ──►  04 statement-extraction ──►  05 criteria+rating ──►  06 similarity/x-lang ──►  07 periphery review
   (per page)        segmentation            (needs 03 schema)            (rates 04)               (dedup + cross-lang)        (gap-driven, selective)
                                       03 statement-data-model ──┘
```

- **01 → 02 → 04 → 05 → 06** is the spine (**core pages only**); **03** (schema) gates **04** and can be built in parallel with 01–02.
- **07 runs only after 06**, driven by 06's gap report — it does *not* reprocess all periphery; it pulls a periphery page through 01–06 only when that page would fill a real cross-lingual gap.
- Every stage **fans out per page / per wiki** — many agents can run one stage across the page list concurrently.

| # | Issue | Depends on |
|---|---|---|
| [01](01-clean-text-extraction.md) | Clean reader-text extraction + cache | — |
| [02](02-core-periphery-segmentation.md) | Core-policy vs periphery segmentation (within a page) | 01 |
| [03](03-statement-data-model.md) | Atomic-statement data model + store | — |
| [04](04-statement-extraction.md) | Atomic-statement extraction | 02, 03 |
| [05](05-statement-criteria-and-rating.md) | Atomic-statement criteria + rating | 04 |
| [06](06-statement-similarity-crosslang.md) | Similarity, dedup, cross-lingual mapping | 04, 05 |
| [07](07-periphery-recall.md) | Periphery review — recall-on-demand (selective) | 06 |

**Background everyone should read first:** [`../classification.md`](../classification.md)
(page→content classification, the level this pipeline operates at), and
[`../atomic_statements_design.md`](../atomic_statements_design.md) (the statement model).

**Unresolved design/research questions and parked concerns:** [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md)
— incl. the statement-overlap / minimal-complete-set problem (OQ-1, affects Issues 04 & 06) and the
non-explicit/implicit-policy coverage concern (OQ-2, parked, scope decision needed).
