# Policy Network — Roadmap

**Primary RQ: where do language editions *truly* diverge?** — which policy domains/norms genuinely differ by editorial choice, vs merely lagging, translating, or neglecting a shared template. Deliverable = a divergence map (M9). See [design §RQ](policy_network_design.md).

Actionable companion to [`policy_network_design.md`](policy_network_design.md). Milestones are ordered by dependency; the two-tier split means **Tier 1 (structural) ships a usable artifact before any LLM spend**, and the methodology gate (M5) blocks *quantitative claims*, not the build.

Decisions in force: first wikis **en + de + nl**; **exclusion-based** namespace policy; **cheap-draft/strong-verify** judge; supplements/info-page body-scope **deferred**; snapshot = **state at 1 Jan** (label = end of prior year).

Legend: 🟢 runs local · 🔵 runs Toolforge · ⚪ either · ⛔ gate (stop & validate).

---

## M0 — Hypotheses + null-model plan  ⛔  🟢
The #1 unresolved risk (both review rounds). **Hypotheses now defined** — see [design §Hypotheses](policy_network_design.md): H1 additive-not-reform, H2 ossification, H3 defensive accretion, H4 new-policy-as-prohibition, H5 cross-wiki decoupling (satellites follow enwiki less over time). Thesis: mature policy ossifies and accretes defensively rather than reforming; satellite wikis decouple over time.
- Deliverable: per-hypothesis metric + null + test layer (done, in design); pre-register reform threshold τ and trend tests; n=3 caps cross-wiki to typology/existence.
- **Early win:** H1 + H2 are partially testable now on the existing mwparserfromhell-cleaned 10-policy drift CSVs — cheap pilot before the full build.
- **Gate:** no quantitative network metric ships until M0 + M5 exist. Parallelizable with M1–M4.

## M1 — 2026 enwiki structural slice (Tier 1, SQL)  🔵
The agreed next build. Current network from replica tables — no dumps, no LLM.
- Scripts (new): `schema.sql` (nodes/edges/registries), `net_build_current.py` (SQL extraction + fixpoint). Reuse: `collect_policy_overview.py` (seed index + QID), `cache.py`.
- **Correct schema** (review 2): `page`; `categorylinks`/`pagelinks`/`templatelinks` via shared `linktarget` (`*_target_id`→`lt_namespace`,`lt_title`); `redirect`; `page_props` (wikibase_item); `langlinks`. BFS for category descent (not recursive SQL). No cross-DB joins.
- **Expand-gate fix:** only rule-positive nodes expand the frontier; LLM-admitted (later) label-only.
- Deliverable: enwiki 2026 nodes + edges + template/category registries in SQLite (→ ToolsDB). The canonical schema everything else targets.
- **Gate:** sane node count; measured hop-depth fan-out; indicator categories/templates spot-checked.

## M2 — Extend current slice to de + nl  🔵
Same script; per-wiki `siteinfo` namespace maps; exclusion-based ns policy (exclude main + per-wiki noise list, default include).
- Deliverable: 3-wiki 2026 networks.
- **Gate:** nl policy index (Portal namespace) is actually discovered; de flat-list structure represented; cross-wiki structural shapes look plausible.

## M3 — Exploration web app skeleton (Tier 1)  🔵  *(parallelizable)*
Flask on Toolforge, reuse wiki-polis deploy pattern. Serves the current 3-wiki network from ToolsDB.
- Deliverable: graph view by wiki, node detail, registry facets, "why admitted?" audit view.
- No API egress needed; depends only on M1–M2 output.

## M4 — Historical reconstruction (Tier 1, dumps)  🔵
The annual time series. Stub-driven, resumable, API-by-revid (no history multistream index exists).
- **Pre-gate ⛔:** verify `stub-meta-history` availability + size for en/de/nl on `/public/dumps`; time a namespace-filtered streaming pass. If infeasible, fall back to API revision-index reconstruction.
- Scripts (new): `stub_inventory.py` (stream stub, exclusion-filter ns, → 1-Jan revid per page-year into `manifest.sqlite`), `fetch_revisions.py` (API-by-revid → `cache/raw/`, hash + provenance), `parse_structure.py` (mwparserfromhell → `cache/struct/`: links/cats/templates), `net_build_historical.py` (per-year fixpoint + fill-back).
- Reuse: the snapshot-selection + mwparserfromhell core from `policy_drift.py`.
- Cache = reproducibility substrate: `raw/` immutable by revid; `clean/<vN>`,`struct/<vN>` version-keyed; manifest with sha256 + source + fetched_at.
- Deliverable: annual structural network 2005→2026 for 3 wikis; fill-back extends pre-2005 where pages predate the anchor.
- **Gate:** fill-back correctness; convergence of the fixpoint per year; bot-edit contamination check on snapshots.

## M5 — Inference layer  ⛔  🟢
Makes network metrics defensible. Pairs with M0.
- Deliverable: null/configuration-model baselines + size-normalization + detrending for every reported metric; capture–recapture estimate of the bootstrap miss-rate (homophilous selection bias) across independent discovery frames; explicit handling of template/navbox complete-subgraph artifacts.
- **Gate:** no density/centrality/modularity/diameter claim ships without this.

## M6 — Tier-2 LLM admission (rule-negative residue only)  🟢
Cheap-draft / strong-verify. Residue is small (~1–2k pages) so cost is single-digit dollars.
- **Pre-gate ⛔:** gold set first — 2 sets (~300–400), stratified by wiki×era×namespace×difficulty, ≥2 coders at 100% overlap, κ≥0.7 on human labels, **recall ≥ 0.95 per language** (false-rejects unrecoverable; report per-language, never pooled).
- Scripts (new): `policy_judge.py` (versioned rubric content-hash; cache keyed by `(page_id, revid, rubric_version, model_id)` — the missing `model_id` was a correctness bug), `gold_eval.py`.
- Deliverable: expanded admitted set + per-language accuracy report. LLM-admitted nodes label-only (don't expand).

## M7 — Final reduction + body definition  ⚪
Strict reduction after lenient admission.
- Drop essays; section-level normative classification (drop lists-of-pages/users, examples, nav). Supplements/info-page inclusion = **deferred decision** (capture + flag now).
- Reduction threshold τ pre-registered; metrics reported as curves over τ.
- Deliverable: reduced "policy body" + full admitted set + reduction reasons (audit archive).

## M8 — Atomic-statement layer  ⛔  🟢
The project's core unit — highest-risk, currently least-specified.
- **Pre-gate ⛔:** operational unit = extractive, span-anchored, deontic-marker-anchored (NOT generative). Do not start until run-to-run stability + human boundary-F1 + coverage clear pre-registered thresholds.
- Deliverable: atomic statements per node-year (~100–300k section-level calls, not millions).

## M9 — Cross-wiki alignment  🟢
At the atomic level; the only level where cross-wiki comparison is meaningful.
- Architecture: block by (QID ∪ langlink) → embedding-ANN → LLM-verify top-k. Never O(n²).
- `relationship` field (genetic/copied vs functional/convergent) from external evidence; known translations as positive control (ties to the earlier translated-page work).
- Deliverable: cross-wiki cluster map + gap report (absence disaggregated by cause, not symmetric).
- **Tests H5** (cross-wiki decoupling): matched-share over years, new-node independence, genetic-signal decay, lead-lag coupling. Distinguish active divergence from abandonment via the `relationship` field + per-node activity. Structural proxy H5(a) testable earlier at M2/M4.

## M10 — Analysis + write-up  🟢
Hypotheses from M0 tested with M5 machinery; cross-wiki typology from M9; web app (M3) as the public artifact.

---

## Cross-cutting (every milestone)
- **Reproducibility:** pin dump run-id + part filename + siteinfo; sha256 every cached artifact; publish manifest + hashes (raw text only with CC BY-SA attribution).
- **Versioning:** cleaner `vN`, parser `vN`, rubric content-hash, model_id — all in output metadata.
- **Inter-coder reliability** (κ, ≥2 coders) at all three judging layers: admission (M6), section/reduction (M7), cross-lingual match (M9).
- **Dev/deploy:** write+test local → push GitHub → `git pull` + `toolforge jobs run` (batch) / webservice (M3). Resumable atomic partials throughout.

## Critical path & parallelism
- **Critical path:** M1 → M2 → M4 → (M6 → M7) → M8 → M9 → M10.
- **Parallel:** M0/M5 (methodology) alongside M1–M4; M3 (web app) after M2.
- **Hard gates:** M0/M5 before quantitative claims · M4 pre-gate (dump feasibility) · M6 pre-gate (gold set) · M8 pre-gate (unit validation).
- **Ship-early:** M1–M4 deliver a complete descriptive structural network + web app with zero LLM spend; the LLM tier (M6–M9) layers on after.
