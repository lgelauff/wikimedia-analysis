# Setup guide — source-collection

How to get the fetch pipeline, Claude Code hooks, and Cowork plug-ins working from scratch.

---

## 1. Dependencies

Requires Python ≥ 3.11 and [uv](https://docs.astral.sh/uv/).

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync

# With optional PDF extraction support
uv sync --extra pdf
```

---

## 2. Environment variables

Copy the example file and fill in your credentials:

```bash
cp .env.example .env
# edit .env — never commit it, it is gitignored
```

See `.env.example` for the full annotated list. The highest-impact variables to set first:

| Variable | What it unlocks |
|---|---|
| `GITHUB_TOKEN` | GitHub REST API: 60 → 5,000 req/hour |
| `IA_ACCESS_KEY` + `IA_SECRET_KEY` | Enables the `spn2` pipeline stage (Internet Archive SavePageNow) |
| `CROSSREF_MAILTO` | Crossref polite pool: 5s → 1s rate limit |
| `WIKIMEDIA_OAUTH_ACCESS_TOKEN` | api.wikimedia.org: 500 → 5,000 req/hour |

### How to load the environment

Claude Code and hook scripts inherit the shell environment from the terminal that launched Claude. **You must load `.env` before starting Claude**, or the credentials will not be visible to hooks and scripts.

**Option A — load manually in shell (run once per session):**

```bash
set -a && source /path/to/source-collection/.env && set +a
```

**Option B — direnv (recommended: loads automatically on `cd`):**

```bash
# Install direnv
brew install direnv

# Add to your shell profile (~/.zshrc or ~/.bashrc)
echo 'eval "$(direnv hook zsh)"' >> ~/.zshrc && source ~/.zshrc

# In the source-collection directory, create an .envrc
echo 'dotenv' > source-collection/.envrc
direnv allow source-collection/
```

direnv loads `.env` automatically whenever you enter the directory and unloads it when you leave. Claude Code inherits these variables if you launch it from the same shell.

**Option C — uv --env-file (single run only, does not affect Claude):**

```bash
uv run --env-file .env python fetch.py --dry-run
```

---

## 3. Claude Code hooks

Hooks intercept Claude's tool calls to run checks before or after an action. This project uses `PreToolUse` hooks to gate fetching behaviour.

### How hooks work

Each hook fires on a matching tool event and runs a command with the tool call JSON piped to stdin. The command signals its decision via exit code:

| Exit code | Meaning |
|---|---|
| `0` | Allow the tool call to proceed |
| `2` + stderr message | Block the tool call; show the stderr message to Claude |
| Any other non-zero | Allow the call; log the error |

### Hook configuration files

| File | Scope | Committed? | Purpose |
|---|---|---|---|
| `~/.claude/settings.json` | All projects on this machine | No (personal) | Global hooks (e.g. OpenRouter, GitHub write guard) |
| `.claude/settings.json` | This project only | **Yes** | Shared project hooks |
| `.claude/settings.local.json` | This project, this machine | No (gitignored) | Local permissions and overrides |

Project hooks merge with global hooks — both run. If any hook exits `2`, the tool call is blocked regardless of what other hooks return.

### Active project hooks (`.claude/settings.json`)

| Hook | Trigger | Script | What it does |
|---|---|---|---|
| `fetch-interceptor` | PreToolUse `WebFetch` | `plug-ins/fetch-interceptor/scripts/intercept_fetch.py` | Checks `cache/` before any WebFetch; blocks on a cache hit, suggests `fetch.py` on a miss |

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "WebFetch",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"/absolute/path/to/plug-ins/fetch-interceptor/scripts/intercept_fetch.py\""
          }
        ]
      }
    ]
  }
}
```

> **Path note:** `.claude/settings.json` uses absolute paths. If you clone the repo to a different location, update the path to match. Cowork plug-ins use `${CLAUDE_PLUGIN_ROOT}` instead — see section 4.

### Known gap: curl

Claude occasionally fetches URLs via `curl` in Bash rather than WebFetch, which bypasses the hook above. A `Bash` PreToolUse hook that parses `curl` invocations and checks the cache is planned — see `notes.txt`.

### Adding a new hook

1. Write the script in `plug-ins/<name>/scripts/`.
2. Add an entry in `.claude/settings.json`:

```json
{
  "matcher": "Bash",
  "hooks": [
    {
      "type": "command",
      "command": "python3 \"/absolute/path/to/scripts/my_hook.py\""
    }
  ]
}
```

3. Test by triggering the relevant tool in a Claude session.

---

## 4. Cowork plug-ins

Plug-ins are the Cowork equivalent of hooks — they fire on the same events but are installed differently and use a different path variable.

### Path variable: `${CLAUDE_PLUGIN_ROOT}`

Inside a Cowork plug-in's `hooks.json`, always reference scripts with `${CLAUDE_PLUGIN_ROOT}`:

```json
"command": "python3 \"${CLAUDE_PLUGIN_ROOT}/scripts/my_script.py\""
```

This variable resolves to the installed plug-in directory at runtime. It is **not** available in Claude Code CLI settings — use absolute paths there instead.

### Available plug-ins

| File | Trigger | What it does |
|---|---|---|
| `plug-ins/fetch-interceptor.plugin` | PreToolUse `WebFetch` | Cache check before any WebFetch |
| `plug-ins/sources-linter.plugin` | PreToolUse `Write` / `Edit` | Validates `sources.txt` entries before saving |
| `plug-ins/robots-checker.plugin` | PreToolUse `Bash` | Blocks `fetch.py --ignore-robots` if domains disallow our User-Agent |

### Installing a plug-in

1. Open Claude Cowork.
2. Go to **Settings → Plugins**.
3. Drag the `.plugin` file onto the window, or click **Install plugin** and select it.

### Packaging a plug-in after edits

```bash
cd plug-ins/sources-linter
zip -r ../sources-linter.plugin .claude-plugin hooks scripts README.md
```

Repeat for each edited plug-in. Commit both the source directory and the `.plugin` file.

---

## 5. Running the fetch pipeline

```bash
# Dry run — show what would be fetched without fetching anything
uv run python fetch.py --dry-run

# Fetch all sources not yet in cache
uv run python fetch.py

# Fetch a single entry by citekey
uv run python fetch.py --citekey smith2024example

# Re-fetch even if already cached
uv run python fetch.py --force

# Use a specific pipeline order (skip SPN2)
uv run python fetch.py --pipeline wikimedia,arxiv,wayback

# Override rate limit for a specific domain
uv run python fetch.py --rate-override arxiv.org=30
```

Fetch failures are automatically logged to `research-vault/inbox/pending.txt`.

---

## 6. Verify the setup

```bash
# Check all lib imports resolve correctly
uv run python -c "from lib import github, wikimedia, wayback, sources; print('ok')"

# Confirm GitHub auth is working (should show limit: 5000, not 60)
uv run python -c "
import os, requests
r = requests.get('https://api.github.com/rate_limit',
    headers={'Authorization': 'Bearer ' + os.environ.get('GITHUB_TOKEN',''),
             'User-Agent': 'test'})
print(r.json()['rate'])
"

# Dry run to confirm sources.txt parses and pipeline is wired
uv run python fetch.py --dry-run
```
