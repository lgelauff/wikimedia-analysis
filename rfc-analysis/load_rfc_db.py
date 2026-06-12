"""
load_rfc_db.py — Convert rfc.sql (MySQL dump) to SQLite, streaming line by line.

Never loads the full file into memory. Accumulates lines into a statement buffer
and executes each complete statement as it closes. Skips BLOB columns and
MySQL-only syntax that SQLite rejects.

Output: datasets/rfc.db

Usage:
    python3 load_rfc_db.py [--force]
"""

import re
import sqlite3
import sys
from pathlib import Path

SQL_FILE = Path("datasets/rfc.sql")
DB_FILE  = Path("datasets/rfc.db")

# Tables whose data we skip entirely (BLOB-heavy, not needed for analysis)
SKIP_DATA_FOR = {"website_article"}   # vectorizer BLOB — we do want its rows though
# Actually we want all rows; we'll just drop the vectorizer column after load.
# Nothing to skip entirely.

# Line-level transforms applied to every line before accumulation
_TRANSFORMS = [
    # Engine / charset options at end of CREATE TABLE
    (re.compile(r"\)\s*ENGINE=\S+.*?;", re.S), ");"),
    # AUTO_INCREMENT in column defs
    (re.compile(r"\bAUTO_INCREMENT\b"), ""),
    # COLLATE …
    (re.compile(r"\bCOLLATE\s+\S+"), ""),
    # DEFAULT CHARSET=…
    (re.compile(r"\bDEFAULT CHARSET=\S+"), ""),
    # KEY / INDEX lines inside CREATE TABLE (handled by stripping whole line below)
    # Types
    (re.compile(r"\blongblob\b",   re.I), "BLOB"),
    (re.compile(r"\blongtext\b",   re.I), "TEXT"),
    (re.compile(r"\bmediumtext\b", re.I), "TEXT"),
    (re.compile(r"\btinytext\b",   re.I), "TEXT"),
    (re.compile(r"\btinyint\b",    re.I), "INTEGER"),
    (re.compile(r"\bdouble\b",     re.I), "REAL"),
    (re.compile(r"\bdatetime\(\d+\)", re.I), "DATETIME"),
    # Backticks → nothing (SQLite accepts bare names)
    (re.compile(r"`"), '"'),
]

# Full-line patterns to skip
_SKIP_LINE = re.compile(
    r"^\s*("
    r"SET\s+"
    r"|LOCK TABLES"
    r"|UNLOCK TABLES"
    r"|/\*"          # MySQL comment blocks
    r")"
, re.I)

# KEY / INDEX lines inside CREATE TABLE
_KEY_LINE = re.compile(r"^\s*(UNIQUE\s+)?KEY\s+", re.I)
_PRIMARY_KEY_LINE = re.compile(r"^\s*PRIMARY KEY\s*\(", re.I)


def transform_line(line: str) -> str | None:
    """Return transformed line, or None to skip it."""
    if _SKIP_LINE.match(line):
        return None
    if _KEY_LINE.match(line):
        return None
    if _PRIMARY_KEY_LINE.match(line):
        return None
    for pat, repl in _TRANSFORMS:
        line = pat.sub(repl, line)
    return line


def iter_statements(path: Path):
    """Yield complete SQL statements by streaming the file line by line."""
    buf = []
    in_insert = False

    with open(path, encoding="utf-8", errors="replace") as fh:
        for raw_line in fh:
            line = raw_line.rstrip("\n")

            transformed = transform_line(line)
            if transformed is None:
                continue

            # Track whether we're inside a multi-line INSERT (for performance reporting)
            stripped = transformed.lstrip()
            if stripped.upper().startswith("INSERT INTO"):
                in_insert = True

            buf.append(transformed)

            # A statement ends when a line ends with ";"
            if transformed.rstrip().endswith(";"):
                stmt = "\n".join(buf).rstrip().rstrip(";")
                if stmt.strip():
                    yield stmt
                buf = []
                in_insert = False

    # Flush any trailing partial statement
    if buf:
        stmt = "\n".join(buf).rstrip().rstrip(";")
        if stmt.strip():
            yield stmt


def load(force: bool = False):
    if DB_FILE.exists() and not force:
        print(f"[skip] {DB_FILE} already exists — pass --force to rebuild")
        sanity_check()
        return

    if DB_FILE.exists():
        DB_FILE.unlink()

    print(f"Opening {SQL_FILE} ({SQL_FILE.stat().st_size / 1e6:.0f} MB) — streaming…")

    con = sqlite3.connect(DB_FILE)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.execute("PRAGMA cache_size=-512000")  # 512 MB page cache

    errors = 0
    stmts  = 0
    inserts = 0

    for stmt in iter_statements(SQL_FILE):
        stmts += 1
        is_insert = stmt.lstrip().upper().startswith("INSERT")
        if is_insert:
            inserts += 1
        if stmts % 500 == 0:
            db_mb = DB_FILE.stat().st_size / 1e6 if DB_FILE.exists() else 0
            print(f"  {stmts:,} stmts  {inserts:,} inserts  db={db_mb:.0f}MB", end="\r")
        try:
            con.execute(stmt)
            # Commit every 1000 INSERT statements to keep memory low
            if is_insert and inserts % 1000 == 0:
                con.commit()
        except sqlite3.OperationalError as e:
            errors += 1
            if errors <= 20:
                print(f"\n  [warn] stmt {stmts}: {e}")
                print(f"         {stmt[:200]}")

    con.commit()
    con.close()
    print(f"\n  Finished: {stmts:,} statements, {inserts:,} inserts, {errors} errors.")

    sanity_check()


def sanity_check():
    print(f"\n=== {DB_FILE} — sanity check ===")
    con = sqlite3.connect(DB_FILE)

    tables = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )]
    print("Row counts:")
    for t in tables:
        n = con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        print(f"  {t:40s} {n:>8,}")

    print("\nRfCs:")
    n_total  = con.execute("SELECT COUNT(*) FROM website_article").fetchone()[0]
    n_closed = con.execute("SELECT COUNT(*) FROM website_article WHERE closed=1").fetchone()[0]
    print(f"  total:  {n_total:,}")
    print(f"  closed: {n_closed:,}")

    print("\nRfCs by year:")
    for yr, n in con.execute("""
        SELECT strftime('%Y', created_at), COUNT(*)
        FROM website_article WHERE created_at IS NOT NULL
        GROUP BY 1 ORDER BY 1
    """):
        print(f"  {yr}  {n:>5,}")

    n_comments = con.execute("SELECT COUNT(*) FROM website_comment").fetchone()[0]
    n_authors  = con.execute("SELECT COUNT(*) FROM website_commentauthor").fetchone()[0]
    n_with_join = con.execute(
        "SELECT COUNT(*) FROM website_commentauthor WHERE joined_at IS NOT NULL"
    ).fetchone()[0]
    print(f"\nComments: {n_comments:,}")
    print(f"Authors:  {n_authors:,}  ({n_with_join:,} with join date)")
    con.close()


if __name__ == "__main__":
    load(force="--force" in sys.argv)
