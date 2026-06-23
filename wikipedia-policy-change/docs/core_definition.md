# Core Membership — Operational Definition

The rule that decides whether a page is **core** (active policy/guideline) for a given
**(wiki, year)**. This is not a fixed list — it is **rebuilt per language** and **reconstructed
per year**, because the indicators (banners, categories, templates) differ by wiki and shift over
time. Used by `net_build_current.py` (current year, SQL) and `net_build_historical.py` (past
years, wikitext). Companion: [`ROADMAP.md`](ROADMAP.md) M4, [`atomic_statements_design.md`](atomic_statements_design.md).
This doc is **page-level** classification; the full page→content classification framework
(and the shift to content-level) is in [`classification.md`](classification.md).

---

## 1. Positive evidence FOR core (that year)

Any one suffices. All are evaluated **as of that year** (1-Jan snapshot).

- **Status banner** — the page carries a policy/guideline status template that year
  (`{{policy}}`, `{{guideline}}`, `{{MoS guideline}}`, `{{naming conventions}}`, … and their
  per-wiki equivalents / redirects).
- **Core category** — member of a designated core policy/guideline category that year.
- **Indicator template** — transcludes a discovered indicator (status) template that year.
- **Current-year only (SQL/Wikidata)** — `templatelinks` to a status template; core-category
  membership; or Wikidata `P31 = Q4656150`. (Replica/Wikidata are current-state only, so these
  apply to the live slice; past years use the wikitext-derived signals above.)

## 2. Positive evidence for NON-core (that year)

Any one demotes the page that year:

- **Absent** — no revision exists at 1-Jan of that year (page not yet created / already deleted).
- **Lifecycle/essay banner** — carries `{{essay}}`, `{{supplement}}`, `{{information page}}`,
  `{{how-to}}`, `{{proposed}}`, `{{draft proposal}}`, `{{failed proposal}}`, `{{rejected}}`,
  or `{{historical}}` (and per-wiki equivalents). This is the page *declaring* it isn't active
  policy.

## 3. Resolution — expansive, never reductive by noise

For a page in year Y:
1. **Positive non-core evidence (§2)** → **not core** (absent → no row; lifecycle banner →
   `candidate`, `status_tier` = the lifecycle tag).
2. **Else positive core evidence (§1)** → **core** (`admitted_via='status_template'` when an
   explicit banner was detected — the promotion signal).
3. **Else no evidence either way** → **inherit**: core if it was core in an adjacent year
   (stickiness), `admitted_via='inherited'`. A mere *absence of a detected banner is regex noise,
   not a demotion.* Policy status is sticky; only §2 evidence reduces it.

This makes membership a clean monotonic step (creation/promotion boundary), not a flickering
signal. Anchored on the current build, which is ground truth (every seed page is core in 2026).

---

## 3a. Namespace-4 page routing — policy vs. venue vs. deliberation

The project namespace holds far more than policy. Pages are **routed by positive evidence into
layers**; the excluded layers are **not discarded** — each is its own dataset (deliberation feeds
the RfC / wiki-polis analysis; enforcement venues feed the governance-process analysis; historical
policy feeds the reform/death analysis). Never silently delete; keep an explicit **Other** for the
unrouted, which is the falsifiability check on the scheme.

The two discriminators are **permanence** and **codified procedure** — *not* the presence of
support/oppose !vote templates (noticeboards and consultations both use them) and *not* whether an
admin tool is involved.

| layer | nature | route / temporal |
|---|---|---|
| **Live policy/guideline** | the norms (§1) | **core**, per-year status |
| **Request / enforcement** (noticeboards, deletion/adminship/protection requests, arbitration) | permanent **+ codified procedure** | **governance-venue layer** — the standing rules page is procedural policy (user-admin); the case-stream is the enforcement record |
| **Discussion page** (village pump, help/reference desks, project talk) | permanent **+ free-form** | discussion corpus; not policy |
| **Consultation** (a specific RfC/survey/Meinungsbild on one question) | **one-off** | deliberation corpus; **backward-invalidate** (event-shaped, must not read as policy change) |
| **Archive** (`/Archive…` + archive markers) | frozen | drop, or route to deliberation if a closed RfC |
| **Historical policy** (`{{historical}}`/`{{superseded}}`) | retired | lifecycle store; **forward-invalidate** (was relevant, no longer) |
| **Container / index / Other** | — | review (see `data/network/core_audit.csv`) |

**Temporal asymmetry:** consultation and archive pages are invalidated *backward* (they were never
standing policy); historical policy is invalidated *forward* (it was policy, then stopped). These
are different operations, not one "exclude" flag.

**Detection is wiki-dependent (same rule as §4/§5).** The layer *concepts* above are universal;
the *signals* that detect them are per-wiki and reconstructed, never hardcoded English:
- **Venue identity** by langlinks of enwiki venue anchors (Articles for deletion, the
  administrators' noticeboard, the village pump, requests-for-X) → their per-wiki equivalents
  (nl `Te beoordelen pagina's` / `De kroeg`; de `Löschkandidaten` / `Umfragen` / `Meinungsbilder`;
  fr `Pages à supprimer` / `Le Bistro` / `Appel à commentaires`).
- **Type templates** discovered per wiki (an RfC/survey banner → consultation; a noticeboard
  header/case template → request-enforcement), scored against that wiki's confirmed set the same
  way policy indicators are, and recorded in the year-keyed `template_registry`.
- **Subpage shape** as a weak cue (a dated/titled child of a venue = instance; the venue root =
  standing page) — confirmatory, not decisive.

So the routing indicators live alongside the policy indicators in the per-(wiki, year) registries
and are auditable the same way.

---

## 4. Rebuilt per language

The indicator **names** are language-specific — never hardcode English. For each wiki, the
banner/category/template set is reconstructed by:
- Wikidata classes (language-agnostic): `Q4656150` (policy/guideline page), `Q11753321` (navbox).
- Langlinks of the enwiki indicators (root category, status templates).
- Per-wiki discovery: scored category/template membership anchored on that wiki's confirmed set
  (the same loop as the current build), plus the template-category "policy and guideline templates".

The §1/§2 evidence *kinds* are universal; their *spellings* are resolved per wiki.

## 5. Reconstructed per year (definitions drift)

The indicator set itself shifts over time: status templates get renamed, categories are created
or merged, the policy/guideline ontology evolves. So the indicator set is reconstructed for each
**(wiki, year)** from that year's state and **recorded** in the year-keyed `category_registry` /
`template_registry` (so every year's definition is auditable).

**Back-compatibility (expected, not assumed):** an indicator valid in year Y is usually valid in
Y±1; template renames are followed via the redirect graph as of that year. Where the definition
genuinely changes, the per-year registry captures it — we do not retro-apply a single definition
across all years.

---

## 6. Per-year expansion (Phase 2 — the node set grows backward)

Phase 1 walks only the fixed current core. Phase 2 makes each year **discover its own members**:

- **The overview page, per year (curated ground truth).** Parse the 1-Jan-Y version of the
  official index (`Wikipedia:List of policies and guidelines` and per-wiki equivalents — we
  already fetch the current ones in `collect_policy_overview.py`). Its links are the community's
  own roster of what was policy/guideline *that year*; its section ("Policies" / "Guidelines")
  gives `status_tier` directly. This is the highest-precision per-year membership source AND the
  main remedy for Phase-1 survivorship bias: pages listed in an old overview but absent from the
  2026 seed are exactly the historical-only policies (merged/deleted/renamed) Phase 1 misses.
  *Caveats:* the list page may not exist / be sparse before ~2007 (the framework crystallized
  then); it gets restructured over 20 years, so section→tier mapping is reconstructed per year.
- For year Y, also find pages that, *that year*, sat in a
  core category or transcluded an indicator template (parsed from each snapshot's wikitext
  `[[Category:…]]` / `{{template}}`), scored against the confirmed-that-year set.
- New members not in the current seed → added with their active-year interval. This is how
  **historical-only pages** (since merged, deleted, or renamed away) enter the network.
- Their in-body links surface further candidates → repeat (the per-year fixpoint), bounded the
  same way as the current build.

So the node set is the **union over all years** of each year's discovered core, not a projection
of 2026 backward. Discovery year ≠ existence year (fill-back).

---

## 7. Reproducibility

Every membership decision traces to its evidence: `provenance` records the indicator + score that
surfaced each page; the year-keyed registries record the indicator set in force that year;
`build_run` pins the git commit + thresholds. Re-running any (wiki, year) reproduces the same
core from the cached snapshots.
