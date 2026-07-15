# Framing Memo — "The Power of a Veto in Community Decisions"

Working title (fixed by author). This memo is intellectual scaffolding, not prose and not
new analysis. Every non-trivial empirical claim is labeled **[confirmed]** (seen in a repo
file or cited source — location given), **[concluded]** (an inference — reasoning stated), or
**[guess]** (unverified intuition to be tested). "Would need to compute: …" flags numbers that
do not yet exist.

---

## 1. Thesis statement (sharpest version)

Wikipedia's Request-for-Comment (RfC) process is nominally *consensus-based*, but consensus
procedures share a structural asymmetry: **the absence of consensus is not a null result — it
is a decision, and that decision is almost always "keep the status quo."** Because change
requires an affirmative consensus while non-change requires only the *failure* of consensus, the
burden of proof falls entirely on those who want change. This hands a determined minority — in
the limit, a single committed objector who refuses to be persuaded and outlasts the discussion —
the power to *veto* change without ever assembling a majority of their own. The paper's claim is
that in a consensus regime, "no" is structurally cheaper than "yes," and we can measure the
resulting veto power empirically in the RfC record: in the rate at which contested proposals
default to the status quo, in how small the blocking side can be while still prevailing, and in
who holds the procedural leverage to make "no" stick.

---

## 2. Why it matters (stakes; what is non-obvious)

- **Consensus is usually sold as the *anti-majoritarian* virtue of the system** — it protects
  minorities from being steamrolled by 51%. The non-obvious flip side is that the very same rule
  *empowers* a minority in the opposite direction: it lets them impose their preferred outcome
  (no change) on a frustrated majority. The paper reframes a celebrated feature as a distribution
  of power, and asks who actually benefits.
- **The default is invisible.** A majority that wins gets a visible "consensus to change." A
  minority that blocks produces "no consensus" — which reads as *nothing happened*, an
  administrative non-event, not an exercise of power. The paper's job is to make the non-event
  legible as an outcome with a beneficiary.
- **It reinterprets a known pathology.** Prior work (Im et al., CSCW 2018) found that **33% of
  RfCs go "stale" — expiring with no closure at all** [confirmed: CSCW2018 slide 34, "2,329
  (33%)"]. Im et al. treat staleness as a *process failure* (discouraging, bad for productivity).
  In veto terms, a stale RfC is not a failure at all — it is a **silent status-quo win by
  attrition**: the proposal died, so nothing changed, so whoever preferred the status quo got
  exactly what they wanted at zero cost. Same fact, opposite valence.
- **Generalizes beyond Wikipedia.** Consensus-default-to-status-quo is the operative rule in
  standards bodies (IETF), open-source maintainership, condo boards, the EU Council's unanimity
  domains, and UN Security Council vetoes. Wikipedia is a rare setting where the entire decision
  record is public and machine-readable, so it is an unusually clean natural laboratory for a
  question that matters far outside it.

---

## 3. Literature positioning

### (a) Veto-player / social-choice theory — the frame we import

- **Tsebelis, *Veto Players* (2002).** Veto players are actors whose agreement is necessary to
  change the status quo; the more of them (and the more ideologically dispersed), the smaller the
  "winset" of the status quo and the greater the *policy stability* — i.e., the harder change
  becomes [confirmed: Tsebelis summary, Princeton/Michigan sources]. This is the paper's spine.
  **Contribution:** Wikipedia RfCs are an unusual veto-player system where veto players are not
  fixed institutional actors (chambers, parties) but **self-selecting volunteers** — anyone who
  shows up and refuses to concede can act as a veto player. The paper extends veto-player theory
  from *designed* institutions to an *emergent, open-entry* one.
- **Buchanan & Tullock, *Calculus of Consent* (1962), Ch. 7 (the unanimity rule).** Under
  unanimity, a defender of the status quo has **dictator-like power**; the rule is biased toward
  vested interests and the existing state [confirmed: Econlib chapter; corroborated by Public
  Choice literature via search]. RfC "consensus" is not literal unanimity, but it sits on the
  spectrum toward it, and inherits the same bias.
- **Status-quo bias** (Samuelson & Zeckhauser 1988; and the institutional-gridlock literature).
  Supermajority/consensus rules privilege the status quo and can produce paralysis even when
  reform is broadly beneficial [confirmed via search: Public Choice / EU-unanimity examples].
  **Gap this fills:** these are largely *theoretical* or macro-institutional claims. The paper
  supplies a **micro-level, large-N empirical measurement** of the status-quo bias inside a
  single consensus institution, with the counterfactual (the proposal that was on the table)
  actually observable.

### (b) Wikipedia governance work — the empirical neighborhood

- **Im, Zhang, Schilling, Karger, Morgan, "Deliberation and Resolution on Wikipedia," CSCW
  2018.** *This is the closest prior work and the paper must be differentiated from it sharply.*
  What they did [confirmed from the slide deck at `datasets/CSCW2018_deliberation_resolution.pdf`
  and `IMETAL_REPRODUCTION.md`]:
  - N = 7,316 enwiki RfCs, 2011–2017.
  - Three-way outcome taxonomy: **formally closed (58%) / informally ended (9%) / stale (33%)**
    [slide 34].
  - Closers are far more experienced and far fewer than participants: **39,759 vs 14,055 mean
    edits; 759 closers vs 14,815 participants** [slides 32].
  - Average duration 45.56 days (σ=81.14); 16.74 days from last comment to formal close [slide
    35].
  - Built an ADT classifier predicting whether an RfC goes stale: **75.3% accuracy vs 67.2%
    baseline** [slide 61]; top features are size/shape of discussion, participant experience,
    participant interest [slides 62–64].
  - Their qualitative "reasons for staleness": vague proposals, participant bickering/socking,
    lack of uninvolved interest/expertise, RfC too complex/contentious, interpersonal
    "wikipolitics" [slides 40–47].

  **The gap — three specific ways the veto paper is *not* Im et al.:**
  1. **Different dependent variable.** Im et al.'s outcome axis is *resolution* (did the RfC get
     closed?). The veto paper's outcome axis is **direction**: *did the proposed change happen,
     or did the status quo survive?* Im et al.'s "formally closed" bucket silently lumps together
     "consensus to change," "consensus to reject," and "no consensus" — three completely
     different things for a veto analysis. **No Im et al. number tells you how often the status
     quo won.** [concluded from their taxonomy; the direction variable is simply absent.]
  2. **Staleness re-valued.** Im et al. frame the 33% stale as a bug to be *predicted and
     prevented*. The veto paper frames it as the **cleanest possible measurement of the
     status-quo default**: an RfC that dies unclosed is a change-that-didn't-happen, i.e., the
     null outcome IS the status-quo victory. The paper repurposes their headline pathology as its
     headline governance finding.
  3. **Power, not process.** Im et al. ask "why do RfCs fail to resolve?" The veto paper asks
     "who wins when they don't, and how few people does it take?" — a question about the
     *distribution of power*, which their design cannot answer.

- **Heaberlin & DeDeo, "The Evolution of Wikipedia's Norm Network," *Future Internet* 2016.**
  Wikipedia's normative system is **highly conservative**: early-created norms dominate the
  network and persist; the system self-organizes around a small set of abstract core principles
  (neutrality, verifiability, good faith) [confirmed via search + task brief]. **Positioning:**
  Heaberlin & DeDeo explain *why the rulebook is sticky at the network level*; the veto paper
  explains *one micro-mechanism that produces stickiness at the decision level* — every
  individual change must clear a consensus bar that the status quo never has to clear. The two
  are complementary: their conservatism is our aggregate consequence.

- **Broader Wikipedia governance** (background, not head-to-head): Halfaker et al. 2013 (rising
  bureaucratic conservatism and its chilling effect on newcomers), Hwang & Shaw on rule-making in
  the five largest Wikipedias [both in the research-vault index: `halfaker2013rise`,
  `hwang2022rules`], and the Wikipedia policy corpus itself (`WP:CONSENSUS`, `WP:What "no
  consensus" means`). The last is a *primary source on the veto mechanism* and should be cited as
  such — see §7 for the crucial nuance it introduces.

### (c) Online-community / deliberation research — the outer ring

- Deliberation-quality and online-governance work (the CSCW/ICWSM tradition; e.g., deliberation
  at scale, Polis, mini-publics — several in the vault under `deliberat`/`democra` tags). Most of
  this literature evaluates deliberation by *quality of discourse* or *representativeness*. The
  veto paper's angle is orthogonal and, we argue, underexamined: not "was the deliberation good?"
  but **"what does the aggregation rule do to power when deliberation ends inconclusively?"** The
  action is in the *default rule*, not the talk.
- **Gap statement (one sentence):** Across all three literatures, there is theory saying
  consensus rules favor the status quo, and there is empirical description of Wikipedia's RfC
  process, but **no one has empirically measured the veto — the status-quo default's actual rate,
  its beneficiaries, and the minimum blocking size — inside a real large-N consensus institution
  where the blocked proposal is observable.** That is the paper.

---

## 4. Operationalization — how to *measure* veto power

Notation: an RfC proposes a move from status-quo state S₀ to alternative S₁. "Change" = S₁
implemented; "status-quo win" = S₀ retained. Each measure below is tagged with data source:
**[SQL]** = PAWS SQL replica (from PLAN.md), **[API]** = MediaWiki Action API content parsing,
**[NEW]** = needs new collection/method, **[LLM]** = needs a classifier/LLM pass.

**M1 — De facto veto rate (headline).**
Fraction of contested RfCs that end in status-quo retention, whether by explicit "no consensus"
close *or* by staleness. This is the paper's central number.
- Stale detection (Legobot tag-removal) is reliable [confirmed: `IMETAL_REPRODUCTION.md` says
  Legobot stale-removal is a sound signal; our current stale/open numbers are "roughly sound"].
  [SQL] + [API].
- Explicit "no consensus" closes require parsing the `{{Rfc result}}` / closing-box text. [API]
  + [LLM to read the close].
- **Crucially new vs. Im et al.:** we must also classify *direction* of formal closes (change vs.
  reject). [API]+[LLM]. Would need to compute: the change/reject/no-consensus split of the 58%
  "formally closed" bucket.

**M2 — Blocking-minority size in vetoed proposals (the sharpest single measure).**
Among RfCs where a *majority of !voters supported the change* but the change did **not** happen,
what was the size (absolute and as a fraction) of the opposing minority? A distribution peaking
at small numbers (e.g., 1–3 objectors blocking a 7–3 majority) is direct evidence of veto power.
- Requires: (i) parsing bolded `Support`/`Oppose` !votes from the thread — standard RfC format,
  tractable [API]; (ii) the outcome direction from M1. Would need to compute: the whole joint
  distribution. This is the measure most legible to a political-science audience.

**M3 — Does a small *determined* minority predict non-change? (mechanism test).**
Regress status-quo outcome on features of the objecting side, holding overall sentiment constant:
number of distinct objectors, their *persistence* (comment count, repeated re-engagement, last-
word behavior), and their tenure/edit-count. Hypothesis: *persistence* of a tiny opposition, not
its size, drives blocking. [API] for threading + !votes; [SQL] for tenure/edit-count. Note Im et
al.'s own model already finds "number of comments," "average reply depth," and participant
experience predict (non-)closure [confirmed: slides 62–64] — we reinterpret those as *veto-
capacity* features rather than *staleness* features.

**M4 — Closer discretion at the margin (does the referee enable or resist the veto?).**
For RfCs closed near the consensus threshold, does the closer call "no consensus" (status-quo
win) or find consensus? Measure closer discretion by comparing the numeric !vote split to the
declared outcome. Because Wikipedia closers weigh *argument strength*, not headcount, a minority
with strong policy grounding can legitimately prevail — this must be separated from pure
obstruction (see §7). [API]+[LLM] to compare close rationale to !vote tally. [NEW] method.

**M5 — Tenure asymmetry as a source of veto-holder power.**
[confirmed baseline: `data/enwiki/summary.txt` — median participant tenure **1,192 days for RfC
vs 682 days for RfA**.] Test whether *higher-tenure participants on the opposing side* are more
successful at producing status-quo outcomes than higher-tenure supporters are at producing
change — i.e., whether procedural seniority converts more efficiently into blocking than into
building. [SQL] tenure + [API] stance + M1 outcome. Would need to compute: the interaction of
tenure × stance × outcome.

**M6 — Venue as a natural experiment on default direction.**
Wikipedia's *own* rules make the status-quo default explicit and **context-dependent**
[confirmed, `WP:What "no consensus" means`, via WebFetch]:
- Article content edits → "no consensus" favors a **status-quo/stability** default.
- Deletion (XfD) → "no consensus" defaults to **keep** (with RfD/FfD exceptions).
- **Policy proposals → the default reverses: no consensus means the new policy is *not* adopted
  and existing policy text may be *removed***, because "policy should reflect consensus."
- Reversing an admin action → "no consensus" **reverses** the action.
Comparing veto rates across these venues is a within-Wikipedia natural experiment: the veto
should bind hardest exactly where the status-quo default protects the incumbent state. [API] to
classify RfC venue/topic (the topical listing pages give this "for free" per
`IMETAL_REPRODUCTION.md` Track B). This is a strong identification strategy and largely
underexploited.

**Priority ranking of operationalizations:** **M1 (headline rate), M2 (blocking-minority size),
and M6 (venue natural experiment)** are the three strongest — each is falsifiable, each maps to
data the plan can largely produce, and together they move from *description* (M1) to *magnitude*
(M2) to *causal identification* (M6). M3–M5 are the mechanism/second-layer analyses.

---

## 5. Candidate research questions & hypotheses (refined from `research_questions.md`)

The current `research_questions.md` is process-descriptive (reading burden, phases, coordinator
flexibility, tenure). The veto thesis sharpens these into power questions:

- **RQ1 (rate).** What fraction of contested RfCs resolve in favor of the status quo (via no-
  consensus close *or* staleness)?
  **H1:** A majority of *contested* RfCs end in status-quo retention — the default wins more
  often than change. [Motivated by the 33% stale + unknown share of no-consensus closes;
  currently unmeasured in the direction sense.]

- **RQ2 (blocking size).** In RfCs where the supporting side outnumbered the opposing side, how
  often, and with how small a minority, did change still fail?
  **H2:** There exists a substantial class of RfCs where a numerical majority favored change yet
  the status quo was retained, and the blocking minority is frequently ≤3 editors. [Direct veto
  evidence.]

- **RQ3 (persistence beats numbers).** Controlling for overall support ratio, does the
  *persistence* of the opposition (comment volume, re-engagement, last-word) predict a status-quo
  outcome better than its *size*?
  **H3:** Persistence dominates size — a single relentless objector is more predictive of non-
  change than several passive ones. [Reinterprets Im et al.'s "number of comments"/"reply depth"
  features as veto capacity.]

- **RQ4 (closer as veto-enabler).** When the !vote split is near the margin, how much does the
  outcome depend on *which* closer acts?
  **H4:** Near-threshold outcomes exhibit high closer-to-closer variance, i.e., the veto is
  partly *manufactured at close*, not just present in the discussion. [Tests whether discretion
  amplifies or dampens the structural default.]

- **RQ5 (seniority → blocking).** Does participant tenure convert asymmetrically into blocking
  vs. building?
  **H5:** High-tenure editors on the opposing side raise the probability of a status-quo outcome
  more than equally high-tenure supporters raise the probability of change. [Uses the confirmed
  1,192-vs-682-day tenure gap as a springboard, but tests a *directional* claim it does not yet
  support.]

- **RQ6 (default direction moderates the veto).** Does the veto bind hardest in venues whose
  no-consensus rule favors the incumbent state (content, deletion) versus venues where it does
  not (policy addition)?
  **H6:** Status-quo-win rates track the documented default direction across venues — strongest
  where "no consensus → keep," weaker or reversed for policy *additions*. [The M6 natural
  experiment; also a validity check that we are measuring the mechanism, not an artifact.]

---

## 6. What current data can already support vs. what is new

**Already supportable (data/methods largely in hand):**
- RfC population and volume over time [confirmed: 1,625 enwiki RfC pages 2006–2026,
  `summary.txt`; monthly volume via SQL per PLAN.md Q2].
- Stale-vs-closed classification via Legobot tag-removal [confirmed reliable,
  `IMETAL_REPRODUCTION.md`] → gives the **staleness half of M1** directly.
- Participant/closer tenure and edit-count distributions [confirmed method, PLAN.md Q1/Q4;
  baseline medians already computed] → **M5 inputs**.
- !vote parsing (Support/Oppose) and opening/closing statement extraction [API, cache.py per
  PLAN.md Phase 2] → **M2/M3 inputs**, needs to be built but is in-scope.
- Venue/topic labels from the topical listing pages [confirmed available "for free",
  `IMETAL_REPRODUCTION.md` Track B] → **M6 labels**.

**Needs new analysis or collection:**
- **Outcome *direction* classification** (change / reject / no-consensus) of formal closes —
  the single most important new artifact; not in any existing dataset including Im et al.'s.
  Requires an [LLM] pass over `{{Rfc result}}` text + a check on whether the target page actually
  changed post-close (proxy already noted in `research_questions.md`: did target policy/article
  change within 30 days). [API]+[LLM].
- **Blocking-minority joint distribution** (M2) — requires linking !vote tallies to outcome
  direction; new join.
- **Closer-variance design** (M4) — requires matching near-threshold RfCs and modeling closer
  identity; new.
- **Reproduction baseline** — Track A (58/9/33) is *not yet reproduced*; current human-close
  split is a known artifact (7% not 58%) [confirmed: `IMETAL_REPRODUCTION.md`]. The veto paper
  should **not** build on the current close-classification until Track A lands. Rebuild via
  closing-box detection + participant-set involvement.

**Data hygiene — do NOT use:**
- **Median RfC duration = 4,958 days** [confirmed present in `summary.txt`; flagged impossible
  for a ~30-day process — almost certainly a page-lifetime or timestamp-join bug]. Use Im et
  al.'s **45.56-day** figure as the credible external anchor until recomputed. Would need to
  compute: a correct per-RfC open→close duration.
- **Median RfC revert rate = 0.0%** [confirmed in `summary.txt`; flagged as almost certainly
  buggy — implausible for contested discussions]. Do not build any "edit-warring/veto-by-revert"
  claim on this until recomputed.

---

## 7. Risks & counterarguments (addressed honestly)

- **R1 — "No consensus → status quo" may be *absence of a mandate*, not a veto.** If a proposal
  genuinely splits the community 50/50, retaining the status quo isn't a minority overriding a
  majority — it's simply no majority for change. **Response:** this is why **M2 is decisive**: the
  veto claim lives specifically in the subset where a *clear majority favored change and change
  still failed*. We must report the majority-blocked subset separately and not let genuinely-split
  cases inflate the veto rate. The honest paper measures both and distinguishes them.
- **R2 — Closer discretion legitimately weights arguments, not heads.** Wikipedia explicitly is
  "not a vote"; a well-grounded minority *should* prevail on policy strength [confirmed:
  `WP:CONSENSUS` via search]. A minority winning on argument quality is *consensus working*, not
  a veto. **Response:** separate **policy-grounded** minorities from **bare-objection** minorities
  (M4 + an [LLM] read of whether oppose rationales cite policy). The veto finding is strongest
  where the blocking side offers little beyond refusal. Concede the legitimate-minority case
  openly; it bounds the claim rather than defeating it.
- **R3 — The default direction is not monolithic.** `WP:What "no consensus" means` shows the
  status-quo default *reverses* for policy additions and admin-action reversals [confirmed via
  WebFetch]. So "no consensus always helps the objector" is false as stated. **Response:** this is
  not a bug but **M6's identification strategy** — the veto should track the documented default
  direction. If it does, that is evidence we are measuring the mechanism; if it doesn't, the
  thesis is in trouble. Build the test in rather than papering over it.
- **R4 — Selection effects.** Proposals only become RfCs *after* informal discussion fails;
  uncontested changes never enter the sample. We observe the contested tail, not the population of
  proposed changes. **Response:** scope the claim to *contested* decisions explicitly (that is
  where veto power matters anyway), and be candid that the base rate of veto across *all* proposed
  changes is unidentified. Possibly bound it using pre-RfC talk-page activity.
- **R5 — Staleness ≠ strategic veto.** Im et al. attribute staleness to closer shortage, topic
  complexity, and plain disinterest [confirmed: slides 40–47] — neglect, not obstruction.
  A proposal can die because nobody cared, not because someone blocked it. **Response:** the
  *outcome* (status-quo retention) is the same regardless of motive, and the paper can make the
  weaker, defensible claim ("the process systematically converts inconclusiveness into status-quo
  wins") without over-claiming strategic intent. Where we *do* claim strategy (M3 persistence),
  back it with the behavioral signature (a specific objector repeatedly re-engaging), not mere
  non-closure.
- **R6 — Alternative explanations for the tenure gap.** RfC (content) vs RfA (adminship) differ
  in subject matter; higher RfC tenure may reflect that content disputes attract domain veterans,
  not that seniority is veto power [concluded]. **Response:** M5 must test the *directional*
  claim (tenure→blocking specifically), not just cite the gap; the raw gap is suggestive, not
  evidence.
- **R7 — Reproduction risk.** Building on the un-reproduced close classification would propagate a
  known bug [confirmed: `IMETAL_REPRODUCTION.md`]. **Response:** gate all outcome-direction work
  behind Track-A reproduction.

---

## 8. Suggested paper structure & venue

**Candidate venues** (in rough order of fit):
- **CSCW / PACM HCI** — home turf of Im et al.; the reviewer pool already knows the RfC object,
  which makes the *reframing* (process→power) legible and the differentiation crisp. Best default.
- **ICWSM** — strong fit for a large-N computational-social-science measurement paper; good if the
  emphasis lands on M1/M2 quantitative results.
- **CHI** — possible if the framing foregrounds design implications (making the default visible;
  closer tooling).
- **Interdisciplinary reach:** a version emphasizing veto-player theory could target *New Media &
  Society*, *Journal of Computer-Mediated Communication*, or a governance/*Public Choice*-adjacent
  outlet — worth a second paper rather than diluting the venue-1 framing.

**Rough section outline:**
1. **Introduction** — the "no" asymmetry; consensus as a distribution of power; the invisible
   default; contributions (first large-N measurement of the RfC veto).
2. **Background & related work** — veto players / unanimity / status-quo bias (import the frame);
   Wikipedia governance incl. Im et al. (differentiate on the *direction* dependent variable) and
   Heaberlin & DeDeo (aggregate conservatism ← our micro-mechanism); the WP consensus policy
   corpus as primary source.
3. **The RfC decision procedure and its defaults** — the consensus rule; the documented,
   venue-dependent status-quo defaults (`WP:What "no consensus" means`); why staleness is a
   status-quo win.
4. **Data & method** — population (Track-A-reproduced), outcome-direction classification,
   !vote/threading parsing, tenure via SQL; explicit note on the two buggy baseline stats being
   excluded and recomputed.
5. **Results** — M1 headline veto rate; M2 blocking-minority-size distribution; M6 venue natural
   experiment; then M3/M4/M5 mechanism analyses.
6. **Robustness & counterarguments** — the R1–R7 checks as a first-class section (majority-blocked
   vs split; policy-grounded vs bare objection; selection scope).
7. **Discussion** — implications for consensus institutions generally; design implications
   (surfacing the default; equalizing the burden of proof); limits.
8. **Conclusion.**

**One-line north star for the author:** the paper succeeds if it can put a *number* on how often
the status quo wins in contested RfCs, and a *distribution* on how few people it takes to make
that happen — and can defend both against the "that's just no-mandate / that's just neglect"
objections.

---

### Source ledger (for traceability)

- `data/enwiki/summary.txt` — 1,625 RfC pages 2006–2026; median 10 editors; tenure 1,192d (RfC)
  vs 682d (RfA); **buggy: 4,958d duration, 0.0% revert rate**. [confirmed]
- `datasets/CSCW2018_deliberation_resolution.pdf` (slide deck) — 7,316 RfCs 2011–2017; 58/9/33
  outcome split; closer vs participant experience & counts; 45.56d duration; ADT 75.3% vs 67.2%;
  feature importances; qualitative staleness reasons. [confirmed]
- `IMETAL_REPRODUCTION.md` — Legobot stale signal reliable; current human-close split is an
  artifact (7% not 58%); Track A vs Track B plan; topical-listing venue labels. [confirmed]
- `PLAN.md`, `research_questions.md` — PAWS SQL + Action API strategy; existing RQs to refine.
  [confirmed]
- Web: Tsebelis veto players (Princeton/Michigan); Buchanan & Tullock unanimity (Econlib);
  status-quo-bias / unanimity-gridlock (Public Choice); Heaberlin & DeDeo 2016 (*Future
  Internet*); `WP:CONSENSUS` and `WP:What "no consensus" means` (primary source on
  venue-dependent defaults). [confirmed via search/fetch — full citations to be pulled into the
  bibliography]
