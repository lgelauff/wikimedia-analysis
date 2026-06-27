# Additional rule sources (beyond the wiki policy cores)

External / curated rule documents worth atomizing and comparing against the in-wiki policy cores.
These enable a **cross-*source*** comparison (a curated guide vs the community-evolved policy of the
same edition) — complementary to the **cross-*language*** comparison the main pipeline does. They
run through the same statement model and similarity layer (GitHub issues #4 / #5 / #7), with a
PDF/text-ingestion front end instead of the wiki-page front end (#2).

| source | lang | type | format | where |
|---|---|---|---|---|
| **Schrijven voor Wikipedia** ("Writing for Wikipedia") | nl | curated guide / handbook | PDF, 68 pp, ~9.1 MB (uploaded 2020-03-19) | [Commons file page](https://commons.wikimedia.org/wiki/File:Schrijven_voor_Wikipedia.pdf) · direct: `https://upload.wikimedia.org/wikipedia/commons/3/3a/Schrijven_voor_Wikipedia.pdf` (pageid 64959650) |

## Schrijven voor Wikipedia — comparison objective

**Goal:** extract the atomic rules/statements from this guide and compare them to the atomic
statements extracted from the **nlwiki policy core**. Questions:
- **Coverage overlap** — which nlwiki norms does the guide also state, and which does it omit?
- **Emphasis** — what does a *curated, didactic* "how to write" guide foreground vs. what the
  community policy corpus actually codifies (the guide may simplify, reorder, or add practical
  norms not in policy)?
- **Cross-source validation** — does the same atomic-statement method produce alignable units across
  a published PDF guide and the wiki policy pages? A useful robustness check on the approach.

**Ingestion notes:** PDF, so it needs text extraction (cache extracted text to `tmp/pdf_cache/` per
project convention) rather than the wiki HTML/wikitext path; it is directly downloadable from
`upload.wikimedia.org` (no access blocker). Once cleaned, it feeds the **same** statement data model
(#4), extraction (#5), and cross-source/-lingual similarity (#7) — the guide's statements become
another set to align against the nlwiki set.

**Status:** *logged* — processing deferred until the nl statement pipeline (issues #2–#6) exists, so
there is something to compare against.
