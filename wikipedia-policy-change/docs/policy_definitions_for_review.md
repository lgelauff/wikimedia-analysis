# What Counts as a Wikipedia Policy — 10 Candidate Definitions for Expert Review

## What this is

Ten genuinely different working definitions of "a Wikipedia policy," for human experts to compare and choose among. They are **not** ten phrasings of one idea: each keys on a *different* axis (how binding it is, what it governs, how it got adopted, how it describes itself, etc.). The aim is to surface the choices an expert is implicitly making, so they can pick deliberately.

## What was sampled

I drew several independent random subsets of pages from the official "list of policies and guidelines" index of 10 language editions, then fetched the actual current page text (lead sentence + any status box/banner) through the MediaWiki API. Languages and rough sampled counts:

- **Latin script:** English (7), German (6), Dutch (4), Spanish (6), French (6)
- **Non-Latin script:** Japanese (7), Chinese (6), Arabic (6), Korean (6), Hebrew (6)

Roughly 55 pages, spanning content rules, conduct rules, process/administrative pages, foundational-principle pages, style guides, and a couple of pages that turned out **not** to be policy at all but were linked from the index. Concrete grounding examples below name the page and language; titles are translated where helpful.

A key cross-language observation drove the design: **the editions do not mark policy status the same way.** English, Spanish, Arabic, Korean and Chinese stamp pages with an explicit status banner (an "official policy" box, a "guideline" box, a "style guideline" box, etc.); German and Hebrew mostly do *not* — they signal status through a shared navigation box and category membership instead, and French distinguishes a binding "rule" from an advisory "recommendation." So any single definition privileges some editions' conventions over others. The ten below deliberately spread across those conventions.

---

## The 10 definitions

### 1. Authority / bindingness
A policy is a page the community treats as a rule editors **must** follow, as opposed to advice they are merely encouraged to weigh — typically signalled by a top-of-page box declaring it an official, enforceable standard.
- *Criterion:* degree of obligation (mandatory vs. advisory).
- *Includes / excludes:* includes pages flagged "official policy"; **excludes** anything flagged as a "guideline," "recommendation," or "essay." French is the sharpest test: it would count a page banner-marked *règle* (rule) but exclude *Consensus*, which is banner-marked *recommandation* (recommendation).
- *Grounding:* "What Wikipedia is not" (Spanish, banner *Política*); "Speedy-deletion criteria" (Korean, banner *정책*/policy); edge case — "Consensus" (French) is excluded here but included under most other definitions.

### 2. Function — what the page is *for*
A policy is a page whose job is to *prescribe how the encyclopedia is built or how editors behave* — to set standards — rather than to inform, list, archive, or coordinate an activity.
- *Criterion:* the page's communicative purpose (normative vs. informational/coordinative).
- *Includes / excludes:* includes both binding policies and advisory guidelines, since both prescribe; **excludes** index pages, press/info pages, and process trackers. This is the only definition that cleanly throws out two pages that were linked from the index but merely inform or coordinate.
- *Grounding:* counts "Reliable sources" (Japanese) and "No personal attacks" (German); **excludes** "Press" (Dutch — background info for journalists) and "Polls/Meinungsbilder" (German — a live list of running community votes).

### 3. Scope of governance — conduct vs. content vs. process
A policy is a rule about **one of three things**: how editors must behave, what may go into articles, or how a formal procedure is run; the definition can be set to admit all three or restricted to a chosen subset.
- *Criterion:* the object being governed (people, text, or procedure).
- *Includes / excludes:* a "conduct-only" reading includes etiquette and no-attacks rules but excludes sourcing and style rules; a "content-only" reading does the reverse; a "process" reading admits deletion machinery. Several editions tag this explicitly (Japanese marks pages *subcategory = 行動 / conduct* vs. *内容 / content*).
- *Grounding:* conduct — "Etiquette" (Japanese, tagged conduct); content — "Reliable sources" (Japanese, tagged content); process — "Speedy-deletion criteria" (French/Korean). Edge case: the three-revert rule (Arabic) is a conduct rule expressed as a hard numeric limit.

### 4. Community ratification — adopted by consensus
A policy is a page that the editing community has collectively **accepted as binding through open discussion**, so its authority comes from documented community agreement rather than from any single author or official.
- *Criterion:* source of legitimacy (community consent).
- *Includes / excludes:* includes long-standing community-ratified rules; **excludes** newly written proposals, one-person essays, and rules imposed from outside the community (e.g. Foundation legal directives). French states this axis outright.
- *Grounding:* "Consensus" (French) literally says rules "summarize the community's consensus more than they create it"; "What Wikipedia is not" (Spanish/Hebrew) is a ratified community standard. Edge case: a Foundation "Office Action" page (German index) would be *excluded* here despite being binding — it isn't community-adopted.

### 5. Process of adoption / lifecycle stage
A policy is a page that has **passed through and currently sits in the "active" stage** of the community's rule-making lifecycle — formally promoted and not since downgraded to proposed, historical, failed, or essay status.
- *Criterion:* current lifecycle state (live vs. proposed/retired).
- *Includes / excludes:* includes any page currently in force regardless of how strong it is; **excludes** drafts, rejected proposals, and superseded/archived rules. This is the only definition that turns purely on *temporal status* and would change its answer year to year.
- *Grounding:* the active machinery that decides this is visible in "Polls/Meinungsbilder" (German), the venue where rules are voted up or down; an in-force example is "Username policy" (Chinese). Edge case: a page tagged "historical" is excluded here but might still satisfy the *function* definition (#2).

### 6. Self-description — the page's own status claim
A policy is any page that **announces itself as a policy** — i.e. carries a status box or opening sentence in which the community declares the page's standing — letting the page's own label decide.
- *Criterion:* explicit self-labelling.
- *Includes / excludes:* includes everything banner-stamped "policy"; on a strict reading **excludes** pages that lack such a banner even if they function identically — which would drop most German and Hebrew rules, since those editions rarely use a status banner. Exposes how banner-dependent any "self-description" rule is.
- *Grounding:* "Reliable sources" (Japanese) opens with a *Guideline* box; "Reliability" (Arabic) opens with a *سياسة*/policy box; edge case — "No personal attacks" (German) carries only a shared conventions navbox and no status banner, so a strict self-description rule excludes it.

### 7. Enforcement — backed by sanctions
A policy is a rule whose violation can trigger a **concrete consequence** — content removal, a block, or administrative action — as opposed to a norm that is encouraged but carries no penalty.
- *Criterion:* presence of an enforcement mechanism.
- *Includes / excludes:* includes rules with teeth (blocking, deletion, reverting limits); **excludes** aspirational or stylistic advice with no sanction attached. Would split the guideline tier in half: some guidelines are enforced, many are not.
- *Grounding:* the three-revert rule (Arabic — breach is itself sanctionable) and "Speedy-deletion criteria" (Korean/French — empowers admins to delete) are in; "Abbreviations style guide" (English) is out — breaking it just gets your text re-styled, not penalized.

### 8. Position in the rule hierarchy — foundational vs. derived
A policy is a page that sits at or near the **top of the rule hierarchy** — a foundational principle from which the more specific rules are derived and to which they must defer.
- *Criterion:* rank/centrality within the body of rules.
- *Includes / excludes:* on a strict reading includes only the small set of core/founding principles and **excludes** the many specific downstream rules; a looser reading includes any page that other pages must yield to. Cleanly separates "constitution-level" pages from ordinary ones.
- *Grounding:* "Five pillars / חמשת עמודי התווך" (Hebrew) presents itself as the five basic principles underlying everything else; German groups such pages under a *Grundprinzipien*/founding-principles category. Edge case: an ordinary style rule like "Abbreviations" (English) is excluded as derived, not foundational.

### 9. Relationship to other rules — generality vs. local exception
A policy is a **general, site-wide rule that overrides narrower or topic-specific pages**, distinguishing it from the localized conventions that apply only within a subject area or that merely implement it.
- *Criterion:* breadth of applicability and override priority.
- *Includes / excludes:* includes broad rules applying to the whole project; **excludes** topic-scoped style sub-pages and local conventions. This is the sharpest tool for the "is the style manual a policy?" question: it admits the general manual's core but excludes its many subject-specific offshoots.
- *Grounding:* general — "Deletion policy" (English, applies project-wide); local exception — "Manual of Style/Abbreviations" (English) and "Manual of Style/Singapore-related articles" (English), which only refine style within narrow scopes. Edge case: a country-specific style page is excluded even though it carries a guideline banner.

### 10. Institutional recognition — listed and categorized as policy by the community's own bookkeeping
A policy is any page the community's **official index and category system records as a policy or guideline** — i.e. it is recognized as such by the project's own catalogue, independent of what the page text says.
- *Criterion:* membership in the community's authoritative roster.
- *Includes / excludes:* includes whatever the index/category lists, so it captures banner-less editions that signal status by category rather than text; **excludes** pages not on any roster. Its weakness is the mirror of its strength: it will wrongly admit non-rules that got linked from the index (which is exactly what happened in the sample).
- *Grounding:* relies on the "list of policies and guidelines" index page itself across all editions, plus categories like *Politicas y convenciones* (Spanish) and *Grundprinzipien* (German); edge case — "Press" (Dutch) is *listed* and so admitted here, even though by function (#2) it is plainly not a policy.

---

## The hardest disagreements experts will face

The deepest split is **binding vs. advisory** (definitions 1 and 7 draw the line tightly; 2, 6 and 10 admit the whole policy-plus-guideline body): editions disagree at the source, since French formally separates *rule* from *recommendation* while German and Hebrew barely mark the distinction at all, so a "policy = binding only" rule silently reclassifies large parts of those wikis. Close behind is **how status is read** — definition 6 (self-description) and definition 10 (institutional listing) will disagree precisely on the banner-less German/Hebrew pages, where the text makes no claim but the category does, and definition 10's reliance on the index also drags in clear non-policies like the Dutch press page and the German polls tracker that definition 2 (function) cleanly rejects. The **content-vs-conduct-vs-process** carve-up (definition 3) is orthogonal to all of these and forces a separate explicit choice. Two perennial edge questions fall out predictably: **"is the Manual of Style a policy?"** — no under definitions 1, 7, 8, 9 (advisory, unenforced, derived, local), but yes under 2, 6, 10 — and **"do essays count?"** — no under every definition except possibly a loose reading of 2, since essays neither bind, enforce, ratify, nor self-declare as policy.
