# Wikipedia Policy Change

Measures how much Wikipedia policy pages have changed over time, across languages.

---

## Overview

For each policy page we fetch one snapshot per calendar year (the last revision of that year) via the MediaWiki Action API and compute a set of change metrics between consecutive annual snapshots.

---

## Scripts

| Script | Purpose |
|---|---|
| `policy_drift.py` | Fetch revision history and compute metrics for one wiki + page. Writes one CSV per page. |
| `plot_policy_drift.py` | Read all CSVs and produce line graphs. `--langs` fetches interwiki equivalents for de/fr/es/ja/nl first. |

**Dependencies** are declared inline (PEP 723). Run with:

```bash
uv run --script policy_drift.py --wiki en.wikipedia --title "Wikipedia:Neutral_point_of_view"
uv run --script plot_policy_drift.py [--langs]
```

---

## Data

### Inputs

- MediaWiki Action API (no scraping). One API call per revision fetched; results cached to `tmp/revisions/<wiki>/<revid>.txt`.
- Interwiki links resolved at run time via `action=query&prop=langlinks` on each enwiki seed page.

### Outputs

`data/policy_drift/<wiki>__<title_slug>.csv` — one row per year.

| Column | Type | Description |
|---|---|---|
| `wiki` | string | e.g. `en.wikipedia` |
| `title` | string | MediaWiki page title |
| `year` | int | Calendar year of the snapshot |
| `revid` | int | Revision ID of the last edit in that year |
| `word_count` | int | Number of tokens in the stripped plain text |
| `sent_count` | int | Number of sentences in the stripped plain text |
| `words_added` | int | Net new word occurrences vs. previous year (see below) |
| `words_removed` | int | Net lost word occurrences vs. previous year (see below) |
| `cosine_vs_prev` | float [0,1] | Cosine similarity of full-text token vectors vs. previous year |
| `containment_old_in_new` | float [0,1] | Fraction of prior-year sentences found in current-year text |
| `containment_new_in_old` | float [0,1] | Fraction of current-year sentences already present in prior-year text |

All metrics are `null` for the first year a page exists (no prior year to compare against).

---

## Definitions

### Text preprocessing

Before computing any metric, wikitext is stripped of markup using regex substitutions in this order:

1. `<ref>` tags and their content
2. HTML comments
3. Templates (`{{ }}`) — single-level only; deeply nested templates may leave residual braces
4. Wikilinks (`[[link|label]]` → label; `[[link]]` → link text)
5. External links (`[url label]` → label; bare URLs → removed)
6. Section headers (`==Foo==` → `Foo`)
7. Bold/italic markers (`''`, `'''`)
8. List/indent prefixes (`*`, `#`, `:`, `;` at line start)
9. Table syntax (`{| … |}`)

The result is normalized to a single flat string of space-separated words. All subsequent metrics operate on this plain-text string.

---

### word_count

**Unit of analysis: full page text.**

```
word_count = len(re.findall(r"\b\w+\b", text.lower()))
```

Token = any contiguous run of word characters (letters, digits, underscore). Punctuation and whitespace are boundaries, not tokens.

---

### words_added / words_removed

**Unit of analysis: full page text, bag-of-words (unordered).**

Each year's text is converted to a `Counter` of token frequencies. The difference between consecutive counters gives the net change per word type:

```
added   = sum( max(0, cur[w] - prev[w])  for all w )
removed = sum( max(0, prev[w] - cur[w])  for all w )
```

This counts vocabulary-level changes, not positional edits. If the word "editor" appears 5 times in year N and 8 times in year N+1, that contributes 3 to `words_added`. It does **not** measure the number of new sentences or paragraphs; it is a rough proxy for expansion vs. contraction.

---

### cosine_vs_prev

**Unit of analysis: full page text, bag-of-words (unordered). Computed once per page-year pair.**

Standard cosine similarity between two term-frequency vectors (no IDF weighting):

```
dot(a, b) / (||a|| * ||b||)
```

where `a` and `b` are the `Counter` vectors of all tokens in the previous and current year respectively.

A value of 1.0 means the two texts use exactly the same words in the same proportions. A value near 0 means the vocabulary is almost entirely different.

**This is a single number per year**, not an average over sentences or paragraphs.

---

### containment_old_in_new

**Unit of analysis: sentences. Aggregated as a fraction (not an average of per-sentence scores).**

Step 1 — sentence splitting of the *prior-year* text:

```python
sentences = [s for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 20]
```

Sentences shorter than 20 characters are discarded (headings, fragment labels).

Step 2 — for each prior-year sentence, check whether its first 60 characters appear as a case-insensitive substring anywhere in the *current-year* full text:

```python
found = s[:60].lower() in current_text.lower()
```

The 60-character prefix is used instead of the full sentence to be robust to minor trailing punctuation changes (e.g. added period, changed citation marker).

Step 3 — aggregate:

```
containment_old_in_new = count(found) / len(prior_year_sentences)
```

**Interpretation:** what fraction of the old policy text was carried forward into the new version. A value of 0.90 means 90% of last year's sentences still appear verbatim (by prefix) somewhere in this year's text.

---

### containment_new_in_old

**Unit of analysis: sentences. Aggregated as a fraction (not an average of per-sentence scores).**

Same as above but with the roles reversed: sentences are split from the *current-year* text and checked against the *prior-year* full text.

```
containment_new_in_old = count(found) / len(current_year_sentences)
```

**Interpretation:** what fraction of this year's policy was already present last year. A low value means most of the current text is genuinely new. Combined with `containment_old_in_new`:

| containment_old_in_new | containment_new_in_old | Pattern |
|---|---|---|
| high | high | Mostly unchanged |
| high | low | New content added, old content kept (expansion) |
| low | high | Old content removed, current text is a subset (pruning) |
| low | low | Substantial rewrite — old and new text diverge |

---

### No per-sentence scores or averages

Neither similarity metric is computed at the sentence level and then averaged. Cosine similarity uses a single vector for the whole document. Containment is a binary match per sentence (found / not found) aggregated into a fraction — not a similarity score per sentence. There is no intermediate per-sentence score that would need averaging.

---

## Languages

The enwiki seed policies are resolved to other-language equivalents via interwiki links (`action=query&prop=langlinks`). Only pages that have an explicit langlink from enwiki are included; no title inference is performed. Coverage varies:

| Language | Policies with interwiki link (out of 10) |
|---|---|
| en | 10 (seed) |
| ja | 9 |
| fr | 6 |
| es | 5 |
| de | 4 |
| nl | varies |

---

## Plots

`data/policy_drift/plots/`

| File | Content |
|---|---|
| `word_count_en.png` | Word count over time, enwiki only |
| `cosine_vs_prev_en.png` | Cosine similarity (vs prior year), enwiki only |
| `containment_old_in_new_en.png` | Old-in-new containment, enwiki only |
| `containment_new_in_old_en.png` | New-in-old containment, enwiki only |
| `*_all.png` | Same metrics, one subplot per wiki (en/de/fr/es/ja/nl) |

X-axis: year. Y-axis: metric value. One line per policy page. Ratio metrics (cosine, containment) are scaled 0–1.
