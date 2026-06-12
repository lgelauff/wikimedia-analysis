# Research Questions — Wikipedia RFC Process

## Track B: Practice analytics

### Policy text during RfC
- **How often are policy proposals edited during an active RfC process?**
  - Data: revision history of the proposal page (or talk subpage) during the RfC open window
  - API: `action=query&prop=revisions&rvstart=<open>&rvend=<close>` on the proposal target
  - Challenge: identifying the open/close timestamps reliably from wikitext templates

### Proposal vs. outcome divergence
- **How often is the proposed statement different from the final outcome?**
  - Requires diffing the proposed wording (from RfC opening) vs. the policy text after close
  - Likely needs LLM comparison; hard to do purely structurally
  - Proxy: did the target policy page change within 30 days after RfC close?

### Coordinator flexibility
- **How much flexibility does the closer/coordinator have in practice?**
  - Operationalize: do closures ever say "consensus to do X" when the RfC asked "should we do Y"?
  - Detect: parse `{{Rfc result}}` template text vs. original RfC question
  - Look for: contested re-opens, challenges to close outcomes (via talk page reverts)

### Reading burden on participants
- **Distribution of words a participant would need to read at start / middle / end of an RfC**
  - Start: word count of the RfC opening statement
  - Middle: word count of all comments up to the median timestamp
  - End: total word count of the full RfC thread
  - Data: revision snapshots at open, 50% of duration, and close
  - API: `action=query&prop=revisions` with timestamps

### Process phases
- **Are there clearly defined phases in practice?**
  - Theory: open → discussion → close (30-day default)
  - Practice: look for template markers (`{{rfc}}` addition, `{{Rfc result}}` addition)
  - Measurable: distribution of comment timestamps within the open window (front-loaded? late surge?)

### Participant tenure
- **What tenure do participants typically have? Distribution over years. Comparison with RfA.**
  - Tenure = account age at time of RfC comment (registration date vs. comment timestamp)
  - Data: extract usernames from RfC threads → `action=query&list=users&usprop=registration`
  - Trend: has participant tenure distribution shifted over the years?
  - Comparison: same metric for RfA (Wikipedia:Requests for adminship) voters — directly comparable
  - PAWS SQL would make this much easier at scale (actor table has registration dates)

---

## Data source notes

| Question | Public API sufficient? | PAWS needed? |
|---|---|---|
| Edits during RfC | Yes (revision history) | No |
| Proposal vs. outcome | Partial (needs LLM) | No |
| Coordinator flexibility | Yes (template parsing) | No |
| Reading burden | Yes (revision snapshots) | No |
| Process phases | Yes (timestamp analysis) | No |
| Participant tenure | Yes for small N | For large N / trends |
| Tenure trends over years | Slow via API | Yes (actor table) |
| RfC vs. RfA comparison | Slow via API | Yes |
