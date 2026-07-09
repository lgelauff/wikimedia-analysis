# Handoff — wikipedia-policy-change

Cross-lingual, cross-time study of Wikipedia **policy as a network of atomic norms**. Reproduces &
extends Heaberlin–DeDeo (2016) (EN, page-level, 2015) to **6 wikis (en/de/nl/fr/es/ja), present-day,
and the atomic-statement level**. See [`related_work.md`](related_work.md) for framing.

## Where things live
- **Pipeline spec = GitHub issues #2–#9** (canonical; edit there). #9 is the tracking index.
  #2 clean-text · #3 segment layer · #4 statement store · #5 extraction · #6 rating · #7 similarity/
  cross-lingual · #8 periphery. The old `docs/issues/*.md` drafts were deleted — GitHub is the source.
- **Design docs** (`docs/`): [`classification.md`](classification.md) (page→content, two levels),
  [`atomic_statements_design.md`](atomic_statements_design.md) (the statement model — read §1b, §2, §2b, §4),
  [`core_definition.md`](core_definition.md) (page membership + §3a namespace-4 router),
  [`segment_statement_schema_draft.md`](segment_statement_schema_draft.md) (APPLIED — the entity/occurrence rationale),
  [`ROADMAP.md`](ROADMAP.md), [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md) (backlog OQ-1..).
- **Network (built, current snapshot)**: `data/network/` (nodes.csv 1,143 · edges.csv · FINDINGS.md
  #1–#5 · core_audit.csv · governance_class.csv). Inference: `net/null_model.py`. Findings are M5-cleared for the snapshot.
- **Exploration (qualitative, LLM-generated — NOT gold)**: `data/exploration/` — hand-walked nl samples
  + viz tools (`coverage_viz.py`, `exclusion_viz.py`, `page_inclusion_viz.py`, `find_review_changes.py`).
- **First real run**: `data/exploration/runs/` — scripted `fetch_clean.py` (#2) + agent extraction (#3/#5)
  for en/de NPOV + RfC. Counts: en NPOV 112, de NPOV 65, en RfC 90, de Dritte Meinung 35.

## Decisions locked this session
- **Statement identity = MEANING** (`entity_id`), not text/position. `source_quote`s are *occurrences*
  (evidence), verbatim + `quote_hash`; attributed by **exact → fuzzy(τ_typo) → semantic** cascade.
  Same meaning ⇒ same entity (merge within wiki); **cross-wiki ⇒ record equivalence, never merge** (#7).
- **Segment layer = labelling, not filtering**: tiles the clean text with `segment_type` + `prominence`
  (central|supporting|context, a TEXT weight, ≠ page `confidence`) + `candidate` + `exclusion` route.
  Nothing dropped un-logged (completeness invariant).
- **Deontic markers are a cue, not required** (procedures, tables, conditions count).
- **Framing**: render the true normative relation (eligibility = "X is eligible only if…", never invert to "a voter must…").
- **Completeness > minimality, overlap OK**; the **deduped norm (#7 cluster)** is the analytical unit, never the raw count.
- **Temporal**: atomize ALL years, **anchored on the current snapshot** (Phase 1 = snapshot; Phase 2 = walk back, attach occurrences by meaning). §2b.
- **Eval criteria are METRICS, not gates** (for now) — promote to gates only before a formal claim.
- **Manual typo-resolution burden is small & bounded**: driven by change-events (annual snapshots
  filter intra-year churn); Phase-1 has none; the review-signal stack (series / talk-page / revert /
  edit-summary in `find_review_changes.py`) turns thousands of raw candidates into a small no-signal residue.

## Open questions (need your call — flagged in the issues/draft)
- `τ_typo` fuzzy band (typo vs meaning); tuned against identity-precision (false merge = hidden reform).
- `prominence`: segment property (cheap default) or statement override?
- Same-meaning merge: automatic vs proposed-then-confirmed?
- Rating: 3- vs 4-point scale; add a `non_redundancy` 13th criterion (or leave to #7)?

## Suggested next steps
1. **#7 alignment on the clean NPOV en↔de pair** — map de's 65 norms onto en's 112; surface en norms
   with no de counterpart (divergence at statement granularity). The cleanest first cross-lingual test.
2. **#3 structural pre-pass** — the coverage viz showed the policies-navbox/footer leaking through #2;
   route nav/footer → `scaffolding, candidate=false`.
3. Add **Meinungsbilder** as the *formal*-RfC de analogue (Dritte Meinung is only the informal half).
4. Build a **browse-and-suggest reviewer UI** (OQ-4) — the viz kit is a preview.
5. Eventually: run the whole pipeline scripted across the 6-wiki core; wire the #3/#4 schema into `net/schema.sql` at M8.

## Gotchas
- **Git**: work goes to `origin/main`. This session the local checkout got reset to the session-start
  commit mid-way; all work was safe on the remote and re-synced with `git checkout -B main origin/main`.
  If files look missing, check `git log origin/main` — the remote is truth.
- `source-collection/raw/` (untracked) and `source-collection/plug-ins/.../hooks.json` (modified) are
  **pre-existing, another project, not ours** — leave them.
- Real runs use **agents as the extraction step** (`fetch_clean.py` → per-page agent → statements.csv).
- API-only, never scrape; UA `WikimediaAnalysis/1.0 (…lgelauff/wikimedia-analysis)`; use `uv run`.
