# Multi-wiki policy network — first structural findings (2026 snapshot)

Source: `nodes.csv` + `edges.csv` (6 wikis: en/de/fr/es/ja/nl). Reproduce with
[`../../net/analyze_network.py`](../../net/analyze_network.py). **Caveat: raw structural
counts — no null/size-normalization model yet (M5 gate). Descriptive, not yet inferential.**

Method: cross-lingual clusters = connected components over **interwiki langlink edges**
(no Wikidata); within-wiki degree normalized by each wiki's mean (densities differ).

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

---

## What this sets up

The interwiki edges that align these cores are the candidate **content** matches for M8/M9.
The peripheral/divergent pages (legal, technical, en-only style) are where the cross-lingual
*content* comparison will be most informative — and §2/§3 say the comparison must carry a
**policy-type** distinction (governance vs style vs legal-boilerplate), not treat all core
pages alike. Before any of this is a *claim*, it needs the M5 null model.
