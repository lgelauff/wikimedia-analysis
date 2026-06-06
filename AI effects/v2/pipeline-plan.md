# Pipeline Plan — AI Effects Run 2
**Date:** 2026-05-26
**Status:** Draft — pre-execution

---

## Principles

- All analysis products (candidates, triage, mappings, verifications, gap analyses, claims, output) live in `v2/`. Nothing from `v1/` is consulted when producing evaluations or ratings.
- Sources (PDFs, cached text) are shared read-only inputs from `research-vault/`. No duplication.
- `core_doc.md` is the only carry-over input — it is the original seed document, not a run-1 product.
- The pipeline runs **3 full cycles** before any claims document or output draft is written.
- All fetch failures are logged automatically to `fetch_errors_cN.log`. These are reviewed at Checkpoint 3 of each cycle; the user retrieves manually where possible.

---

## Seed strategies

Five orthogonal strategies — all five used in Cycle 1, scaled down in Cycles 2–3 (see per-cycle notes).

| ID | Strategy | Tool | Goal |
|---|---|---|---|
| S1 | Gap-targeted Elicit queries | Elicit | Surface papers the first run missed by querying from gap notes, not findings |
| S2 | Forward citation tracking | Semantic Scholar / OpenAlex API | Find all empirical follow-up work citing the 8 anchor papers |
| S3 | Adversarial / contradiction search | Semantic Scholar / Google Scholar | Find strongest available counter-evidence for every major claim |
| S4 | Venue sweep | arXiv cs.IR + cs.CY, WikiWorkshop 2025, CHI/CSCW 2025, Reuters Institute DNR 2025 | Systematic coverage of venues the first run likely missed |
| S5 | Gap-specific targeted queries | Semantic Scholar / Elicit | One query per documented gap in claims_v2.md; fills known holes |

### S1 seed queries (Cycle 1)
1. `"AI search zero-click traffic revenue news publishers empirical 2024 2025"` — targets D-theme revenue gap
2. `"Wikipedia editing contribution motivation AI substitution longitudinal"` — targets C1/G3 gap
3. `"AI information literacy source verification critical thinking empirical"` — targets H-theme, seeking counter-evidence

### S2 anchor papers
khosravi2026impact, delriochanona2024large, burtch2024consequences, aral2026rise, shumailov2024ai, wikimedia2025crawlers, pew2025click, gerlich2025ai

### S3 adversarial queries (Cycle 1)
- `"AI search complementarity traffic"`
- `"AI Wikipedia editing no decline increase"`
- `"AI improves open source contribution quality"`
- `"generative AI benefits information literacy source awareness"`
- `"AI overview traffic neutral no effect"`

### S4 venues
- arXiv cs.IR, cs.CY — all papers May 2025–present
- WikiWorkshop 2025 proceedings
- ICWSM 2025 / CSCW 2025
- Reuters Institute Digital News Report 2025

---

## Pipeline steps (one cycle)

### Step 1 — Candidate generation and deduplication

For each seed strategy: collect paper titles, abstracts, DOIs/URLs.
Deduplicate against research-vault: `uv run lookup.py --json` for each candidate.
Candidates not in vault → `candidates_new_cN.json`.
Candidates already in vault → `candidates_existing_cN.json` (noted but not re-fetched).

Output: `candidates_new_cN.json`, `candidates_existing_cN.json`

---

### Checkpoint 1 — Human review of candidate list

Review `candidates_new_cN.json`.
Decision: approve for abstract triage / reject outright.
Expected volume: 100–200 entries in Cycle 1; smaller in Cycles 2–3.

---

### Step 2 — Abstract triage

LLM (judge model) scores each approved abstract:
- Relevance: `relevant` / `marginal` / `irrelevant`
- Stance: `supporting` / `contradicting` / `qualifying`
- Which theme(s) it likely addresses

Output: `triage_cN.json`

---

### Checkpoint 2 — Human review of triage

Review marginal calls and any paper flagged as strong counter-evidence.
Decide include/exclude per paper.
Expected volume proceeding to retrieval: 20–40 papers in Cycle 1.

---

### Step 3 — Full-text retrieval

Add approved papers to `research-vault/inbox/pending.txt` via `lookup.py`.
Run `uv run ingest.py --collect` to fetch via source-collection.
All HTTP failures (timeout, 403, 404, connection refused) are written automatically to `fetch_errors_cN.log`:
```
timestamp | url/doi | error_type | http_status
```

Output: new cache files in `research-vault/cache/`, PDFs in `research-vault/pdfs/` where obtainable, `fetch_errors_cN.log`

---

### Checkpoint 3 — Human: review fetch failures

Review `fetch_errors_cN.log`.
Drop any manually retrievable PDFs into `research-vault/inbox/`, then run `uv run ingest.py`.
Mark remaining failures as unresolvable.

---

### Step 4 — Claim mapping

LLM (judge model) reads each new paper's cached text and maps it to:
- Existing theme(s) from `core_doc.md`
- Specific gap note(s) it fills (from previous cycle's gap_analysis or from v1/claims_v2.md gap notes — read as reference only)
- Whether it supports / contradicts / qualifies a theme direction
- Flag: does it suggest a theme not covered by `core_doc.md`?

Output: `claim_mapping_cN.json`

---

### Checkpoint 4 — Human: new theme and counter-evidence review

Review new-theme candidates — approve or fold into existing themes.
Review counter-evidence assignments — confirm the mapping is correct.

---

### Step 5 — Verification pass

Run `verify_source.py` on all new papers assigned to claims.
For each paper: extract the relevant passage(s), score match against the theme direction.
Failures and fetch errors → appended to `fetch_errors_cN.log`.

Output: `verification_results_cN.json`

Model: bulk (mistral-large) by default; escalate to judge for flagged or contradicting sources.

---

### Checkpoint 5 — Human: verification flag review

Review mismatches, low-confidence scores, and contradicting sources.
Decide: does new evidence change a theme's evidential strength?

---

### Step 6 — Gap analysis

Compare new evidence against the theme directions in `core_doc.md` and the gap notes carried from the previous cycle (or from `v1/claims_v2.md` gap notes, read as a reference checklist only — not as a framing document).

Produce `gap_analysis_cN.md` structured as:
- **Gaps filled** — theme directions now supported by verified evidence
- **Gaps narrowed** — new evidence exists but incomplete
- **Gaps still open** — no evidence found in this cycle
- **New gaps opened** — evidence found that complicates a previously confident direction
- **Counter-evidence** — verified sources that contradict or substantially qualify a direction

Output: `gap_analysis_cN.md`

---

### Checkpoint 6 — Human: integration decisions

Final human review before the next cycle's seeds are written.
Questions to resolve:
- Are there still open high-priority gaps? → inform Cycle N+1 seed S5 queries
- Did any theme direction change enough to affect Cycle N+1 scope?
- After Cycle 3 only: are we confident enough in each theme to draft output?

---

## Per-cycle seed scope

| Cycle | Seeds active | Primary goal |
|---|---|---|
| 1 | S1, S2, S3, S4, S5 | Broad exploration — find what the first run missed |
| 2 | S2 (new anchor papers from C1), S3 (re-run on newly confident themes), S5 (rewritten for surviving gaps) | Deepen gaps that survived Cycle 1; pressure-test newly strong themes |
| 3 | S5 only (written against open gaps from gap_analysis_c2.md); S3 if new "strong" themes emerged in C2 | Convergence — fill remaining gaps or confirm they cannot be filled |

---

## Output files per cycle

| File | Written by | Purpose |
|---|---|---|
| `candidates_new_cN.json` | Step 1 | New papers approved for triage |
| `candidates_existing_cN.json` | Step 1 | Papers already in vault (noted, not re-fetched) |
| `triage_cN.json` | Step 2 | Abstract scores and include/exclude decisions |
| `fetch_errors_cN.log` | Steps 3, 5 | All runtime fetch failures with error type and timestamp |
| `claim_mapping_cN.json` | Step 4 | New papers mapped to themes and gap notes |
| `verification_results_cN.json` | Step 5 | Passage-level verification outcomes |
| `gap_analysis_cN.md` | Step 6 | What was found, filled, opened, and contradicted this cycle |

---

## After Cycle 3

Only after all three cycles are complete:

**Step 7 — Write claims.md**
Produce a new claims document (`v2/claims.md`) from scratch, based solely on the verified evidence from Cycles 1–3. Do not inherit claim phrasings from `v1/claims_v2.md`. Use `core_doc.md` theme directions as the structural skeleton.

**Step 8 — Write output.md**
Draft `v2/output.md` for themes where evidence is rated strong. Hold partial-evidence themes as flagged stubs.

---

## Starting point

Run S1 (Elicit, three queries above) and S5 (gap-specific) first — lowest effort, highest signal.
Run S2 (forward citations via OpenAlex) in parallel.
Run S3 and S4 in a second wave after Checkpoint 2.
