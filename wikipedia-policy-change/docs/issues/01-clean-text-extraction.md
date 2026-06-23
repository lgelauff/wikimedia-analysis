# Issue 01 — Clean reader-text extraction + cache

## Objective
For every page in the 6-wiki network, extract the **clean reader-facing text** — everything that
carries meaning to a reader — and **discard navigation, layout, and link/markup machinery**. Cache
both the source and the cleaned text so downstream stages (and re-runs) never re-fetch.

"Reader-meaningful" = prose paragraphs, list items, table *content* that states rules, section
headings, and text-bearing template params (e.g. a `{{nutshell}}` summary). **Not**: nav/infobox
templates, categories, interlanguage links, `<ref>` plumbing, edit-section links, TOC, sidebars,
maintenance banners, raw wikilink/HTML markup.

## Scope
6 wikis (en/de/nl/fr/es/ja); the confirmed core (~1,143 pages) + periphery where available.
**Current snapshot only.**

## Inputs
- `../../data/network/nodes.csv` — the page list (`wiki`, `page_id`, `title`, `namespace`).
- *(optional, for periphery)* the candidate/suspect tier from the build. **Note:** this is not in
  the committed repo — it lives in the ToolsDB `node` table (`confidence='suspect'`). Exporting it
  is a prerequisite if periphery is in scope; otherwise run core-only and flag periphery as TODO.

## Outputs
- A text cache, one entry per page:
  - `text/<wiki>/<page_id>.txt` — the cleaned reader text (UTF-8, structure preserved as
    plain text with section markers).
  - `html/<wiki>/<page_id>.html` — the cached source render (**temporary**; may be pruned once
    text extraction is validated — kept so cleaning is re-runnable without re-fetching).
  - `manifest.csv` — per page: `wiki, page_id, title, revid, source (api/html), fetched_at,
    sha256(text), n_chars`.
- A short coverage report (below).

## Approach
1. Fetch each page's current render. **`action=parse` (rendered HTML) is acceptable here** — this
   is the current snapshot, so today's templates are the correct ones. Cache the HTML.
2. Strip to reader text: drop nav/infobox/maintenance/TOC/ref/edit-link DOM; keep prose, lists,
   rule-bearing tables, headings, nutshell/summary text. (mwparserfromhell is the wikitext
   fallback; for HTML, a DOM strip is simpler — see context docs for tool trade-offs.)
3. Normalize whitespace; preserve section structure as lightweight markers.
4. Hash and write to cache + manifest.

## Context documents
- [`../classification.md`](../classification.md) §2 — what "content" means vs page-level.
- [`../related_work.md`](../related_work.md) §5 — tool trade-offs (WikiExtractor drops lists;
  Sweble; mwparserfromhell) and the wikitext-vs-HTML reconstructability note.
- [`../data_architecture.md`](../data_architecture.md) — cache-as-substrate, storage tiers, hashing.
- [`../../.claude/cleaning_analysis.md`](../../.claude/cleaning_analysis.md) — concrete cleaning
  issue catalog (nested templates, signatures, refs, tables). *(local, gitignored; ask if missing.)*

## Acceptance criteria
- Clean text exists for 100% of in-scope pages; manifest complete and hash-stable on re-run.
- **Scaffolding-leakage check:** cleaned text shares little/no text with the page's navboxes.
- **Coverage spot-check:** on a sample (≥20 pages spanning all 6 wikis), cleaned text captures the
  human-visible prose with no nav/ref leakage (manual review).
- Respects API rate limits + project UA.

## Parallelism
Fully per-page; fan out across the page list / wikis.

## Open questions
- Include periphery now or core-only v1? (Default: core-only; periphery once the candidate set is exported.)
- Keep HTML cache long-term or prune after Issue 02 validates? (Default: keep until 02 is accepted.)
