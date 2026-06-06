"""
parse_elicit.py — Parse Elicit .bib exports and merge into candidates_s1_c1.json.
Deduplicates against research-vault and existing candidates_new_c1.json.
"""

from __future__ import annotations
import json
import re
import sys
from pathlib import Path

_HERE  = Path(__file__).parent
_VAULT = Path.home() / "Documents" / "GitHub" / "research-vault"

# Map bib filenames to query labels
BIB_FILES = {
    "Elicit - Sources(9).bib":  "S1-Q1: traffic/CTR longitudinal",
    "Elicit - Sources(10).bib": "S1-Q2: contributor pipelines",
    "Elicit - Sources(11).bib": "S1-Q3: information literacy counter-evidence",
}


def parse_bib(text: str) -> list[dict]:
    entries = []
    for block in re.split(r"\n(?=@)", text.strip()):
        if not block.strip():
            continue
        title_m   = re.search(r'\btitle\s*=\s*\{(.+?)\}', block, re.DOTALL)
        author_m  = re.search(r'\bauthor\s*=\s*\{(.+?)\}', block, re.DOTALL)
        year_m    = re.search(r'\byear\s*=\s*\{(\d{4})\}', block)
        doi_m     = re.search(r'\bdoi\s*=\s*\{(.+?)\}', block)
        url_m     = re.search(r'\burl\s*=\s*\{(.+?)\}', block)
        title  = title_m.group(1).strip().replace('\n', ' ') if title_m else ""
        author = author_m.group(1).strip() if author_m else ""
        year   = int(year_m.group(1)) if year_m else None
        doi    = doi_m.group(1).strip() if doi_m else None
        url    = url_m.group(1).strip() if url_m else None
        # clean doi
        if doi and doi.startswith("10."):
            pass  # already clean
        elif doi:
            doi = re.sub(r'^https?://(dx\.)?doi\.org/', '', doi)
        if title:
            entries.append({
                "title":   title,
                "authors": [a.strip() for a in re.split(r'\band\b', author)][:5],
                "year":    year,
                "doi":     doi or None,
                "url":     url or None,
                "abstract": "",
            })
    return entries


def load_vault_keys() -> set[str]:
    index_path = _VAULT / "index.json"
    if not index_path.exists():
        return set()
    records = json.loads(index_path.read_text())
    keys: set[str] = set()
    for r in records:
        if r.get("DOI"):
            keys.add(r["DOI"].lower())
            keys.add(re.sub(r'^https?://(dx\.)?doi\.org/', '', r["DOI"]).lower())
        if r.get("URL"):
            keys.add(r["URL"].rstrip("/"))
        keys.add(r["id"])
    return keys


def main() -> None:
    vault_keys = load_vault_keys()
    all_new: list[dict] = []
    all_existing: list[dict] = []
    seen_dois: set[str] = set()

    for bib_file, query_label in BIB_FILES.items():
        path = _HERE / bib_file
        if not path.exists():
            print(f"  MISSING: {bib_file}", file=sys.stderr)
            continue
        entries = parse_bib(path.read_text(encoding="utf-8"))
        print(f"\n{query_label}: {len(entries)} entries")
        for e in entries:
            e["strategy"] = "S1"
            e["query"] = query_label
            # dedup
            doi_key = e["doi"].lower() if e.get("doi") else None
            url_key = e["url"].rstrip("/") if e.get("url") else None
            dedup_key = doi_key or url_key or e["title"].lower()[:80]
            if dedup_key in seen_dois:
                continue
            seen_dois.add(dedup_key)
            # vault check
            in_vault = (
                (doi_key and doi_key in vault_keys) or
                (url_key and url_key in vault_keys)
            )
            if in_vault:
                # find citekey
                e["vault_citekey"] = "in vault"
                all_existing.append(e)
                print(f"  [vault] {e['title'][:70]}")
            else:
                all_new.append(e)
                print(f"  [new]   {e['title'][:70]}")

    out_new  = _HERE / "candidates_s1_new_c1.json"
    out_exist = _HERE / "candidates_s1_existing_c1.json"
    out_new.write_text(json.dumps(all_new, indent=2, ensure_ascii=False))
    out_exist.write_text(json.dumps(all_existing, indent=2, ensure_ascii=False))
    print(f"\n→ {len(all_new)} new candidates: {out_new.name}")
    print(f"→ {len(all_existing)} already in vault: {out_exist.name}")


if __name__ == "__main__":
    main()
