# net/ — policy network build (M1)

Current/2026 structural slice of the policy network from the Toolforge replica.
No dumps, no LLM. See [`../docs/policy_network_design.md`](../docs/policy_network_design.md) and [`../docs/ROADMAP.md`](../docs/ROADMAP.md).

- `schema.sql` — ToolsDB tables (node, edge, category_registry, template_registry, build_run).
- `net_build_current.py` — BFS the policy/guideline category tree → admit (category OR status-template) → edges (category/template/wikilink, redirect-resolved) → QIDs → write ToolsDB + local SQLite.

## Run on Toolforge

**Key rule:** create the venv AND run the script with the *same* image (`python3.11`).
A venv built in a job won't work from the bastion (different interpreter path).
Run via `toolforge jobs run`; write SQLite to `~` (a pod's `/tmp` is ephemeral).

```bash
become wikimedia-policies

# one-time: clone + venv
cd $HOME && git clone https://github.com/lgelauff/wikimedia-analysis.git
# NB: plain `python3 -m venv` runs ensurepip, which spawns a subprocess the pod
# blocks (hangs, no logs). Use --without-pip + curl-bootstrap (no subprocess):
toolforge jobs run venv --image python3.13 --wait --command \
  "python3 -m venv ~/venv --without-pip && curl -sS https://bootstrap.pypa.io/get-pip.py | ~/venv/bin/python3 && ~/venv/bin/python3 -m pip install pymysql"
toolforge jobs logs venv
ls ~/venv/bin/        # expect python3, pip

# one-time: load schema into ToolsDB
mariadb --defaults-file=~/replica.my.cnf -h tools.db.svc.wikimedia.cloud \
  $(grep '^user' ~/replica.my.cnf | cut -d= -f2 | tr -d ' ')__policies \
  < $HOME/wikimedia-analysis/wikipedia-policy-change/net/schema.sql

# update later
git -C $HOME/wikimedia-analysis pull

# smoke test (shallow, SQLite only) — read summary from logs
toolforge jobs run net-smoke --image python3.13 --mem 1Gi --wait \
  --command "~/venv/bin/python -u ~/wikimedia-analysis/wikipedia-policy-change/net/net_build_current.py --wiki enwiki --year 2026 --max-depth 2 --no-toolsdb --sqlite ~/net_smoke.db"
toolforge jobs logs net-smoke

# full build (writes ToolsDB)
toolforge jobs run net-build --image python3.13 --mem 2Gi --wait \
  --command "~/venv/bin/python -u ~/wikimedia-analysis/wikipedia-policy-change/net/net_build_current.py --wiki enwiki --year 2026 --max-depth 4"
toolforge jobs logs net-build
```

## M1 gate (sanity-check the summary)
- node count plausible (hundreds–low thousands, not tens of thousands → category drift)
- namespace spread dominated by ns 4 (+ some 10/12/14/100), **no ns 0**
- policy→policy edge count non-trivial
- BFS depth fan-out reasonable (watch the per-depth `+N categories` log; if depth 4 explodes, lower `--max-depth`)

Tune `--max-depth` from the smoke test before the full run. Idempotent: re-running replaces that (wiki, year) slice.
