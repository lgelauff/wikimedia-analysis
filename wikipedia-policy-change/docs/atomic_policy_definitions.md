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
- **Out of band:** dimensions §4 (ratification) and §5 (live invocation) are **not** scored by
  the span agent; they are populated by a separate **deliberation** pass over discussion pages.

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
- **context** — derived from the rest of the host page (neighbouring statements, lead, nutshell),
  not from the candidate span alone.
- **inherited** — taken from the host page's status (banner / category / index membership).
- **structural** — computed from the network or the statement lifespan model (cross-reference
  in-degree, first/last year, revert history), not judged from text.
- **deliberation** — established from discussion / talk / RfC / Village-Pump pages via a separate
  pass, **not** scored by the span agent (see §4, §5).

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
**Three separate scope questions** — each a standalone 0–1 indicator (a statement can satisfy
more than one). There is no combined "scope" axis.

| code | indicator | source |
|---|---|---|
| `SCOPE_content` | governs what goes into articles | span |
| `SCOPE_conduct` | governs how editors behave / interact | span |
| `SCOPE_process` | defines how a procedure / venue runs | span |

## 4. Ratification — *deliberation-sourced, not agent-scored*
**Definition:** strength of community-legitimacy backing behind the statement.

Relevant, but it cannot be read off the policy page or the candidate span. Establishing that a
statement is community-ratified means tracing its **deliberation history** — the talk-page / RfC /
Village-Pump discussion that adopted it. Populated by a separate deliberation pass (after digging
through the discussion record), **not** by the span agent. No per-span score.

## 5. Live invocation — *deliberation-sourced, not agent-scored*
**Definition:** how actively the statement functions as a live rule — the degree to which editors
**cite it as a justification** when arguing for, or asking for, a decision.

Sourced the same way as §4: read from discussion pages where editors refer to the statement as a
motivation in an argument, **not** scored by the span agent. (The statement's active/removed
lifespan is separate metadata from the identity model.)

## 6. Contextual relation
**Definition:** how the statement sits relative to the rest of its page — from standalone and
central to dependent on / derivative of other statements on the page.

| code | indicator | source |
|---|---|---|
| `CTX_standalone` | interpretable on its own, not reliant on surrounding statements (no unresolved "this", "such cases", "the above") | span + context |
| `CTX_summary` | restates / condenses another rule stated elsewhere on the page (lead, nutshell) | context |
| `CTX_central` | central to the page's stated topic rather than a peripheral aside / example / see-also | context |

## 7. Enforcement
**Definition:** strength of sanction attached, from none to explicit and actionable.

| code | indicator | source |
|---|---|---|
| `ENF_consequence` | the span names a consequence for violation (block, ban, delete, revert, removal) | span |
| `ENF_agent` | it names an enforcing agent / mechanism (admins may…, may be reported to…) | span |
| `ENF_concrete` | the consequence is concrete / actionable rather than vague | span |
| `ENF_pagecontext` | enforcement is discussed or referred to elsewhere in the page's policy text | context |

## 8. Foundationality
**Definition:** position in the rule hierarchy, from derived local detail to foundational principle.

| code | indicator | source |
|---|---|---|
| `FOUND_principle` | phrased as a general principle (broad, abstract) | span |
| `FOUND_derived` | the page gives clear indications of more specific derived rules / policy stemming from it ("see X for details", "implemented by…", "in more detail at…") | context |
| `FOUND_notexception` | not itself an exception / qualifier | span |

## 9. Generality
**Definition:** breadth of applicability, from a narrow exception/qualifier to a universal rule.

| code | indicator | source |
|---|---|---|
| `GEN_projectwide` | applies project-wide, with no topic / domain restriction | span |
| `GEN_unconditional` | free of conditional scoping ("except", "unless", "in the case of", "for X articles") | span |
| `GEN_primary` | a primary rule, not a qualifier hanging off another rule | span |

## 10. Layout prominence
**Definition:** extent to which the **page layout affirms the statement's importance**, from
buried in the body to placed and emphasized as a key rule.

| code | indicator | source |
|---|---|---|
| `LAYOUT_lead` | appears in the page lead / opening section rather than deep in the body | context |
| `LAYOUT_highlighted` | set off by layout — nutshell box, highlighted/boxed, bold or emphasized | context |
| `LAYOUT_heading` | is, or sits directly under, a top-level section heading rather than buried in a sub-list / footnote | context |

---

## Notes

- Several indicators already have a home in the schema: bindingness ≈ `deontic_type`,
  function ≈ the `rule | procedure | summary | meta | scaffolding` segment type, and
  `FOUND_deferred` ≈ statement-level cross-reference in-degree — see
  [`atomic_statements_design.md`](atomic_statements_design.md). The statement's active/removed
  lifespan (`first_year` / `last_year` / `status`) is carried as identity-model metadata, separate
  from these indicators.
- Dimensions §4 and §5 join the **deliberation / RfC track** (see [`ROADMAP.md`](ROADMAP.md) M11,
  RQ2) — the discussion record behind a statement, not its policy-page text.
- The **span** indicators each need a per-language **deontic / sanction / scope lexicon**
  (six wikis); these are the lexical hooks that keep the indicators extractive and reproducible.
- Generality and Enforcement directly feed the H3 (defensive accretion) and H4 (new policy as
  prohibition) hypotheses at the atomic level — see [`policy_network_design.md`](policy_network_design.md).
