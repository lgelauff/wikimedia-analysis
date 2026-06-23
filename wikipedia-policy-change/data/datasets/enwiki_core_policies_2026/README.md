# Dataset — English Wikipedia core policies & guidelines (2026)

**`enwiki_2026_core.csv`** — the 316 pages that constitute the **core** policy/guideline
body of English Wikipedia as of the 2026 snapshot.

| field | |
|---|---|
| wiki | en.wikipedia (ns 4, the `Wikipedia:` project namespace) |
| snapshot year | 2026 |
| rows | 316 |
| `page_title` | MediaWiki `page_title` (underscores, no `Wikipedia:` prefix) |

These are the *confirmed* nodes only — the "core of the core." The surrounding
**candidate territory** (~33k pages: essays, supplements, scored category/navbox
members) is captured separately in the build output, not in this dataset.

---

## How we got here (method)

Built by [`net/net_build_current.py`](../../../net/net_build_current.py). A page is **core** iff
it is in the project namespace (ns 4) **and** meets a near-ground-truth signal:

1. **Status banner** — transcludes a policy/guideline status template
   (`{{policy}}`, `{{guideline}}`, `{{MoS guideline}}`, `{{naming conventions}}`, …), **or**
2. **Wikidata** — its item asserts `P31 = Q4656150` ("Wikimedia project policies and
   guidelines page"). 265/316 (~84%) carry a Wikidata item.

**Overrides / exclusions:**
- An **essay/non-binding banner** (`{{essay}}`, `{{supplement}}`, `{{information page}}`,
  `{{historical}}`, …) demotes a page to *candidate* even if it sits in a policy category —
  the page is explicitly saying "this is not policy." (~32k essay-tagged pages excluded.)
- **Sandbox/archive subpages** (`.../sandbox`, `.../Archive_NNN`) that inherit a banner are
  dropped (3 such false positives removed).
- **Mainspace (ns 0) excluded** entirely.

Categories and templates are **signals for admission**, never graph edges. The policy
network itself is the in-body wikilink graph between these core pages (parsed from
wikitext, not `pagelinks`) — 2,735 core→core links in this snapshot.

**Reproducibility:** every build emits a git-stamped immutable snapshot
(`policy_net_archive/enwiki_2026_<timestamp>_<commit>.sqlite`) with a full per-node
`provenance` table (which template/category/navbox + score surfaced each page). This CSV
is the title list extracted from build commit `083203b`.

---

## Composition note

The **Manual of Style** (~60 subpages) and **Naming conventions** (~80 subpages) families
together make up ~44% of the core. They are formally guidelines and belong here, but
their sheer count can swamp the ~180 "top-level" policies/guidelines in any aggregate or
visualisation. Treat each family as a *cluster* when analysing.

---

## Future work — policy typing

This dataset treats "policy/guideline" as one flat body. A clear next step is to
**categorise core pages into functional types**, e.g.:

- **conduct** (Civility, Harassment, NPA, Edit warring)
- **content** (NPOV, Verifiability, NOR, BLP, Notability)
- **procedural / process** (Deletion process, RfA, Dispute resolution, CheckUser)
- **copyright** (Copyrights, Non-free content, Image use)
- **style** (Manual of Style family)
- **naming** (Naming conventions family)
- **enforcement / access** (Blocking, Banning, Oversight, admin rights)

The **Manual of Style is a peculiar type**: it is enormous, highly modular (per-topic
subpages), almost purely prescriptive on *form* rather than *conduct or content*, and it
evolves differently from behavioural/content policy. It likely warrants its own treatment
(or exclusion) in some analyses rather than being pooled with, say, BLP or Civility.

Type assignment can reuse the same signals (status-template variant, category, Wikidata)
plus the Tier-2 LLM judge. Deferred to later work; flagged here so the distinction isn't
lost.
