#!/usr/bin/env python3
"""Back-compat shim.

The fetch pipeline now lives in the importable `source_collection` package.
Prefer invoking it as a module (portable, no absolute path):

    python -m source_collection.fetch --sources … --out …

This shim keeps `python fetch.py …` working for existing callers/allowlists.
"""
from source_collection.fetch import main

if __name__ == "__main__":
    main()
