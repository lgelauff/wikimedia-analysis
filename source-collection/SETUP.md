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

direnv automatically loads `.env` whenever you `cd` into the directory and unloads it when you leave. Claude Code inherits the shell environment, so variables loaded by direnv are visible to both hooks and scripts without any extra steps.

**Option C — uv --env-file (for manual runs only):**

```bash
uv run --env-file .env python fetch.py --dry-run
```

This only applies to the single `uv run` invocation and does not affect Claude Code or hooks.

> **Important:** Claude Code reads the environment from the shell that launched it. If you start Claude Code before loading `.env`, the variables will not be available to hooks or scripts. Always load `.env` first — Option B (direnv) is the most reliable way to ensure this.

---

## 3. Claude Code hooks

Hooks intercept Claude's tool calls to add gates and checks. This project defines hooks in `.claude/settings.json` (committed, shared across the team) and `.claude/settings.local.json` (local only, gitignored).

### How hooks work

Each hook fires on a tool event and runs a shell command. The command receives a JSON payload on stdin describing the tool call, and communicates back via exit code:

| Exit code | Meaning |
|---|---|
| `0` | Allow the tool call to proceed |
| `2` + stderr output | Block the tool call; stderr is shown to Claude as the reason |
| anything else | Allow the call, but log the error |

The stdin payload looks like:

```json
{
  "tool_name": "WebFetch",
  "tool_input": { "url": "https://example.com" }
}
```

For `PostToolUse`, the payload also includes `tool_response`.

### Active hooks in this project

Defined in `.claude/settings.json`:

| Hook | Event | Matcher | Script | What it does |
|---|---|---|---|---|
| fetch-interceptor | `PreToolUse` | `WebFetch` | `plug-ins/fetch-interceptor/scripts/intercept_fetch.py` | Checks `cache/` first; blocks WebFetch on a hit, suggests `fetch.py` on a miss |

### Hook script path — CLI vs Cowork

This is the most important difference between the two systems:

| Context | Path format | Example |
|---|---|---|
| **Claude Code CLI** (`.claude/settings.json`) | Absolute path | `python3 "/Users/you/repo/scripts/hook.py"` |
| **Cowork plug-in** (`hooks/hooks.json`) | `${CLAUDE_PLUGIN_ROOT}` variable | `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/hook.py"` |

`${CLAUDE_PLUGIN_ROOT}` is resolved by the Cowork installer to the plug-in's installed location. It is **not** available in Claude Code CLI settings — use an absolute path there instead.

> If you clone this repo to a different location, update the absolute path in `.claude/settings.json` to match.

### Global vs project hooks

| File | Scope | Committed? |
|---|---|---|
| `~/.claude/settings.json` | All projects on this machine | No (personal) |
| `.claude/settings.json` | This project only | Yes |
| `.claude/settings.local.json` | This project, this machine | No (gitignored) |

Project hooks are merged with global hooks — both run. A global hook that blocks a tool call does not prevent project hooks for the same event from also running.

### Adding a new hook (CLI)

1. Write the hook script (reads stdin JSON, exits 0 or 2).
2. Add an entry to `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"/absolute/path/to/your_hook.py\""
          }
        ]
      }
    ]
  }
}
```

3. Test by triggering the matched tool in Claude and checking the output.

---

## 4. Claude Cowork plug-ins

Plug-ins are the Cowork equivalent of Claude Code hooks. They are self-contained directories packaged as `.plugin` files (zip archives) and installed via the Cowork interface.

### Plug-in structure

```
my-plugin/
├── .claude-plugin/
│   └── plugin.json        # Required: name, version, description
├── hooks/
│   └── hooks.json         # Hook definitions (use ${CLAUDE_PLUGIN_ROOT} for paths)
├── scripts/               # Hook scripts
│   └── my_hook.py
└── README.md
```

### hooks.json format

```json
{
  "hooks": [
    {
      "event": "PreToolUse",
      "matcher": "WebFetch",
      "hooks": [
        {
          "type": "command",
          "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/scripts/my_hook.py\""
        }
      ]
    }
  ]
}
```

Always use `${CLAUDE_PLUGIN_ROOT}` for script paths in plug-ins. The Cowork installer resolves this to the plug-in's installed location at install time.

### Available plug-ins

| File | Event | Matcher | What it does |
|---|---|---|---|
| `plug-ins/fetch-interceptor.plugin` | `PreToolUse` | `WebFetch` | Checks cache before fetching; blocks on hit |
| `plug-ins/sources-linter.plugin` | `PreToolUse` | `Write`, `Edit` | Validates `sources.txt` on every save |
| `plug-ins/robots-checker.plugin` | `PreToolUse` | `Bash` | Blocks `fetch.py --ignore-robots` for violating domains |

### Installing a plug-in

1. Open Claude Cowork.
2. Go to **Settings → Plugins**.
3. Drag the `.plugin` file onto the window, or click **Install plugin**.

### Packaging a plug-in

After editing source files, repackage with zip from inside the plug-in directory:

```bash
cd plug-ins/sources-linter
zip -r ../sources-linter.plugin .claude-plugin hooks scripts README.md
```

The zip must contain files at the root (not inside a subdirectory), matching the structure above. Commit both the source directory and the `.plugin` file.

---

## 5. Running the fetch pipeline

```bash
# Dry run — show what would be fetched without fetching
uv run python fetch.py --dry-run

# Fetch all sources
uv run python fetch.py

# Fetch a single entry by citekey
uv run python fetch.py --citekey smith2024example

# Force re-fetch (ignore existing cache)
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
# Check all lib imports resolve
uv run python -c "from lib import github, citoid, openalex, wikimedia; print('ok')"

# Check GitHub auth (limit should be 5000, not 60)
uv run python -c "
import os, requests
r = requests.get('https://api.github.com/rate_limit',
    headers={'Authorization': f'Bearer {os.environ[\"GITHUB_TOKEN\"]}',
             'User-Agent': 'WikimediaAnalysis/1.0'})
print(r.json()['rate'])
"

# Confirm sources.txt parses correctly
uv run python fetch.py --dry-run

# Confirm the fetch-interceptor hook is active (Claude Code CLI)
# Trigger a WebFetch in Claude on any URL — the hook should log either
# a cache hit (blocked) or a cache miss (allowed with fetch.py suggestion).
```
