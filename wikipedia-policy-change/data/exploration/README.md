# Exploration data — hand-authored pipeline samples

Small, **hand-authored** samples that walk a single real page through the atomic-statement pipeline
*by hand* (a human/LLM acting as the black-box extractor), to sanity-check the design **before** the
scripted pipeline (GitHub issues #2–#8) exists.

**These are not pipeline output.** They are illustrative + a seed for a future gold/eval set (the
rater-validation set in #6, the boundary-F1 set in #5). When the real pipeline runs, it regenerates
its own data; these stay as reference examples and hand labels to compare against.

Schema matches the planned statement store (#4): `statement_id` = `<wiki>:<page_id>:<seq>`, plus
`source_quote` (closest original-language quote), `statement_orig` (nl), `statement_en`
(interpretation aid — **not** a matching key), `segment_type`, `deontic_type`, `governance_class`.
Char offsets are omitted (hand sample). See [`../../docs/classification.md`](../../docs/classification.md)
and [`../../docs/atomic_statements_design.md`](../../docs/atomic_statements_design.md).

**Each sample is paired with an `_exclusions.csv`** — what we deliberately did *not* turn into a
statement, and why (proposal metadata → meta, vote rationales → deliberation, layout → scaffolding,
duplicated summaries → linked-not-counted). **Completeness invariant:** every part of the page is
accounted for as either an extracted statement *or* a logged exclusion — no silent drops, so a
reviewer can audit whether a real norm was wrongly excluded.

**Framing note (`deontic_type`):** statements carry the correct **normative relation**, not just the
proposition. Eligibility rules are rendered as *"a user is eligible to vote only if…"* (subject = the
person acquiring the right), **never** as *"a voter must…"* (which reverses an eligibility condition
into an obligation). `deontic_type` ∈ {eligibility, obligation, prohibition, permission, condition,
definition, scope}.

## Samples

| file | page | page_id / revid | n | notes |
|---|---|---|---|---|
| [`nlwiki_stemgerechtigde_gebruikers.csv`](nlwiki_stemgerechtigde_gebruikers.csv) | nl `Wikipedia:Stemlokaal/Stemgerechtigde gebruikers` | 5097832 / 52475456 (2018-10-18) | 11 | voter-eligibility rules |
| [`nlwiki_stemgerechtigde_gebruikers_exclusions.csv`](nlwiki_stemgerechtigde_gebruikers_exclusions.csv) | ↳ exclusions for the above | — | 9 | what was *not* extracted + why |

### nlwiki_stemgerechtigde_gebruikers
Source: https://nl.wikipedia.org/wiki/Wikipedia:Stemlokaal/Stemgerechtigde_gebruikers — a 2018
*Stemvoorstel* (vote instance). **Routing note:** by the §3a router this page is a
**deliberation/consultation instance**, not standing policy — the canonical eligibility rule lives at
`Wikipedia:Stemprocedure#Artikel 3`. It was atomized here anyway because (a) it states the rules in
prose and (b) a *passed* vote is a **dated adoption event** (accepted 60–26, 17 Oct 2018), so it dates
the birth of the activity-requirement rules. What this sample exercises:
- **deontic-informed-not-required** — `:1 :2 :3 :7 :8` are conditional eligibility *definitions* with
  no must/should; a marker/regex extractor misses them.
- **routing before counting** — ~80% of the page is vote rationales (deliberation), dropped at
  segmentation; only the ~11 norms survive.
- **overlap = finding** — `:2`→`:3` reads as H3 accretion (recency qualifier added); `:4`→`:5` as
  genuine reform (lifetime → lapsing).
- **governance_class** = user-admin throughout (a clean case).
