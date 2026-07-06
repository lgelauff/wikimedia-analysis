# Pipeline runs — real scripted + agent extraction (not hand-authored)

First **real** end-to-end run (vs the hand-authored `../nlwiki_*` exploration): `fetch_clean.py`
(#2, `action=parse`→reader text, NFC) → an LLM agent per page (#3 segment + #5 extract) into the
meaning-first schema. One file set per page: `.clean.txt` (input), `.statements.csv`, `.exclusions.txt`.

## Results
| page | wiki | kind | statements |
|---|---|---|---|
| Neutral point of view | en | content policy | **112** |
| Neutraler Standpunkt | de | content policy (NPOV) | **65** |
| Requests for comment | en | process | **90** |
| Dritte Meinung | de | process (RfC-ish) | **35** |

## What the real run shows
- **Verbosity gap is real at the statement level.** NPOV: **en 112 vs de 65 (~1.7×)** — the same
  ~2× gap the page-level density found (#3), now as a count of atomic norms, not prose length.
- **NPOV en↔de are a clean #7 pair**: both `governance_class=content`, both obligation/prohibition-
  heavy (en obl 50/proh 25; de obl 34/proh 14) — same normative shape, en denser. Good alignment test.
- **RfC has no dewiki equivalent — and it shows in the governance mix.** en RfC = user-user 59 +
  **user-admin 26** (Legobot + closure machinery) + content 5; de Dritte Meinung = content 23 +
  user-user 12 and **zero user-admin** — a peer-only dispute process with no bot/admin layer. en's RfC
  is a bot-mediated formal process; de splits the function (Dritte Meinung / Meinungsbilder / Umfragen)
  and the everyday analogue has none of the admin machinery. A real structural divergence.
- **Meaning-first + deontic-not-required worked**: en-RfC captured policy-through-structure (7-day
  min / 30-day Legobot auto-expiry) with no deontic word; NPOV rendered eligibility as permission/
  condition, not inverted into "a voter must".
