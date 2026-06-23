# Atomic Policy Definitions — Per-Statement Indicators

Atomic-level operationalization of the ten page-level definitions in
[`policy_definitions_for_review.md`](policy_definitions_for_review.md). Those ten ask
*"is this **page** a policy?"*. Here each becomes a property of a **single candidate
statement**, scored on a 0–1 scale.

Milestone context: [`ROADMAP.md`](ROADMAP.md) M8 (atomic-statement layer); the unit and its
extraction gate are in [`atomic_statements_design.md`](atomic_statements_design.md).

## Agent I/O contract

- **Input:** the host page (as context) + one candidate statement span.
- **Output:** a score in **[0, 1]** for each indicator below — independently.

A *definition* is the 0→1 axis (e.g. bindingness = purely descriptive → hard obligation).
The lettered items under it are **indicators** — signals that place a statement on that axis.
They are *not* the definition.

## Scoring model — flat bag of indicators

Every indicator yields its own 0–1 score and **stands on its own**. We deliberately do **not**
fix aggregation now:

- **No gating.** No indicator zeroes another; a missing signal is just a low score on that one
  indicator.
- **No fixed weights.** How indicators combine into a per-definition score, or into a composite
  "policy-strength", is **learned from the scored data later**, not hard-coded here.
- The job now is to **generate the indicators and get scores for them**. Aggregation,
  weighting, and which indicators turn out to matter are downstream empirical questions.

## Indicator source

- **span** — extractive: the agent points at tokens in the candidate span (per-language
  deontic / sanction / scope lexicons needed). Defensible under the M8 extraction gate.
- **inherited** — taken from the host page's status (banner / category / index membership).
- **structural** — computed from the network or the statement lifespan model (cross-reference
  in-degree, first/last year, revert history), not judged from text.

---

## 1. Bindingness
**Definition:** degree of obligation imposed, from purely descriptive to a hard obligation.

| code | indicator | source |
|---|---|---|
| `BIND_operator` | the span carries a deontic operator (must / should / may / required / prohibited / expected) | span |
| `BIND_obligation` | the operator is an obligation/prohibition rather than a weak modal | span |
| `BIND_unhedged` | the obligation is unhedged (no "generally", "where possible", "editors may wish to") | span |

## 2. Function
**Definition:** extent to which the span is a genuine free-standing rule/procedure vs. scaffolding.

| code | indicator | source |
|---|---|---|
| `FUNC_normative` | the span expresses a norm, rule, procedure, or definition | span |
| `FUNC_constrains` | it constrains how editors edit or behave | span |
| `FUNC_removal` | removing it would change editors' obligations/permissions | span |
| `FUNC_original` | it is original normative content, not a restatement/summary of a rule stated elsewhere | span |

## 3. Scope of governance
**Definition:** what the statement governs. Three independent memberships (a statement can be mixed).

| code | indicator | source |
|---|---|---|
| `SCOPE_content` | governs what goes into articles | span |
| `SCOPE_conduct` | governs how editors behave / interact | span |
| `SCOPE_process` | defines how a procedure / venue runs | span |

## 4. Ratification
**Definition:** strength of community-legitimacy backing behind the statement.

| code | indicator | source |
|---|---|---|
| `RAT_selfcite` | the span cites consensus / an RfC / a discussion as its basis | span |
| `RAT_pageratified` | the host page is in ratified status (policy/guideline banner or core category) | inherited |
| `RAT_stable` | the statement is long-lived / stable (present across many years) | structural |

## 5. Currency
**Definition:** how active and current the statement is, from removed/historical to live.

| code | indicator | source |
|---|---|---|
| `CUR_present` | present in the latest snapshot (status = active) | structural |
| `CUR_pageactive` | the host page is in active (non-historical/proposed) status | inherited |
| `CUR_norevert` | persisted without removal/revert across its interval | structural |

## 6. Self-description
**Definition:** degree to which the span declares its own normative standing.

| code | indicator | source |
|---|---|---|
| `SELF_status` | the span states its own authority / status ("this is policy", "editors are required to follow this") | span |
| `SELF_summary` | the span is a status-labelling nutshell / summary element | span |

## 7. Enforcement
**Definition:** strength of sanction attached, from none to explicit and actionable.

| code | indicator | source |
|---|---|---|
| `ENF_consequence` | the span names a consequence for violation (block, ban, delete, revert, removal) | span |
| `ENF_agent` | it names an enforcing agent / mechanism (admins may…, may be reported to…) | span |
| `ENF_concrete` | the consequence is concrete / actionable rather than vague | span |

## 8. Foundationality
**Definition:** position in the rule hierarchy, from derived local detail to foundational principle.

| code | indicator | source |
|---|---|---|
| `FOUND_principle` | phrased as a general principle (broad, abstract) | span |
| `FOUND_deferred` | other statements / pages defer to or restate it (cross-ref in-degree above the per-wiki median) | structural |
| `FOUND_notexception` | not itself an exception / qualifier | span |

## 9. Generality
**Definition:** breadth of applicability, from a narrow exception/qualifier to a universal rule.

| code | indicator | source |
|---|---|---|
| `GEN_projectwide` | applies project-wide, with no topic / domain restriction | span |
| `GEN_unconditional` | free of conditional scoping ("except", "unless", "in the case of", "for X articles") | span |
| `GEN_primary` | a primary rule, not a qualifier hanging off another rule | span |

## 10. Institutional recognition
**Definition:** extent to which the norm is recognized in the project's own catalogue, from
body-only to restated on an official index/summary.

| code | indicator | source |
|---|---|---|
| `INST_restated` | the norm is restated on an index / summary / Five-Pillars / simplified-ruleset page | structural |
| `INST_pagelisted` | the host page is listed in the official policy index / core category | inherited |
| `INST_shortcut` | the statement carries a stable shortcut / anchor that other pages link to | structural |

---

## Notes

- Several indicators already have a home in the schema: bindingness ≈ `deontic_type`,
  function ≈ the `rule | procedure | summary | meta | scaffolding` segment type, currency ≈ the
  statement lifespan (`first_year` / `last_year` / `status`), and `FOUND_deferred` ≈ statement-level
  cross-reference in-degree — see [`atomic_statements_design.md`](atomic_statements_design.md).
- The **span** indicators each need a per-language **deontic / sanction / scope lexicon**
  (six wikis); these are the lexical hooks that keep the indicators extractive and reproducible.
- Generality and Enforcement directly feed the H3 (defensive accretion) and H4 (new policy as
  prohibition) hypotheses at the atomic level — see [`policy_network_design.md`](policy_network_design.md).
