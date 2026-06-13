-- schema.sql — ToolsDB tables for the policy network (M1: current/2026 structural slice).
-- Database: s#####__policies  (prefix = your replica.my.cnf user= line; never hardcode).
-- Designed to extend to historical years (the `year` column) without schema change.
-- Snapshot rule: year = state at 1 Jan of that year. The current slice uses the
-- dump/replica "now" labelled with the run year (passed in by the script).

-- One row per admitted node per year.
CREATE TABLE IF NOT EXISTS node (
  wiki          VARCHAR(32)    NOT NULL,
  page_id       INT UNSIGNED   NOT NULL,
  year          SMALLINT       NOT NULL,
  title         VARBINARY(255) NOT NULL,
  namespace     INT            NOT NULL,
  is_redirect   TINYINT        NOT NULL DEFAULT 0,
  wikidata_qid  VARBINARY(32)  DEFAULT NULL,
  admitted_via  VARCHAR(16)    NOT NULL,         -- 'category' | 'template' | 'both'
  PRIMARY KEY (wiki, year, page_id),
  KEY k_ns   (wiki, year, namespace),
  KEY k_qid  (wiki, year, wikidata_qid)
) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- One row per outgoing relation from an admitted node.
-- to_page is the resolved canonical page_id (after redirect) when the target is a
-- real page; NULL when the target page does not exist. to_admitted flags whether
-- the target is itself an admitted node (policy->policy edge).
CREATE TABLE IF NOT EXISTS edge (
  wiki        VARCHAR(32)    NOT NULL,
  year        SMALLINT       NOT NULL,
  from_page   INT UNSIGNED   NOT NULL,
  edge_type   VARCHAR(16)    NOT NULL,           -- 'category' | 'template' | 'wikilink'
  to_ns       INT            NOT NULL,
  to_title    VARBINARY(255) NOT NULL,
  to_page     INT UNSIGNED   DEFAULT NULL,
  to_admitted TINYINT        NOT NULL DEFAULT 0,
  KEY k_from (wiki, year, from_page),
  KEY k_type (wiki, year, edge_type),
  KEY k_to   (wiki, year, to_page)
) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Discovered template indicators (per year x wiki).
CREATE TABLE IF NOT EXISTS template_registry (
  wiki              VARCHAR(32)    NOT NULL,
  year              SMALLINT       NOT NULL,
  template_title    VARBINARY(255) NOT NULL,
  n_transclusions   INT            NOT NULL DEFAULT 0,   -- within the admitted set
  is_indicator      TINYINT        NOT NULL DEFAULT 0,
  PRIMARY KEY (wiki, year, template_title)
) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Discovered category indicators (per year x wiki); depth = BFS hops from root.
CREATE TABLE IF NOT EXISTS category_registry (
  wiki            VARCHAR(32)    NOT NULL,
  year            SMALLINT       NOT NULL,
  category_title  VARBINARY(255) NOT NULL,
  n_members       INT            NOT NULL DEFAULT 0,     -- within the admitted set
  depth_from_root INT            NOT NULL DEFAULT 0,
  is_indicator    TINYINT        NOT NULL DEFAULT 1,
  PRIMARY KEY (wiki, year, category_title)
) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Provenance of each build run (pinned inputs for reproducibility).
CREATE TABLE IF NOT EXISTS build_run (
  wiki        VARCHAR(32)  NOT NULL,
  year        SMALLINT     NOT NULL,
  built_at    VARBINARY(32) NOT NULL,            -- ISO timestamp (passed in)
  source      VARBINARY(64) NOT NULL,            -- 'replica:current' or 'dump:<run-id>'
  root_category VARBINARY(255) NOT NULL,
  max_depth   INT NOT NULL,
  n_nodes     INT NOT NULL,
  n_edges     INT NOT NULL,
  PRIMARY KEY (wiki, year, built_at)
) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
