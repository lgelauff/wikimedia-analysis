# Statement rating rubric (exploration)

Granular, split-out criteria (OQ-7), scored on a **coarse anchored ordinal** (OQ-6) — numeric, not
pass/fail, but deliberately low-resolution (LLMs aren't calibrated for fine scores).

**Scale:** `2` = clearly meets · `1` = partial/borderline · `0` = fails · `NA` = not applicable.

| criterion | 2 (pass) means | 0 (fail) means |
|---|---|---|
| atomicity | exactly one claim | joins claims (and/but/because) un-split |
| declarative | a claim | a question / heading |
| concreteness | names a specific obligation/condition | vague generality |
| scope | sensible breadth | trivially-broad or one obscure detail |
| neutrality | non-leading framing | loaded / editorialising |
| faithfulness | preserves the source's meaning | distorts/inverts the content |
| subject_correct | the actual normative subject ("a user") | a presupposed role ("a voter must…") |
| deontic_direction | relation as in source (eligibility/permission/obligation/prohibition) | e.g. eligibility rendered as an obligation |
| qualifier_completeness | keeps exceptions/parentheticals | flattens hedges ("generally") into hard rules |
| self_contained | interpretable alone | needs surrounding context |
| translation_fidelity | `statement_en` faithfully renders `statement_orig` | mistranslation (`NA` if source = en) |
| source_grounding | `source_quote` supports it | quote doesn't support the statement |

`overall` = `review` if any criterion < 2 · `note` if flagged but all 2 · else `ok`.
**Still open (OQ-6/OQ-7):** 3- vs 4-point scale; whether to add `non_redundancy` as a 13th criterion
(currently handled by `06_within_overlap` + #7). These scores are **diagnostic**, hand-authored, and
**not calibrated** — a real run calibrates against a human gold set (α≈0.8).
