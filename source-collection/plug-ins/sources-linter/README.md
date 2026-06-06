# sources-linter

Validates `sources.txt` on every Write or Edit, before the file is saved.

## What it checks

| Check | Rule |
|---|---|
| Required fields | Every entry must have `citekey`, `url` (unless access is paywall/login/blocked), and `access` |
| Citekey convention | Must match `author+year+keyword` — lowercase letters and digits only (e.g. `smith2024sources`) |
| Duplicate citekeys | Flags any citekey that appears more than once |
| Valid access values | Must be one of: `open`, `paywall`, `login`, `blocked`, `unknown` |
| Open without URL | `access=open` entries must have a `url` |

## Behaviour

- **Errors found** → blocks the write and lists all issues. Fix them or override if intentional.
- **No errors** → write proceeds silently.
- **Non-sources.txt file** → hook exits immediately, no effect.

## Hook trigger

`PreToolUse` on `Write` and `Edit`.
