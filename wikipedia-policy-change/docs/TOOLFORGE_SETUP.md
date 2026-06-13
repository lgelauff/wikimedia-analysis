# Toolforge setup — wikimedia-policies tool

New dedicated tool for the wikimedia-policies build (M1+). I prepare repo scaffolding + this checklist; **you run the bastion steps** (SSH to the bastion is out of scope for the agent) and paste results back. Pattern follows the wiki-polis lessons.

Prereq: you already have a Toolforge account. These steps create a *new tool* under it.

---

## 1. Create the tool

On the bastion (`ssh <you>@login.toolforge.org`):

```
# Request/create a new tool named "wikimedia-policies"
# via https://toolsadmin.wikimedia.org/tools/  (Create new tool)
# then become it:
become wikimedia-policies
```

The tool gets its own home `/data/project/wikimedia-policies/`, its own `replica.my.cnf` (replica + ToolsDB creds), and its own quota.

## 2. Verify replica access

```
become wikimedia-policies
mariadb --defaults-file=$HOME/replica.my.cnf -h enwiki.analytics.db.svc.wikimedia.cloud enwiki_p \
  -e "SELECT page_id,page_namespace,page_title FROM page WHERE page_namespace=4 LIMIT 3;"
```
- Hostname pattern: `<wiki>.analytics.db.svc.wikimedia.cloud`, db `<wiki>_p` (e.g. `enwiki_p`, `dewiki_p`, `nlwiki_p`). The old `.labsdb` aliases may be dropped — use `.analytics.db.svc.wikimedia.cloud`.
- **Schema note (verified March migration):** category/link joins go through `linktarget` — `categorylinks.cl_target_id → linktarget.lt_namespace/lt_title` (no more `cl_to`); same for `pagelinks.pl_target_id`, `templatelinks.tl_target_id`.

## 3. Create the ToolsDB database (canonical serving store)

```
mariadb --defaults-file=$HOME/replica.my.cnf -h tools.db.svc.wikimedia.cloud
```
```sql
CREATE DATABASE s#####__policies CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```
- Replace `s#####` with the credential username prefix from `replica.my.cnf` (the `user=` line) — it's a **numeric** account (e.g. `s51234`), **not** the tool name `wikimedia-policies`. The `s#####__` prefix must match exactly or you get "Access denied".
- The suffix (`policies`) is a free label but **avoid hyphens** — MySQL identifiers with `-` must be backtick-quoted everywhere. Use `policies` / `wikimedia_policies`, not `wikimedia-policies`. (Tool name and DB name are allowed to differ.)

## 4. Clone the repo (GH handoff)

```
cd $HOME
git clone https://github.com/lgelauff/wikimedia-analysis.git
# build scripts live in wikimedia-analysis/wikipedia-policy-change/
```
Update pattern later: `git -C $HOME/wikimedia-analysis pull`.

## 5. Confirm dumps mount

```
ls /public/dumps/public/enwiki/ | tail -5          # recent dump dates (only ~last 6-7 retained)
ls /public/dumps/public/enwiki/latest/ | grep stub  # stub-meta-history files
```
- Note the latest dump date + that `stub-meta-history` exists; we pin one run-id for reproducibility.

## 6. Batch jobs (not webservice — the build is not a web app)

```
toolforge jobs images           # list available images (use a python3.x image)
# example once a script exists:
toolforge jobs run net-build --image python3.11 --mem 2Gi \
  --command "cd $HOME/wikimedia-analysis/wikipedia-policy-change && python3 net_build_current.py"
toolforge jobs logs net-build
```
- Python deps: create a venv in the tool home and `pip install` there (uv is not documented for Toolforge; follow the wiki-polis venv lessons). Jobs are killable → scripts must be resumable (atomic partials).

## 7. (Later, M3) Web app
Reuse the wiki-polis Flask/Toolforge deploy pattern (`~/www/python` real dir, venv-in-webservice-shell, `webservice restart` from `~`). Separate milestone.

---

## What I provide vs what you run
- **I provide:** the scripts (`net_build_current.py`, `schema.sql`, etc.), resumable/atomic, env-detecting (replica on Toolforge, skip locally), pinning dump run-id + siteinfo + hashes.
- **You run:** steps 1–6 on the bastion; paste back the replica smoke-test output, the ToolsDB user prefix (`s#####`), the latest dump date, and `toolforge jobs images`. Those four unblock M1 on Toolforge.

## Open values to capture (paste back)
- [ ] Tool name (`wikimedia-policies`)
- [ ] ToolsDB user prefix `s#####`
- [ ] Replica smoke-test: does the `linktarget` join return rows?
- [ ] Latest `/public/dumps` enwiki dump date + stub-meta-history present?
- [ ] `toolforge jobs images` available python image tag
