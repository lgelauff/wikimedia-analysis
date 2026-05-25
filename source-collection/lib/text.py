"""
text.py — pure text-extraction functions (no I/O).
"""

import html
import re
from io import BytesIO


def html_to_text(raw: str, max_chars: int = 120_000) -> str:
    """Strip <script>/<style> blocks, all tags, unescape HTML entities, collapse whitespace."""
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def pdf_to_text(data: bytes, max_chars: int = 120_000) -> str:
    """Extract text from PDF bytes using pypdf. Returns a placeholder if pypdf is not installed."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return "[pypdf not installed — install with: pip install pypdf]"
    reader = PdfReader(BytesIO(data))
    pages, total = [], 0
    for page in reader.pages:
        t = page.extract_text() or ""
        pages.append(t)
        total += len(t)
        if total >= max_chars:
            break
    return "\n".join(pages)[:max_chars]
