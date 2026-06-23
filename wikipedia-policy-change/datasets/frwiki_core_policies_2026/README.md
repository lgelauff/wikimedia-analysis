# Dataset — French Wikipedia core policies & guidelines (2026)

**`frwiki_2026_core.csv`** — the 177 pages that constitute the **core** policy/guideline
body of French Wikipedia as of the 2026 snapshot.

| field | |
|---|---|
| wiki | wikipédia.wikipedia (ns 4, the `Wikipédia:` project namespace) |
| snapshot year | 2026 |
| rows | 177 |
| `page_title` | MediaWiki `page_title` (underscores, no `Wikipédia:` prefix) |

These are the *confirmed* core nodes only. Wikidata coverage: 159/177
(~89%) carry a Wikidata item. Internal structure: 1,551 core→core
in-body wikilinks among these pages (the French slice of the policy network).

## Governance-object split (provisional)

Heaberlin–DeDeo (2016) typology, assigned structurally (see
[`../../net/classify_governance.py`](../../net/classify_governance.py) and FINDINGS #5):

**content 82 (46%) · user-user 41 (23%) · user-admin 48 (27%) · Other 6 (3%)**

## Method

Built from the 6-wiki 2026 network snapshot in [`../../data/network/`](../../data/network/)
(`net/net_build_current.py` → `nodes.csv`), filtered to `wiki = frwiki`. Core membership,
the per-wiki indicator reconstruction, and the namespace-4 page-routing rule (policy vs.
venue vs. deliberation) are defined in
[`../../docs/core_definition.md`](../../docs/core_definition.md). Categories/templates are
admission *signals*, never graph edges; the network is the in-body wikilink graph.

Regenerate: `uv run --script ../build_core_datasets.py`.
