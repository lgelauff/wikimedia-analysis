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

## 5. Methods & tooling for the content layer

Capturing each page's **content core** reproducibly across languages *and* times is the substrate
for M8/M9 (see [`content_core_extraction.md`](content_core_extraction.md) once written). The
literature splits the problem into a *space* step (clean text) and a *time* step (content identity
across revisions); we don't reinvent either.

**Clean-text extraction (space).** Established tools, none fitting our exact combo:
- **WikiExtractor (Attardi)** — https://github.com/attardi/wikiextractor — popular, but *expands*
  templates from dump-time definitions and **discards lists/tables/refs/images**. Dealbreakers:
  it drops normative **lists**, and dump-time expansion is not our reconstructability model.
- **Sweble** — full-grammar wikitext parser → AST
  (https://www.researchgate.net/publication/221367823). Principled but heavy/older; precision
  fallback if mwparserfromhell proves insufficient.
- **mwparserfromhell (ours)** — AST-lite, no expansion; the right base. Our three differentiators —
  **keep lists, do NOT expand templates** (so old revisions stay reconstructable), **language-
  agnostic** — are purpose-specific; no off-the-shelf tool does reproducible + reconstructable +
  structure-preserving, so this is a real gap we fill, not reinvention.

**Cross-time content identity (time) — WikiWho.** Flöck & Acuña, WWW 2014.
https://www.mediawiki.org/wiki/WikiWho · API https://wikiwho.wmcloud.org/ · code
https://github.com/wikimedia/wikiwho_api (+ Rust reimpl github.com/Schuwi/wikiwho_rs).
Computes **token-level provenance across all revisions** — for every token, the exact revisions
that added / deleted / reinserted it — at **95% accuracy**, **open source**, covering **all six of
our languages** (80+ editions; precomputed EN dataset *TokTrack*, Zenodo 345571). This is a
published, validated solution to exactly the cross-revision identity problem the atomic layer
needs, so we **build statement identity on top of WikiWho** rather than hand-rolling byte-hash +
fuzzy matching (see [`atomic_statements_design.md`](atomic_statements_design.md) §2).
**Verified (2026-06):** the hosted API is **articles-only** — a probe on `Wikipedia:Civility`
returned `HTTP 400 {"Error":"Only articles! Namespace 4 is not accepted."}`. So we **self-host the
open-source algorithm** (`wikiwho`/`wikiwho_rs`) on the revision histories we fetch — namespace is
irrelevant when we supply the history. Reproducibility = pin the algorithm version.

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
- Flöck, F. & Acuña, M. (2014). *WikiWho: Precise and Efficient Attribution of Authorship of
  Revisioned Content.* WWW 2014. https://www.mediawiki.org/wiki/WikiWho
- Attardi, G. *WikiExtractor.* https://github.com/attardi/wikiextractor
- Dohrn, H. & Riehle, D. (2011). *Design and implementation of the Sweble Wikitext parser.*
  WikiSym 2011. https://www.researchgate.net/publication/221367823
