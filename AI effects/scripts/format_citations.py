"""
format_citations.py

Replaces abbreviated footnote definitions in output.md with full Chicago
Notes-Bibliography style citations, sourced from sources.bib.

Uses pybtex for BibTeX parsing (handles LaTeX encoding, accented characters).
Relies on <!-- fn-map: 1=citekey1 2=citekey2 --> comments written by
draft_output.py to match footnote numbers to bib entries without fuzzy matching.

Usage:
    python -m scripts.format_citations [--input output.md] [--dry-run]
"""

import argparse
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from pybtex.database import parse_file, Entry

_BIB_FILE = Path(__file__).parent.parent / "sources.bib"
_OUTPUT   = Path(__file__).parent.parent / "output.md"


# ---------------------------------------------------------------------------
# Chicago formatter
# ---------------------------------------------------------------------------

def _clean(s: str) -> str:
    """Strip LaTeX braces and common escape sequences, decode accented characters."""
    import latexcodec  # noqa: ensure available
    try:
        s = s.encode("utf-8").decode("latex")
    except Exception:
        pass
    s = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", s)  # \emph{x} → x
    s = s.replace("{", "").replace("}", "").replace("\\&", "&")
    return re.sub(r"\s+", " ", s).strip()


def _person_full(p) -> str:
    """Format a pybtex Person as 'Last, First Middle'."""
    last  = _clean(" ".join(str(x) for x in p.last_names))
    first = _clean(" ".join(list(p.first_names) + list(p.middle_names)))
    if not last:
        return first
    return f"{last}, {first}".strip(", ")


def _format_authors_chicago(persons: list) -> str:
    """
    Chicago author list:
      1 author  → Last, First
      2 authors → Last, First, and First Last
      3+        → Last, First, First Last, and First Last
    """
    if not persons:
        return ""
    if len(persons) == 1:
        return _person_full(persons[0])
    formatted = [_person_full(persons[0])]
    for p in persons[1:-1]:
        last  = _clean(" ".join(str(x) for x in p.last_names))
        first = _clean(" ".join(list(p.first_names) + list(p.middle_names)))
        formatted.append(f"{first} {last}".strip())
    last_p = persons[-1]
    last  = _clean(" ".join(str(x) for x in last_p.last_names))
    first = _clean(" ".join(list(last_p.first_names) + list(last_p.middle_names)))
    formatted.append("and " + f"{first} {last}".strip())
    return ", ".join(formatted)


def chicago_citation(entry: Entry, citekey: str) -> str:
    """
    Produce a Chicago Notes-Bibliography footnote citation.

    Format varies by entry type:
      article     → Author(s). "Title." *Journal* vol, no. N (year): pages. URL.
      book        → Author(s). *Title*. City: Publisher, year. URL.
      inproceedings/incollection
                  → Author(s). "Title." In *Booktitle*, pages. year. URL.
      techreport  → Author(s). "Title." Institution, year. URL.
      misc/other  → Author(s). "Title." Howpublished/Publisher, year. URL.
    """
    f = {k.lower(): _clean(v) for k, v in entry.fields.items()}
    persons = entry.persons.get("author", [])
    authors = _format_authors_chicago(persons)
    year   = f.get("year", "n.d.")
    title  = f.get("title", "")
    doi    = f.get("doi", "")
    url    = f.get("url", "")
    etype  = entry.type.lower()

    parts: list[str] = []

    if authors:
        parts.append(f"{authors}.")

    if etype == "book":
        parts.append(f"*{title}*.")
        pub = f.get("publisher", "")
        city = f.get("address", "")
        venue = f"{city}: {pub}" if city else pub
        if venue:
            parts.append(f"{venue}, {year}.")
        else:
            parts.append(f"{year}.")
    elif etype in ("article",):
        parts.append(f'"{title}."')
        journal = f.get("journal", "")
        vol     = f.get("volume", "")
        num     = f.get("number", "")
        pages   = f.get("pages", "").replace("--", "–")
        venue = f"*{journal}*" if journal else ""
        if vol:
            venue += f" {vol}"
            if num:
                venue += f", no. {num}"
        venue += f" ({year})"
        if pages:
            venue += f": {pages}"
        parts.append(venue + ".")
    elif etype in ("inproceedings", "incollection"):
        parts.append(f'"{title}."')
        book = f.get("booktitle", "")
        pages = f.get("pages", "").replace("--", "–")
        venue = f"In *{book}*" if book else ""
        if pages:
            venue += f", {pages}"
        venue += f". {year}."
        parts.append(venue)
    elif etype == "techreport":
        parts.append(f'"{title}."')
        inst = f.get("institution", "")
        if inst:
            parts.append(f"{inst}, {year}.")
        else:
            parts.append(f"{year}.")
    else:  # misc, online, etc.
        parts.append(f'"{title}."')
        howpub = f.get("howpublished", f.get("publisher", ""))
        if howpub:
            parts.append(f"{howpub}, {year}.")
        else:
            parts.append(f"{year}.")

    # URL / DOI — always include one
    if doi:
        parts.append(f"https://doi.org/{doi}")
    elif url:
        parts.append(url)
    else:
        parts.append("(URL not available)")

    # Append citekey as a discreet hint
    citation = " ".join(parts)
    return f"{citation} [{citekey}]"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(input_path: Path, dry_run: bool) -> None:
    bib = parse_file(str(_BIB_FILE))

    text = input_path.read_text(encoding="utf-8")

    # Find every fn-map comment and the footnote definitions within its theme block
    fn_map_pattern = re.compile(r"<!-- fn-map: ([^>]+) -->")
    footnote_def   = re.compile(r"(\[\^(\d+)\]:)[^\n]*", re.MULTILINE)

    replacements = 0
    missing_keys: set[str] = set()

    def replace_section(section_text: str) -> str:
        nonlocal replacements
        fm = fn_map_pattern.search(section_text)
        if not fm:
            return section_text  # no map — leave untouched

        # Parse the map: "1=key1 2=key2 ..."
        num_to_key: dict[int, str] = {}
        for token in fm.group(1).strip().split():
            if "=" in token:
                n, k = token.split("=", 1)
                num_to_key[int(n)] = k

        def replace_footnote(m: re.Match) -> str:
            nonlocal replacements
            num = int(m.group(2))
            key = num_to_key.get(num)
            if not key:
                return m.group(0)  # number out of map range — leave as-is
            if key not in bib.entries:
                missing_keys.add(key)
                return m.group(0)
            citation = chicago_citation(bib.entries[key], key)
            replacements += 1
            return f"{m.group(1)} {citation}"

        result = footnote_def.sub(replace_footnote, section_text)

        # Deduplicate: if the same citekey appears under multiple footnote numbers,
        # collapse all references to the first number and drop the later definitions.
        key_to_first_num: dict[str, int] = {}
        for n, k in num_to_key.items():
            if k not in key_to_first_num:
                key_to_first_num[k] = n

        # Build a reverse map: later_num → first_num for duplicated keys
        remap: dict[int, int] = {}
        for n, k in num_to_key.items():
            first = key_to_first_num[k]
            if first != n:
                remap[n] = first

        if remap:
            # Replace inline markers pointing to later numbers
            for later, first in sorted(remap.items(), reverse=True):
                result = re.sub(rf"\[\^{later}\](?!:)", f"[^{first}]", result)
            # Remove duplicate footnote definitions (keep only first occurrence)
            seen_def: set[int] = set()
            def dedup_def(m: re.Match) -> str:
                n = int(m.group(1))
                if n in seen_def:
                    return ""  # drop duplicate
                seen_def.add(n)
                return m.group(0)
            result = re.sub(r"^\[\^(\d+)\]:[^\n]*\n?", dedup_def, result, flags=re.MULTILINE)

        return result

    # Process section by section (split on <!-- theme: markers)
    chunks = re.split(r"(?=<!-- theme:)", text)
    new_chunks = [replace_section(c) for c in chunks]
    new_text = "".join(new_chunks)

    if missing_keys:
        print(f"Warning: {len(missing_keys)} citekeys not found in bib: {sorted(missing_keys)}")

    print(f"Replaced {replacements} footnote definitions with Chicago citations.")

    if dry_run:
        print("(dry-run: no file written)")
        return

    input_path.write_text(new_text, encoding="utf-8")
    print(f"Written: {input_path}")

    export_docx(input_path)


def export_docx(md_path: Path) -> None:
    """Renumber footnotes globally and export to a .docx alongside the .md file."""
    if not shutil.which("pandoc"):
        print("Warning: pandoc not found — skipping DOCX export.")
        return

    text = md_path.read_text(encoding="utf-8")

    # Renumber footnotes globally (each theme section restarts at [^1])
    chunks = re.split(r"(?=<!-- theme:[\w\-\d]+ -->)", text)
    counter = 0
    out_chunks = []
    for chunk in chunks:
        defined = sorted(set(int(m) for m in re.findall(r"^\[\^(\d+)\]:", chunk, re.MULTILINE)))
        if not defined:
            out_chunks.append(chunk)
            continue
        mapping = {}
        for local in defined:
            counter += 1
            mapping[local] = counter
        for local in sorted(mapping, reverse=True):
            g = mapping[local]
            chunk = re.sub(rf"\[\^{local}\](?!:)", f"[^{g}]", chunk)
            chunk = re.sub(rf"^\[\^{local}\]:", f"[^{g}]:", chunk, flags=re.MULTILINE)
        out_chunks.append(chunk)
    renumbered = "".join(out_chunks)

    docx_path = md_path.with_suffix(".docx")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as tmp:
        tmp.write(renumbered)
        tmp_path = tmp.name

    result = subprocess.run(
        ["pandoc", tmp_path, "-o", str(docx_path), "--from", "markdown", "--to", "docx", "-s"],
        capture_output=True, text=True,
    )
    Path(tmp_path).unlink(missing_ok=True)

    if result.returncode == 0:
        print(f"Exported: {docx_path}")
    else:
        print(f"DOCX export failed: {result.stderr.strip()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Format footnotes as Chicago citations")
    parser.add_argument("--input", "-i", default=str(_OUTPUT), help="Path to output.md")
    parser.add_argument("--dry-run", action="store_true", help="Print stats without writing")
    args = parser.parse_args()
    run(Path(args.input), args.dry_run)


if __name__ == "__main__":
    main()
