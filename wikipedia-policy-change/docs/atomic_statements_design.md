# Atomic-Statement Layer — Design (M8, forward plan)

**Status:** forward design. NOT yet built — M8 is gated (see ROADMAP). The `statement`
tables land in `schema.sql` only when M8 starts and clears its pre-gate. This doc exists
so the storage model is decided *before* we build, not discovered mid-build.

Companion: storage tiers & size budgets in [`data_architecture.md`](data_architecture.md);
milestone context in [`ROADMAP.md`](ROADMAP.md) M8.

---

## 1. The unit

An **atomic normative statement** = one prescriptive/proscriptive proposition in a policy
page (one rule, exception, qualifier, or definition). The unit is:

- **Extractive, not generative** — a span of the actual cleaned text, not an LLM paraphrase.
  Two runs must yield alignable spans; a generative decomposition would produce whatever the
  model prefers and isn't measurable.
- **Span-anchored** — recorded as `(source_revid, char_start, char_end)` into the cleaned text.
- **Deontic-marker-anchored** — segmentation guided by deontic cues (must / should / may /
  must not / editors are expected to …), which gives reproducible boundaries.

**Pre-gate (⛔, same as ROADMAP M8):** do not start until run-to-run boundary stability,
human boundary-F1, and coverage clear pre-registered thresholds. Until then the layer
"generates whatever number the model prefers, not a measurement."

---

## 2. Core decision — statements are entities with lifespans, NOT per-year snapshots

Policy text is highly stable year-to-year — that stability *is* the ossification hypothesis.
So a statement present in 2020 is byte-identical in 2021 ~90%+ of the time. Storing it once
per year is both wasteful and analytically wrong: we want statement **identity over time**,
not 21 independent copies.

**Model:** decompose once, then track each statement's **interval** and version only on change.

- Identity across years is carried by **byte-hash** of the span text: unchanged span → same
  hash → same `statement_id`, for free (~90% of cases).
- The changed remainder gets **fuzzy/embedding match** to decide "same statement, edited" vs
  "new statement" vs "removed."

This collapse is the measurement:
- **birth year** (`first_year`) = additive accretion (H1)
- **long lifespan, zero edits** = ossification (H2)
- **edit that adds a qualifier/exception** = defensive accretion (H3)
- **removal / inversion** = genuine reform (RQ2 / H1 tail)

---

## 3. Change-gating (cost + row collapse)

Only decompose a **page-year whose cleaned text differs from the prior snapshot**. We already
know which page-years materially changed from the structural pass (the cache stores per-revid
text + we compute drift). Unchanged page-years inherit the prior year's statement set and IDs
unchanged → no LLM call. Given ossification, the large majority of page-years are unchanged →
roughly **1/3 the decomposition calls**, same IDs carried forward.

---

## 4. Provisional schema (add to `schema.sql` at M8, not before)

Text is stored **by reference** to the cleaned-text cache, never duplicated inline.

```sql
-- One row per statement ENTITY (its whole life), not per year.
statement(
  statement_id   BIGINT,          -- stable id (hash-seeded)
  wiki           VARCHAR,
  page_id        INT,             -- host page (cross-page lineage = extension, see §6)
  first_year     SMALLINT,
  last_year      SMALLINT,        -- NULL/open if still present in latest snapshot
  n_versions     SMALLINT,        -- 1 for the stable majority
  deontic_type   VARCHAR,         -- obligation|prohibition|permission|definition|other
  status         VARCHAR,         -- active|removed
  PRIMARY KEY (wiki, statement_id)
)

-- Only rows where the span text MATERIALLY CHANGED (most statements have exactly one).
statement_version(
  wiki           VARCHAR,
  statement_id   BIGINT,
  version_no     SMALLINT,
  year_from      SMALLINT,
  year_to        SMALLINT,
  text_hash      VARBINARY,       -- identity key
  source_revid   INT,             -- the snapshot this version was extracted from
  char_start     INT,             -- span anchor into cleaned text of source_revid
  char_end       INT,
  KEY (wiki, statement_id)
)
```

These are **structure rows** (small) — they live in SQLite + ToolsDB like `node`/`link`.
The span text itself is recovered from `cache/clean/<vN>/<revid>.txt` via the anchor.

---

## 5. Embeddings

For cross-wiki matching (M9) and "same statement, edited" detection. **Embed unique
statements (~450k), not statement-years** — the identity collapse cuts the vector count ~20×.

- Stored in a **vector store** (FAISS / `sqlite-vec` / Parquet), keyed by `statement_id`
  (and `version_no` when a statement is edited). **Out of the relational DB** — embeddings are
  the only layer that genuinely outgrows SQLite (see `data_architecture.md`).
- Specific store chosen at M8 (options recorded, not locked).

---

## 6. Cross-page lineage (extension, not Phase 1)

Statements can move between pages on split/merge (a section spun out into a new page). Phase 1
assumes a statement belongs to one `page_id`. Tracking a statement's migration across pages
(via the same hash/fuzzy identity) is an extension — designed when the within-page model is
validated. Ties to the reform case studies (RQ2) and the `relationship` lineage idea in M9.

---

## 7. Cost & scale — naive vs identity model

| | naive (per page×year×statement) | identity model |
|---|---|---|
| statement rows | ~9.5M | **~450k** |
| text in DB | few GB | **~150 MB** (refs, not inline) |
| embeddings | ~40 GB | **~2 GB** (vector store) |
| LLM decompositions | every page-year | **changed page-years only (~1/3)** |

Assumes ~3,000 pages (core + expansion × 3 wikis) × ~21 years × ~150 statements/page, with
~90% year-over-year stability. The only layer leaving SQLite is the ~2 GB of embeddings.

---

## 8. Eval gates (pre-registered, before any analysis uses statements)

- **Boundary stability** — two decomposition runs on the same snapshot produce alignable spans
  (Jaccard/F1 over boundaries above a floor).
- **Human boundary-F1** — vs a hand-segmented gold set; per-language, never pooled.
- **Coverage** — fraction of normative text captured by some statement.
- **Identity precision** — sampled audit of "same statement, edited" links (false merges are
  the dangerous error — they hide reform).
