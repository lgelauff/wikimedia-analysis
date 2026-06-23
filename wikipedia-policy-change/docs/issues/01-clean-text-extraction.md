# Clean reader-text extraction + cache

> **Scope: `wikipedia-policy-change/` only** — all paths/context are within this project of the `wikimedia-analysis` repo; do not touch other folders.

## Objective
For every page in the 6-wiki network, extract the **clean reader-facing text** — everything that
carries meaning to a reader — and **discard navigation, layout, and link/markup machinery**. Cache
both the source and the cleaned text so downstream stages (and re-runs) never re-fetch.

"Reader-meaningful" = prose paragraphs, list items, table *content* that states rules, section
headings, and text-bearing template params (e.g. a `{{nutshell}}` summary). **Not**: nav/infobox
templates, categories, interlanguage links, `<ref>` plumbing, edit-section links, TOC, sidebars,
maintenance banners, raw wikilink/HTML markup.

## Scope
6 wikis (en/de/nl/fr/es/ja); **the confirmed core only** (~1,143 pages). **Current snapshot only.**
Periphery is **not** in scope here — it is handled later and selectively in #8.

## ⚠️ Flag — historical pages (Phase 2 carry-over, design now)
When this extraction is later run on **historical revisions** (Phase 2, all-years — see
[`../atomic_statements_design.md`](../atomic_statements_design.md) §2b), a template transcluded in an
old revision **may have been deleted, renamed, or substantially changed since.** Rendering an old
revision (`action=parse&oldid=`) expands it with **today's** templates — so a deleted template
silently yields **missing content**, and a changed one yields **wrong content**. Given that step 3
makes template-delivered content first-class, this is a real **content-loss hazard**, not an edge case.

**Required behaviour:** detect when a page-revision transcludes a template that is missing or has
changed relative to that revision's era; **raise a flag** on that page-revision (a `template_flag`
column in the manifest) — **do not silently drop**; and **ensure it is followed up** (recover the
template's contemporaneous version from history, or mark the page-year as degraded so it is excluded
/ revisited, never lost). This is a concrete reason the historical path favours **raw wikitext +
contemporaneous template resolution** over HTML rendering (related_work §5 / the wikitext-not-HTML
decision). Track flagged page-revisions so none slip through.

## Inputs
- `../../data/network/nodes.csv` — the page list (`wiki`, `page_id`, `title`, `namespace`).

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
3. **Fully capture template-delivered content.** A large share of reader-meaningful text on policy
   pages is *delivered through templates* (nutshell/summary boxes, shortcut/quotation boxes,
   transcluded rule snippets, parameter text). The extractor must **understand template content and
   include all of it** — verify that content-bearing templates are captured and that only genuine
   nav/maintenance/infobox chrome is dropped. The current snapshot uses the rendered HTML, where
   today's templates are already expanded in the DOM, so the rule is: keep *everything the reader
   sees*, including template output; never discard a block just because it came from a template.
4. Normalize whitespace; preserve section structure as lightweight markers.
5. Hash and write to cache + manifest.

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
- Keep HTML cache long-term or prune after #3 validates? (Default: keep until #3 is accepted.)
