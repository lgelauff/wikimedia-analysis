# Paper (PINNED — not started)

> ⚠️ **STATUS: PARKED / EXPLORATORY. NOTHING HERE IS FINAL.**
> This folder is a placeholder for a possible paper growing out of `rfc-analysis/`.
> No scope, thesis, method, or dataset has been committed to. The notes below are
> first-instinct ideas captured so they aren't lost — they are **starting points to
> argue with, not decisions**. Treat every line as provisional and challengeable.

---

## Working title (provisional)

**"The power of a veto in community decisions"**

⚠️ This is a **hook / framing device**, not the subject of the analysis. The title
gestures at a theme; it does **not** mean the paper argues a veto thesis. See the next
section — an earlier draft made exactly that mistake.

## What the paper is actually about (corrected orientation)

The paper is **descriptive / exploratory**. Its empirical contribution is to
**characterize the RfC (Request-for-Comment) process as it actually exists**:

- what an RfC process *looks like* in practice,
- how it is *used* (volume, participation, duration, outcomes),
- how the *process itself varies* across different communities.

The "veto" idea is, at most, a motivating lens or one observation among many — **not**
the analytical spine. The analysis is not built to prove a claim about vetoes.

> ⚠️ **Lesson from the first pass:** the initial framing memo
> (`notes/first-pass-veto-framing_SUPERSEDED.md`) inverted this — it forced the whole
> analysis to serve the veto thesis. That is backwards and has been set aside. That
> file is kept **only** for the literature/prior-art notes it gathered (veto-player
> theory, Im et al. CSCW 2018, etc.), not for its framing. Do not treat it as direction.

## Candidate axes of variation (all flagged as of interest; NOT all in scope)

The descriptive comparison could run along any/all of these. **Doing all four is
almost certainly too ambitious for one paper** — scope will need to be narrowed later.

- **Cross-project** — enwiki vs Commons, Wikidata, Meta, Wiktionary, … (different projects run consensus processes differently).
- **Cross-language** — enwiki vs dewiki, frwiki, … (same project type, different community norms).
- **Cross-topic within enwiki** — policy vs technical vs content-dispute venues, etc.
- **Over time** — how the process evolved 2006–2026 as the community matured.

⚠️ These were all marked "of interest" in an early conversation. That is a wish-list,
not a research design. Expect to drop most of them.

## What already exists to build on (in `rfc-analysis/`)

- `research_questions.md`, `PLAN.md` — existing (broader) RQs and a PAWS-SQL + Action-API data strategy.
- `data/enwiki/summary.txt` — baseline stats: ~1,625 enwiki RfCs (2006–2026), median ~10 editors/RfC, tenure ~1,192d (RfC) vs ~682d (RfA).
  - ⚠️ **Two stats in that file are almost certainly BUGGY** — "median duration 4,958 days" and "0.0% revert rate." Do **not** rely on them; they need re-checking.
- `IMETAL_REPRODUCTION.md` — notes on reproducing / relating to the CSCW 2018 prior work; flags that some current outcome splits may be artifacts.

## Prior art (nearest neighbors — to be positioned against later, not now)

- **Im et al., CSCW 2018** — "Deliberation and Resolution on Wikipedia" (7,316 enwiki RfCs, 2011–2017). PDF in `../datasets/`. Closest empirical prior work; a descriptive paper must differentiate from it.
- **Heaberlin & DeDeo (2016)** — Wikipedia norm-network / policy self-organization.
- Author's research library: `/Users/lodewijk/Documents/GitHub/research-vault/` (read-only).

## Open questions / decisions deferred (do NOT resolve now)

- Is this one paper or two (descriptive characterization vs. a separate veto-themed argument)?
- Which comparison axis (or single community) is the actual spine?
- Does "veto" survive as a title once the analysis is descriptive, or is it a different paper?
- Unit of analysis: the RfC? the participant? the community-year?
- Venue (CSCW / ICWSM / CHI / …) — untouched.

## Folder layout

```
paper/
  README.md    ← this file (the pin)
  drafts/      ← paper text when it eventually starts (empty)
  figures/     ← generated figures (empty)
  notes/       ← working notes; incl. the SUPERSEDED first-pass framing memo
```

---

*Captured as a placeholder. Revisit deliberately — none of the above is a commitment.*
