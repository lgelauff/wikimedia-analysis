# statement-rater

A small Wikimedia-OAuth web app that crowdsources **equivalence ratings** for statement
alignment. A rater sees one source statement and up to three candidates, and marks each
candidate **Full equivalent** / **Partial match**, or says **None of these match**.

Built to replace hand-labelling the `align_de_en_npov` review CSV
(`wikipedia-policy-change/data/exploration/runs/`), but the schema is generic — any batch of
"one source + N candidates" items can be loaded.

## Status

Local-dev complete and tested. **Not yet deployed**: deploying to Toolforge and registering
the OAuth consumer are manual steps (see *Deployment*).

## Run locally

```bash
cd statement-rater
uv sync
uv run python seed.py --set-id de-en-npov --name "de↔en NPOV alignment" --k 3 data/de-en-npov.csv
uv run flask --app app run --debug --host 127.0.0.1 --port 5001
```

Then open <http://127.0.0.1:5001/dev-login?username=YourName> — `/dev-login` exists only in
debug mode and fakes an OAuth identity so you can rate without a registered consumer.
(Port 5001, not 5000: macOS ControlCenter/AirPlay squats on 5000.)

The dev database is SQLite at `instance/dev.db` (gitignored). It is fully reproducible from
the seed command above, so deleting it costs nothing.

## Adding statements

Write a CSV and seed it — that's the whole flow:

| column | meaning |
| --- | --- |
| `ext_id` | optional external id (e.g. `dewiki:npov:5`); enables idempotent re-seeding |
| `source_text` | **required** — statement shown primary (English) |
| `source_sub` | optional — smaller line underneath (e.g. the German original) |
| `cand1_id`, `cand1_text`, `cand2_id`, `cand2_text`, … | candidate pairs, any number |

```bash
uv run python seed.py --set-id my-set --name "My set" --k 5 data/my-set.csv
```

`--k` sets how many independent judgments each item needs before it retires (**default 3**,
configurable **per set**). `--inactive` seeds a set without serving it yet. Re-running is
idempotent when `ext_id` is present.

`data/de-en-npov.csv` was generated from the alignment run — see the generator snippet in the
commit that added it.

## How items are served

A logged-in rater is shown a **random** item that is (a) in an active set, (b) not retired,
and (c) not already judged by them. On submit, the item's judgment count increments and it
retires once it reaches the set's `k_target`. When nothing is left, the rater sees a
thank-you page.

## Data model

- `rating_sets` — `id` (slug), `name`, `k_target`, `is_active`
- `items` — `set_id`, `ext_id`, `source_text`, `source_sub`, `candidates` (JSON), `n_judgments`, `retired`
- `judgments` — `item_id`, `centralauth_id`, `wiki_username`, `verdict` (JSON), unique per (item, user)

Verdict JSON: `{"none": false, "ratings": {"<candidate_id>": "full" | "partial"}}`

## Admin

`/stats` and `/export/<set_id>.csv` are restricted to the usernames in `SUPERADMIN_USERS`
(top of `app.py`). Export gives one row per judgment for analysis.

## Deployment (Toolforge) — manual steps

Not done yet. Adapted from `chatstream-moderate`, so the same pattern applies:

1. Register an OAuth 2.0 consumer on Meta (`Special:OAuthConsumerRegistration`), scope `basic`,
   callback `https://<tool>.toolforge.org/oauth-callback`.
2. Put secrets in `/etc/passwords/` on the tool account: `oauth-client-id`,
   `oauth-client-secret`, `oauth-redirect-uri`, `secret-key`, and `db-host`/`db-user`/
   `db-password`/`db-name`. `_read_secret()` falls back to env vars locally.
   With the `db-*` secrets present the app switches from SQLite to Toolforge MariaDB
   (`pip install '.[prod]'` for `pymysql`).
3. Add a WSGI entrypoint + `uwsgi.ini` (copy from `chatstream-moderate`) and deploy.

Sessions are Flask's default signed cookies (only an id + username + CSRF token). Switch to
server-side sessions if that ever needs to hold more.
