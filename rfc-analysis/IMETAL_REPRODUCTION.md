# Im et al. (CSCW 2018) — corrected method + reproduction vs. improvement

Re-derived from the talk slides (`datasets/CSCW2018_deliberation_resolution.pdf`).
Two explicit tracks: **(A) faithful reproduction** (match their method + numbers) and
**(B) doing better** (extensions). Keep them separate — don't let B contaminate A's
comparability.

---

## What Im et al. actually did (corrected)

An RfC = a `{{rfc}}` tag placed on a talk page. The tag auto-lists the page on topical
**`Wikipedia:Requests for comment/<topic>`** pages ("within 24h… added to the following
lists; when discussion ends, remove this tag and it's removed from the list").

**Three outcomes, discriminated by WHO removes the tag and whether a formal close exists:**

| outcome | resolved? | tag removed by | signal |
|---|---|---|---|
| **Formally closed** | yes | **uninvolved editor (closer)** | a **closing box** (`{{closed rfc top}}`/`{{archive top}}` "The following discussion is closed…") added by someone who did **not** participate |
| **Informally ended** | yes | participant / initiator / uninvolved | tag removed, **no** formal closing box (overwhelming agreement or initiator withdrawal) |
| **Stale** | no | **Legobot** | Legobot removes the expired tag (~30d, no closer acted) |

Their reference numbers (2011–2017): **7,316 RfCs — 58% formal, 9% informal, 33% stale**;
closers far more experienced than participants (~39.8k vs ~14k edits); avg duration 45.6d.

**Operational signals required:**
1. **Population + open** = `{{rfc}}` placement (≈ Added to a topical list).
2. **Close = the tag-removal edit** (who + when). Legobot → stale. Human → formal/informal.
3. **Formal vs informal** = presence of a **closing-box template** added by an **uninvolved**
   editor → needs (a) the closing box in wikitext, (b) the **participant set** (who edited the
   discussion) to judge involved-vs-uninvolved.
4. **Participants** = non-bot editors of the discussion between open and close.

---

## Where our notebook diverged (why 7% not 58%)

`paws_rfc_imetal.ipynb` (my reconstruction, NOT their method):
- Keyed opens on Legobot **"Adding RFC ID"** talk-edits (one clerk bot, one summary string).
- Detected human closes by **edit-summary REGEXP** ("rfc closed" etc.).

Both are wrong vs. the paper:
- **Close ≠ edit summary.** Formal closure is a **closing-box template**, not a summary keyword.
  Matching summaries catches a small minority → 7% "human_close" instead of ~58%+9% human-ended.
- **Open keying is incomplete** (~6% within-era miss + the pre-2013 **RFC bot** era + a 2020
  summary-variant), because we keyed on one bot's one summary instead of the tag/listing.
- We never computed the **closer-involvement** distinction at all (formal vs informal).

So the current opens/stale numbers are roughly sound (Legobot stale-removal is a reliable
signal); the **human-close split is not a reproduction** and must be rebuilt.

---

## Track A — faithful reproduction (match Im et al.)

Goal: reproduce 7,316 / 58 / 9 / 33 on **2011–2017**, their window.
- **Population/open:** RfCs from the `{{rfc}}` tag (via the topical listing pages' Added events
  and/or the talk-page tag placement). Window-limit to 2011–2017 for the comparison.
- **Close:** detect the **tag-removal** revision per RfC (wikitext diff: `{{rfc}}` present→absent);
  closer = that editor; Legobot → stale.
- **Formal vs informal:** closing-box template (`{{closed rfc top}}`/`{{archive top}}`/
  `{{discussion top}}`) added by an **uninvolved** editor → formal; else informal.
- **Participants/closer-experience:** non-bot editors open→close; total edit counts for closers.
- **Validate:** our split should land near 58/9/33 and ~45d duration. Gap = remaining method
  divergence to chase.

This is the bar that proves we can reproduce; only then are deviations *findings*, not bugs.

---

## Track B — doing better (beyond Im et al.)

Each is an explicit extension, kept OUT of the Track-A comparison:
- **Listing-page frame, back to 2005** — drive population from the topical pages' Added/Removed
  history (clerk-bot **and** the manual pre-bot era). Fixes pre-2011 + the bot blind spots.
- **Clerk-bot union** — RFC bot ∪ Legobot ∪ successors, not Legobot alone (pre-2013 coverage).
- **Disqualified outcome (new, 4th category)** — human removals for "not a policy / invalidly
  formed / incorrectly placed" are *ejections*, not resolutions; Im et al. fold these into
  informal/stale. Splitting them out de-noises the resolution rate. (Found in the listing-page
  summaries.)
- **Reopen handling** — a fresh tag/RFC-ID = a new instance; transient removal+revert = not a
  close (persistence check). Im et al. don't detail this.
- **Topic labels for free** — which topical listing page → subject area; the
  `…/Wikipedia policies and guidelines` list isolates **policy RfCs**, the bridge to the
  policy-change track's reform-case-study RQ.
- **Extended window 2011–2026** + the complementary deliberation venues (Village Pump, CENT)
  as *separate labeled datasets* (never merged into the Legobot-pure set).

---

## Build implication

Both tracks need the same core that the notebook skipped: **per-RfC tag-removal detection +
closing-box detection + participant set** (talk-page wikitext, keyed on the known RfC pages).
The listing pages give the population cheaply (API-only, to 2005); the outcome classification
is the substantive work and is identical for A and B — A just restricts the window and the
taxonomy to their three classes.
