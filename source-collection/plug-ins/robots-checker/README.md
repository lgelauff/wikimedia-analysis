# robots-checker

Intercepts any `fetch.py --ignore-robots` Bash call and reports which domains
in `sources.txt` disallow our User-Agent before the run proceeds.

## What it does

1. Detects Bash commands containing `fetch.py` and `--ignore-robots`.
2. Finds `sources.txt` (via explicit `--sources` arg or by walking up from cwd).
3. For each fetchable URL (skipping paywall/login/blocked entries), checks
   the domain's `robots.txt` against our User-Agent.
4. Deduplicates by domain to avoid redundant network calls.
5. **Violations found** → blocks the run and lists offending domains with their robots.txt URLs.
6. **No violations** → run proceeds with a brief confirmation message.

## User-Agent checked

```
WikimediaAnalysis/1.0 (personal research project; https://github.com/lgelauff/wikimedia-analysis)
```

## Behaviour on network errors

If a domain's robots.txt cannot be fetched (timeout, DNS error, etc.), that
domain is treated as **allowed** — the checker errs on the side of not blocking.

## Hook trigger

`PreToolUse` on `Bash`.
