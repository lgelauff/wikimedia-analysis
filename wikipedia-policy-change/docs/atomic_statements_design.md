# Atomic-Statement Layer — Design (M8, forward plan)

**Status:** forward design. NOT yet built — M8 is gated (see ROADMAP). The `statement`
tables land in `schema.sql` only when M8 starts and clears its pre-gate. This doc exists
so the storage model is decided *before* we build, not discovered mid-build.

Companion: storage tiers & size budgets in [`data_architecture.md`](data_architecture.md);
milestone context in [`ROADMAP.md`](ROADMAP.md) M8.

## 0. Purpose (north star)

The end goal is **comparable atomic policy elements across languages** — the unit of comparison
is the *element*, not the page. This inverts the precision/recall split:
- **Page set = recall net.** Cast wide; include borderline pages (process/venue pages like
  polls, deletion machinery — "policy-through-structure") rather than excluding them, because
  the real filtering happens at the element level. Excluding a process page at the page level
  silently drops a whole *kind* of policy (procedural), which is often where wikis differ most.
- **Element extraction = precision.** Decide what is a genuine policy element here, then align
  elements cross-lingually (M9). Pages look nothing alike across wikis (banner vs navbox vs
  process page); elements are what's comparable.

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

### 1a. Segment type — pages MIX rule and summary

A page is not uniformly "policy": it interleaves (a) **genuine rule** ("editors must…"),
(b) **procedure** — policy-through-structure: a process/venue definition that is normative by
*being the process* ("a vote runs N days", "deletion follows these steps"), not by deontic
phrasing — these are real policy elements (procedural tier), NOT scaffolding;
(c) **summary-of-rule** (nutshell/"in short" boxes that restate the rule, or summaries of
*other* policies), (d) **meta-pointer** (cross-references, "how X relates to Y", lists), and
(e) **scaffolding** (examples, history, see-also, nav). So page-level "policy-ness" is best
read as a **composition** (fraction of genuine rule vs summary vs meta vs scaffolding), not a
binary label — and "pages that *are* policy" differ from "pages *about* policy" (Five pillars,
Simplified ruleset, the index pages are meta; they're also the heavily-linked hubs that surface
as core via overview/iw signals).

Each extracted segment therefore carries a **type**: `rule | procedure | summary | meta | scaffolding`.
Consequences for the model:
- `rule` AND `procedure` segments are independent **policy elements** (statements) — procedural
  governance counts even without deontic phrasing.
- A `summary` that restates a nearby rule is **linked to that rule, not counted as a separate
  statement** (double-counting guard) — and it matters because summaries get rewritten as the
  policy ecosystem shifts while the underlying rule ossifies, so conflating them would smear
  H1/H2/H3 (additive accretion / ossification / defensive detail).
- `meta`/`scaffolding` are excluded from the statement count (kept as page attributes if useful).

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

### 2a. Build identity on WikiWho token provenance, not hand-rolled matching

The fuzzy/embedding step above is exactly the cross-revision content-identity problem that
**WikiWho** (Flöck & Acuña, WWW 2014) already solves at the **token level, 95% accuracy, open
source, all six of our languages** — see [`related_work.md`](related_work.md) §5. Rather than
hand-roll span matching, **anchor statement identity on WikiWho token IDs**: each token already
carries its full add/delete/reinsert history across revisions, so a statement = a span of tokens
whose persistence/edits aggregate from token histories that are *already validated*. This yields
H1 (birth) / H2 (long unchanged lifespan) / H3 (qualifier added = token insertion into an existing
statement) / reform (token deletion or inversion) largely for free, and replaces the most
error-prone part of this design — false merges that hide reform (§8) — with a measured 95% baseline.

**Gate before committing:** WikiWho's hosted API may be article-namespace only — unconfirmed for
`Wikipedia:` pages. The open-source algorithm runs on revision histories we fetch regardless, so
the fallback is local self-hosting. A one-page cross-lingual probe (one policy across
en/de/nl/fr/es/ja) settles which path before this is locked in. Byte-hash identity stays as the
cheap fast-path for unchanged spans; WikiWho replaces the fuzzy remainder.

This collapse is the measurement:
- **birth year** (`first_year`) = additive accretion (H1)
- **long lifespan, zero edits** = ossification (H2)
- **edit that adds a qualifier/exception** = defensive accretion (H3)
- **removal / inversion** = genuine reform (RQ2 / H1 tail)

**Separates verbosity from interconnection** (the page-level confound). Link density per
*page* conflates two things; per *statement* it splits cleanly:
- **verbosity / detail** = statements per policy — itself the H3 signal ("more detailed").
- **interconnection** = cross-references per statement — verbosity-free "how woven."
So a cross-wiki density gap (e.g. en ~2× denser per page) resolves into two distinct,
comparable claims — is the edition more *detailed*, more *interconnected*, or both — only
once the unit is the statement, not the page.

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
