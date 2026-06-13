# Clean Base — Proposal (for review)

Status: **PROPOSAL**. Nothing executed yet. On approval, this becomes the consolidated design and the script/schema are rebuilt to match; the accreted `policy_network_design.md` stays in git history.

M1 (enwiki depth-2) is built and validated; M2 (de/nl) is mid-run. This proposes a cleaner conceptual base before we go further, driven by two findings from the M1 build.

---

## 1. The findings that motivate the cleanup

1. **Templates are not graph edges**, and only *some* templates indicate policy — in two distinct ways:
   - **Type A (located on the page):** a status banner (`{{policy}}`, `{{guideline}}`) on page X marks **X itself** as policy → admits the host.
   - **Type B (links to policy pages):** a navbox (`{{Wikipedia policies and guidelines}}`) doesn't mark its host — it **enumerates other policy pages** → its targets are policy candidates (discovery) and a grouping facet.
   - Everything else (`{{cite web}}`, `{{reflist}}`, infoboxes, maintenance) is noise.
2. **`pagelinks` conflates body links with navbox boilerplate** — MediaWiki expands a Type-B navbox on every host page, so `pagelinks` records *every host → every policy in the navbox*, manufacturing a dense clique (the "complete-subgraph artifact" the methodology review warned about). `pagelinks` cannot distinguish a boilerplate link from a genuine in-body cross-reference. **Therefore the graph must come from raw-wikitext links, not `pagelinks`.** Body links are literally in the page's wikitext; navbox-injected links are not. This also makes the current slice consistent with the historical reconstruction (which parses wikitext anyway).
3. **Categories are not graph edges either** — the M1 build showed **3,045 category edges, 0 policy→policy**, because category membership is policy→*category*, not policy→policy.

→ Categories and templates are **node-level signals** (admission + grouping), never edges. The one graph = genuine in-body wikilinks (from wikitext, not `pagelinks`).

---

## 2. Proposed conceptual model

**One graph (from wikitext), two facet layers, node attributes.**

- **The network graph = genuine in-body wikilinks between admitted pages**, parsed from raw wikitext (NOT `pagelinks`, which is navbox-inflated). This is the only edge set. (Out-links to non-admitted pages kept but flagged, for in-degree/coverage.)
- **Category membership** = a *facet* of each node (which indicator categories it sits in). Admission + grouping + filtering — never an edge.
- **Template transclusion** = a *facet* of each node, each template tagged with a **role**. Admission (status) + discovery/grouping (navigation) — never an edge.
- **Navbox membership** = a *facet*: which Type-B policy navbox(es) enumerate a page (the curated grouping), kept separate from the body-link graph.
- **Node attributes** = title, namespace, redirect, QID, admitted_via, status tier.

### Discovery by indicator scoring + confirmed/suspect tiers

Replace blind depth-bounded BFS with **scored propagation anchored on a confirmed seed**. This is precision-oriented and self-limiting — drift can't sneak in because a wayward category/template simply scores low.

**Confidence tiers (node attribute `confidence`):**
- **`confirmed`** — meets any near-ground-truth signal: carries a Type-A status template (`{{policy}}`/`{{guideline}}`/…); sits in a core category (`Category:Wikipedia policies`, `…guidelines`); **or** asserts `P31 = Q4656150` ("Wikimedia project policies and guidelines page") on Wikidata. This is the anchor set **C**. (Wikidata is sparse — ~26% of M1 nodes had any QID — so it corroborates, never gates alone. No policy/guideline split at the Wikidata class level; that tier comes from the Type-A template.)
- **`suspect`** — reached *through* a scored category or navbox but lacks its own status marker. Stays suspect until it (a) acquires a status template, or (b) passes the Tier-2 LLM judge (M6). May be dropped at reduction.

**Indicator scoring (rank, then work down):**
- *Category* `cat`: `support = |members(cat) ∩ C|`, `density = support / |members(cat)|`. Indicator if `support ≥ s_min` **and** `density ≥ d_min`. Its non-C members → suspects.
- *Template* `t` (Type-B): on its link *targets*: `support = |targets(t) ∩ C|`, `density = support / |targets(t)|`. Policy-navbox if it clears the same bars. Its non-C targets → suspects.
- Rank indicators by `support`; descend the list admitting suspects until the threshold cut. Score stays anchored on **C** (not on suspects) to prevent runaway propagation; optional decayed re-scoring rounds if needed.

Every suspect records the indicator + score that surfaced it (auditable). `s_min`/`d_min` are versioned parameters; the ranked list is inspectable so we can set the cut by eye on real data.

### Template roles (the "only some templates indicate policy, two ways" point)

| role | mechanism | examples | use |
|---|---|---|---|
| `status` | **on the page** (Type A) | `{{policy}}`, `{{guideline}}`, `{{historical}}` | admits the **host**; node attribute (tier/lifecycle) |
| `navigation` | **links to policies** (Type B) | `{{Wikipedia policies and guidelines}}` navbox | its **targets** are policy candidates (discovery) + grouping facet |
| `noise` | neither | `{{cite web}}`, `{{reflist}}`, infoboxes, maintenance | ignored for the network; registry only |

**Role assignment — four features, strongest first** (no hardcoded lists; all language-agnostic):
1. **The template's own categories** — a template page is itself categorized (`Category:Wikipedia policy and guideline templates`, `…navigational boxes`, `…citation templates`, maintenance). This *declares* its role; query `categorylinks` on the template's `page_id`.
2. **Target-overlap with confirmed** — a Type-B policy-navbox is one whose link targets are mostly confirmed policy pages (the scoring above).
3. **Name pattern** — cheap fallback.
4. **Template QID `P31`** — Wikidata navbox flag: `Q11753321` ("Wikimedia navigational template") → navigation role; `Q11266439` (generic "Wikimedia template") is uninformative. Supplementary (sparse coverage).

LLM only for the ambiguous tail. Stored in `template_registry.role` (+ optionally the template's own categories/QID for audit).

**Recursive anchor:** the category `Wikipedia policy and guideline templates` *enumerates the Type-A status templates directly* — so discovering that one template-category hands us the whole status-template set, and every page transcluding them is **confirmed**. A second independent route into **C**, language-agnostic via the same category-scoring.

---

## 3. Proposed schema (replaces the lumped `edge` table)

```
node(wiki, page_id, year, title, namespace, is_redirect, wikidata_qid,
     admitted_via, status_tier)                         -- PK (wiki,year,page_id)

link(wiki, year, from_page, to_page, to_admitted)       -- in-body wikilinks (from WIKITEXT,
                                                          -- not pagelinks). to_page NULL if missing.

node_category(wiki, year, page_id, category_title)      -- membership facet
node_template(wiki, year, page_id, template_title, role)-- transclusion facet (role-tagged)
navbox_member(wiki, year, page_id, navbox_title)        -- which Type-B navbox enumerates the page

category_registry(wiki, year, category_title, depth_from_root, n_members, is_indicator)
template_registry(wiki, year, template_title, role, n_transclusions, is_indicator)

build_run(wiki, year, built_at, source, root_category, max_depth, n_nodes, n_links)
```

Changes from the M1 schema:
- `edge` (lumped, navbox-inflated) → `link` (in-body wikilinks from **wikitext**, not `pagelinks`).
- Category/template relations move to `node_category` / `node_template` facets.
- New `navbox_member` facet for Type-B grouping.
- `node` gains `status_tier`; `template_registry` gains `role`.
- Net effect: the graph holds genuine cross-references (no navbox cliques); signals live in clearly-named facets.

---

## 4. Proposed script structure (`net_build_current.py` refactor)

Same pipeline, cleaner separation, template/category demoted from edges:

```
resolve_seeds(wiki)            -> root category (WIKI_ROOTS), status templates
discover_categories(root)      -> indicator category tree (BFS, bounded depth)
admit(categories, templates)   -> admitted page set + admitted_via + status_tier
                                  (SQL: fast — categorylinks/templatelinks)
fetch_wikitext(admitted)       -> raw wikitext per page (current dump or API, cached)
extract_links(wikitext)        -> in-body wikilink graph (policy->policy + flagged out-links)
extract_facets(admitted)       -> node_category, node_template (role-tagged), navbox_member
resolve_qids(admitted)
write(node, link, facets, registries, build_run)   -> ToolsDB + SQLite
```

Note: admission stays SQL (fast); the **link graph now comes from wikitext** (mwparserfromhell `filter_wikilinks`), so the current slice needs ~1.5k wikitext fetches (cached) — modest, and it unifies current + historical on one method. `tag_template_role(name, targets)` — heuristic on name patterns + the fraction of the template's link targets that are admitted policy pages (Type-B detector); LLM for the tail later.

---

## 5. Proposed consolidated DESIGN.md (TOC)

Rewrite the accreted doc into one current-state document:
1. Goal + research questions (RQ1 where-diverge / RQ2 reform case studies / RQ3 inflection points)
2. Hypotheses (H1–H5) with metric + null + test layer
3. Definitions — node, the one graph (wikilinks), category/template facets, tiers, lifecycle
4. Admission (lenient OR-gate) + reduction (strict, late) + the discovered-indicator loop
5. Two-tier architecture (structural Tier-1 ships first; LLM Tier-2 on residue)
6. Data model (§3 above)
7. Workflow — current-slice (SQL) + historical (stub → 1-Jan revid → API content → cache)
8. Data source + cache-as-reproducibility-substrate
9. Infra (Toolforge jobs / local LLM / web app) + dev-deploy
10. Risks + the two review rounds' resolved items

Old `policy_network_design.md` → preserved in git history (not deleted in working tree until the new one lands).

---

## 6. Restart plan (on approval)

1. Write consolidated `DESIGN.md`; retire `policy_network_design.md`.
2. New `schema.sql` (§3); refactor `net_build_current.py` (§4).
3. `DROP`/reload ToolsDB; rebuild enwiki + dewiki + nlwiki at depth 2.
4. Re-confirm the M1/M2 gates against the clean tables.
5. Delete this proposal.

---

## Open questions for you

- **Out-links to non-admitted pages**: keep them in `link` (flagged `to_admitted=0`) for in-degree/coverage, or drop entirely and store only the policy→policy graph? (Proposal: keep, flagged — cheap and useful for the bootstrap miss-rate analysis.)
- **Category co-membership layer**: do you want a derived policy↔policy "shares-a-category" edge layer (separate from the wikilink graph) for analysis, or leave categories purely as node facets? (Proposal: node facets only for now; derive co-membership at analysis time if useful.)
- **Depth**: stay at depth 2 for the clean rebuild, or retune? (Proposal: depth 2 — validated, healthy.)
