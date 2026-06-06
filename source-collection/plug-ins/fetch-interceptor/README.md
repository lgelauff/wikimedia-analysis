# fetch-interceptor

Intercepts every `WebFetch` call and routes it through the `source-collection` fetch pipeline before allowing it to proceed.

## What it does

When Claude is about to call `WebFetch` for a URL, this plugin:

1. **Checks the cache** — scans `source-collection/cache/*.md` for a file whose `Source:` header matches the URL.  
   - **Hit**: blocks `WebFetch` and tells Claude to use `Read` on the cached file instead.  
   - **Miss**: logs a suggestion to run `fetch.py` first, then lets `WebFetch` proceed normally.

## Why

The `fetch.py` pipeline applies rate limiting, `robots.txt` compliance, Wayback Machine fallbacks, and SPN2 archiving. Raw `WebFetch` bypasses all of that. This hook ensures cached research sources are always served from the authoritative local copy, and reminds Claude to use the pipeline for uncached URLs.

## How the cache lookup works

Cache files are `source-collection/cache/<citekey>.md`. Each starts with a header block:

```
# Title
Source: https://example.com/paper
Fetched: 2025-01-01  Snapshot: 2024-12-15  Method: wayback
```

The hook matches on the `Source:` line (exact URL, trailing slash stripped).

## Installation note

After installing the plugin, update the `command` path in `hooks/hooks.json` to match the plugin's installed location on your system.
