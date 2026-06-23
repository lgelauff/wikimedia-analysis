# Policy Network — Design (v0, brainstorm processed)

**Goal:** Reconstruct the *body* of Wikipedia governance (policies + guidelines + related normative pages) as an annual, evolving **network** for 2–3 language wikis, then align the networks cross-lingually via Wikidata QIDs to find structural gaps and divergences.

This supersedes the per-page drift framing: a policy page is a node in a temporal graph, not an independent time series.

---

## Research question + hypotheses (M0)

**Primary RQ: Where do language editions *truly* diverge?** — in which policy domains and on which norms do editions develop genuinely different governance, as opposed to merely lagging, translating, or neglecting a shared template?

The operative word is **"truly."** Apparent divergence has four causes; only the last is the target:
1. **Coverage gap** — a policy simply doesn't exist (yet) in that edition.
2. **Translation lag** — imported from en, not yet re-synced; looks divergent, isn't independent.
3. **Abandonment** — an imported translation left to rot; divergence by neglect, not choice.
4. **Genuine divergence** — both editions active, normative content actually differs by editorial choice. ← *the target*

Answering it = a **divergence map**: for each cross-wiki-matched policy cluster (M9), a divergence score + a classification into the four causes (via the genetic/functional `relationship` field + per-node activity), projected onto the topical structure of the network (content / conduct / deletion / notability / procedure …) so we can see *where* genuine divergence concentrates.

**Secondary RQ: what does genuine policy *reform* look like, when it happens? — develop case studies.** If reform is rare (H1/H2), the reform events are the informative tail; the right method for a small-N tail is the case study, not statistics. This RQ also **joins the two tracks**: a true reform should have a *deliberation* behind it (an RfC / Village Pump discussion + closing rationale), so each case study links the textual reform to the governance process that produced it.

*True reform* = a transition that **replaces or inverts a norm**, not additive accretion or defensive detail (and not a cleaning/markup artifact, not a page move, not a bot/revert). Detection → case-study pipeline:
1. **Candidate detection (Tier-1, cheap):** rank node-year transitions by a reform score — low `containment_old_in_new` (old text gone) + large net change + `cosine` drop — on mwparserfromhell-cleaned data. *Early win: runnable now on the existing drift CSVs.*
2. **Artifact filter:** drop template/markup churn, page moves, bot edits, and changes that revert within N snapshots (non-durable).
3. **Cross-page reform:** catch reform that happened via merge/split/spin-out, not in-place rewrite (uses the provenance/lineage layer — content moved *and transformed*).
4. **Semantic confirmation (M7/M8):** did a normative principle actually change (rule added/removed/inverted, threshold moved, scope changed), vs reorganization? Classify reform type.
5. **Rank + select exemplars** across domains (content / conduct / deletion / notability / procedure).
6. **Case study each:** before/after norm; triggering revision(s) + editors; the associated **RfC/VPP deliberation + closing rationale** (RfC track); timeline; durability (did it stick or get rolled back?); and — for satellite wikis — whether the reform was independent or followed en (ties to H5 / the divergence map).

**Third RQ: what are the inflection points in Wikipedia policy development? — when did the trajectory bend?** System-level and temporal (complements RQ1's *where* and RQ2's *what* — together: where / what / when). Inflection points = regime shifts in the aggregate policy system: bursts or collapses in new-policy creation, the **onset of ossification** (when per-node change rate dropped — when did it freeze?), reform waves (temporal clusters of RQ2 events), structural reorganizations (the ~2005–07 formalization of the policy/guideline distinction; major mergers like WP:ATT), and editor-base-driven shifts.

Operationalization:
- Build aggregate annual series per wiki: new-node count, reform-event count, total corpus size, mean per-node change, new-edge count, network density.
- **Change-point detection** (e.g. PELT / Bayesian) on each series → candidate inflection years. *Must run on M5-normalized series* — a change-point in raw density is a growth artifact, not a regime shift.
- Qualitative overlay: align detected inflections with known external events (editor-base growth curve, major controversies, WMF/governance milestones) — association, not causation (n=3).
- **Cross-wiki:** are inflection points synchronized (shared external driver) or staggered/lagged (each community matures on its own clock)? Staggered + lagged ossification onset is direct evidence for H5 decoupling / independent maturation.
- *Early proxy:* change-points on raw aggregate series testable at Tier-1 (M2/M4); the defensible version needs M5.

Overarching thesis behind it: **mature Wikipedia policy ossifies and accretes defensively rather than reforming; satellite editions decouple from en over time — and the three RQs ask *where* that decoupling is real, *what* the rare genuine reforms look like, and *when* the trajectory bent.** Five falsifiable sub-hypotheses feed the RQ. H1 and H2 are a spectrum and must be tested *against* each other (is there much change at all → H2; and when there is, is it additive → H1); H5 + the artifact-disambiguation above are what make the RQ answerable.

| # | Hypothesis | Operationalization (metric) | Null | Tested by |
|---|---|---|---|---|
| **H1** | Policies add content but rarely reform | Per snapshot pair: word_count ↑ while `containment_old_in_new` stays high (old text retained); a "reform" = `containment_old_in_new` below threshold τ. Predict reforms are rare vs additions; added ≫ removed. | Reforms occur at a rate comparable to additions (old text frequently replaced). | **Tier 1** (drift metrics) — *partially testable on existing 10-policy data now* |
| **H2** | Policies are mostly frozen — limited meaningful change | Per-node change magnitude (`1−cosine_vs_prev`, net word change) declines with policy age and calendar year; recent years → cosine ≈ 1. Trend test. | Change rate is constant or rising over time. | **Tier 1**. Separate per-node stasis from system growth (new nodes) — both can hold. |
| **H3** | Changes are defensive: more verbose, more edge cases, more detail, responding to specifics | Added content skews to exceptions/qualifiers/clarifications/procedure over new principles; linguistic defensiveness rises (conditionals, "except/unless", cross-refs, sentence length, specificity). | Additions introduce new principles at the same rate as defensive detail. | **M8 atomic** (statement-type classification) + cheap linguistic features earlier |
| **H4** | New policies mostly exist to stop people doing things | New policy *nodes* skew proscriptive (deontic: prohibition > permission/obligation) and cluster in conduct/enforcement regions of the network. | New policies are balanced proscriptive/permissive-enabling. | **M8** (deontic polarity) + **network** (new-node topical placement) |
| **H5** | Over time, other-language wikis develop their own policy preferences and follow enwiki less | (a) **Structural:** share of a wiki's nodes matched to an en node (via QID∪langlink) declines over years; (b) **origin:** share of *new* nodes that are independently created (no en equivalent) rises; (c) **content/genetic:** for matched policies, the genetic (translated-from-en) signal weakens and cross-lingual divergence grows; (d) **lead-lag:** early de/nl change events follow en changes at a lag; coupling weakens over time. | Coupling to en is constant over time (stable matched-share, persistent lead-lag) — or was never present (no initial high overlap). | **(a) Tier-1 network** (early proxy, M2/M4) · **(b)/(c)/(d) M9** + atomic |

**Cross-wiki angle (de/nl):** is ossification (H2) and defensive accretion (H3) a *universal* property of mature peer-governance, or en-specific? And do the satellite wikis *decouple* from en over time (H5)? n=3 (really en + 2 test wikis) caps this to existence/typology claims, not general inference.

**H5 measurement subtleties:** "follows en less" is measured against a *moving target* — en is itself ossifying (H2), so apparent divergence could be (i) en freezing while others keep evolving, (ii) others actively moving away, or (iii) others simply *neglecting* an imported translation (abandonment, not independence). These must be distinguished: pair the genetic/functional `relationship` field (M9) and per-node activity (is the diverging node still being edited?) to separate active divergence from abandonment. The structural proxy (a) is testable at Tier-1 without the atomic layer — a potential early signal.

**Confounds to control (all):** the mwparserfromhell cleaning fix is mandatory — the old regex manufactured phantom "change" (template nesting) that would masquerade as reform/anti-ossification; bot/category-only edits; survivorship (frozen-then-demoted `{{historical}}` pages vs active); and the growing-panel null-model requirement (M5) for any network-level H4 claim.

**Early win:** H1 and H2 are partially testable *right now* on the existing mwparserfromhell-cleaned 10-policy drift CSVs — a cheap pilot before the full build.

---

## Build decisions (this session)

- **First wikis:** en + de + nl (contrasting structures: en two-tier hierarchy, de flat list, nl Portal-namespace index) → scale to 5 later.
- **Next action:** build the 2026 SQL slice (enwiki current network from replica tables — no dumps, no LLM).
- **Tier-2 judge model:** cheap tier (Haiku-class); validate accuracy on a gold set.
- **Body scope (supplements/information pages in/out):** DEFERRED — capture + flag now, decide inclusion later.

---

## Review round 2 — corrections & decisions

Three-reviewer panel (data-engineering, methodology, LLM). Full reviews in `.claude/policy_network_review2_{data,method,llm}.md`.

**New decisions:**
- **Namespace policy = exclusion-based, not inclusion.** Exclude main (ns 0) + a per-wiki list of clearly-non-governance namespaces; default-include the rest. Projects differ — some wikis host essays/governance in User space — so an allowlist would miss things; we blocklist instead. (Accepts a larger historical scan than a governance whitelist; the 2026 SQL slice is unaffected.)
- **Tier-2 judge = cheap-draft / strong-verify** (two-stage): cheap model first pass, strong model re-checks negatives near the threshold.

**Must-fix corrections (fold into the relevant sections before building):**
1. **LLM-admitted nodes do NOT expand the frontier.** Only rule-positive nodes expand; LLM-admitted nodes are labeled but are traversal dead-ends. Otherwise the node *population* becomes judge-version-dependent.
2. **Replica schema (2026 build):** `cl_to` is removed; `pagelinks`/`categorylinks`/`templatelinks` all go through the shared **`linktarget`** table (`*_target_id` → `lt_namespace`, `lt_title`). No cross-DB joins on replicas → Phase D QID alignment is two-step. Recursive category descent = BFS in code, not one SQL query. Namespace numbers/names per wiki from `siteinfo`, never hardcoded English prefixes.
3. **No bz2 multistream index for HISTORY dumps** (only current-articles). API-by-revid is the primary wikitext fetch; stream-by-part is the offline fallback.
4. **Inference gate (the #1 threat, still open):** no quantitative network metric (density, centrality, modularity, diameter) may be reported until size-normalized against a **null/configuration model** and detrended for panel growth. Template/navbox edges inject complete-subgraph artifacts — handle explicitly.
5. **Bootstrap selection bias:** the discovered-indicator snowball is homophilous — under-finds vocabulary-divergent / link-isolated governance on de/nl (the very cross-wiki signal of interest). Estimate miss-rate via capture–recapture across independent frames.
6. **1-Jan off-by-one:** the 1-Jan-Y snapshot = state at end of Y−1; label time-series accordingly. Detect lifecycle status transitions (proposed→rejected/promoted) at *event* resolution from the stub; use annual snapshots for topology only.
7. **Cache key bug:** add `model_id` to verdict cache keys (verdicts collide on model switch); `rubric_version` = content-hash; verdict cache is a first-class publishable artifact. For raw revisions, default to publishing **manifest + hashes only** (CC BY-SA attribution obligation) rather than the text blobs.
8. **Atomic layer:** define the unit as **extractive, span-anchored** (deontic-marker-*informed* but not required); statements are **entities with lifespans** (version-on-change), not per-year snapshots. No hard pre-gate — pilot first and watch the quality metrics diagnostically (they may become gates before a formal claim). Full design: [`atomic_statements_design.md`](atomic_statements_design.md).
9. **Cross-wiki matching:** block by (QID ∪ langlink) → embedding-ANN → LLM-verify top-k. Never O(n²). Add a `relationship` field (genetic/copied vs functional/convergent) backed by external evidence; use known translations as a positive control.
10. **Validity hygiene:** state falsifiable hypotheses + their nulls (currently descriptive only; n=3 caps cross-wiki to typology + existence claims); inter-coder reliability (κ, ≥2 coders) at all three judging layers; pre-register the reduction threshold τ and report metrics as curves over τ.

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
- **Tier 2 — semantic (the fuzzy ~20%, LLM):** "smells like policy" admission for pages with no rule signal (§1.4b-B), section-level normative classification, atomic-statement decomposition, cross-wiki atomic matching. Applied only where Tier 1 doesn't decide. Runs off-Toolforge — *not* because egress is blocked (it isn't), but for secrets hygiene (no API keys on shared infra), cost, and acceptable-use spirit (don't run a commercial LLM pipeline on donated infra).

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

**Scale.** Derived structure is small (~50k node-years, 1–3M edge-rows — trivial for SQLite/ToolsDB). The atomic-statement layer does NOT explode if modelled as statement **entities with lifespans** (version-on-change), not per-year snapshots: ~450k rows / ~150 MB, with only the ~2 GB of embeddings leaving SQLite for a vector store. Full storage tiers, size budgets, and the ToolsDB-quota constraint live in [`data_architecture.md`](data_architecture.md); the statement model in [`atomic_statements_design.md`](atomic_statements_design.md). The heavy part is the **input**: dated enwiki SQL dumps (`pagelinks`/`categorylinks`/`templatelinks` are tens of GB *each, per date*) and XML history (multi-TB). Don't move those off-infra.

**Hybrid 3-stage architecture (compact handoffs):**
| Stage | Where | Why |
|---|---|---|
| 1. Structure extraction (dumps/replicas → nodes, edges, registries, yearly snapshots) | **Toolforge jobs** | Dumps mounted at `/public/dumps/`; replicas are Toolforge-only; no TB downloads. K8s `jobs` framework, not PAWS (sessions time out). |
| 2. LLM judging + atomic decomposition | **Local** | Off-Toolforge for secrets hygiene / cost / acceptable-use spirit — NOT because egress is blocked (outbound is generally available). Operates on compact text exported from stage 1. |
| 3. Network analysis + cross-wiki alignment + plots | **Local** | Small derived tables; iterative. |
| 4. Exploration web app (graph/timeline/registry/audit views) | **Toolforge** (static export preferred for annual read-only data; or thin Flask over precomputed ToolsDB tables) | Serves precomputed output; keep heavy compute in jobs, not the request path. |

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
