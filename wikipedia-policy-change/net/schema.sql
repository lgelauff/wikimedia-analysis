-- schema.sql — ToolsDB tables for the policy network (clean base).
-- Database: s#####__policies (prefix = your replica.my.cnf user= line; never hardcode).
-- year-keyed so it extends to historical snapshots unchanged. Snapshot rule:
-- year = state at 1 Jan of that year. The current slice uses replica "now" + the API.
--
-- Model: ONE graph (link = in-body wikilinks from wikitext, NOT pagelinks) +
-- node-level FACETS (category membership, template transclusion w/ role, navbox
-- membership). Categories and templates are signals, never edges.

DROP TABLE IF EXISTS node;
DROP TABLE IF EXISTS link;
DROP TABLE IF EXISTS node_category;
DROP TABLE IF EXISTS node_template;
DROP TABLE IF EXISTS navbox_member;
DROP TABLE IF EXISTS category_registry;
DROP TABLE IF EXISTS template_registry;
DROP TABLE IF EXISTS build_run;
DROP TABLE IF EXISTS edge;   -- retire the lumped M1 table

-- One row per admitted node per year.
CREATE TABLE node (
  wiki          VARCHAR(32)    NOT NULL,
  page_id       INT UNSIGNED   NOT NULL,
  year          SMALLINT       NOT NULL,
  title         VARBINARY(255) NOT NULL,
  namespace     INT            NOT NULL,
  is_redirect   TINYINT        NOT NULL DEFAULT 0,
  wikidata_qid  VARBINARY(32)  DEFAULT NULL,
  confidence    VARCHAR(10)    NOT NULL,            -- 'confirmed' | 'suspect'
  admitted_via  VARCHAR(24)    NOT NULL,            -- status_template|core_category|wikidata|scored_category|scored_navbox
  status_tier   VARCHAR(16)    DEFAULT NULL,        -- policy|guideline|essay|lifecycle (from Type-A template)
  PRIMARY KEY (wiki, year, page_id),
  KEY k_ns   (wiki, year, namespace),
  KEY k_conf (wiki, year, confidence)
) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- THE graph: in-body wikilinks (parsed from wikitext). to_page = resolved canonical
-- page_id (NULL if target missing); to_admitted = target is itself an admitted node.
CREATE TABLE link (
  wiki        VARCHAR(32)    NOT NULL,
  year        SMALLINT       NOT NULL,
  from_page   INT UNSIGNED   NOT NULL,
  to_ns       INT            NOT NULL,
  to_title    VARBINARY(255) NOT NULL,
  to_page     INT UNSIGNED   DEFAULT NULL,
  to_admitted TINYINT        NOT NULL DEFAULT 0,
  KEY k_from (wiki, year, from_page),
  KEY k_to   (wiki, year, to_page),
  KEY k_adm  (wiki, year, to_admitted)
) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Facet: category membership (signal, not edge).
CREATE TABLE node_category (
  wiki           VARCHAR(32)    NOT NULL,
  year           SMALLINT       NOT NULL,
  page_id        INT UNSIGNED   NOT NULL,
  category_title VARBINARY(255) NOT NULL,
  KEY k_pg  (wiki, year, page_id),
  KEY k_cat (wiki, year, category_title)
) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Facet: template transclusion, role-tagged.
CREATE TABLE node_template (
  wiki           VARCHAR(32)    NOT NULL,
  year           SMALLINT       NOT NULL,
  page_id        INT UNSIGNED   NOT NULL,
  template_title VARBINARY(255) NOT NULL,
  role           VARCHAR(12)    NOT NULL,           -- status|navigation|noise
  KEY k_pg   (wiki, year, page_id),
  KEY k_tmpl (wiki, year, template_title)
) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Facet: which Type-B policy navbox enumerates a page (curated grouping).
CREATE TABLE navbox_member (
  wiki         VARCHAR(32)    NOT NULL,
  year         SMALLINT       NOT NULL,
  page_id      INT UNSIGNED   NOT NULL,
  navbox_title VARBINARY(255) NOT NULL,
  KEY k_pg  (wiki, year, page_id),
  KEY k_nav (wiki, year, navbox_title)
) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Discovered category indicators, with their score vs the confirmed set.
CREATE TABLE category_registry (
  wiki           VARCHAR(32)    NOT NULL,
  year           SMALLINT       NOT NULL,
  category_title VARBINARY(255) NOT NULL,
  support        INT            NOT NULL DEFAULT 0,  -- |members ∩ confirmed|
  n_members      INT            NOT NULL DEFAULT 0,
  density        FLOAT          NOT NULL DEFAULT 0,  -- support / n_members
  is_indicator   TINYINT        NOT NULL DEFAULT 0,
  PRIMARY KEY (wiki, year, category_title)
) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Discovered template indicators, role + score.
CREATE TABLE template_registry (
  wiki            VARCHAR(32)    NOT NULL,
  year            SMALLINT       NOT NULL,
  template_title  VARBINARY(255) NOT NULL,
  role            VARCHAR(12)    NOT NULL DEFAULT 'noise',
  support         INT            NOT NULL DEFAULT 0,  -- targets ∩ confirmed (navbox) or transclusions on confirmed (status)
  density         FLOAT          NOT NULL DEFAULT 0,
  is_indicator    TINYINT        NOT NULL DEFAULT 0,
  PRIMARY KEY (wiki, year, template_title)
) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE build_run (
  wiki        VARCHAR(32)   NOT NULL,
  year        SMALLINT      NOT NULL,
  built_at    VARBINARY(32) NOT NULL,
  source      VARBINARY(64) NOT NULL,
  n_confirmed INT NOT NULL,
  n_suspect   INT NOT NULL,
  n_links     INT NOT NULL,
  s_min       INT NOT NULL,
  d_min       FLOAT NOT NULL,
  PRIMARY KEY (wiki, year, built_at)
) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
