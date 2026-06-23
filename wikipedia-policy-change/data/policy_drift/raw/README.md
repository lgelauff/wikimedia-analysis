# Raw wikitext — yearly policy snapshots

Tracked raw source text for the drift analysis. One file per revision:

```
raw/<wiki>/<revid>.txt
```

- **What:** the wikitext of each yearly snapshot revision referenced in the drift CSVs
  (`../<wiki>__<title_slug>.csv`, column `revid`) — ~621 revisions across en/de/es/fr/ja/nl.
- **Provenance:** each file is named by its immutable MediaWiki `revid`; the (wiki, title, year)
  it belongs to is the matching row in the drift CSV. Content is fetched once from the MediaWiki
  Action API and never changes (revisions are immutable).
- **Populated by** `policy_drift.py` (`CACHE_DIR` points here); files are written on fetch and
  reused on subsequent runs. Requires outbound access to `*.wikipedia.org`.
- **License:** Wikipedia content is **CC BY-SA**; reuse requires attribution (wiki + revid give
  the exact source revision).

This is a deliberate exception to the "raw text stays off-git" default in
[`../../docs/data_architecture.md`](../../docs/data_architecture.md): the drift snapshot set is
small and bounded, so it is kept in-repo as the reproducibility substrate for the drift CSVs. The
much larger historical reconstruction cache (`net_build_historical.py`) stays off-git.
