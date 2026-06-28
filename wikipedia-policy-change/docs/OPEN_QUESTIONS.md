# Open questions & parked concerns

> **Scope: `wikipedia-policy-change/` only.**

A backlog of unresolved design/research questions and deliberately-parked concerns surfaced during
planning and the expert panel review. Not assigned to a numbered issue yet — revisit before the
relevant stage runs.

---

## OQ-1 — Statement overlap & the minimal complete set (ACTIVE — affects #5 & 06)

**The problem.** Raw statement *count* is not yet a meaningful unit: under "completeness > minimality"
(#5) the count tracks prose verbosity and boilerplate density, not how much policy a page
carries (en is the most boilerplate-heavy of the six, so it would inflate). We accept over-extraction
for recall — **but a count is only interpretable once we understand the overlap structure.**

**What we actually want (open):**
1. **Detect overlap between statements** — when do two extracted statements say the same thing, or
   one contain/entail the other, or partially overlap? (semantic similarity vs. entailment vs.
   containment — to be decided.)
2. **Find the complete set with minimal overlap** — the smallest set of statements that still fully
   describes the policy (a MECE-ish cover): complete coverage, minimal redundancy.
3. **Correct counts using the overlap structure** — once overlap is characterized, report the
   deduplicated/cover set as the comparative unit instead of the raw count.

**Status:** the user's framing — "count isn't necessarily helpful yet, but if we understand how
[statements] overlap with each other, we can correct for that; still figuring out how to find the
overlap and the complete set with minimal overlap." This is the core method question behind #7's
dedup and the right unit for any cross-wiki/density claim. **Not yet solved.** Keep raw extraction
inclusive (recall); resolve the overlap→cover method before making count-based comparisons.

---

## OQ-2 — Non-explicit / implicit policy: rules that bind without a quotable sentence (PARKED — possibly out of scope)

**The concern (from the panel; the "extractive vs generative unit" discussion).** A meaningful share
of real Wikipedia policy does **not** bind through an explicit, quotable deontic sentence that a
span-extractor can lift. It binds through:
- **cross-references** — "see [[WP:BLPSOURCES]]"; the operative rule lives on another page, the citing
  sentence is just a pointer;
- **procedural structure** — a process *is* the norm ("an AfD runs 7 days"), often stated only in a
  template/diagram, not deontic prose;
- **list/table indices** — `WP:CSD` "G7" means nothing without its table row; de `Relevanzkriterien`
  are numeric inclusion thresholds in tables, no modal verb;
- **meta-rules** — `WP:IAR` conditions the bindingness of *every other* statement;
- **register/convention** — nl policy phrased as "het is gebruikelijk" ("it is customary") *is* the
  rule but trips no deontic cue.

A purely extractive, span-anchored, deontic-marker-driven unit captures the explicit prose and
**systematically under-represents this implicit/structural normative content** — and that content is
often "where wikis differ most."

**Why parked.** Resolving it well likely requires cross-page reference resolution, procedural-semantics
modelling, and per-wiki non-modal cue handling — plausibly a research project of its own, beyond this
project's scope. The concern is **valid** and should not be silently dropped.

**Decision (provisional):** treat it as a **known, documented coverage limitation** of the extraction
layer rather than a thing this project resolves. Record per-page unresolved cross-references as a
coverage caveat (cheap). Revisit whether any subset (e.g. procedural statements, which #3
already types as `procedure`) is tractable within scope. **Owner decision needed:** in or out of scope.

---

## OQ-3 — Demotion signals for de/nl (no `{{historical}}` banner) (PARKED — revisit later)

de and nl rarely use lifecycle banners (`{{historical}}`/`{{proposed}}`); they signal that a rule is
abandoned/superseded through **category exit** and **removal from the official policy index**, not a
banner. The current core-membership rule ([`../core_definition.md`](../core_definition.md) §2–3) only
lists banner-style negative evidence, so its stickiness/inherit rule may keep abandoned de/nl pages
flagged "core." **Provisional fix (when revisited):** add *category-exit* and *index-removal* as
first-class §2 demotion signals for those wikis. Low-priority; revisit before any de/nl historical
claim. (Panel finding, confirmed.)

## OQ-4 — Browseable visualization + crowd-sourced corrections (FUTURE IDEA)

Rather than exhaustively reviewing the pipeline output up front, ship a **browseable visualization** of
the network / statements and let people (editors, researchers) **explore it and suggest improvements**
in place — surfacing mis-classifications, bad extractions, missing equivalents as community feedback
instead of a closed review. Fits the "see how far we get, then reflect" approach: get a usable
artifact in front of people early; corrections become data. Ties to M3 (web app). Capture now;
design later.

## OQ-5 — Same-statement identity by *meaning* (across time AND across language) (ACTIVE)

A statement is an **interpretation**, not its source span (atomic_statements_design §1). So whether
two statements are "the same" — the **same statement reworded a year later**, or the **same norm in
another language** — is a **semantic** judgment, *not* text/token identity. These are **one problem**:
statement equivalence by meaning, applied across-time and across-language.

Consequences:
- **Byte/token identity only settles the *unchanged* case** (identical text → same statement, cheap).
  A text *change* does not imply a statement change (rephrasing / clearer wording / better
  understanding leave the statement intact) — that needs a semantic decision.
- **WikiWho is reconsidered** (atomic_statements_design §2a): token provenance tracks *text*, not
  *statements*, so it's at most a cheap change-*signal*, never the identity layer. The user is
  unconvinced it's worth using even for that. **Open.**
- Shared machinery with #7 (cross-language matching) and OQ-1 (overlap): solve
  statement-equivalence-by-meaning once, apply in all three places.

## OQ-6 — Numeric (not pass/fail) statement ratings, done right (TO-DO — affects #6)

Move the rating layer from `pass/fail` to **useful numeric** scores — but the literature is clear that
naive 0–100 is *worse*, not better (LLMs aren't calibrated for fine-grained scores; binary is more
reliable than high-resolution). Recommended design, grounded in the LLM-as-judge literature:
- **Low-resolution anchored ordinal** per criterion (e.g. 0/1/2 = fail/partial/pass, or 4-point with an
  explicit `NA/unknown`) — keeps the "partial" signal pass/fail discards, without false precision.
- **Anchor each level** with a definition + a worked example in the rubric (rater-training for the model).
- **Chain-of-thought then score** (G-Eval): reason first, number last; the `reason` field becomes the
  audit trail.
- **Calibrate against the human gold set** and report agreement (Krippendorff's α ≈ 0.8 target) — this
  *is* #6's rater-validation step; treat scores as diagnostic, never compare raw scores cross-time/
  cross-wiki without calibration (they drift).
- Advanced (optional): token-logprob-weighted scores; post-hoc (Wasserstein) calibration to human.
- **Reproducibility:** release the rubric + prompts + ratings (reify-and-reproduce).
Refs: Evidently / Confident-AI (G-Eval) / Monte Carlo LLM-as-judge guides; RULERS (arXiv:2601.08654,
evidence-anchored locked rubrics). **Owner decision:** ordinal resolution (3- vs 4-point) + whether to
add logprob weighting. Until taken up, the exploration `05_ratings.csv` stays pass/fail (diagnostic).

## OQ-7 — The rating rubric: granular, split-out criteria (DECIDED: split out, do not merge)

**Decision (user):** the rubric uses **granular, split-out** criteria — do **not** merge them. The
exploration sample wrongly folded `neutrality` (and the subject/direction check) into `faithfulness`;
split them back out. This is **in line with the LLM-as-judge literature** (OQ-6): decomposing one fused
judgment into several narrow per-criterion judgments ("decision-tree decomposition") is more reliable
and lower-bias than a single conflated score — *granular criteria*, even though each criterion's *score*
stays a coarse ordinal (OQ-6).

**Quality-criteria set (B), split-out:**
1. `atomicity` — exactly one claim (no un-split and/but/because)
2. `declarative` — a claim, not a question/heading
3. `concreteness` — specific obligation/condition, not vague
4. `scope` — neither trivially-broad nor a single obscure detail
5. `neutrality` — non-leading, non-editorializing framing  *(split out of faithfulness)*
6. `faithfulness` — preserves the source's **meaning** (no distortion/inversion of content) *(now narrower)*
7. `subject_correct` — the actual normative subject (e.g. "a user", not a presupposed role) *(split out)*
8. `deontic_direction` — correct normative relation (eligibility/permission/obligation/prohibition as in
   source; not an eligibility rendered as an obligation) *(split out)*
9. `qualifier_completeness` — keeps exceptions/parenthetical qualifiers; doesn't flatten hedges
10. `self_contained` — interpretable without surrounding context
11. `translation_fidelity` — `statement_en` faithfully renders `statement_orig` (NA if source = en)
12. `source_grounding` — `source_quote` supports the statement

Keep the three label kinds distinct: **(A) classification attributes** (segment_type/deontic_type/
governance/generality/location/salience), **(B) these quality criteria**, **(C) §8 system metrics**.
**Still open:** whether to add `non_redundancy` (overlaps #7/OQ-1) as a 13th, and the OQ-6 score
resolution (3- vs 4-point ordinal). The exploration `05_ratings.csv` should be re-run on this set.

## How to use this file
When a question here is taken up, either fold it into the relevant numbered issue or promote it to its
own issue, and note the resolution here. Don't delete — keep the resolved rationale.
