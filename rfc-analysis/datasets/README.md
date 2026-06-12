# RfC Analysis — External Datasets

## rfc.sql  (PRIMARY)

| Field | Value |
|---|---|
| **Source** | Figshare https://figshare.com/articles/dataset/rfc_sql/7038575 |
| **Download** | https://ndownloader.figshare.com/files/12935099 |
| **Paper** | "Deliberation and Resolution on Wikipedia: A Case Study of Requests for Comments", Im et al., CSCW 2018. https://dl.acm.org/doi/10.1145/3274343 |
| **Size** | ~1.1 GB (SQL dump) |
| **Coverage** | English Wikipedia RfCs, 2011–2017, N=7,316 |
| **License** | Not explicitly stated on Figshare (paper is ACM open access) |
| **Local file** | not downloaded (1.1 GB MySQL dump, import impractical without MySQL) |
| **Paper PDF** | `datasets/CSCW2018_deliberation_resolution.pdf` |

### Known schema (from paper)
Tables reported in the paper include:
- RfC metadata: page title, open/close timestamps, closer username
- Closing statement text
- Participant list with comment counts
- Thread/reply structure (authors, timestamps, word counts)
- Outcome label (consensus / no-consensus / withdrawn / other)

### Known gaps
- Cuts off at 2017 — misses ~8 years of RfCs
- English Wikipedia only
- Schema not formally published; inferred from paper methods section
- No participant registration dates (tenure requires separate API lookup)
- No full comment text in structured form (only closing statement)

---

## Wikipedia Talk Corpus  (SUPPLEMENTARY)

| Field | Value |
|---|---|
| **Source** | Figshare https://figshare.com/articles/dataset/Wikipedia_Talk_Corpus/4264973 |
| **Coverage** | All English Wikipedia talk page diffs, 2001–2015 |
| **Size** | Large (yearly .tar.gz files) |
| **License** | CC0 |
| **Use for** | Full comment text recovery; reading burden analysis |

---

## WikiConv Corpus  (SUPPLEMENTARY)

| Field | Value |
|---|---|
| **Source** | Figshare https://figshare.com/projects/WikiConv/57110 |
| **Paper** | EMNLP 2018 |
| **Coverage** | Full conversational history of all Wikipedia talk pages |
| **Use for** | Reconstructing full RfC thread text for post-2017 period |
