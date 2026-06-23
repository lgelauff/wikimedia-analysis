# Core-policy vs periphery segmentation (within a page)

> **Scope: `wikipedia-policy-change/` only** — all paths/context are within this project of the `wikimedia-analysis` repo; do not touch other folders.

## Objective
A policy page is not uniformly policy: it interleaves genuine rules with summaries, cross-
references, examples, and history. Within each page's clean text (#2), **segment the text and
label each segment as core policy text vs periphery**, so #5 extracts atomic statements only
from the parts that actually state norms.

Segment types (from [`../atomic_statements_design.md`](../atomic_statements_design.md) §1a):

| type | core? | examples |
|---|---|---|
| `rule` | **core** | "Editors must cite reliable sources." |
| `procedure` | **core** | "A deletion discussion runs 7 days." (normative by being the process) |
| `summary` | periphery (linked) | nutshell / "in short" boxes restating a rule |
| `meta` | periphery | cross-references, "how X relates to Y", pointers |
| `scaffolding` | periphery | examples, history, see-also, navigation prose |

`rule` + `procedure` = **core policy text** (feeds #5). `summary` is kept but linked to the
rule it restates (not a separate norm). `meta`/`scaffolding` are excluded from statement extraction.

## Scope
6 wikis; all pages from #2. Current snapshot.

## Inputs
- The clean-text cache + manifest from **#2** (`text/<wiki>/<page_id>.txt`).

## Outputs
- `segments/<wiki>/<page_id>.jsonl` — one row per segment: `{page_id, wiki, seq, char_start,
  char_end, section_path, text, segment_type, is_core}`.
- A per-page composition summary: fraction `rule|procedure|summary|meta|scaffolding` (this *is* a
  finding — it quantifies how much of each page is genuine norm vs apparatus).

## Approach
1. Split the clean text into candidate segments (sentence/clause level, guided by deontic markers
   — must/should/may/expected to — and by structural boundaries: headings, list items).
2. Classify each segment into the five types. Anchor on deontic cues + section role; an LLM judge
   for the ambiguous tail. Wiki-dependent cues (deontic words differ per language) — resolve per wiki.
3. Mark `is_core = segment_type in {rule, procedure}`.

## Context documents
- [`../atomic_statements_design.md`](../atomic_statements_design.md) §1a — segment types + the rule/summary double-counting guard.
- [`../classification.md`](../classification.md) §2a — segment type as content-level classification.
- [`../core_definition.md`](../core_definition.md) §3a — the policy-vs-venue routing concepts (page-level analogue).

## Acceptance criteria
- Every page's text is fully partitioned (segments cover the text, no gaps/overlaps in the segmentation itself).
- Per-page composition summary produced for all pages.
- **Human spot-check** (≥20 pages, all 6 wikis): `is_core` labels agree with a human reading on a
  sampled set (report agreement — a **metric** to spot bad segmentation and understand the system,
  not a blocking gate yet).

## Dependencies
#2.

## Parallelism
Per-page.

## Open questions
- Segment granularity: sentence vs clause? (Default: sentence, but split on `and/but/because` for
  atomicity downstream — see #5.)
- Does `summary` text get its own statements or only a link to the rule? (Default: link only, per design §1a.)
