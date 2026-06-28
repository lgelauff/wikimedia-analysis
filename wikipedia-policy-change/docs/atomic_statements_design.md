# Atomic-Statement Layer — Design (M8, forward plan)

**Status:** forward design. NOT yet built. The `statement` tables land in `schema.sql` when this
layer starts. This doc exists so the storage model is decided *before* we build, not discovered
mid-build. There is **no hard pre-gate** — build a small pilot and watch the §8 metrics
diagnostically (pilot-first, not gate-first); those metrics may become gates later, before any
formal/published claim.

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

An **atomic normative statement** = one prescriptive/proscriptive proposition (one rule, exception,
qualifier, or definition).

**One source span can carry several statements — even a single sentence.** Policy prose (especially
English) packs multiple propositions into one complex sentence via coordination, subordinate
clauses, and embedded exceptions. So statements are **not 1:1 with sentences or spans**: many
distinct statements may share the same `source_quote`, and a segment is a *container*, not a unit.
Extraction decomposes to **propositions, not sentences** (completeness > minimality — §0, §4).

**The statement is an interpretation, not a span of text.** The statement is *our* normalized
proposition — usually **not** verbatim page text, and usually not even page-shaped. The **span is
the *source*, not the statement**: it's where we found the statement, and how we **confirm it exists
and what it means** — evidence/provenance, not identity. (Like a citation: the quote is the source;
the statement is the claim it supports.) The unit is therefore:

- **Interpretive, but span-*sourced* (not "whatever the model prefers").** Every statement is
  anchored to a source span that evidences it (`source_quote` + the offsets below), so it is
  grounded and confirmable — that grounding, plus the §5/§8 rating against criteria, is what makes
  it measurable, *not* verbatim-ness. The statement text itself (`statement_orig`/`statement_en`) is
  a normalized rendering, the span (`source_quote`) is the evidence.
- **Span-anchored for provenance** — the source is recorded as `(source_revid, char_start,
  char_end)` + `source_quote` into the cleaned text. This anchors *where the statement was
  confirmed*; it is not the statement's identity (see §2 — wording changes, the statement persists).
- **Deontic-marker-*informed*, not -required** — deontic cues (must / should / may / must not /
  editors are expected to …) are a **strong indicator** of a statement and a clean boundary signal
  *where present*, but are **not a necessity**. Normative content also appears without any deontic
  marker — procedures, inclusion-criteria tables (e.g. de `Relevanzkriterien`), and descriptive-
  consensus phrasing ("it is customary" / "op de Nederlandstalige Wikipedia is het gebruikelijk…").
  So deontic markers are a **cue, not a filter** on what counts as a statement.
  (See [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md) OQ-2 on the implicit normative content this entails.)

**Quality metrics (diagnostic — NOT gates yet):** run-to-run boundary stability, human
boundary-F1, and coverage are computed as **metrics to identify bad statements and understand how
the extraction is behaving** — not as pass/fail gates that block the work. We want to fill them out
to learn how the system works first. They may be **promoted to hard pre-registered gates later**,
before any formal/published claim — but for now they inform, they don't block.

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
- `scaffolding` and **purely** non-normative material (signatures, layout, nav, generic background)
  are excluded. **`meta`/framing is NOT hard-excluded**, see §1b.

### 1b. Inclusive extraction with a location/context salience weight

Extraction is **inclusive** (recall-first): we do **not** hard-drop the lead/intro/framing, because
**the lead is often where the *foundational*, highest-generality statements live** — e.g. a policy's
opening "on Wikipedia, in principle no one is in charge; decisions seek consensus" is a real high-level
norm, not background. Hard exclusion is reserved for **purely** non-normative material (signatures,
layout, nav, generic encyclopedic background).

Instead of include/exclude being binary, every statement carries a **`salience` weight driven by its
location/context on the page** — lead/framing **down-weighted**, body/operative sections normal. This
is a **metric** (a prior on how operative the statement is), *not* a filter: a down-weighted lead
statement is still extracted and still compared. It composes with the orthogonal **generality** axis
(foundational / general / local) — a lead statement is typically *low salience but high generality*,
which is exactly the foundational tier we most want for cross-wiki comparison. Down-weight, don't drop.

---

## 2. Core decision — statements are entities with lifespans, NOT per-year snapshots

Policy text is highly stable year-to-year — that stability *is* the ossification hypothesis.
So a statement present in 2020 is byte-identical in 2021 ~90%+ of the time. Storing it once
per year is both wasteful and analytically wrong: we want statement **identity over time**,
not 21 independent copies.

**Model:** decompose once, then track each statement's **interval**; a statement persists even as
its wording changes.

- **Identity is by *meaning*, not by text.** A wording change — rephrasing, clearer language, a
  better shared understanding — usually does **not** change the statement; the statement persists,
  the source text moves. So same-statement-over-time is a **semantic** judgment, *not* a hash of the
  span. (This is the heart of the user's correction: text change ≠ statement change.)
- **Byte-identity is only a cheap shortcut for the *unchanged* case.** If the source span is
  byte-identical across years (≈90% of the time — the ossification stability) the statement is
  certainly unchanged → carry the same `statement_id` for free. But a text *change* does **not**
  imply a statement change — the changed remainder needs a **same-statement-by-meaning** decision
  (rephrase / refine / genuine reform / new / removed).
- **Across-time and across-language identity are the same problem** — "are these two the same
  statement?", decided by meaning (#7 / OQ-1). Solve it once, apply both directions.

### 2a. WikiWho — a text-change *signal*, NOT the statement-identity mechanism (reconsidered)

**Reservation (open).** An earlier draft proposed anchoring statement identity on **WikiWho** token
provenance (Flöck & Acuña 2014; token-level, 95%, OSS, our 6 languages — [`related_work.md`](related_work.md) §5).
On reflection that conflates the two things §1–§2 just separated: **WikiWho tracks *token/text*
identity, not *statement* identity.** A reworded statement has entirely different tokens yet is the
**same statement**, so token provenance cannot tell us whether the *statement* changed — that is the
semantic judgment of §2. WikiWho would over-report "change" every time the text was merely rephrased.

So WikiWho is, at most, a **cheap change-detector / pre-filter**, not the identity layer: it tells us
**where the text moved**, which (a) confirms the unchanged-text shortcut (no token change in a span →
statement certainly unchanged) and (b) localizes *where* to run the semantic same-statement check.
**We do not anchor statement identity on token IDs.** Whether to use WikiWho at all for this — even
as a signal — is **open** (the user is unconvinced); the real identity mechanism is semantic
matching (§2), shared with the cross-language problem.

**Factual note (if WikiWho is used at all):** the hosted WikiWho API is **articles-only** — a probe
on `Wikipedia:Civility` returned `HTTP 400 {"Error":"Only articles! Namespace 4 is not accepted."}` —
so policy pages would require **self-hosting** the OSS algorithm (`wikiwho`/`wikiwho_rs`) on the
revision histories we fetch. That remains true, but per §2a WikiWho would only be a change-localizing
**signal**: byte-identity is the cheap fast-path for unchanged spans, and the changed remainder is
resolved by **semantic same-statement matching (§2), not** by token provenance.

This collapse is the measurement (all keyed on *statement* change, not text change):
- **birth year** (`first_year`) = additive accretion (H1)
- **long lifespan, statement unchanged** = ossification (H2) — *even if the wording was tidied/reworded*
- **statement edited to add a qualifier/exception** = defensive accretion (H3)
- **statement removed / inverted** = genuine reform (RQ2 / H1 tail)

**Separates verbosity from interconnection** (the page-level confound). Link density per
*page* conflates two things; per *statement* it splits cleanly:
- **verbosity / detail** = statements per policy — itself the H3 signal ("more detailed").
- **interconnection** = cross-references per statement — verbosity-free "how woven."
So a cross-wiki density gap (e.g. en ~2× denser per page) resolves into two distinct,
comparable claims — is the edition more *detailed*, more *interconnected*, or both — only
once the unit is the statement, not the page.

### 2b. Temporal scope — atomize ALL years, anchored on the current year (the link)

**Decision:** atomize **every year**, not just the current snapshot. The time series *is* the
analysis (H1/H2/H3, reform) — a single snapshot shows no change. But the years are **not atomized
independently** (that would produce a different, hard-to-align statement set per year). Instead:

- **The current-year statement set is the anchor / reference spine.** Extract it first (the
  current-snapshot pipeline, Issues 01–06).
- **Walk earlier years back and match their text to the current-year statements by *meaning*** (§2 —
  semantic identity, not byte/token). Stay **as close as possible to the current-year form**: a
  historical instance that means the same thing is the *same statement entity*, just with earlier
  wording.
- **The link = a statement *entity* threaded across years.** Each entity has a stable id and an
  interval (`first_year`→`last_year`); the **current-year form is its canonical version**, and every
  historical instance links to it via the entity id. This is the lineage thread the user asked for.
- **Statements with no current-year form** (removed/reformed before now) are the **reform/death
  tail** — discovered by their *absence* from the anchor, given their own entity with
  `last_year < current`. (Mirrors the network's Phase-2 fill-back: anchor on current, walk back, and
  also catch historical-only items the anchor can't see.)

Because identity is **semantic** (§2), the HTML-vs-wikitext substrate seam between the current
snapshot and the historical wikitext doesn't have to byte-align — we match by meaning across
substrates, which removes that concern. Practically: **current snapshot = Phase 1** (the reference
set); **all-years anchored walk-back = Phase 2.**

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

## 8. Eval metrics (diagnostic for now; candidates to become gates before formal claims)

**For now these are metrics, not gates** — we compute them to spot bad statements and understand
the system, not to block the pipeline. Promote to hard pre-registered gates only before a
formal/published claim.

- **Boundary stability** — two decomposition runs on the same snapshot produce alignable spans
  (Jaccard/F1 over boundaries above a floor).
- **Human boundary-F1** — vs a hand-segmented gold set; per-language, never pooled.
- **Coverage** — fraction of normative text captured by some statement.
- **Identity precision** — sampled audit of "same statement, edited" links (false merges are
  the dangerous error — they hide reform).
