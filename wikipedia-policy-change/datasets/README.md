# Datasets — core policy/guideline bodies (2026)

One folder per wiki: the **confirmed core** policy/guideline pages of each edition at the
2026 snapshot, as a `page_title` CSV plus a README (counts, Wikidata coverage, internal
link count, and the provisional governance-object split).

| wiki | folder | rows | source |
|---|---|---|---|
| English | [`enwiki_core_policies_2026/`](enwiki_core_policies_2026/) | 316 | build `083203b` (earlier) |
| German | [`dewiki_core_policies_2026/`](dewiki_core_policies_2026/) | 149 | `data/network/` 2026 |
| Dutch | [`nlwiki_core_policies_2026/`](nlwiki_core_policies_2026/) | 129 | `data/network/` 2026 |
| French | [`frwiki_core_policies_2026/`](frwiki_core_policies_2026/) | 177 | `data/network/` 2026 |
| Spanish | [`eswiki_core_policies_2026/`](eswiki_core_policies_2026/) | 148 | `data/network/` 2026 |
| Japanese | [`jawiki_core_policies_2026/`](jawiki_core_policies_2026/) | 193 | `data/network/` 2026 |

The five non-English folders are generated from the 6-wiki network snapshot
(`data/network/nodes.csv`) by [`build_core_datasets.py`](build_core_datasets.py); rerun:
`uv run --script build_core_datasets.py`.

**Version note:** the English folder is hand-authored from an **earlier** build (316 rows,
commit `083203b`); the current network snapshot has enwiki at **347**. The other five are
from the current snapshot, so the English count is not directly comparable until enwiki is
regenerated (`build_core_datasets.py --include-en`, which would overwrite the hand-authored
enwiki README — left as a deliberate choice, not done automatically).

Method, membership rule, and the namespace-4 page-routing (policy vs. venue vs. deliberation)
are in [`../docs/core_definition.md`](../docs/core_definition.md). The full network (nodes,
edges, governance class, core audit) is in [`../data/network/`](../data/network/).
