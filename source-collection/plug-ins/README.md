# Plugins

Custom plugins for [Claude Cowork](https://claude.ai/cowork), extending Claude's behavior for this research project.

## What is a plugin?

A plugin is a self-contained directory that adds skills, hooks, agents, and MCP server integrations to Claude Cowork. Plugins are packaged as `.plugin` files (zip archives) and installed via the Cowork interface.

**Official documentation:** [Claude Cowork plugin development guide](https://docs.anthropic.com/en/docs/claude-code/plugins)

## Plugins in this folder

| Plugin | File | Description |
|--------|------|-------------|
| [fetch-interceptor](fetch-interceptor/) | [fetch-interceptor.plugin](fetch-interceptor.plugin) | Intercepts `WebFetch` calls and checks `source-collection/cache/` first. Blocks the call on a cache hit; suggests `fetch.py` pipeline on a miss. |
| [sources-linter](sources-linter/) | _(not yet packaged)_ | Validates `sources.txt` on every Write/Edit: required fields, citekey convention, duplicate keys, valid access values. |
| [robots-checker](robots-checker/) | _(not yet packaged)_ | Intercepts `fetch.py --ignore-robots` runs and reports which domains disallow our User-Agent before proceeding. |

## Plugin structure

```
plugin-name/
├── .claude-plugin/
│   └── plugin.json       # Required manifest (name, version, description)
├── skills/               # On-demand knowledge and slash commands
│   └── skill-name/
│       └── SKILL.md
├── hooks/
│   └── hooks.json        # Automatic triggers (PreToolUse, PostToolUse, etc.)
├── scripts/              # Helper scripts called by hooks
├── agents/               # Autonomous subagent definitions
├── .mcp.json             # MCP server integrations
└── README.md
```

## Installing a plugin

1. Open Claude Cowork.
2. Go to **Settings → Plugins**.
3. Drag the `.plugin` file onto the window, or click **Install plugin** and select it.

## Creating a new plugin

Use the `/create-cowork-plugin` skill inside a Cowork session to be guided through discovery, component planning, implementation, and packaging.

After creating a plugin:
- Place the source directory here alongside the others.
- Add a row to the table above.
- Commit both the source folder and the `.plugin` file.
