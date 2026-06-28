# Exploration data — LLM-generated qualitative pipeline samples

Small, **LLM-generated** samples that qualitatively walk a single real page through **every stage of the
atomic-statement pipeline** (GitHub issues #2–#6), materializing one file per stage — so we can *see*
what each intermediate artifact would roughly look like before the scripted pipeline exists.

> ⭐ **QUALITATIVE REFERENCE (LLM-generated).** These are an **LLM's worked pass** through the pipeline
> (the model acting as the black-box extractor) — a **qualitative** exercise to build a feel for what
> each stage produces and where the design strains, **not** a quantitative gold/eval set. They are not
> pipeline output, and they can't validate themselves: a **human-labeled** set for the #5 boundary-F1 /
> #6 rater-validation gates is a *separate* thing still to be created. Use these as reference examples
> that informed the design (exclusions-as-output, `salience`, `deontic_type`, char-offset spans, the
> numeric rubric, count = deduped norm) — not as a scoring benchmark.

> ⚠️ **Scale caveat.** The statement counts here (24 / 11) are a **minimal, representative** pass —
> *not* the completeness-maximal extraction the pipeline targets. A real "completeness > minimality,
> overlap OK" run decomposes every qualifier/exception/conjunction and keeps narrow+broad variants, so
> the raw count climbs steeply (dozens → 100+ even on a short page). **Raw count tracks extractor
> aggressiveness, not policy verbosity** — so the analytical unit is always the **deduplicated norm**
> (post-#7 cluster, see `06_*`), never the raw statement count. (OQ-1.)

## Per-page subfolders (stage → file)
Each sample is a subfolder with the pipeline stages laid out as files:

| file | stage (issue) | what it is |
|---|---|---|
| `00_source.md` | — | provenance + #3a routing classification (policy? deliberation?) |
| `00_signals.csv` | #1/#3a | **project-specific** category/template/location signals + the policy-vs-not verdict |
| `01_clean_text.txt` | #2 | reader-meaningful text (layout/markup stripped) |
| `02_segments.jsonl` | #3 | segments tagged `segment_type` + `is_core` |
| `04_statements.csv` | #5 | atomic statements (schema = the #4 store) |
| `04_exclusions.csv` | — | what was *not* extracted + why (**completeness invariant**) |
| `05_ratings.csv` | #6 | per-statement ratings — **12 granular criteria, numeric 0/1/2** (see [`RATING_RUBRIC.md`](RATING_RUBRIC.md)) |
| `06_within_overlap.csv` | #7 | within-page near-duplicate / overlap pairs |

Cross-page / cross-lingual matching (#7) is a *shared* artifact at this level, not per-page.

## Samples
| sample | page | kind | n stmts |
|---|---|---|---|
| [`nlwiki_stemprocedure/`](nlwiki_stemprocedure/) | `Wikipedia:Stemprocedure` (75512) | ✅ **standing policy** (`{{Vast}}`, `Vaste reglementen`), 6 articles | 24 |
| [`nlwiki_stemgerechtigde_gebruikers/`](nlwiki_stemgerechtigde_gebruikers/) | `Wikipedia:Stemlokaal/Stemgerechtigde gebruikers` (5097832) | ⚠️ **NOT policy** — a `{{Stemvoorstel}}` (vote proposal ≈ enwiki RfC); deliberation instance | 11 (proposed) |
| [`06_crosspage_alignment.md`](06_crosspage_alignment.md) | the two above, aligned | #7 cross-page mapping | — |

The pair is deliberate and shows the **policy-vs-deliberation routing** in one topic: an **actual
policy** (Stemprocedure, `{{Vast}}` + `Vaste reglementen`) next to a **proposal that is not policy**
(Stemgerechtigde gebruikers, `{{Stemvoorstel}}` + signature templates + no category). Same subject,
opposite §3a routing — see each `00_signals.csv`. The cross-page file then shows real **matches** (the
two base eligibility conditions; "no new options") **and a divergence** (the proposal's activity
requirement applies only to personnel votes, never the general Stemprocedure). The proposal's
statements are **proposed** rules; in a real run that page routes to the deliberation corpus.

## What these samples exercise (design checks)
- **deontic-informed-not-required** — eligibility conditions with no must/should are still captured.
- **routing before counting** — ~80% of the vote instance is deliberation, dropped at segmentation.
- **framing (`deontic_type`)** — eligibility rendered as *"a user is eligible only if…"*, not *"a voter must…"*.
- **overlap = finding** — `:2`→`:3` reads as H3 accretion; `:4`→`:5` as reform.
- **completeness invariant** — every part of each page is a statement *or* a logged exclusion (no silent drops).
- **inclusive extraction + location salience** — the lead/intro is **down-weighted, not dropped**:
  `nlwiki:75512:25` ("on Wikipedia, in principle no one is in charge") is a *foundational* lead norm
  recovered from over-exclusion, carried with `location=lead, salience=low` (see `atomic_statements_design.md` §1b).
- **governance_class** — user-admin throughout (a clean case).

**Page inclusion tool:** [`page_inclusion_viz.py`](page_inclusion_viz.py) takes the **real rendered page**
(`action=parse` → reader text, no markup) and shades each actual block green (included → statement) or
red (excluded), as HTML + a minimap PNG. Output: [`nlwiki_stemgerechtigde_gebruikers/page_inclusion.html`](nlwiki_stemgerechtigde_gebruikers/page_inclusion.html) / [`.png`](nlwiki_stemgerechtigde_gebruikers/page_inclusion.png) — 31% of text included, the rest deliberation.
(Block→statement match is content-word overlap; a few vote comments that *quote* a rule false-match — exact once spans land.)

**Exclusion tool:** [`exclusion_viz.py`](exclusion_viz.py) shades each block of an annotated page by
kind (included vs excluded: deliberation/meta/scaffolding/summary) → HTML + PNG, so it's instantly
visible how much is dropped and why. Output (vote instance): [`nlwiki_stemgerechtigde_gebruikers/exclusion_marked.png`](nlwiki_stemgerechtigde_gebruikers/exclusion_marked.png)
— ~66% of blocks (~80%+ by volume) is excluded deliberation.

**Coverage tool:** [`coverage_viz.py`](coverage_viz.py) colours each sentence of the page text by how
many statements cover it (gap→yellow→green→blue) — spots accidental skips and over-coverage. Output:
`nlwiki_stemprocedure/`'s set → [`coverage_stemprocedure_v2.html`](coverage_stemprocedure_v2.html). Matching is
content-word overlap (a proxy); becomes exact once extraction stores char-offset spans.

Schema/refs: [`../../docs/atomic_statements_design.md`](../../docs/atomic_statements_design.md),
[`../../docs/classification.md`](../../docs/classification.md).
