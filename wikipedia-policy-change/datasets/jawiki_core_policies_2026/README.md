# Dataset — Japanese Wikipedia core policies & guidelines (2026)

**`jawiki_2026_core.csv`** — the 193 pages that constitute the **core** policy/guideline
body of Japanese Wikipedia as of the 2026 snapshot.

| field | |
|---|---|
| wiki | wikipedia.wikipedia (ns 4, the `Wikipedia:` project namespace) |
| snapshot year | 2026 |
| rows | 193 |
| `page_title` | MediaWiki `page_title` (underscores, no `Wikipedia:` prefix) |

These are the *confirmed* core nodes only. Wikidata coverage: 180/193
(~93%) carry a Wikidata item. Internal structure: 1,754 core→core
in-body wikilinks among these pages (the Japanese slice of the policy network).

## Governance-object split (provisional)

Heaberlin–DeDeo (2016) typology, assigned structurally (see
[`../../net/classify_governance.py`](../../net/classify_governance.py) and FINDINGS #5):

**content 87 (45%) · user-user 33 (17%) · user-admin 68 (35%) · Other 5 (2%)**

## Method

Built from the 6-wiki 2026 network snapshot in [`../../data/network/`](../../data/network/)
(`net/net_build_current.py` → `nodes.csv`), filtered to `wiki = jawiki`. Core membership,
the per-wiki indicator reconstruction, and the namespace-4 page-routing rule (policy vs.
venue vs. deliberation) are defined in
[`../../docs/core_definition.md`](../../docs/core_definition.md). Categories/templates are
admission *signals*, never graph edges; the network is the in-body wikilink graph.

Regenerate: `uv run --script ../build_core_datasets.py`.
