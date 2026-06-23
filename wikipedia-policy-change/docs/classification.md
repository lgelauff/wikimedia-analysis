# Classification — page-level (built) → content-level (next)

Classification is the spine of this project: the end goal is comparing *atomic policy elements
across languages*, and that depends on a chain of classifications — what is policy, what kind of
policy, and (the next frontier) what each piece of text inside it is *doing*.

There are two resolutions at which we can classify: the **page** and the **content**. Everything
we have built so far classifies the **page**, from page-level signals. The comparison we actually
want can only be done on the **content**. This document lays out both levels as one framework and
marks the shift between them.

**Guiding principle:** policy-ness — and policy *type* — is decided by **content**, not by graph
position or admission path. Page-level signals are *priors*, not verdicts (low degree ≠ not-policy;
boilerplate is still policy; an ambiguous page is reviewed, never auto-demoted). Page-level
classification casts the recall net; content-level classification supplies the precision.

---

## 1. Page-level classification — what we've built

Three stacked questions, all answered from **page-level** evidence (status banners, categories,
Wikidata items, in-body link structure, venue/subpage shape). Each is reconstructed **per wiki**
and **per year** (concepts universal, signals language-specific).

### 1a. Membership — *is this page core policy at all?*
Positive/negative evidence, expansive, sticky. → [`core_definition.md`](core_definition.md) §1–3.

### 1b. Page type — *policy, or a venue / discussion / archive?*
The namespace-4 **router**: live policy/guideline · request-enforcement (noticeboards) ·
discussion (village pump) · consultation (one-off RfC/survey) · archive · historical policy ·
container/Other. Discriminator = **permanence × codified-procedure**. Excluded types are kept as
their own datasets (deliberation → the RfC/wiki-polis corpus; historical → the reform corpus).
→ [`core_definition.md`](core_definition.md) §3a.

### 1c. Governance object — *what does the policy govern?*
DeDeo (2016) typology — **content / user-user / user-admin** — assigned **structurally** by
personalized-PageRank from seed anchors over the link graph.
→ [`../net/classify_governance.py`](../net/classify_governance.py), FINDINGS #5,
[`related_work.md`](related_work.md).

**Facets recorded alongside** (orthogonal axes, not one label): `origin` (community / wmf),
`tier` (policy / guideline / essay), `generality` (foundational / general / local), and the
`core_audit` buckets (legal · style · transliteration · …). → `data/network/core_audit.csv`.

### The limits of page-level — why content-level is needed
1. **A page is multi-type.** One page mixes content rules, conduct rules, procedure, summaries,
   and scaffolding. Page-level forces a single label and *hides the mixture* — exactly the
   limitation DeDeo hit (single-label coding, κ=0.59; disagreements were the genuinely mixed
   pages).
2. **The governance assignment (1c) is a structural proxy, and partly circular** — it is
   PageRank-over-structure, and we validate it with Louvain over the *same* structure. It shows
   self-consistency, not content truth.
3. **Verbosity and interconnection are conflated** — links-per-page mixes "how interconnected"
   with "how detailed." Page-level can't separate them (FINDINGS #3).
4. **Policy-ness itself is content** — the page signals are priors; the verdict isn't on the page.

---

## 2. Content-level classification — what we want next

Classify the **text**, not the page. The unit is the **atomic normative statement** (extractive,
span-anchored; deontic-*informed* but not deontic-*required* —
[`atomic_statements_design.md`](atomic_statements_design.md),
M8). Each classification below is per-*statement*, so the **page becomes a composition** over them
rather than a single label.

### 2a. Segment type — *what is this piece of text doing?*
`rule | procedure | summary | meta | scaffolding`. `rule` and `procedure` are genuine policy
elements; `summary` links to the rule it restates (double-counting guard); `meta`/`scaffolding`
are excluded from the statement count. → `atomic_statements_design.md` §1a.

### 2b. Governance object per statement — *content / user-user / user-admin*, grounded
A statement almost always governs **one** object ("cite your sources" = content; "don't insult
editors" = user-user). So the **page's content/user/admin split becomes a measured mixture**, not
a forced vote — this dissolves both DeDeo's single-label problem and the circularity of 1c, by
replacing the structural proxy with a content-grounded measure.

### 2c. Deontic type — *obligation / prohibition / permission / definition*
From the deontic markers that anchor the statement boundaries. Tests **H4** (new policy arrives as
prohibition).

### 2d. Cross-wiki element alignment — *the same rule in another edition?*
At the statement level only (the only level where cross-wiki comparison is meaningful). Block by
QID∪langlink → embedding-ANN → verify; unmatched element → targeted net expansion. → M9.

### What content-level unlocks
- the multi-type page becomes a **measured composition** (2a/2b);
- **verbosity (statements/page) separates from interconnection (links/statement)** — resolves
  FINDINGS #3's confound;
- the governance split stops being circular — **content-grounded, not structural** (2b);
- recall gaps become **element queries**, not silent misses (2d / M9 net expansion);
- statement **identity over time** (via WikiWho token provenance — `atomic_statements_design.md`
  §2a) gives birth/death/edit = H1/H2/H3 directly.

---

## 3. The shift, and what carries over

| | **Page-level (built)** | **Content-level (next)** |
|---|---|---|
| role | recall net + routing | precision + the unit of comparison |
| unit | the page | the atomic statement |
| signals | banners, categories, QID, link position, venue shape | the cleaned text + deontic markers |
| governance type | structural proxy (PageRank) | content-grounded (per statement) |
| page is… | forced into one label | a composition over its statements |
| status | core_definition + classify_governance + core_audit | M8 (gated) + M9 |

The **same axes recur at both levels** — governance object appears page-level as a structural
proxy (1c) and content-level as a grounded measure (2b); the content-level value is the ground
truth the page-level proxy approximates. Page-level classification is **not discarded** — it stays
as the wide net and the router; content-level is the precision layer that the net feeds.

---

## 4. Validation

- **Page-level:** structural null models (M5), the isolate audit (`core_audit.csv`, no
  auto-demotion), and the expert definitions for the membership boundary (M6 gold set, κ≥0.7,
  recall≥0.95/lang, held-out negatives).
- **Content-level (diagnostic metrics for now, not gates):** boundary stability run-to-run, human
  boundary-F1, coverage, identity-precision audit (false merges hide reform), and inter-coder κ at
  the segment and cross-lingual layers — computed to **find bad statements and understand the
  system**, not to block the pipeline; promotable to gates before a formal claim.
  → `atomic_statements_design.md` §8, ROADMAP M6/M7/M9.

---

## See also
- [`core_definition.md`](core_definition.md) — page membership (§1–3) + the namespace-4 router (§3a)
- [`atomic_statements_design.md`](atomic_statements_design.md) — the content unit, segment types, WikiWho identity
- [`related_work.md`](related_work.md) — the DeDeo governance typology + Butler role framework we build on
- [`../net/classify_governance.py`](../net/classify_governance.py) + `data/network/FINDINGS.md` #5 — the structural governance classifier
- `data/network/core_audit.csv` — page-type buckets, origin, disposition
