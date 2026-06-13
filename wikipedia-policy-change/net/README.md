# net/ — policy network build (clean base)

Current policy network for one wiki. Admission + facets from the Toolforge replica;
the **link graph from wikitext** (API + mwparserfromhell), not pagelinks. No LLM.
See [`../docs/CLEAN_BASE_PROPOSAL.md`](../docs/CLEAN_BASE_PROPOSAL.md) and [`../docs/ROADMAP.md`](../docs/ROADMAP.md).

- `schema.sql` — ToolsDB tables: `node` (+confidence/admitted_via/status_tier), `link`
  (wikilink graph), facets `node_category` / `node_template`(role) / `navbox_member`,
  `category_registry` / `template_registry` (scored), `build_run`.
- `net_build_current.py` — confirmed seed (status-template ∪ core-category ∪ Wikidata
  P31=Q4656150) → **scored** category + navbox discovery (support/density vs confirmed)
  → suspects → wikitext link graph → role-tagged facets → ToolsDB + SQLite.

## Run on Toolforge

**Same image for venv and run** (`python3.13`). venv needs **pymysql + mwparserfromhell**.
Outbound API calls (wikitext, siteinfo, Wikidata) run from the job pod.

```bash
become wikimedia-policies

# one-time: clone + venv (--without-pip + curl-bootstrap; ensurepip hangs in the pod)
cd $HOME && git clone https://github.com/lgelauff/wikimedia-analysis.git
toolforge jobs run venv --image python3.13 --wait --command \
  "python3 -m venv ~/venv --without-pip && curl -sS https://bootstrap.pypa.io/get-pip.py | ~/venv/bin/python3 && ~/venv/bin/python3 -m pip install pymysql mwparserfromhell"
ls ~/venv/bin/        # expect python3, pip

# one-time: (re)load schema into ToolsDB  (DROPs + recreates the clean tables)
mariadb --defaults-file=~/replica.my.cnf -h tools.db.svc.wikimedia.cloud \
  $(grep '^user' ~/replica.my.cnf | cut -d= -f2 | tr -d ' ')__policies \
  < $HOME/wikimedia-analysis/wikipedia-policy-change/net/schema.sql

# update later
git -C $HOME/wikimedia-analysis pull

# smoke (SQLite only, skip Wikidata for speed) — read summary from ~/net-smoke.out
toolforge jobs run net-smoke --image python3.13 --mem 2Gi --wait \
  --command "~/venv/bin/python -u ~/wikimedia-analysis/wikipedia-policy-change/net/net_build_current.py --wiki enwiki --year 2026 --no-toolsdb --no-wikidata --sqlite ~/net_smoke.db"
cat ~/net-smoke.out

# full build (ToolsDB + Wikidata) per wiki
toolforge jobs run net-en --image python3.13 --mem 2Gi --wait \
  --command "~/venv/bin/python -u ~/wikimedia-analysis/wikipedia-policy-change/net/net_build_current.py --wiki enwiki --year 2026"
cat ~/net-en.out
# then: --wiki dewiki , --wiki nlwiki  (jobs net-de / net-nl)
```

## Gate (read the summary)
- `confirmed` count plausible; `suspect` a sensible fraction (not 10× confirmed → loosen/tighten `--s-min`/`--d-min`)
- namespace spread ns-4-dominated, **no ns 0**
- `policy->policy` link count non-trivial (these are in-body wikilinks, no navbox cliques)
- template roles: a handful `status` / `navigation`, the bulk `noise`
- inspect `category_registry` / `template_registry` ordered by `support` to set the score cut by eye

Tuning: `--s-min` (min confirmed overlap), `--d-min` (min policy-density). Idempotent: re-running replaces that (wiki, year) slice. `--no-wikidata` skips the Wikidata API calls.
