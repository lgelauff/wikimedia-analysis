# Exploration data — hand-authored pipeline samples

Small, **hand-authored** samples that walk a single real page through **every stage of the
atomic-statement pipeline** (GitHub issues #2–#6), materializing one file per stage — so we can *see*
what each intermediate artifact would roughly look like before the scripted pipeline exists.

**These are not pipeline output.** They are illustrative + a seed for future gold/eval sets (the
rater-validation set in #6, the boundary-F1 set in #5). The real pipeline regenerates its own data;
these stay as reference examples and hand labels.

## Per-page subfolders (stage → file)
Each sample is a subfolder with the pipeline stages laid out as files:

| file | stage (issue) | what it is |
|---|---|---|
| `00_source.md` | — | provenance + #3a routing classification |
| `01_clean_text.txt` | #2 | reader-meaningful text (layout/markup stripped) |
| `02_segments.jsonl` | #3 | segments tagged `segment_type` + `is_core` |
| `04_statements.csv` | #5 | atomic statements (schema = the #4 store) |
| `04_exclusions.csv` | — | what was *not* extracted + why (**completeness invariant**) |
| `05_ratings.csv` | #6 | per-statement ratings against the criteria rubric |
| `06_within_overlap.csv` | #7 | within-page near-duplicate / overlap pairs |

Cross-page / cross-lingual matching (#7) is a *shared* artifact at this level, not per-page.

## Samples
| sample | page | kind | n stmts |
|---|---|---|---|
| [`nlwiki_stemprocedure/`](nlwiki_stemprocedure/) | `Wikipedia:Stemprocedure` (75512) | **standing policy** `{{Vast}}`, 6 articles | 24 |
| [`nlwiki_stemgerechtigde_gebruikers/`](nlwiki_stemgerechtigde_gebruikers/) | `Wikipedia:Stemlokaal/Stemgerechtigde gebruikers` (5097832) | **vote instance** (2018), dated adoption event | 11 |
| [`06_crosspage_alignment.md`](06_crosspage_alignment.md) | the two above, aligned | #7 cross-page mapping | — |

The pair is deliberate: the **standing rule** (Stemprocedure Art. 3) and the **vote that amended
related rules** (Stemgerechtigde gebruikers) — so the cross-page file shows real **matches** (the two
base eligibility conditions; the "no new options" rule) **and a real divergence** (the activity
requirement exists only for personnel votes, not general ones).

## What these samples exercise (design checks)
- **deontic-informed-not-required** — eligibility conditions with no must/should are still captured.
- **routing before counting** — ~80% of the vote instance is deliberation, dropped at segmentation.
- **framing (`deontic_type`)** — eligibility rendered as *"a user is eligible only if…"*, not *"a voter must…"*.
- **overlap = finding** — `:2`→`:3` reads as H3 accretion; `:4`→`:5` as reform.
- **completeness invariant** — every part of each page is a statement *or* a logged exclusion (no silent drops).
- **governance_class** — user-admin throughout (a clean case).

Schema/refs: [`../../docs/atomic_statements_design.md`](../../docs/atomic_statements_design.md),
[`../../docs/classification.md`](../../docs/classification.md).
