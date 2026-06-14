# Data Architecture — storage tiers, size budgets, reproducibility

Single standing reference for **where each kind of data lives and how big it gets**. Consolidates
storage decisions previously scattered across `policy_network_design.md` (§2, §4b, cache block).
Companion: the atomic layer's own sizing in [`atomic_statements_design.md`](atomic_statements_design.md);
live DDL in [`../net/schema.sql`](../net/schema.sql).

---

## 1. The storage-tiering rule

Three tiers, by data type — **never mix them**:

| tier | what | where | why |
|---|---|---|---|
| **Structure** | nodes, links, facets, registries, provenance, statements-as-rows | **SQLite + ToolsDB** | small, relational, queryable; the web app serves this |
| **Text** | raw wikitext, cleaned text | **gzipped files** in `policy_cache/`, referenced by `revid`/`page_id` | bulky, write-once, addressed by id — never inline in the DB |
| **Embeddings** | statement vectors | **vector store** (FAISS / `sqlite-vec` / Parquet), keyed by `statement_id` | the only layer that genuinely outgrows a relational store |

**Invariant:** the relational DB and the per-build archive hold *structure + references*, never
blobs. Text is recovered from the cache via `(revid, char_span)`; embeddings via `statement_id`.

---

## 2. Size budgets (3 wikis, full history)

| layer | rows / size | store | comfortable? |
|---|---|---|---|
| structural `node`/`link`/facets (current) | ~50 MB | SQLite/ToolsDB | ✅ |
| structural + Phase-2 expansion | ~500 MB, ~6M link rows | SQLite/ToolsDB | ✅ |
| raw wikitext cache | ~0.1–1.3 GB | files | ✅ (disk) |
| cleaned text | ~0.5–1 GB | files | ✅ (disk) |
| atomic statements (rows, identity model) | ~450k rows, ~150 MB | SQLite/ToolsDB | ✅ |
| statement **embeddings** | **~2 GB** | vector store | ✅ (not in DB) |

SQLite is happy into the tens of GB with indexing; nothing here approaches that. See
`atomic_statements_design.md` §7 for the naive-vs-identity comparison that keeps these small.

---

## 3. The binding constraint is ToolsDB quota, not SQLite

SQLite is a local file — it scales with disk. The real limit is the **ToolsDB (MariaDB) per-tool
quota**. Therefore:

- **ToolsDB holds only the structural network the web app serves** (nodes, links, facets,
  registries, provenance, statement rows). Compact and indexed.
- **Everything heavy stays off ToolsDB** — text as files, embeddings in a vector store, full
  per-build snapshots as SQLite archive files.
- Watch the quota as data grows; request an increase before it binds. Do **not** let text or
  vectors into ToolsDB.

---

## 4. Cache = reproducibility substrate

The cache is the pinned evidence base. Because dumps expire (~6 months), pages get deleted, and
the live API drifts, the **raw layer is often the only durable copy of the exact inputs** — the
whole analysis must be re-derivable from cache alone, no re-fetch. Layout, keyed by immutable
revid:

```
policy_cache/<wiki>/
  raw/<revid>.txt                    # immutable input — fetch once, PRESERVED (not tmp/)
  clean/<cleaner_vN>/<revid>.txt     # derived from raw — keyed by cleaner version
  struct/<parser_vN>/<revid>.json    # derived from raw — links/cats/templates
manifest.sqlite                      # (page_id, year)->revid; revid->{ns, timestamp, sha256, source, fetched_at}
```

Rules: `raw/` keyed by revid alone (content never changes) and preserved durably (publishable
under CC BY-SA with attribution — title list + hashes safest by default). Derived layers are
version-keyed so a cleaner/parser change regenerates from raw without re-fetch, and every result
is attributable to a specific version.

*(The historical build currently caches `policy_cache/raw/<wiki>/<revid>.txt`; `clean/` and
`struct/` arrive with the content/atomic work.)*

---

## 5. Per-build immutable archive + provenance (already implemented)

- Every build emits a git-stamped immutable snapshot:
  `policy_net_archive/<wiki>_<year>_<timestamp>_<commit>.sqlite` — never overwritten.
- The `provenance` table records *why* each node is core/candidate (which template/category/
  navbox + score). The `build_run` table pins `git_commit` + thresholds.
- Archives hold **structure only** — no text, no embeddings (reference them).

---

## 6. Decision log

- Structure → SQLite + ToolsDB; text → files; embeddings → vector store. *(locked)*
- ToolsDB = served structural network only; quota is the binding limit. *(locked)*
- Statement text stored by reference (span anchor), never inline. *(locked, see atomic doc)*
- Embed unique statements, not statement-years. *(locked, see atomic doc)*
- Vector store choice (FAISS / sqlite-vec / Parquet) — *deferred to M8/M9.*
- Raw-cache publication format (full text vs hashes+titles) — *default hashes+titles; revisit.*
