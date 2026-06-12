# RfC Analysis — Plan

## Data strategy

### Primary: PAWS SQL replicas
PAWS gives direct SQL access to Wikimedia analytics databases. Available tables:

| Table | What we use it for |
|---|---|
| `revision` | All edits to RfC pages — timestamps, editors |
| `actor` | User registration dates → tenure |
| `page` + `categorylinks` | Enumerate all RfC pages by category |
| `comment_revision` | Edit summaries (can identify open/close events) |

Covers all years (2004–present), all Wikimedia projects, no import needed.
Only accessible from within the PAWS environment (`wmpaws.run_sql()`).

### Secondary: MediaWiki Action API (local)
For page content and structured parsing that SQL doesn't provide:
- Full wikitext of each RfC page → parse `{{rfc}}` and `{{Rfc result}}` templates
- Participant usernames from comment signatures
- Opening statement text (reading burden)
- Close statement text (coordinator flexibility)

Already implemented in `cache.py` and `source-collection/wikimedia.py`.

### Reference: CSCW 2018 rfc.sql (archived, not downloaded)
- 7,316 English Wikipedia RfCs, 2011–2017
- Pre-parsed threading and close statements
- Figshare: https://figshare.com/articles/dataset/rfc_sql/7038575
- Paper: `datasets/CSCW2018_deliberation_resolution.pdf`
- Use for: cross-validation, schema reference, literature comparison
- Not downloaded locally (1.1 GB MySQL dump, import impractical without MySQL)

---

## Research questions → PAWS queries

### Q1. Participant tenure distribution
```sql
-- For each RfC comment, get the commenter's account age at time of comment
SELECT
    r.rev_timestamp,
    a.actor_registration,
    DATEDIFF(r.rev_timestamp, a.actor_registration) AS tenure_days
FROM revision r
JOIN actor a ON r.rev_actor = a.actor_id
JOIN page p ON r.rev_page = p.page_id
WHERE p.page_namespace = 4
  AND p.page_title LIKE 'Requests_for_comment/%'
  AND r.rev_timestamp >= '20110101000000'
```

### Q2. RfC volume over time
```sql
SELECT
    LEFT(r.rev_timestamp, 6) AS ym,
    COUNT(DISTINCT p.page_id) AS pages_touched,
    COUNT(*) AS edits
FROM revision r
JOIN page p ON r.rev_page = p.page_id
WHERE p.page_namespace = 4
  AND p.page_title LIKE 'Requests_for_comment/%'
GROUP BY ym ORDER BY ym
```

### Q3. Policy page edit activity (edits during vs. outside RfC windows)
Requires joining RfC open/close timestamps (from API) with revision timestamps
on the target policy page. Two-step: API fetch for timestamps, SQL for edit counts.

### Q4. RfA comparison (same tenure metric)
```sql
-- Same query as Q1 but for Requests_for_adminship/%
WHERE p.page_title LIKE 'Requests_for_adminship/%'
```

---

## Phases

### Phase 1 — PAWS baseline (run in PAWS notebook)
- `paws_rfc_baseline.ipynb`
- Q1 tenure distribution (2011–present)
- Q2 RfC volume trend by year
- Q4 RfC vs. RfA tenure comparison
- Output: CSVs in `data/` for local plotting

### Phase 2 — API content scraping (local)
- `scrape_rfc_content.py`
- Enumerate closed RfCs via `Category:Wikipedia requests for comment (resolved)`
- For each: fetch wikitext, parse open/close timestamps + outcome from templates
- Extract opening statement word count (reading burden at start)
- Store structured records in `data/rfc_structured.jsonl`

### Phase 3 — Analysis notebooks (local)
- `analysis_tenure.ipynb` — tenure distributions, trends, RfC vs RfA
- `analysis_reading_burden.ipynb` — word counts at open/mid/close
- `analysis_phases.ipynb` — comment density curves, phase structure
- `analysis_outcomes.ipynb` — closure rates, coordinator patterns

### Phase 4 — Cross-project (stretch)
Apply Phase 1 queries to Commons, Wikidata, Meta replicas.

---

## Immediate next step
Draft `paws_rfc_baseline.ipynb` with the Q1 + Q2 + Q4 queries,
ready to run when inside the PAWS environment.
