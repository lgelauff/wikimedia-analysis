# Design: AI Effects on the Knowledge Ecosystem — Document Production Plan

## Goal
Produce a well-sourced document (`core_doc.md`) on the effects of AI on the knowledge ecosystem.
Every factual claim must be backed by a source that **verifiably contains the supporting information**.
Where credible sources disagree or complicate a claim, that counterevidence must be represented honestly.

---

## Folder structure

```
AI effects/
├── core_doc.md          # Archival input — original sketch of claims (do not modify)
├── output.md            # The white paper being produced
├── design.md            # This file
├── sources.bib          # BibTeX citation database
├── sources.txt          # Human-readable overview (copyright, availability)
├── pdf sources/         # Local PDF copies, named [citekey].pdf
├── tmp/                 # Cache and intermediate files (persists across sessions, not committed to git)
│   ├── dropbox/         # Drop PDFs here for processing; not permanent storage
│   └── external_ai_responses/  # Responses from external AI tools (leads only)
└── scripts/             # Reusable scripts for source finding and verification
    ├── extract_claims.py
    ├── find_sources.py
    ├── verify_source.py
    ├── build_bib.py
    └── briefs/          # Agent prompt files
        └── scoper_brief.md
```

---

## Workflow

### Phase 1 — Claim extraction
- Parse `core_doc.md` using `extract_claims.py` and extract every factual claim
- Group claims by topic/theme
- Output: `tmp/core_doc_claims.json` — claims with placeholders for sources

### Phase 2 — Scoping (iterative waves)
- The Scoper agent reads `tmp/core_doc_claims.json` and `sources.txt` together
- Brief: `scripts/briefs/scoper_brief.md`
- Operates in waves — scope expands only with explicit user sign-off between waves:

  **Wave 1**: refine existing 8 themes, rewrite vague claims as research questions,
  propose expansion candidates from current sources. Wait for sign-off.

  **Wave N**: incorporate approved expansions, send search agents out with focused briefs,
  read new sources returned, propose next round of expansions. Repeat until scope is complete.

- State tracked in `tmp/scope_waves.json` — records what was proposed, approved, and rejected per wave
- Output per wave: refined theme list, rewritten claims, search briefs for approved themes
- **Scope only expands on explicit user approval — the Scoper never adds themes unilaterally**

### Phase 3 — External AI literature sweeps
- Submit structured queries (see `scripts/briefs/external_agent_queries.md`) to external AI agents
  (Perplexity, ChatGPT, Gemini, etc.) asking for a mini literature review per theme
- These tools often surface sources that structured API searches miss (grey literature,
  recent preprints, policy documents, blog posts from credible institutions)
- **Treat all output as leads only** — not verified sources
- Collect responses in `tmp/external_ai_responses/`, one file per tool per theme
- Feed leads into Phase 4 alongside API search results

### Phase 4 — Source discovery
- For each theme, use a search agent to find candidate sources — both supporting and contradicting
- Search targets:
  - Google Scholar / Semantic Scholar API
  - arXiv (cs.IR, cs.CY, cs.AI)
  - Wikimedia Research publications
  - Institutional reports (UNESCO, OECD, Pew, Reuters Institute, etc.)
  - High-quality journalism (only as supplementary, not primary)
- Source quality hierarchy:
  1. Peer-reviewed academic paper
  2. Preprint with institutional backing (arXiv, SSRN)
  3. Official institutional/government report
  4. Reputable journalism (with original data)
- For **each theme**, the agent must explicitly ask: *"Is there credible evidence that contradicts or substantially qualifies this claim?"*
  - Counterevidence is only included if it meets the same quality bar as supporting sources
  - Weak or industry-funded contrarian sources are noted but not cited
- Output: candidate source list per theme, tagged as supporting / contradicting / qualifying, with abstracts

### Phase 5 — Source verification
- For each candidate source:
  1. Fetch/locate the PDF → store in `pdf sources/[citekey].pdf`
  2. Run a verification script that:
     - Extracts the relevant passage(s) from the PDF
     - Checks whether the passage supports the claim (semantic match)
     - Flags mismatches, over-claims, or ambiguous support
  3. Human review of flagged sources before accepting
- Output: verified source list with passage excerpts and match confidence

### Phase 6 — BibTeX population
- For each verified source, create a BibTeX entry in `sources.bib`
- Add a row to `sources.txt` (citekey, authors, year, copyright, PDF status)
- Assign citekey using format: `[firstauthorlastname][year][firstwordoftitle]`
  - Example: `bender2021stochastic`

### Phase 7 — Document finalisation
- Write each theme block in `output.md` using the structure defined below
- Insert numbered footnotes at claim locations
- Cross-check: every claim has a verified source; every source is cited
- Final pass for consistency, tone, and coverage gaps
- Renumber footnotes on request

---

## Model usage

All scripts accept a `--model` parameter. The unified wrapper lives at `scripts/llm.py`
and routes automatically to Mistral or Anthropic based on the model name prefix.

### Named aliases

| Alias  | Model string                    | Use case                                      |
|--------|---------------------------------|-----------------------------------------------|
| `cheap`  | `mistral-small-latest`         | Mechanical tasks (BibTeX formatting, tagging) |
| `bulk`   | `mistral-large-latest`         | Default: extraction, verification, batch work |
| `judge`  | `claude-sonnet-4-6`            | Scoping, synthesis, ambiguous verification    |
| `fast`   | `claude-haiku-4-5-20251001`    | Fast Claude pass when speed matters           |
| `best`   | `claude-opus-4-6`              | Most capable, highest cost                    |

### Task → default model mapping

| Task / script            | Default model | Rationale |
|--------------------------|---------------|-----------|
| `extract_claims.py`      | `bulk`        | Structured extraction |
| `verify_source.py`       | `bulk`        | Passage matching; upgrade to `judge` for flagged claims |
| `build_bib.py`           | `cheap`       | Mechanical BibTeX templating |
| Scoper agent             | `judge`       | Scope decisions require judgment |
| Source search agents     | `judge`       | Web reasoning, quality assessment |
| `output.md` drafting     | `judge`       | Policy prose synthesis |

### API keys required

- Mistral models → `MISTRAL_API_KEY` in `.env`
- Claude models  → `ANTHROPIC_API_KEY` in `.env`

The wrapper loads both from `.env` automatically (see `scripts/llm.py`).

---

## Scripts (`scripts/`)

Scripts are written to be reusable — they take file paths and parameters as arguments,
not hardcoded to this document. They can be adapted for other research projects.

| Script | Purpose | Default model |
|---|---|---|
| `llm.py` | Unified LLM wrapper (Mistral + Anthropic); named aliases; CLI entry point | — |
| `extract_claims.py` | Parse any markdown file, extract claims needing citations | `bulk` |
| `find_sources.py` | Agent-assisted search for candidate sources per theme | `judge` |
| `verify_source.py` | Given a PDF and a claim, extract relevant passages and score match | `bulk` |
| `build_bib.py` | Scaffold a BibTeX entry from a DOI, URL, or sources.txt batch | `cheap` |
| `briefs/scoper_brief.md` | Prompt for the Scoper agent (Phase 1a) | — |
| `briefs/external_agent_queries.md` | Queries for external AI tools (Phase 1b) | — |

---

## Source verification criteria

A source is **accepted** only if:
- [ ] The specific claim (not just the topic) is addressed in the source
- [ ] The passage is from the source itself, not a secondary citation within it
- [ ] The source is dated (no undated web pages as primary sources)
- [ ] The author/institution is identifiable and credible
- [ ] The PDF or a stable archived URL is stored locally, OR flagged as "access needed" for the user to retrieve

**Access policy**: if a source cannot be accessed due to a paywall or institutional restriction,
do not discard it. Mark it as `access: needed` in `sources.txt` and flag it to the user.
The user may have institutional access and can retrieve it. Never downgrade a source's
quality assessment based on access limitations alone.

A source is **flagged** if:
- The relevant passage is ambiguous or requires interpretation
- The source is a preprint without peer review
- The claim relies on a single source with no corroboration

**Counterevidence handling:**
- Contradicting sources go through the same verification process as supporting ones
- Only contradicting sources that meet the quality bar are included in the document
- Contradicting sources that are low-quality, methodologically weak, or have undisclosed conflicts of interest are logged in `sources.txt` with a note explaining why they were excluded — they are not silently discarded
- The verifier must distinguish between two types of disagreement:
  - **Factual disagreement**: the source disputes the underlying data or finding → integrated directly into the claim, the summary line must reflect the genuine uncertainty
  - **Interpretive disagreement**: the source accepts the facts but disagrees that the effect is harmful or significant → noted but does not weaken the factual claim; may appear as a brief contextual remark at most
- The default is: if the facts are not in dispute, the claim stands as stated

---

## Claims are thematic directions, not final phrasings

Claims in `core_doc.md` express a direction and intent, not a final sentence.
The specific language of every claim in `output.md` is determined by what the sources
actually support. A claim like "traffic is dropping" stands as a theme — the precise
qualifier (how much, how fast, under what conditions) is filled in by the evidence.
Never reject a claim because its original phrasing is imprecise.

---

## Document structure (per theme)

Each theme is covered in a compact block:
1. **Summary line** (1–2 sentences) — the headline finding, defensible from sources alone
2. **Context paragraph** — what the effect is, why it matters, why it is harmful
3. **Evidence paragraph** — what specific sources say; factual counterevidence integrated here if it exists

Length per theme: roughly one page. Total document length will grow as themes are added beyond the initial 8.

---

## Open questions
- [x] Citation style: **numbered footnotes** — renumbered on request as the document evolves
- [x] Format: **white paper** — policy-focused, accessible to a broad non-academic audience; plain language preferred, jargon acceptable only where no simpler alternative exists; evidence presented plainly without methodological detail
