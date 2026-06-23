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
  (#2–#7) does **not** run on the periphery/candidate tier. Periphery is handled **after** the
  pipeline, selectively and gap-driven, in **#8** (recall-on-demand: only pull in a periphery
  page if it fills a real gap found at #7).
- **Current snapshot first — but all years is the goal.** These issues (#2–#7) build the
  **current-year** statement set, which is the **anchor/reference spine**. The full intent is to
  atomize **all years** (the time series powers H1/H2/H3 + reform) — done as **Phase 2**, anchored
  on this snapshot and walked back, matching by *meaning* (see
  [`../atomic_statements_design.md`](../atomic_statements_design.md) §2b). So the snapshot is Phase 1
  of the statement work, not the whole of it. Rendered HTML / `action=parse` is fine for the current
  snapshot (and cached); the historical walk-back uses raw wikitext, and because identity is semantic
  the two substrates need not byte-align.
- **Principle — completeness:** statements may **overlap**; **completeness > minimality**. Better to
  capture a rule twice than miss it.
- **Principle — reify & reproduce (applies to every issue):** prefer the **more reified** option
  everywhere — every intermediate is a **concrete, inspectable, materialized artifact** (a file/row
  with an explicit schema), never an implicit or in-memory step — and make every stage **as
  reproducible as possible**: versioned inputs, pinned `model_id`/`prompt_version`, content-hashes,
  cached outputs, recorded provenance, deterministic where it can be. (LLM stages aren't bit-
  identical, so "reproducible" here means **re-traceable + cached + provenanced**, not necessarily
  identical output.)

**Pipeline & dependencies:**

```
#2 clean-text  ──►  #3 core/periphery  ──►  #5 statement-extraction ──►  #6 criteria+rating ──►  #7 similarity/x-lang ──►  #8 periphery review
   (per page)        segmentation            (needs #4 schema)            (rates #5)               (dedup + cross-lang)        (gap-driven, selective)
                                       #4 statement-data-model ──┘
```

- **#2 → #3 → #5 → #6 → #7** is the spine (**core pages only**); **#4** (schema) gates **#5** and can be built in parallel with #2–#3.
- **#8 runs only after #7**, driven by #7's gap report — it does *not* reprocess all periphery; it pulls a periphery page through #2–#7 only when that page would fill a real cross-lingual gap.
- Every stage **fans out per page / per wiki** — many agents can run one stage across the page list concurrently.

| # | Issue | Depends on |
|---|---|---|
| [#2](01-clean-text-extraction.md) | Clean reader-text extraction + cache | — |
| [#3](02-core-periphery-segmentation.md) | Core-policy vs periphery segmentation (within a page) | #2 |
| [#4](03-statement-data-model.md) | Atomic-statement data model + store | — |
| [#5](04-statement-extraction.md) | Atomic-statement extraction | #3, #4 |
| [#6](05-statement-criteria-and-rating.md) | Atomic-statement criteria + rating | #5 |
| [#7](06-statement-similarity-crosslang.md) | Similarity, dedup, cross-lingual mapping 🚧 *preliminary* | #5, #6 |
| [#8](07-periphery-recall.md) | Periphery review — recall-on-demand (selective) 🚧 *very ill-defined, placeholder* | #7 |

**Background everyone should read first:** [`../classification.md`](../classification.md)
(page→content classification, the level this pipeline operates at), and
[`../atomic_statements_design.md`](../atomic_statements_design.md) (the statement model).

**Unresolved design/research questions and parked concerns:** [`../OPEN_QUESTIONS.md`](../OPEN_QUESTIONS.md) (project backlog, in `docs/`)
— incl. the statement-overlap / minimal-complete-set problem (OQ-1, affects #5 & #7) and the
non-explicit/implicit-policy coverage concern (OQ-2, parked, scope decision needed).
