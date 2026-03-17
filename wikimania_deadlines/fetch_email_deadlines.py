"""
Phase 2 — Email archive deadlines.

For each Wikimania edition:
  1. Downloads monthly archives from wikimania-l (+ wikimedia-l fallback)
     covering ~9 months before the conference through the conference month.
  2. Parses mbox into individual messages, filters to those mentioning
     deadlines / submissions / scholarships / registration.
  3. Sends filtered batches to Mistral for structured date extraction.
  4. Merges results into editions/wikimania_YYYY.json, only filling fields
     that are currently null/unknown (never overwrites confirmed dates).

Run:  python fetch_email_deadlines.py [year]   # single edition
      python fetch_email_deadlines.py           # all editions
"""

import email
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from cache import fetch_email_archive, MONTHS
from llm import query_mistral

EDITIONS_DIR = Path(__file__).parent / "editions"

# ---------------------------------------------------------------------------
# Mailing lists to try, in priority order
# ---------------------------------------------------------------------------
LISTS = ["wikimania-l", "wikimedia-l"]

# How many months before August of the conference year to scan
MONTHS_BEFORE = 9

# Keywords that flag an email as potentially containing deadline info
FILTER_KEYWORDS = [
    "deadline", "submission", "scholarship", "registration",
    "call for", "cfp", "speaker", "notification", "acceptance",
    "program", "programme", "schedule", "apply", "application",
    "open for", "closes", "extended", "extension",
]

# Maximum characters to send to Mistral in one call (~6k tokens)
MAX_CHARS_PER_CALL = 18_000

# Deadline types we want Mistral to look for
DEADLINE_TYPES = """
- program_submission_open              : when the call for submissions/proposals opened
- program_submission_deadline          : original deadline to submit a proposal/talk
- program_submission_deadline_extended : extended/new deadline if the original was pushed back
- program_acceptance_notification      : when accepted speakers are notified
- program_speaker_confirmation         : deadline for accepted speakers to confirm participation
- program_schedule_published           : when the full program/schedule was published
- scholarship_applications_open        : when scholarship applications opened
- scholarship_deadline                 : original scholarship application deadline
- scholarship_deadline_extended        : extended scholarship deadline
- scholarship_results_notification     : the date the scholarship results/decisions were ACTUALLY SENT OUT (past tense — use the email's own date, not a future planned date)
- scholarship_acceptance_confirmation  : deadline for scholarship awardees to confirm acceptance
- registration_open                    : when public registration opened
- registration_earlybird_deadline      : end of early-bird / discounted registration
- registration_deadline                : last day for online registration
"""

EXTRACTION_SYSTEM = (
    "You are a precise data extraction assistant. "
    "Extract only dates that are explicitly stated in the text. "
    "Do not infer or guess. Return valid JSON only."
)

EXTRACTION_PROMPT = """\
Below are emails from the Wikimania {year} mailing list archives.
Extract deadline dates that are SPECIFICALLY about Wikimania {year}.
Ignore dates about other events (Wikimedia Conference, WMCON, affiliates, etc.).
Only include dates that fall between October {prev_year} and September {year}.

Deadline types to look for:
{types}

Return a JSON array. Each element:
{{
  "type": "<deadline_type from the list above>",
  "date": "<YYYY-MM-DD if exact, YYYY-MM if only month/year known, null if unclear>",
  "date_confidence": "confirmed" if exact date stated, "approximate" if inferred from context,
  "evidence": "<the exact sentence or phrase where you found the date, max 200 chars>",
  "email_subject": "<subject line of the email containing this date>"
}}

Rules:
- Only extract dates explicitly stated, never guess.
- If a date has no year, use {year} if it fits the context.
- Prefer the most specific date when multiple are mentioned for the same deadline.
- For scholarship_results_notification: use the email's own send date (the Date: header),
  not a future date mentioned in the body. An email announcing results IS the notification.
- If no relevant dates found, return [].

--- EMAILS ---
{emails}
--- END ---

JSON array:"""


# ---------------------------------------------------------------------------
# Mbox parsing
# ---------------------------------------------------------------------------

def parse_messages(raw_text: str) -> list[dict]:
    """Split a raw mbox text into list of {subject, body, date} dicts."""
    # mbox messages are separated by "From " at the start of a line
    raw_msgs = re.split(r'(?m)^From \S+.*$', raw_text)
    results = []
    for chunk in raw_msgs:
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            msg = email.message_from_string("From: x\n" + chunk)
            subject = msg.get("Subject", "")
            # decode encoded subject
            subject = str(email.header.make_header(
                email.header.decode_header(subject)))
            date    = msg.get("Date", "")
            body    = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        try:
                            body += part.get_payload(decode=True).decode(
                                errors="replace")
                        except Exception:
                            body += str(part.get_payload())
            else:
                try:
                    body = msg.get_payload(decode=True).decode(errors="replace")
                except Exception:
                    body = str(msg.get_payload())
            results.append({"subject": subject, "date": date, "body": body})
        except Exception:
            continue
    return results


def is_relevant(msg: dict) -> bool:
    text = (msg["subject"] + " " + msg["body"]).lower()
    return any(kw in text for kw in FILTER_KEYWORDS)


def format_for_prompt(msgs: list[dict]) -> str:
    parts = []
    for i, m in enumerate(msgs, 1):
        body_snippet = m["body"][:1200].strip()
        parts.append(
            f"[Email {i}]\nDate: {m['date']}\nSubject: {m['subject']}\n\n"
            f"{body_snippet}\n"
        )
    return "\n---\n".join(parts)


# ---------------------------------------------------------------------------
# Mistral extraction
# ---------------------------------------------------------------------------

def extract_deadlines_from_emails(
    msgs: list[dict], year: int
) -> list[dict]:
    """Batch emails and call Mistral, return list of raw deadline dicts."""
    if not msgs:
        return []

    all_results = []

    # Split into batches of MAX_CHARS_PER_CALL
    batches, current, current_len = [], [], 0
    for m in msgs:
        chunk = format_for_prompt([m])
        if current_len + len(chunk) > MAX_CHARS_PER_CALL and current:
            batches.append(current)
            current, current_len = [], 0
        current.append(m)
        current_len += len(chunk)
    if current:
        batches.append(current)

    for i, batch in enumerate(batches):
        prompt = EXTRACTION_PROMPT.format(
            year=year,
            prev_year=year - 1,
            types=DEADLINE_TYPES,
            emails=format_for_prompt(batch),
        )
        try:
            raw = query_mistral(prompt, system=EXTRACTION_SYSTEM)
            # Strip markdown code fences if present
            raw = re.sub(r'^```(?:json)?\s*', '', raw.strip(), flags=re.MULTILINE)
            raw = re.sub(r'\s*```$', '', raw.strip(), flags=re.MULTILINE)
            # Try full array parse first (greedy: first [ to last ])
            parsed = None
            m = re.search(r'\[.*\]', raw, re.DOTALL)
            if m:
                try:
                    parsed = json.loads(m.group(0))
                except json.JSONDecodeError:
                    pass
            # Fallback: extract individual complete JSON objects
            if parsed is None:
                parsed = []
                for obj_m in re.finditer(r'\{[^{}]*\}', raw, re.DOTALL):
                    try:
                        parsed.append(json.loads(obj_m.group(0)))
                    except json.JSONDecodeError:
                        pass
                if parsed:
                    print(f"    (batch {i+1}: used fallback object extraction, "
                          f"{len(parsed)} objects)")
            if isinstance(parsed, list):
                all_results.extend(parsed)
            time.sleep(0.5)
        except Exception as e:
            print(f"    Mistral error (batch {i+1}): {e}")

    return all_results


# ---------------------------------------------------------------------------
# Merge into JSON
# ---------------------------------------------------------------------------

def classify_source_type(url: str) -> str:
    if "meta.wikimedia.org" in url:
        return "meta_wiki"
    if "lists.wikimedia.org" in url:
        return "mailing_list"
    return "mailing_list"


def archive_url(list_name: str, year: int, month: str) -> str:
    return (f"https://lists.wikimedia.org/pipermail/"
            f"{list_name}/{year}-{month}.txt.gz")


def find_message_url(list_name: str, year: int, month: str,
                     subject: str, evidence: str) -> str:
    """
    Look up the specific message URL in the pipermail HTML index.
    Searches the subject.html index by subject line; falls back to
    searching for the evidence snippet in individual message files.
    Returns the per-message URL, or the monthly archive index URL.
    """
    import ssl, urllib.request, urllib.error
    import certifi
    ctx = ssl.create_default_context(cafile=certifi.where())
    base = f"https://lists.wikimedia.org/pipermail/{list_name}/{year}-{month}"

    # Step 1: fetch the subject index HTML
    try:
        req = urllib.request.Request(
            f"{base}/subject.html",
            headers={"User-Agent": "WikimaniaDeadlinesResearch/1.0"},
        )
        with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
            index_html = r.read().decode("utf-8", errors="replace")
    except Exception:
        return f"{base}/"   # fallback: monthly index

    # Step 2: find href by matching the subject (strip Re:/Fwd: prefix for fuzzy match)
    def _norm(s):
        # Strip list prefix [Foo-l], Re:/Fwd:, whitespace
        s = re.sub(r'\[[\w-]+\]\s*', '', s)
        s = re.sub(r'^\s*(re|fwd|fw)\s*:\s*', '', s, flags=re.IGNORECASE)
        return re.sub(r'\s+', ' ', s).strip().lower()

    clean_subject = _norm(subject)
    # Find all <a href="NNNNNN.html">subject text</a> pairs
    links = re.findall(r'<a\s+href="(\d+\.html)"[^>]*>(.*?)</a>', index_html, re.IGNORECASE | re.DOTALL)
    for href, link_text in links:
        link_clean = _norm(link_text)
        if not link_clean:
            continue
        if clean_subject in link_clean or link_clean in clean_subject:
            return f"{base}/{href}"

    # Step 3: no subject match — search evidence snippet in message bodies
    if evidence:
        snippet = evidence[:80].lower()
        for href, _ in links[:50]:   # check first 50 messages to limit requests
            try:
                req2 = urllib.request.Request(
                    f"{base}/{href}",
                    headers={"User-Agent": "WikimaniaDeadlinesResearch/1.0"},
                )
                with urllib.request.urlopen(req2, timeout=10, context=ctx) as r2:
                    body = r2.read().decode("utf-8", errors="replace").lower()
                if snippet in body:
                    return f"{base}/{href}"
                time.sleep(0.1)
            except Exception:
                continue

    return f"{base}/"   # fallback: monthly index


def _date_in_range(date_str: str, year: int) -> bool:
    """Return True if date plausibly belongs to this edition (Oct prev–Sep conf year)."""
    try:
        y = int(date_str[:4])
        return (year - 1) <= y <= year
    except (ValueError, TypeError):
        return False


def merge_results(
    data: dict,
    raw_results: list[dict],
    archive_urls: list[str],
) -> int:
    """
    Merge Mistral-extracted deadline dicts into the edition JSON data dict.
    Only fills fields that are currently null/unknown.
    Returns number of fields updated.
    """
    # Build lookup of existing deadlines by type
    existing = {}
    for bucket in data["buckets"].values():
        for d in bucket.get("deadlines", []):
            existing[d["type"]] = d

    # Determine which bucket each type belongs to
    bucket_map = {}
    for bucket_name, bucket in data["buckets"].items():
        for d in bucket.get("deadlines", []):
            bucket_map[d["type"]] = bucket_name
    # Also map types that may not exist yet
    for t in [
        "program_submission_open", "program_submission_deadline",
        "program_submission_deadline_extended", "program_acceptance_notification",
        "program_speaker_confirmation", "program_schedule_published",
    ]:
        bucket_map.setdefault(t, "program")
    for t in [
        "scholarship_applications_open", "scholarship_deadline",
        "scholarship_deadline_extended", "scholarship_results_notification",
        "scholarship_acceptance_confirmation",
    ]:
        bucket_map.setdefault(t, "scholarship")
    for t in [
        "registration_open", "registration_earlybird_deadline",
        "registration_deadline_online", "registration_deadline_inperson",
        "registration_late_deadline",
    ]:
        bucket_map.setdefault(t, "registration")

    updated = 0
    for r in raw_results:
        dtype = r.get("type")
        date  = r.get("date")
        conf  = r.get("date_confidence", "approximate")
        evidence = r.get("evidence", "")
        subject  = r.get("email_subject", "")

        if not dtype or not date:
            continue
        # Guard evidence/subject against None
        evidence = evidence or ""
        subject  = subject or ""
        # Reject out-of-range dates (likely from other events on the list)
        year = data["year"]
        if not _date_in_range(str(date), year):
            continue
        if dtype not in bucket_map:
            continue

        # Normalise approximate month-only dates
        if re.match(r'^\d{4}-\d{2}$', str(date)):
            # Month-only → use first of month, mark approximate
            date = date + "-01"
            conf = "approximate"

        cur = existing.get(dtype)
        cur_conf = cur.get("date_confidence") if cur else None
        cur_date = cur.get("date") if cur else None

        # Never overwrite not_applicable
        if cur_conf == "not_applicable":
            continue
        # Never overwrite confirmed
        if cur_conf == "confirmed" and cur_date:
            continue
        # Don't replace approximate with approximate (no upgrade)
        if cur_conf == "approximate" and cur_date and conf != "confirmed":
            continue

        # Search all scanned archive months for the specific message URL
        msg_url = archive_urls[0] if archive_urls else ""
        if subject:
            for arch_url in archive_urls:
                m_arch = re.search(r'/pipermail/([^/]+)/(\d{4})-(\w+)', arch_url)
                if not m_arch:
                    continue
                candidate = find_message_url(
                    m_arch.group(1), int(m_arch.group(2)), m_arch.group(3),
                    subject, evidence,
                )
                if re.search(r'/\d+\.html$', candidate):
                    msg_url = candidate
                    break  # found a specific message link

        new_entry = {
            "type": dtype,
            "date": date,
            "date_confidence": conf,
            "notes": f"From email: '{subject[:80]}' — '{evidence[:150]}'",
            "sources": [{
                "url": msg_url,
                "source_type": "mailing_list",
                "verified": False,
                "verified_date": None,
                "verified_text_found": None,
            }],
        }

        bucket_name = bucket_map[dtype]
        # Update or append
        bucket_deadlines = data["buckets"][bucket_name]["deadlines"]
        replaced = False
        for i, d in enumerate(bucket_deadlines):
            if d["type"] == dtype:
                bucket_deadlines[i] = new_entry
                replaced = True
                break
        if not replaced:
            bucket_deadlines.append(new_entry)

        existing[dtype] = new_entry
        updated += 1

    return updated


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def process_edition(year: int) -> None:
    json_path = EDITIONS_DIR / f"wikimania_{year}.json"
    if not json_path.exists():
        print(f"  {year}: JSON file missing, skipping")
        return

    data = json.loads(json_path.read_text())

    # Determine months to scan
    conf_month_idx = 7  # August (0-based)
    periods = []
    for delta in range(MONTHS_BEFORE, -1, -1):
        total = conf_month_idx - delta
        y = year + total // 12
        m = total % 12
        periods.append((y, MONTHS[m]))

    all_relevant_msgs = []
    used_archive_urls = []

    for list_name in LISTS:
        for y, month in periods:
            text = fetch_email_archive(list_name, y, month)
            time.sleep(0.15)
            if not text:
                continue
            msgs = parse_messages(text)
            relevant = [m for m in msgs if is_relevant(m)]
            if relevant:
                all_relevant_msgs.extend(relevant)
                used_archive_urls.append(archive_url(list_name, y, month))

    if not all_relevant_msgs:
        print(f"  {year}: no relevant emails found in archives")
        return

    # Deduplicate by subject+date
    seen = set()
    deduped = []
    for m in all_relevant_msgs:
        key = (m["subject"][:60], m["date"][:16])
        if key not in seen:
            seen.add(key)
            deduped.append(m)

    print(f"  {year}: {len(deduped)} relevant emails across "
          f"{len(used_archive_urls)} archives — querying Mistral...")

    raw = extract_deadlines_from_emails(deduped, year)

    if not raw:
        print(f"  {year}: Mistral found no deadline dates")
        return

    n = merge_results(data, raw, used_archive_urls)

    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"  {year}: {len(raw)} dates extracted, {n} fields updated")
    for r in raw:
        print(f"    {r.get('type','?')}: {r.get('date','?')} "
              f"({r.get('date_confidence','?')}) — {(r.get('evidence') or '')[:80]}")


def main():
    target_years = None
    if len(sys.argv) > 1:
        target_years = [int(a) for a in sys.argv[1:]]

    years = target_years or list(range(2006, 2026))
    # Skip 2020 (cancelled)
    years = [y for y in years if y != 2020]

    print(f"Processing {len(years)} editions via email archives...\n")
    for year in years:
        print(f"Wikimania {year}:")
        process_edition(year)
        print()


if __name__ == "__main__":
    main()
