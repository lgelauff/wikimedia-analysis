# Setup guide — source-collection

How to get the fetch pipeline, Claude Code hooks, and plug-ins working from scratch.

---

## 1. Dependencies

Requires Python ≥ 3.11 and [uv](https://docs.astral.sh/uv/).

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync
```

For PDF extraction (optional):

```bash
uv sync --extra pdf
```

---

## 2. Environment variables

Copy the example file and fill in your credentials:

```bash
cp .env.example .env
# edit .env — never commit it, it is gitignored
```

See `.env.example` for the full list with explanations. The most impactful ones to set first:

| Variable | Why | Impact |
|---|---|---|
| `GITHUB_TOKEN` | GitHub REST API auth | 60 → 5,000 req/hour |
| `IA_ACCESS_KEY` + `IA_SECRET_KEY` | Internet Archive SPN2 | Enables the `spn2` pipeline stage |
| `CROSSREF_MAILTO` | Crossref polite pool | 5s → 1s rate limit |
| `WIKIMEDIA_OAUTH_ACCESS_TOKEN` | api.wikimedia.org auth | 500 → 5,000 req/hour |

### Loading the environment

**Option A — load in shell before running Claude or fetch.py:**

```bash
set -a && source /path/to/source-collection/.env && set +a
```

Add this to your shell profile (`.zshrc` / `.bashrc`) or run it at the start of each session.

**Option B — direnv (recommended for automatic loading):**

```bash
brew install direnv   # or: curl -sfL https://direnv.net/install.sh | bash
echo 'eval "$(direnv hook zsh)"' >> ~/.zshrc   # or bash
source ~/.zshrc

# In source-collection/:
echo 'dotenv' > .envrc
direnv allow
```

direnv will automatically load `.env` whenever you `cd` into the directory and unload it when you leave. Claude Code inherits the shell environment, so variables loaded by direnv are visible to hooks and scripts.

**Option C — uv --env-file (for manual runs only):**

```bash
uv run --env-file .env python fetch.py --dry-run
```

This only applies to the single `uv run` invocation; it does not affect Claude Code or hooks.

> **Important:** Claude Code reads the environment from the shell that launched it. If you start Claude Code before loading `.env`, the variables will not be available to hooks or scripts. Always load `.env` first (Option A or B).

---

## 3. Claude Code hooks

Hooks intercept Claude's tool calls to add gates and checks. This project defines hooks in `.claude/settings.json` (committed, shared) and `.claude/settings.local.json` (local only, gitignored).

### How hooks work

Each hook fires on a tool event (`PreToolUse`, `PostToolUse`) and runs a shell command. The command reads a JSON payload from stdin describing the tool call. It can:

- **Exit 0** — allow the tool call to proceed normally
- **Exit 2 + write to stderr** — block the tool call and show the message to Claude
- **Exit other** — allow the call but log the error

### Active hooks in this project

| Hook | Trigger | Script | What it does |
|---|---|---|---|
| `fetch-interceptor` | PreToolUse on `WebFetch` | `plug-ins/fetch-interceptor/scripts/intercept_fetch.py` | Checks `cache/` before WebFetch; blocks on hit, suggests `fetch.py` on miss |

Defined in `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "WebFetch",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"/absolute/path/to/intercept_fetch.py\""
          }
        ]
      }
    ]
  }
}
```

> The path in `settings.json` is absolute. If you clone this repo to a different location, update the path in `.claude/settings.json` to match.

### Adding a new hook

1. Write the script in `plug-ins/<name>/scripts/`.
2. Add an entry to `.claude/settings.json` under the appropriate event.
3. Test with `--dry-run` or by triggering the tool manually in Claude.

### Global vs project hooks

| File | Scope | Committed? |
|---|---|---|
| `~/.claude/settings.json` | All projects on this machine | No (personal) |
| `.claude/settings.json` | This project only | Yes |
| `.claude/settings.local.json` | This project, this machine | No (gitignored) |

Project hooks are merged with global hooks — both run. If a global hook blocks a tool call, project hooks for the same event still run.

---

## 4. Claude Cowork plug-ins

Plug-ins are the Cowork equivalent of hooks. They are packaged as `.plugin` files (zip archives) and installed via **Settings → Plugins** in the Cowork interface.

### Available plug-ins

| File | Trigger | What it does |
|---|---|---|
| `plug-ins/fetch-interceptor.plugin` | PreToolUse on `WebFetch` | Same as the CLI hook above |
| `plug-ins/sources-linter.plugin` | PreToolUse on `Write`/`Edit` | Validates `sources.txt` entries before saving |
| `plug-ins/robots-checker.plugin` | PreToolUse on `Bash` | Blocks `fetch.py --ignore-robots` if any domain disallows our User-Agent |

### Installing

1. Open Claude Cowork.
2. Go to **Settings → Plugins**.
3. Drag the `.plugin` file onto the window, or click **Install plugin**.

### Packaging (after editing a plug-in)

```bash
cd plug-ins/sources-linter
zip -r ../sources-linter.plugin .claude-plugin hooks scripts README.md
```

### Script paths in hooks.json

In Cowork plug-ins, use `${CLAUDE_PLUGIN_ROOT}` to reference scripts inside the plug-in:

```json
"command": "python3 \"${CLAUDE_PLUGIN_ROOT}/scripts/my_script.py\""
```

In Claude Code `.claude/settings.json`, use an absolute path instead — `${CLAUDE_PLUGIN_ROOT}` is not available outside Cowork:

```json
"command": "python3 \"/absolute/path/to/scripts/my_script.py\""
```

---

## 5. Running the fetch pipeline

```bash
# Dry run — show what would be fetched without fetching
uv run python fetch.py --dry-run

# Fetch all sources
uv run python fetch.py

# Fetch a single entry
uv run python fetch.py --citekey smith2024example

# Force re-fetch (ignore cache)
uv run python fetch.py --force

# Skip Citoid/OpenAlex pre-flight enrichment
uv run python fetch.py --no-enrich

# Use a specific pipeline (e.g. skip SPN2)
uv run python fetch.py --pipeline wikimedia,arxiv,wayback

# Override rate limit for a domain
uv run python fetch.py --rate-override arxiv.org=30
```

Fetch failures are automatically logged to `research-vault/inbox/pending.txt` for manual retrieval.

---

## 6. Verifying the setup

```bash
# Check all imports resolve
uv run python -c "from lib import github, citoid, openalex, wikimedia; print('ok')"

# Check GitHub auth (should show your rate limit, not 60/hour)
uv run python -c "
import os, requests
r = requests.get('https://api.github.com/rate_limit',
    headers={'Authorization': f'Bearer {os.environ[\"GITHUB_TOKEN\"]}',
             'User-Agent': 'test'})
print(r.json()['rate'])
"

# Dry run to confirm sources.txt parses correctly
uv run python fetch.py --dry-run
```
