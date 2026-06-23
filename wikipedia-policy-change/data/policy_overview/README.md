# Policy overview pages — raw wikitext

For each of the top ~20 Wikipedia editions, the raw wikitext of that wiki's top-level
**"list of policies and guidelines" / policy-overview index page** — one snapshot per language,
plus an index.

```
<wiki>.wikitext   — raw wikitext of the overview page (e.g. en.wikipedia.wikitext)
index.csv         — wiki, lang, title, fetched_at, char_count
```

Collected by [`../../collect_policy_overview.py`](../../collect_policy_overview.py)
(`uv run --script collect_policy_overview.py`; needs outbound access to `*.wikipedia.org`).

## How it was collected

- **Language set:** top ~20 editions by active-editor community size (2024), seeded from the
  enwiki master page `Wikipedia:List of policies and guidelines`.
- **Title discovery (three tiers, in order):** (1) Wikidata sitelinks of the enwiki seed item →
  (2) direct enwiki langlinks for anything still missing → (3) a hardcoded manual-override title
  for languages those two miss.
- **Fetch:** the *current* wikitext of the discovered page via the MediaWiki Action API
  (`prop=revisions`, main slot), saved verbatim to `<wiki>.wikitext`.

## This is NOT necessarily complete or uniform — read before using

- **Missing languages.** 18 of the 20 target languages are present; **`fa` (Persian) and
  `tr` (Turkish) are absent** — discovery found no usable page and they were skipped. Coverage is
  whatever the three-tier discovery resolved, not a guaranteed 20/20.
- **The pages are heterogeneous in kind.** Not every edition has a single master "list of policies
  and guidelines", so the mapped page is sometimes a *different or narrower* page: e.g.
  de = `Wikipedia:Grundprinzipien` (founding principles, not a full list), nl =
  `Portaal:Hulp en beheer` (help/admin portal), cs = `Nápověda:Pravidla` (Help namespace), he =
  `ויקיפדיה:מדיניות`, uk = `Вікіпедія:Правила` (redirects to the full list). The wide `char_count`
  spread in `index.csv` (≈3k–30k) reflects this — they are **not** equivalent documents.
- **enwiki-anchored framing.** Discovery starts from the enwiki seed and walks outward, so the set
  inherits enwiki's notion of "the overview page"; the manual overrides patch known mismatches but
  may still pick a non-canonical page for a given wiki.
- **Point-in-time, not versioned.** Each file is the page's current wikitext as of `fetched_at` in
  `index.csv` (most rows are `cached` from an earlier run; de/nl/uk were re-fetched 2026-06-12).
  There is no history here — this is a seed/index snapshot, not the longitudinal data
  (that's `../policy_drift/`).
- **Index pages, not policies.** These are the *overview/list* pages, one per wiki — not the
  policy texts they point to.

## License

Wikipedia content is **CC BY-SA**; reuse requires attribution. The wiki + page title in
`index.csv` (and the `fetched_at` timestamp) identify the source.
