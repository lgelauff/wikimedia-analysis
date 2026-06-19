# Related work & references — where this project sits

The project is, at its core, a **reproduction and extension of Heaberlin & DeDeo (2016)**:
their English-only, page-level, through-2015 study of the Wikipedia *norm network*, extended
to **multiple language editions, the present day (2026), and the atomic-statement level**. This
doc records the prior art, what each contributes, and the open space we fill. Two distinct
questions run through the literature and must be kept separate:

- **Boundary** — *is page X a norm/policy at all?* (see [`policy_definitions_for_review.md`](policy_definitions_for_review.md))
- **Typology** — *what kinds of policy are there, once inside?* (the categories below)

---

## 1. Heaberlin & DeDeo (2016) — the direct ancestor

**"The Evolution of Wikipedia's Norm Network."** *Future Internet* 8(2):14. arXiv:1512.01725.
- Paper: https://www.mdpi.com/1999-5903/8/2/14 · PDF: https://arxiv.org/abs/1512.01725
- **Public dataset:** http://tuvalu.santafe.edu/~simon/styled-9/styled-10/
  (`heaberlin_dedeo_norm_network.zip` — nodes.csv [TAB-delimited: creation date, edit count,
  page views, LDA topic loadings] + the filtered hyperlink network).

**Method (it matches ours — we converged independently, which validates our choices):**
- Nodes = pages in the `Wikipedia:`/`WP:` namespace, spidered from *Assume good faith*.
- Edges = **in-body hyperlinks, directed, unweighted**, parsed from page HTML and **excluding
  standard navigational templates, lists, and infoboxes**; redirect/synonym-resolved. This is the
  same call we made (in-body wikilinks, *not* `pagelinks`; redirects resolved).
- Scale: **1976 nodes, 17,235 edges, density 0.0044, 95% in one giant component.**
  56 policy + 113 guideline; 1807 non-policy (1255 essays, 182 proposals, 125 humor).
- **English only, through 2015.**

**Their typology (we adopt as the citable backbone):** three kinds by *what is governed* —
**user-content · user-user · user-admin** — extending Ostrom's commons-governance categories;
hand-coded on 40 pages, Cohen's κ = 0.59 ("moderate"), norm-identification precision 97.5%.
Separately, **Louvain community detection** yields structural "norm bundles" (four neighborhoods:
*article quality, content policy, collaboration, administrators*) that **decouple topologically
over time while gaining semantic coherence.** Our finer kinds map under their scheme
(style/transliteration → user-content; conduct → user-user; procedural/admin → user-admin), and
the pages that fit *none* cleanly — legal/WMF boilerplate, meta/index — are exactly our peripheral
isolates, which is why our typology keeps an explicit **Other** residual (see
[`../data/network/core_audit.csv`](../data/network/core_audit.csv)).

**Their metric suite (adopt for direct comparability):**
- Eigenvector centrality (= PageRank, ε = 0.15) for page importance.
- **Gini coefficient of centrality** to track rising inequality over time — their version of our
  "ossify but accrete" finding.
- Influence via random walk on the **direction-reversed** network (n = 5 steps); influence-
  **overlap** O(p,q) for "spheres of influence."
- Semantics: **LDA topic model → Jensen–Shannon distance → semantic coherence** (Pearson of
  influence vs. −JSD).

**Key results to reproduce/compare against:** normative evolution is **highly conservative**
(core norms created early dominate and persist; EC rank corr 2001↔2015 = 0.87, year-to-year > 0.9);
neighborhoods decouple while internal coherence rises; the system trends toward bureaucratic
inequality.

---

## 2. Butler, Joyce & Pike (2008) — the role framework

**"Don't look now, but we've created a bureaucracy: the nature and roles of policies and rules in
Wikipedia."** CHI 2008.
- PDF: https://www.kostakos.org/courses/socialweb10F/reading_material/5/butler08.pdf

Grounds Wikipedia policy in **organizational rule theory**, framing policies by the **multiple,
overlapping roles** they play (a single page can both restrict copyright use *and* establish
legitimacy through legal diction). This is the vocabulary for our *functional* axis and the source
of "policy-through-structure" (process/venue pages that are normative by being the procedure).
DeDeo explicitly positions the user-content/user-user/user-admin scheme as **complementary** to
Butler's function-based view — categories of *what is governed* vs. *what role the page plays*.

---

## 3. Cross-lingual prior work — touched, never networked

The cross-edition angle is our novelty; the closest existing work is qualitative or content-level,
not structural:

- **"Assessing the impact of translation guidelines… across four language communities"** —
  praxeological (interview + document) study of how documented standards differ across editions.
  https://www.researchgate.net/publication/358838662
- **"Wikipedia Beyond the English Language Edition"** (CSCW 2021) — documents governance
  differences across editions (local context, community, technology) but builds no policy network.
  https://dl.acm.org/doi/pdf/10.1145/3449129

No prior work builds a **cross-lingual policy network**, aligns cores across editions, or descends
to the **atomic-statement** level.

---

## 4. Our contribution = the space they leave open

| Axis | Heaberlin–DeDeo | This project |
|---|---|---|
| Languages | English only | en + de + nl + fr + es + ja (extensible) |
| Time | through 2015 | through 2026 |
| Unit | whole page (LDA topics) | page **and** atomic normative statement (M8) |
| New analyses | — | cross-wiki interwiki alignment; **hidden-equivalents** (structural matching of unlinked but functionally-equivalent pages, M9); differently-subdivided families |

**Validation plan:** download the EN-2015 release → check node-set overlap and centrality-rank
correlation against our EN core → if we reproduce their 1976-node network, our method is validated
against peer-reviewed ground truth before any extension is claimed. Then adopt their metric suite
(EC, Gini, influence-overlap, Louvain bundles, LDA/JSD coherence) so all results are directly
comparable to a published baseline.

---

## Citation list

- Heaberlin, B. & DeDeo, S. (2016). *The Evolution of Wikipedia's Norm Network.* Future Internet
  8(2):14. https://www.mdpi.com/1999-5903/8/2/14 · arXiv:1512.01725 · data:
  http://tuvalu.santafe.edu/~simon/styled-9/styled-10/
- Butler, B., Joyce, E. & Pike, J. (2008). *Don't look now, but we've created a bureaucracy: the
  nature and roles of policies and rules in Wikipedia.* CHI 2008.
- *Assessing the impact of translation guidelines across four language communities.*
  https://www.researchgate.net/publication/358838662
- *Wikipedia Beyond the English Language Edition.* CSCW 2021.
  https://dl.acm.org/doi/pdf/10.1145/3449129
