# Source — nl Wikipedia:Stemlokaal/Stemgerechtigde gebruikers
- page_id: 5097832 | revid: 52475456 | 2018-10-18
- url: https://nl.wikipedia.org/wiki/Wikipedia:Stemlokaal/Stemgerechtigde_gebruikers
- language: nl

## ⚠️ This page is NOT a policy
It is a **`{{Stemvoorstel}}` — a proposal to be voted on** — i.e. the nl-wiki equivalent of an
**English Wikipedia RfC**. A proposal is not policy: until adopted it carries no force, and even once
adopted the *rule* lives in the standing pages it amends (`Wikipedia:Stemprocedure`,
`Wikipedia:Regelingen rond moderatoren`, `Wikipedia:Arbitragecommissie/Reglementen`), **not here**.

**Routing verdict (#3a): deliberation / consultation instance → deliberation corpus, NOT the policy
core.** Only the text *inside the proposal* would ever be policy, and only by adoption elsewhere.

### Project-specific signals (see `00_signals.csv`)
The nl signals that mark this as *not policy* (the wiki-dependent detection of §3a):
- **template `{{Stemvoorstel}}`** — vote proposal (the decisive marker);
- **26× `Gebruiker:*/Handtekening`** + `{{Tegen}}` — a page full of signed votes (deliberation);
- **no category** — a standing regulation sits in `Categorie:Wikipedia:Vaste reglementen` /
  `…Stemmen en peilen` (cf. Stemprocedure); the absence here is itself a signal;
- **subpage of `Wikipedia:Stemlokaal/`** — under the voting venue.

### Why it's still in `exploration/`
Kept as an instructive example: it *states rules in prose* and is a **dated event** (accepted 60–26,
17 Oct 2018). The statements extracted here are **proposed** rules — useful to see the extractor work,
but in a real run this page routes to deliberation and the adopted rules are atomized from the standing
pages. Contrast with the sibling `nlwiki_stemprocedure/` (an actual policy).
