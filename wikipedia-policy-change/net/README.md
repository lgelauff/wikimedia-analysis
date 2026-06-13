# net/ — policy network build (M1)

Current/2026 structural slice of the policy network from the Toolforge replica.
No dumps, no LLM. See [`../docs/policy_network_design.md`](../docs/policy_network_design.md) and [`../docs/ROADMAP.md`](../docs/ROADMAP.md).

- `schema.sql` — ToolsDB tables (node, edge, category_registry, template_registry, build_run).
- `net_build_current.py` — BFS the policy/guideline category tree → admit (category OR status-template) → edges (category/template/wikilink, redirect-resolved) → QIDs → write ToolsDB + local SQLite.

## Run on Toolforge

```bash
become wikimedia-policies
git -C $HOME/wikimedia-analysis pull          # get latest

# one-time: venv + load schema into ToolsDB
toolforge jobs run venv --image python3.11 --wait \
  --command "python3 -m venv ~/venv && ~/venv/bin/pip install pymysql"
mariadb --defaults-file=~/replica.my.cnf -h tools.db.svc.wikimedia.cloud \
  $(grep '^user' ~/replica.my.cnf | cut -d= -f2 | tr -d ' ')__policies \
  < $HOME/wikimedia-analysis/wikipedia-policy-change/net/schema.sql

# quick smoke test first (shallow, SQLite only, no ToolsDB write)
~/venv/bin/python $HOME/wikimedia-analysis/wikipedia-policy-change/net/net_build_current.py \
  --wiki enwiki --year 2026 --max-depth 2 --no-toolsdb --sqlite /tmp/net.db

# full build as a job
toolforge jobs run net-build --image python3.11 --mem 2Gi --wait \
  --command "~/venv/bin/python $HOME/wikimedia-analysis/wikipedia-policy-change/net/net_build_current.py --wiki enwiki --year 2026 --max-depth 4"
toolforge jobs logs net-build
```

## M1 gate (sanity-check the summary)
- node count plausible (hundreds–low thousands, not tens of thousands → category drift)
- namespace spread dominated by ns 4 (+ some 10/12/14/100), **no ns 0**
- policy→policy edge count non-trivial
- BFS depth fan-out reasonable (watch the per-depth `+N categories` log; if depth 4 explodes, lower `--max-depth`)

Tune `--max-depth` from the smoke test before the full run. Idempotent: re-running replaces that (wiki, year) slice.
