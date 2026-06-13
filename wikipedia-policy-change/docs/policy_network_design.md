# Policy Network — Design (v0, brainstorm processed)

**Goal:** Reconstruct the *body* of Wikipedia governance (policies + guidelines + related normative pages) as an annual, evolving **network** for 2–3 language wikis, then align the networks cross-lingually via Wikidata QIDs to find structural gaps and divergences.

This supersedes the per-page drift framing: a policy page is a node in a temporal graph, not an independent time series.

---

## 0. Scope decisions (locked)

- **The body = policies ∪ guidelines**, treated as one corpus. We do not separate them in the headline analysis (status tier still recorded per node-year so the split is recoverable).
- **Essays are excluded** — personal/individual in nature, not collective governance. Recorded but flagged out of the body.
- **Citation frequency is NOT a definitional criterion.** Defining "policy" as "frequently cited" would bias toward old, central pages and bake the network structure into the definition. We *do* record in-degree (cite frequency) as a free attribute from the edge table and can study it — just never use it to decide membership.
- **Collection is inclusive; exclusion is a final, reproducible step.** We do not gate the snowball on a policy/not-policy judgment. We pull broadly, attach observable labels (templates, categories, lifecycle tags, link in/out-degree, LLM verdict for fuzzy cases), and then apply a single, tunable, auditable **exclusion pass** at the end. The exclusion criteria are a parameter of the analysis, not baked into traversal.

**Consequence — the snowball needs a non-definitional stopping rule.** Namespace whitelist does NOT work: policy/governance lives across multiple namespaces (Wikipedia:, Help:, Category: descriptions, MediaWiki:, some Template: docs), not just ns-4. Bound instead by **expansion signal**: *record* every linked neighbour as a node+edge, but only *expand the frontier* from nodes carrying ≥1 governance signal (status template, policy/guideline category, or Wikidata class Q4656150). Non-signal nodes are still recorded (so edges/in-degree are complete) but are dead-ends for traversal. Plus bounded hop depth + page_id dedupe. This bounds explosion without making a keep/drop judgment — the end-stage exclusion pass decides membership.

---

## 0a. Two tiers — structural skeleton vs LLM layer

The pipeline splits into a cheap structural tier that builds most of the network, and an expensive LLM tier applied only to the residue. Tier 1 is shippable on its own.

- **Tier 1 — structural (~80%, no LLM, no content understanding):** stub-meta-history → per-year revid selection → *light* wikitext parse of selected revisions (mwparserfromhell: `[[Category:…]]`, `{{templates}}`, `[[wikilinks]]`) → nodes + category/template/link edges + rule-gate admission via discovered indicators (§1.4b-A). Builds the entire network topology and most of the membership. The exploration web app (Stage 4) can run on Tier 1 output alone.
  - *Note:* the stub gives identity + revision timeline only — template/category edges still require the light parse of each selected revision (or current SQL tables for the present slice; those have no history).
- **Tier 2 — semantic (the fuzzy ~20%, LLM):** "smells like policy" admission for pages with no rule signal (§1.4b-B), section-level normative classification, atomic-statement decomposition, cross-wiki atomic matching. Applied only where Tier 1 doesn't decide. Runs off-Toolforge (no API egress there).

This de-risks delivery: a complete structural network exists before any LLM spend.

**Current-slice fast path (no parsing, no dumps).** The 2026 (current) network can be built entirely from SQL link tables on the Toolforge replicas — no wikitext parse:
- `page` (node inventory), `categorylinks` (cl_from→cl_to), `templatelinks`+`linktarget` (transclusion), `pagelinks`+`linktarget` (wikilinks), `redirect` (shortcut/redirect resolution), `page_props.wikibase_item` (QID), `langlinks` (interwiki).
- Join `page` ⋈ categorylinks/templatelinks filtered to indicator categories/templates → admitted nodes + edges directly.
- **Limit:** replica tables are current-state only — no historical version. So this builds/validates the 2026 anchor and the web-app skeleton; **historical years still need the stub+wikitext reconstruction** (no dated table states exist). Recommended first build: the 2026 network from replica tables.

## 0b. Refinements (v1, from review responses)

- **Unit of analysis drills down: page → section → atomic normative statement.** Not everything on a policy page is policy — lists of pages, lists of users, examples, and nav are not normative. The LLM operates at **section/subpage level**, not whole-page, classifying each segment as normative-policy vs not. The long-term target is **atomic statements** (individual normative propositions), which is also the only level at which cross-wiki matching is meaningful (see below).
- **Cross-wiki comparison happens at the atomic-statement level, not the page level.** Page/QID alignment is too coarse and too sparsely covered. Real equivalence = matching atomic normative statements across wikis. QID/langlink alignment is just scaffolding to narrow the candidate space.
- **This is no longer an Im et al. reproduction.** It's a new contribution; drop "validate against Im" as a requirement (Im stays relevant only for the RfC-process track, not this network track).
- **Dumps — both SQL and content dumps, dated:**
  - *Structure* (the network): SQL dumps — `pagelinks`+`linktarget`, `categorylinks`, `templatelinks`, `langlinks`, `redirect`, `page_props`. These are **dated** per dump, giving point-in-time graph state (the live PAWS replicas are current-only).
  - *Content* (the text): either XML history dumps (`pages-meta-history`, raw wikitext) or **Enterprise HTML dumps** (rendered — resolves the template/parse problem at source). Decide per the cleaning analysis.
- **Deleted pages are partially recoverable after all.** A dump taken in year Y contains pages that existed then, even if deleted later. Walking forward through **dated dumps** captures the rejected/superseded/merged layer that the *current* replica omits. Left-censoring shrinks to "pages created and deleted entirely within a gap between dumps."
- **Merges, pragmatically:** technically page_id survives a merge, but in practice the merged-away page becomes a soft redirect / `{{historical}}` shell. Policy consolidations are messy. Handle by detecting redirect/historical status per year and recording the lineage edge, not by assuming page_id death.
- **Interwiki (langlinks) is a cross-wiki signal too** — available in SQL dumps; use alongside QIDs for Phase D candidate narrowing.

### 1.4b Admission model — two-gate multi-judge

A linked page is **admitted** to the network as a policy node if **EITHER**:

- **(A) Rule gate:** it carries ≥1 acknowledged policy indicator that year (category, template, or Wikidata property — see 1.4c), **OR**
- **(B) LLM gate:** the section-level judge determines it "smells like policy" (primary purpose is to prescribe/proscribe editor conduct, content standards, or process — community-binding norms, not personal opinion or pure how-to).

Admission is deliberately lenient (union, not intersection) so nothing real is lost early. Admitted nodes join the expansion frontier. Non-admitted neighbours are still recorded as edge targets (so in-degree is complete) and archived in `rejected_candidates`.

A **final reduction pass** then tightens the admitted set: drop essays, drop lifecycle-dead shells where appropriate, and drop non-normative sections/segments. The reduction criteria are versioned parameters, re-runnable cheaply.

### 1.4c Seed policy indicators (enwiki) — bootstrap, not the operative list

This list **seeds** the discovery loop; the operative indicator set per year × wiki is *discovered* and stored in `policy_templates` / `policy_categories` (§2). We never hardcode localized names — German/Japanese indicators emerge from observing those wikis' own policy pages. Detected **per year** (templates/categories/Wikidata change over time). Resolve template-redirect aliases as of that year.

**Positive — status templates (admit):**
- `{{policy}}`, `{{guideline}}`, `{{MoS guideline}}` / `{{style guideline}}`, `{{subcat guideline}}`, `{{naming conventions}}`, `{{procedural policy}}`, `{{notability guideline}}`, `{{editing guideline}}`, `{{conduct guideline}}`, `{{content guideline}}`

**Positive — categories (admit):**
- root `Category:Wikipedia policies and guidelines` and descendants: `Category:Wikipedia policies`, `Category:Wikipedia guidelines`, `Category:Wikipedia content policies`, `Category:Wikipedia behavioral guidelines`, `Category:Wikipedia naming conventions`, `Category:Wikipedia deletion`, `Category:Wikipedia editing guidelines`, `Category:Wikipedia style guidelines`, `Category:Wikipedia procedural policies`

**Positive — Wikidata (admit):**
- `P31` (instance of) = `Q4656150` (Wikimedia project policies and guidelines page) or `Q1156854` (policy)

**Lifecycle — admit but tag (orthogonal axis, not a tier):**
- `{{historical}}`, `{{proposed}}`, `{{draft proposal}}`, `{{failed proposal}}` / `{{rejected}}`, `{{disputed tag}}`

**Negative / exclude-at-reduction (admit only if LLM-positive, flag for the final cut):**
- `{{essay}}` (personal — excluded from the body), `{{supplement}}`, `{{information page}}`, `{{wikipedia how-to}}`, `{{WikiProject advice}}`

**Weak signals (LLM context, not hard rules):**
- has WP:-shortcut redirect(s); listed on the official policy/guideline index that year; transcludes the `{{Wikipedia policies and guidelines}}` navbox; namespace is ns-4 (necessary-ish, not sufficient — see §0b, policy spans other namespaces too)

### 1.5 Borrowing from Wikidata

Wikidata supplies a ready **ontology** we can borrow as the definitional scaffold (verified live):
- `Q14204246` = *Wikimedia project page* (generic ns-4 — too broad)
- `Q4656150` = *Wikimedia project policies and guidelines page* (the useful class)
- `Q1156854` = *policy* (generic concept; e.g. on Verifiability)

**Use:** Q4656150 is a high-precision **seed/expansion signal** (when present, the page is governance). **Do not** use it as the membership oracle: coverage is inconsistent (Civility, a real behavioral guideline, lacks it) and it is a current snapshot with no history. Borrow the vocabulary; verify membership from category/template history + the late exclusion pass.

---

## 1. Definitions

### 1.1 The hard problem: the ontology is non-stationary

The formal concept of "policy" did **not** exist on enwiki in 2002. The policy/guideline/essay trichotomy crystallised ~2005–2008. Any fixed 2026 definition applied to 2003 is anachronistic. **Therefore "policy status" must be a time-varying attribute of a node, never a fixed filter.**

### 1.2 Operational definition (tiered, applied per year)

A page is in scope for year *Y* if it meets **≥1** criterion. Record which tier(s):

- **T1 — Formal status:** carries a status template that year (`{{policy}}`, `{{guideline}}`, `{{MoS guideline}}`, localized equivalents) **or** is listed on the official policy/guideline index page that year.
- **T2 — Functional:** LLM judge (frozen rubric) determines the page's *primary purpose* is to **prescribe or constrain** editor conduct, content standards, or process — normative/procedural, not informational or encyclopedic.
- **T3 — Essay/related:** explicitly marked non-binding (`{{essay}}`, `{{supplement}}`) but normative in topic. Tracked, flagged, **not** counted as binding policy.

**Excluded** (archived, not deleted): mainspace articles, noticeboards/discussion archives, user pages, purely instructional help with no normative force. Borderline → judge.

The unit recorded is the **tier label per node per year**, so the rulebook's formalization process is itself measurable.

### 1.3 Node identity

- **Within a wiki:** MediaWiki `page_id` (stable across page *moves*/renames; we resolve titles→page_id at each year). Caveat: deletion+recreation mints a new page_id; page merges end a page_id.
- **Cross-wiki:** Wikidata `QID` where one exists. QID coverage of policy pages is partial; absence is common. Wikidata itself postdates 2013 — QIDs are a *current* mapping projected backward, not a historical fact.
- **`node_id` = `{wiki}:{page_id}`** is the canonical key.

### 1.4 "Policy content" vs scaffolding

A page = normative core + scaffolding (nav, see-also, history, examples, shortcuts). Extraction is **section-level**: classify each section as normative vs scaffolding (some normative content lives in templates/tables, so don't assume prose-only).

---

## 2. Data structures

### `policy_nodes` (one row per node, identity layer)
`node_id, wiki, page_id, current_title, qid, first_seen_year, last_seen_year, discovery_method, discovery_seed`

### `policy_node_year` (one row per node × year, the core panel)
`node_id, year, title_that_year, revid, exists(bool), status_tier(T1policy|T1guideline|T3essay|T2functional|rejected), status_marker(raw template), prose_words, link_count, is_index(bool), judge_verdict, judge_confidence, rubric_version`

### `policy_edges_year` (edge list per year — the network)
`year, from_node_id, to_node_id, link_type(body|seealso|shortcut|template|index), resolved_via_redirect(bool)`

### `content_provenance` (lineage — "what content came from which page")
`year, node_id, segment_id, segment_hash, first_appeared_year, first_appeared_node, prev_node(if moved)`
Built via shingled MinHash across the whole corpus-year to detect text that migrated between pages (splits/merges).

### `rejected_candidates` (audit archive — verify later)
`node_id, discovered_year, discovered_from, judge_verdict, judge_reason, rubric_version`

### `policy_templates` (template registry — discovered per year × wiki)
`template_node_id({wiki}:{template_page_id}), wiki, year, template_name, description, role(status|lifecycle|nav|shortcut|other), is_indicator(bool), n_transclusions_in_admitted_set, discovery_method`
- Populated by observing which templates the admitted page set transcludes that year (`templatelinks`), then classifying each (seed list §1.4c + the template's own doc/description, LLM for unknowns).
- Templates flagged `is_indicator` become **reverse-lookup discovery vectors**: every page transcluding them that year (reverse `templatelinks`) is a new candidate.
- `description` comes from the template's documentation subpage or an LLM one-liner; stored so the indicator set is auditable and its meaning is captured as of that year.

### `policy_categories` (category registry — discovered per year × wiki)
`category_node_id({wiki}:{category_page_id}), wiki, year, category_name, description, role(policy|guideline|lifecycle|topical|other), is_indicator(bool), n_members_in_admitted_set, discovery_method`
- Populated by observing which categories the admitted page set belongs to that year (`categorylinks`), then classifying each.
- Categories flagged `is_indicator` become reverse-lookup discovery vectors: every member that year is a new candidate.
- Same description/audit treatment as templates.

Both registries are keyed by **year + wiki** because the indicator vocabulary itself evolves and differs per language. The §1.4c list is the *seed*, not the operative set — the operative set is discovered.

### `cross_wiki_map` (alignment layer)
`cluster_id, qid, wiki, node_id, alignment_method(wikidata|llm|manual), confidence`

### Cache = reproducibility substrate (not a tmp/ convenience)

The cache IS the pinned evidence base. Because dumps expire (~6 months), pages get deleted, and the live API drifts, the **raw layer is often the only durable copy of the exact inputs** — the entire analysis must be re-derivable from cache alone, with no re-fetch. Layout, keyed by immutable revid:

```
cache/<wiki>/
  raw/<revid>.wikitext              # immutable input — fetched once, PRESERVED (not tmp/)
  html/<revid>.html                 # immutable — only if action=parse is adopted
  clean/<cleaner_vN>/<revid>.txt     # derived from raw — keyed by cleaner version
  struct/<parser_vN>/<revid>.json    # derived from raw — links/cats/templates
manifest.sqlite                      # (page_id, year)->revid; revid->{ns, timestamp, sha256, source, fetched_at}
```

Rules:
- **raw/ and html/ keyed by revid alone** — content never changes; fetch once, keep forever. Preserved durably (Toolforge persistent storage + a publishable compressed data release), NOT in gitignored `tmp/`.
- **Provenance + hash per artifact** — record source (dump date+file, or API fetch timestamp) and **sha256** so reproduction is *verifiable*, not just fast.
- **Committed manifest** — small, version-controlled index (`revid → sha256 + source + fetched_at`); others verify their cache matches ours by hash even if blobs live outside git.
- **Derived layers version-keyed** — clean/ and struct/ regenerate from raw (never from html); the `<...vN>` path tag makes every result reproducible and attributable to a specific cleaner/parser version.

---

## 3. Workflow (human- and machine-readable)

```
PHASE A — Anchor both ends
- [A1] Fetch official policy/guideline index page for enwiki at the 2005 anchor and at 2026.
       (2005 = first year the policy/guideline structure is reliably present. Pre-2005
       history is reachable via fill-back [B6], not via a 2002 index that may not exist.)
- [A2] Parse index → seed set of titles. Resolve each title → page_id (current) → QID (Wikidata).
- [A3] First-pass content collection for seed set at both anchor years.

PHASE B — Per-year sweep (walk forward 2005 → 2026; fill-back may extend earlier than 2005)
- [B1] For year Y: resolve current node set's titles→page_id→revid (revision in effect at Y-01-01T00:00:00Z — see snapshot rule). Mark exists=Y/N (via revision history).
- [B2] Discovery vectors from the current admitted set that year (three channels):
       (i)   outlinks (`pagelinks`) → candidate pages (any namespace),
       (ii)  templates transcluded (`templatelinks`) → register in policy_templates; flag indicators; reverse-lookup all pages transcluding indicator templates that year → candidates,
       (iii) categories (`categorylinks`) → register in policy_categories; flag indicators; reverse-lookup all members that year → candidates,
       (iv)  interwiki/langlinks → cross-wiki candidate seeds (used in Phase D).
- [B3] Resolve candidate titles→page_id, resolving redirects to canonical page_id.
- [B4] ADMIT via two-gate (§1.4b): (A) rule gate — carries a discovered/seed indicator that year, OR (B) LLM gate — section-judge says "smells like policy". Admitted → node + frontier. Not admitted → record edge target + archive in rejected_candidates. Attach all observed labels.
- [B5] Snowball = iterative fixpoint over the persisted edge set: repeat B2–B4, expanding ONLY from newly-admitted nodes. Each pass is mostly set arithmetic over stored links ("which targets aren't yet nodes?"); the costly wikitext parse runs ONCE per newly-admitted (page, year), never repeated. **Stop when a pass admits nothing new** (network closed for that year). Resumable: persisted edges + admitted set let a killed run resume at the next pass. Template/category reverse-lookups are expansion too — a newly-flagged indicator surfaces a whole cohort at once. Tier-2 LLM gate runs only on the unadmitted residue after the structural fixpoint settles.
- [B6] Fill-back: for each node first discovered in Y, check its revision history for existence in Y-1, Y-2, … and backfill earlier snapshots + edges. (Discovery year ≠ existence year.)
- [B7] Write policy_node_year + policy_edges_year partials for Y (resumable, atomic).

PHASE B' — Final reduction (after the lenient OR-gate admission; reproducible, tunable)
- [B'1] Drop essays ({{essay}}) and clearly non-governance admitted pages using observable signals (templates, categories, lifecycle).
- [B'2] Reduce to normative content: drop non-policy sections/segments (lists of pages, lists of users, examples, nav) via the section-level judge.
- [B'3] Emit the reduced "real policy body" + the full admitted set + reduction reasons (archive for audit). Reduction criteria are versioned parameters; re-running with different thresholds is cheap.

PHASE C — Provenance
- [C1] Across all corpus-years, shingle+MinHash all node text.
- [C2] Detect segments appearing on a new node that previously lived on another → record lineage (split/merge/spin-out).

PHASE D — Cross-wiki alignment (after B+C done for 2–3 wikis)
- [D1] Attach QIDs to all nodes per wiki.
- [D2] Align networks by QID → matched clusters.
- [D3] For unmatched nodes, LLM semantic match across wikis → candidate equivalents.
- [D4] Gap report: policy function present in wiki X but missing/absent in wiki Y; structural divergences (different clustering of the same functions).
```

---

## 4. Scripts

**Already have (reuse):**
- `policy_drift.py` — yearly revision-index fetch + last-rev-per-year snapshot selection + mwparserfromhell cleaning. Reuse the snapshot+clean core for B1/A3.
- `collect_policy_overview.py` — seed index-page fetch + Wikidata QID resolution. Reuse for A1/A2/D1.
- `cache.py` — wikitext caching.

**To write:**
- `link_extractor.py` — parse wikilinks per snapshot, resolve redirects→page_id, classify link_type. (B2/B3)
- `policy_judge.py` — LLM gate; frozen versioned rubric; temp 0; gold-set eval harness measuring judge accuracy vs a hand-labeled set. (B4)
- `build_policy_network.py` — orchestrates the per-year sweep, snowball, fill-back; writes node/edge partials. (Phase B)
- `provenance.py` — MinHash text-reuse for content lineage. (Phase C)
- `cross_wiki_align.py` — QID alignment + LLM semantic matching + gap report. (Phase D)
- `identity.py` — title↔page_id↔QID resolution, redirect/move/merge handling (shared util).

---

## 4b. Infrastructure, scale & dev workflow

**Scale.** Derived structure is small (~50k node-years, 1–3M edge-rows, ~1.5GB snapshot text across 3 wikis — trivial for SQLite/ToolsDB). The atomic-statement layer is the only large table (~6M rows + an LLM call each). The heavy part is the **input**: dated enwiki SQL dumps (`pagelinks`/`categorylinks`/`templatelinks` are tens of GB *each, per date*) and XML history (multi-TB). Don't move those off-infra.

**Hybrid 3-stage architecture (compact handoffs):**
| Stage | Where | Why |
|---|---|---|
| 1. Structure extraction (dumps/replicas → nodes, edges, registries, yearly snapshots) | **Toolforge jobs** | Dumps mounted at `/public/dumps/`; replicas are Toolforge-only; no TB downloads. K8s `jobs` framework, not PAWS (sessions time out). |
| 2. LLM judging + atomic decomposition | **Local** (or wherever API egress works) | Toolforge outbound network is proxy-locked — external LLM APIs blocked. Operates on compact text exported from stage 1. |
| 3. Network analysis + cross-wiki alignment + plots | **Local** | Small derived tables; iterative. |
| 4. Exploration web app (graph/timeline/registry/audit views) | **Toolforge webservice** (Flask, reuse wiki-polis) | Serves ToolsDB; public, interactive; no API egress needed. |

**Data source — single full-history dump, not dated dumps (CORRECTION).** `dumps.wikimedia.org` / the `/public/dumps` mount retain only ~the last 6–7 monthly runs — there is NO multi-year archive of dated SQL dumps. So point-in-time `templatelinks`/`categorylinks`/`pagelinks` per year back to 2005 do **not** exist anywhere. Instead: history is cumulative, so the **single latest `pages-meta-history` XML dump contains every revision back to 2001**. That one (multi-TB, mounted on Toolforge, streamable) is the source of truth. We select the per-year revision per page and **parse its wikitext ourselves** (mwparserfromhell) to extract links/categories/templates as of that year.

**Namespace strip at the stub stage (key scale win).** Full-history dumps are split by page-id range, not namespace — there's no pre-made ns-4 file. But:
- Stream the **`stub-meta-history`** dump first (metadata only — page, `<ns>`, every revid + timestamp, NO wikitext; tiny vs the full dump). Filter by `<ns>` to the target set, discarding ~98% mainspace before touching content.
- Target namespaces: **all except main (ns 0)**. We drop only mainspace (articles — never policy, ~bulk of revision volume) and keep everything else: Wikipedia/Project (4), Template (10), Category (14), Help (12), MediaWiki (8), Portal (100), Draft (118), User (2), and all talk namespaces. Rationale: don't pre-judge which namespace hosts governance — nl's policy index lives in **Portal**, and "collect broad, filter late" means the namespace strip shouldn't be the filter. Admission (rule OR LLM, §1.4b) still gates what becomes a node, so the extra namespaces cost only a slightly larger candidate pool, not extra parse work (parse cost is per *admitted* node). Talk namespaces stay available for later deliberation signal.
- From the stub, compute the per-year revid per candidate: **the revision in effect at 1 January of year Y** (last revision with timestamp ≤ Y-01-01T00:00:00Z) — one fixed annual sampling instant, snapshot selection from metadata alone. A page with no revision before that instant simply doesn't exist that year.
- Fetch wikitext for ONLY the selected (page, revid) pairs — via API (fine for ~thousands) or the bz2 multistream byte-offset index. Content actually decompressed collapses from "all enwiki history" to a few thousand specific revisions. Consequences: the SQL link tables drop to a **current-state validation** role only; the reverse-lookup ("what transcludes template T in year Y") is computed by us from our own parsed node↔template table, not read from a dump; deleted pages remain censored (excluded from `pages-meta-history`); upside = one pinned, reproducible input.

**Output / exploration layer (Stage 4).** The reduced network + full admitted set live in **ToolsDB**, served by a **Flask app on Toolforge** (reuse the wiki-polis deploy pattern) for human exploration: per-year graph view, per-policy timeline, template/category registry facets, cross-wiki side-by-side, and "why excluded?" audit views. This shapes the schema now — stable node IDs, ToolsDB as canonical serving store, indexed on (year, wiki, node), and the admitted-set + reduction-reasons kept queryable.

**Dev/deploy workflow (locked):** write + test scripts locally in this repo → push to GitHub → `git pull` on the Toolforge bastion → run via `toolforge jobs run` (batch, not webservice — this is not a web app). Output to ToolsDB or the tool's data dir; commit only compact derived tables, never dumps/large intermediates (gitignore them). Claude writes the scripts; the user deploys/runs on Toolforge (SSH to the bastion is out of scope here) and pastes `toolforge jobs logs` output back for debugging.

**Script design constraints:**
- Detect environment: use replicas/dumps when on Toolforge, fail gracefully / skip when run locally (per Toolforge lessons).
- Resumable + atomic partial writes (same pattern as the imetal monthly chunking) — Toolforge jobs can be killed/restarted.
- Pin all inputs (dump date, rubric version, model id) in output metadata for reproducibility.

---

## 5. Risks / what might be missing (author's pre-review list)

1. **Non-stationary ontology** (see 1.1) — biggest conceptual trap; handled by tier-per-year.
2. **page_id is not global; no cross-wiki global id.** QID coverage partial; Wikidata is 2013+.
3. **Snowball link explosion / namespace bleed** — policy pages link to noticeboards, essays, help, mainspace. Needs depth bound + judge gate + namespace whitelist.
4. **Redirects/shortcuts** (WP:NPOV → …) inflate the graph; must resolve to canonical page_id or the network double-counts.
5. **Moves/merges/splits/deletions** break identity continuity. Deleted pages' revisions are NOT in public replicas/dumps → left-censoring of pages that died before our anchor.
6. **Survivorship bias** — snowballing from 2026 misses pages deleted earlier; walking forward from 2005 mitigates but can't recover deleted content.
7. **LLM judge reproducibility** — needs frozen prompt + rubric version, temp 0, and a human gold set to report precision/recall. Judge drift across model versions is a reproducibility hazard.
8. **Revision selection — DECIDED:** snapshot = revision in effect at **1 January of year Y** (last rev ≤ Y-01-01T00:00:00Z). One fixed annual instant. Revisions deferred to later; mid-year creation/deletion handled by exists=N when no revision precedes the instant.
9. **Historical text source** — per-year full-corpus via API is many calls; PAWS dumps may be far cheaper and give point-in-time wikitext. Decide API vs dump early.
10. **Edge semantics** — which links count as governance edges? Body links only, or see-also/templates too? Different choices = different networks; must be explicit and consistent.
11. **Content extraction granularity** — section-level normative classification is itself an LLM/heuristic task with its own error rate.
12. **Cost** — LLM judge over thousands of candidate-page-years × multiple wikis. Need batching, caching by (page_id, revid), and a cheap pre-filter before the judge.
```
