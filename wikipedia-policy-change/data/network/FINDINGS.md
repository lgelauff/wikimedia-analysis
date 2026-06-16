# Multi-wiki policy network — first structural findings (2026 snapshot)

Source: `nodes.csv` + `edges.csv` (6 wikis: en/de/fr/es/ja/nl). Reproduce structure with
[`../../net/analyze_network.py`](../../net/analyze_network.py); inference with
[`../../net/null_model.py`](../../net/null_model.py).

Method: cross-lingual clusters = connected components over **interwiki langlink edges**
(no Wikidata); within-wiki degree normalized by each wiki's mean (densities differ).

**M5 inference (cleared for #1, #3, #4):** each headline number below now has a null /
size-normalization baseline (`null_model.py`, 500 replicas, seed 12345). Tests: (A) bootstrap
95% CI on mean within-wiki degree — size control for the density gap; (B) rank-permutation null
for cross-lingual periphery/centre consistency; (C) **degree-preserving configuration-model
rewire** (double-edge-swap, interwiki fixed) for the hidden-equivalents count — the swap holds
the degree sequence exactly, so a surviving signal is not a degree (or residual navbox-clique)
artifact. Results inlined per finding. Remaining caveats are stated where they still apply
(verbosity confound on #3 is *not* resolved by M5 — it needs the atomic layer).

---

## 1. Validation + a universal: what's central vs peripheral everywhere

Of 152 cross-lingual clusters spanning ≥3 wikis (47 span all 6):

- **Universally central** (high normalized degree in every language) = the known
  conceptual core: **What Wikipedia is not, Verifiability, NPOV, No original research,
  Citing sources, Consensus, Administrators.** This validates the method — the policies
  everyone knows are foundational come out central everywhere.
- **Universally peripheral** = two clean kinds:
  1. **Externally-imposed / legal boilerplate** — Privacy policy, Medical disclaimer,
     General disclaimer, Text of the GNU FDL, Open proxies.
  2. **Niche technical-role / operational pages** — Interface administrators, Edit filter
     manager, Account creator, Administrator recall, Speedy keep.

**Reading:** the "policy network" is the community's argued-out content/conduct rules;
WMF-mandated legal pages and narrow technical-role pages attach at the **rim, identically
across all six languages**. A cross-lingual structural universal, with no semantic analysis.

**Inference (M5, test B):** of 152 clusters spanning ≥3 wikis, **7 are top-quintile-central in
every wiki they appear in** (null mean ~0.7; **p = 0.002**) and **3 are bottom-quintile-peripheral
in every wiki** (null mean 1.22; **p = 0.006**). Both consistency effects are significant against
the rank-permutation null. The centre effect is the stronger and cleaner one (the known core);
the periphery effect is real but *modest* — most legal/technical pages are low-degree but not
strictly bottom-quintile in literally every appearance, so the universal-periphery claim holds
directionally but is thinner than the universal-centre claim.

---

## 2. Divergence: en's Manual of Style is an en-specific proliferation

- en's **Manual of Style + Naming conventions = 139 pages = 40% of its entire core.**
- **65% of them (90 pages) have NO equivalent in any of the other 5 wikis** — en-only granularity.
- Style apparatus as share of core: **en 40% · de 20% · es 16% · fr 11% · ja 11% · nl 6%**
  — en's is **2–7× larger** proportionally than everyone else's.

**Reading:** en has uniquely elaborated *style/formatting* guidance (an advisory tier,
arguably a different *kind* of rule) into ~140 interlinked pages most editions never built.
A concrete RQ1 divergence — and a reason to treat **style as its own policy type**, so the
90 en-only style pages don't read as "policies the other wikis are missing" (they're not
missing governance; en just has more style granularity).

---

## 3. en is ~2× denser internally — and it's NOT a MoS artifact

Internal density (within-wiki links per core page), full core vs. with the en-style
cluster removed:

| wiki | full | ex-MoS |
|---|---|---|
| **en** | **23.3** | **27.1** |
| ja | 14.1 | 14.6 |
| fr | 12.8 | 13.4 |
| de | 12.1 | 12.6 |
| es | 10.8 | 11.6 |
| nl | 7.6 | 7.8 |

The hypothesis was that en's density lead came from its huge, self-cross-referencing MoS.
**The MoS test refutes that one:** removing the MoS cluster *raises* en's density (27.1),
because the MoS subpages are *lower*-degree than en's governance core. The MoS is a large but
**structurally peripheral appendage**, not the dense center (consistent with §1).

**But a second confound remains and page-level structure can't resolve it: verbosity.**
Links-per-page conflates genuine interconnection (rules that reference each other) with
detail-level (a longer, more-elaborated page carries more wikilinks just from having more
prose). So "en 2× denser" may mean en's governance is more *interconnected*, or that en's
policies are more *detailed/verbose* — and the latter is itself **H3** (defensive accretion),
a finding rather than noise. The two only separate at the **atomic-statement level**:
verbosity = statements per policy; interconnection = cross-references *per statement*. Until
then, #3 is "en pages carry ~2× more internal links per page," not yet "en governance is 2×
more interconnected."

**Inference (M5, test A):** bootstrap 95% CIs on mean within-wiki degree are **en [20.8, 26.0]**
vs the next-densest **ja [12.3, 16.0]** — **non-overlapping**, so the lead is not a sampling
artifact and (mean degree being scale-free in node count) not a by-product of en's larger core.
M5 does **not** settle the verbosity-vs-interconnection split above — that is a *units* problem
(per-page vs per-statement), not an inference one, resolved only at the atomic layer.

---

## 4. Hidden equivalents: structure finds unlinked cross-wiki matches — in differently-subdivided families

Each page gets a language-agnostic **fingerprint** = the set of cross-lingual clusters its
within-wiki neighbors belong to. Cross-wiki page pairs that are **not** interwiki-linked (not
co-clustered) but have near-identical fingerprints are candidate equivalents the langlinks miss.
82 pairs at neighborhood Jaccard ≥ 0.45; the top ones share one signature:

| Jacc | page A | page B |
|---|---|---|
| 0.75 | en:Notability (academics) | ja:特筆性 (書籍) [Notability (books)] |
| 0.57 | en:Notability (web) | ja:特筆性 (音楽) [Notability (music)] |
| 0.60 | en:Notability (films) | fr:Notoriété des entreprises [companies] |
| 0.50 | nl:Fancruft | fr:Notoriété des personnes [people] |

**Reading:** these are not *exact* equivalents (academics ≠ books) — they are **structural
siblings**. Each edition subdivides a domain (notability, inclusion-criteria, trivia/style)
into topic-specific subpages, but the subdivisions don't align 1:1, so **no langlink connects
them** — yet they occupy the same neighborhood. So the unlinked-but-equivalent pages are exactly
**the domains each wiki carves up differently**: the 1:1 core (NPOV, V) already has langlinks;
the interesting cross-wiki structure lives in the differently-granular families, and structural
neighborhood-alignment surfaces them with no content analysis.

Two consequences:
- **This is the M9 hard case, made concrete and cheap.** The real matching problem isn't the
  1:1 core but aligning differently-granular families (does ja's one 特筆性(書籍) cover rules
  en splits across several Notability subpages?) — which only the atomic/content layer resolves.
  Structure is a strong, no-LLM **candidate generator** for those pairs.
- **Structural-only has false positives** — e.g. nl:Bronvermelding [citing sources] ↔
  fr:Diffamation [libel] share the sourcing core but aren't equivalent. So this proposes
  candidates; M9 (content/embedding) verifies. Reproduce: `analyze_network.py` §5.

**Inference (M5, test C):** against a degree-preserving configuration-model null (double-edge-swap
of each wiki's within-wiki graph, interwiki edges fixed, 500 replicas), a random network with the
**identical degree sequence** produces a mean of **1.3** such pairs (sd 1.2, max 7) — vs the
observed **82**. That is **z ≈ 67, p = 0.002** (empirical floor at 1/501): the cross-wiki
neighborhood alignment is **real structure, not a degree artifact**, and — because the swap also
destroys any residual clique structure — not a navbox/template-transclusion artifact either. The
*false-positive* caveat is separate and unchanged: these are validated as non-random candidates,
their semantic equivalence still needs content verification (M9).

---

## What this sets up

The interwiki edges that align these cores are the candidate **content** matches for M8/M9.
The peripheral/divergent pages (legal, technical, en-only style) are where the cross-lingual
*content* comparison will be most informative — and §2/§3 say the comparison must carry a
**policy-type** distinction (governance vs style vs legal-boilerplate), not treat all core
pages alike. Before any of this is a *claim*, it needs the M5 null model.
