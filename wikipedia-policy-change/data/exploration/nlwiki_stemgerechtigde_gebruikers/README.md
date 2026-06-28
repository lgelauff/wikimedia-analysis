# Sample: nl Wikipedia:Stemlokaal/Stemgerechtigde gebruikers (vote instance, 2018)
Per-stage pipeline artifacts (hand-authored; black-box extractor). Stage → file:
- `00_source.md` — provenance + routing (deliberation instance; canonical rule at Stemprocedure Art.3)
- `01_clean_text.txt` — #2 reader text (vote section retained but marked non-core)
- `02_segments.jsonl` — #3 segments, core vs periphery (`is_core`)
- `04_statements.csv` — #5 atomic statements (11) — schema = the #4 store
- `04_exclusions.csv` — what was NOT extracted + why (completeness invariant)
- `05_ratings.csv` — #6 ratings against the criteria rubric
- `06_within_overlap.csv` — within-page overlap (:2↔:3 = H3 accretion)
Cross-page mapping to Stemprocedure → `../06_crosspage_alignment.md`.
