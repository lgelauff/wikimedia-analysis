# Sample: nl Wikipedia:Stemprocedure (standing policy, {{Vast}})
Per-stage pipeline artifacts (LLM-generated; black-box extractor). Stage → file:
- `00_source.md` — provenance + routing (standing policy)
- `00_signals.csv` — project-specific category/template signals + the policy-vs-not verdict
- `01_clean_text.txt` — #2 reader text (cleaned nl prose, 6 articles)
- `02_segments.jsonl` — #3 segments by article, core vs periphery
- `04_statements.csv` — #5 atomic statements, **minimal** pass (24) — schema = the #4 store
- `04_statements_v2_inclusive.csv` — #5 **gracious** pass (43): + intro principles, all of Art.1, qualifiers/parentheticals, compound splits; adds a `salience` col (core/supporting/context) so lead/context is **down-weighted, not dropped**
- `04_exclusions.csv` — what was NOT extracted + why ({{Vast}}/sidebar/rationale/category)
- `05_ratings.csv` — #6 ratings against the criteria rubric
- `06_within_overlap.csv` — within-page overlap (:18∧:19 conjunction)
Cross-page mapping to the vote instance → `../06_crosspage_alignment.md`.
