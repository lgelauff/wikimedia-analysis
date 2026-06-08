"""
text.py — pure text-extraction functions (no I/O).
"""

import html
import re
from io import BytesIO


def _detect_encoding(raw: bytes, content_type: str = "") -> str:
    """Detect charset using the HTML5 encoding sniffing algorithm.

    Priority order per https://html.spec.whatwg.org/multipage/parsing.html#determining-the-character-encoding:
      1. BOM (UTF-8, UTF-16 BE/LE)
      2. <meta charset> or <meta http-equiv="Content-Type"> prescan (first 1024 bytes)
      3. Transport layer: charset= in Content-Type header
      4. Heuristic: charset_normalizer if available
      5. Default: UTF-8

    The EDGI web-monitoring-processing project (GPL-3) applies the same priority
    order. This implementation is written independently from the HTML5 spec.
    """
    # 1. BOM sniffing
    if raw[:3] == b"\xef\xbb\xbf":
        return "utf-8-sig"
    if raw[:2] == b"\xfe\xff":
        return "utf-16-be"
    if raw[:2] == b"\xff\xfe":
        return "utf-16-le"

    # 2. <meta> prescan — covers both:
    #    <meta charset="utf-8">
    #    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    m = re.search(
        rb'<meta[^>]+charset\s*=\s*["\']?\s*([^"\';\s>]+)',
        raw[:1024],
        re.IGNORECASE,
    )
    if m:
        enc = m.group(1).decode("ascii", errors="ignore").strip()
        if enc:
            return enc

    # 3. Transport layer
    if "charset=" in content_type:
        enc = content_type.split("charset=", 1)[1].split(";")[0].strip(' "\'')
        if enc:
            return enc

    # 4. Heuristic
    try:
        from charset_normalizer import detect
        result = detect(raw[:10_000])
        if result.get("encoding"):
            return result["encoding"]
    except ImportError:
        pass

    return "utf-8"


def html_to_text(raw: bytes | str, max_chars: int = 120_000, content_type: str = "") -> str:
    """Strip <script>/<style> blocks, all tags, unescape HTML entities, collapse whitespace.

    Accepts bytes (charset auto-detected from BOM, <meta> tags, and Content-Type header)
    or a pre-decoded str.
    """
    if isinstance(raw, bytes):
        enc = _detect_encoding(raw, content_type)
        try:
            raw = raw.decode(enc, errors="replace")
        except (LookupError, UnicodeDecodeError):
            raw = raw.decode("utf-8", errors="replace")

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
