# Clean Base — Proposal (for review)

Status: **PROPOSAL**. Nothing executed yet. On approval, this becomes the consolidated design and the script/schema are rebuilt to match; the accreted `policy_network_design.md` stays in git history.

M1 (enwiki depth-2) is built and validated; M2 (de/nl) is mid-run. This proposes a cleaner conceptual base before we go further, driven by two findings from the M1 build.

---

## 1. The two findings that motivate the cleanup

1. **Templates are not graph edges** — a page transcluding `{{cite web}}` says nothing about governance. Templates matter only as (a) admission *signals* (status templates) and (b) navbox grouping — and navbox-rendered links are already in the wikilink graph (`pagelinks` captures links from transcluded templates).
2. **Categories are not graph edges either** — the M1 build showed **3,045 category edges, 0 of them policy→policy**, because category membership is policy→*category*, not policy→policy.

→ Both are **node-level signals**, not relations in the policy→policy network.

---

## 2. Proposed conceptual model

**One graph, two facet layers, node attributes.**

- **The network graph = wikilinks between admitted pages.** Edges are policy→policy `pagelinks`. This is the only edge set. (Out-links to non-admitted pages are kept but flagged, for in-degree/coverage — not part of the policy→policy graph.)
- **Category membership** = a *facet* of each node (which indicator categories it sits in). Used for admission, grouping, and filtering — never an edge.
- **Template transclusion** = a *facet* of each node (which templates it uses), each tagged with a **role**. Used for admission (status role) and optional grouping (navigation role) — never an edge.
- **Node attributes** = title, namespace, redirect, QID, admitted_via, status tier.

### Template roles (the "not every template is relevant" point)

| role | examples | network use |
|---|---|---|
| `status` | `{{policy}}`, `{{guideline}}`, `{{historical}}` | **admission signal** + node attribute (tier/lifecycle). Not an edge. |
| `navigation` | `{{Wikipedia policies and guidelines}}` sidebar/navbox | optional grouping layer; its links already in the wikilink graph |
| `noise` | `{{cite web}}`, `{{reflist}}`, `{{shortcut}}`, infoboxes, maintenance | ignored for the network; kept in registry for completeness only |

Role assignment: name-pattern heuristic first (cheap, covers the bulk), LLM for the ambiguous tail later (M6-adjacent). Stored in `template_registry.role`.

---

## 3. Proposed schema (replaces the lumped `edge` table)

```
node(wiki, page_id, year, title, namespace, is_redirect, wikidata_qid,
     admitted_via, status_tier)                         -- PK (wiki,year,page_id)

link(wiki, year, from_page, to_page, to_admitted)       -- the wikilink graph only
                                                          -- to_page NULL if target missing

node_category(wiki, year, page_id, category_title)      -- membership facet
node_template(wiki, year, page_id, template_title, role)-- transclusion facet (role-tagged)

category_registry(wiki, year, category_title, depth_from_root,
                  n_members, is_indicator)
template_registry(wiki, year, template_title, role, n_transclusions, is_indicator)

build_run(wiki, year, built_at, source, root_category, max_depth,
          n_nodes, n_links)
```

Changes from the M1 schema:
- `edge` (lumped) → `link` (wikilink graph only). Category/template relations move to `node_category` / `node_template` facet tables.
- `node` gains `status_tier` (policy / guideline / essay / lifecycle).
- `template_registry` gains `role`.
- Net effect: the graph table holds ~38k meaningful rows instead of 269k mostly-noise rows; signals live in clearly-named facet tables.

---

## 4. Proposed script structure (`net_build_current.py` refactor)

Same pipeline, cleaner separation, template/category demoted from edges:

```
resolve_seeds(wiki)            -> root category (WIKI_ROOTS), status templates
discover_categories(root)      -> indicator category tree (BFS, bounded depth)
admit(categories, templates)   -> admitted page set + admitted_via + status_tier
extract_links(admitted)        -> wikilink graph (policy->policy + flagged out-links)
extract_facets(admitted)       -> node_category, node_template (+ role tagging)
resolve_qids(admitted)
write(node, link, facets, registries, build_run)   -> ToolsDB + SQLite
```

`tag_template_role(name)` — heuristic classifier (regex on known status/nav/citation/maintenance patterns; default `noise`), with a hook for LLM refinement later.

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
