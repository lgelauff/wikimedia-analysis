"""
text.py — pure text-extraction functions (no I/O).
"""

import html
import re
import urllib.parse
from io import BytesIO

# --- outbound-link preservation -------------------------------------------
# Tag-stripping throws away every href, so a landing page that exists only to
# point at a PDF collects as a page that mentions a document and never names
# where it lives. These constants bound what we keep so a link-farm page cannot
# blow up the cache.
MAX_LINKS = 500          # per page; extraction stops once this many are kept
MAX_ANCHOR_CHARS = 200   # anchor text is a label, not content
_SKIP_SCHEMES = ("javascript:", "mailto:", "tel:", "data:", "about:")

_A_TAG_RE = re.compile(r"<a\b([^>]*)>(.*?)</a\s*>", re.IGNORECASE | re.DOTALL)
# `\b` is the wrong boundary for an attribute name: `-` is a non-word character,
# so \bhref also matches the tail of `data-href`, silently returning the wrong
# attribute AND losing the real href. Require a non-word, non-hyphen char before.
_ATTR_START = r"(?<![\w-])"
_ATTR_VALUE = r"""\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s">]+))"""
_HREF_RE = re.compile(_ATTR_START + "href" + _ATTR_VALUE, re.IGNORECASE)
_REL_RE = re.compile(_ATTR_START + "rel" + _ATTR_VALUE, re.IGNORECASE)
_TYPE_RE = re.compile(_ATTR_START + "type" + _ATTR_VALUE, re.IGNORECASE)
_BASE_RE = re.compile(
    r"<base\b[^>]*" + _ATTR_START + "href" + _ATTR_VALUE, re.IGNORECASE
)


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


def _attr(match_regex, attrs: str) -> str:
    m = match_regex.search(attrs)
    if not m:
        return ""
    return (m.group(1) or m.group(2) or m.group(3) or "").strip()


def extract_links(
    raw: bytes | str,
    base_url: str = "",
    max_links: int = MAX_LINKS,
    content_type: str = "",
    context: str = "",
) -> list[dict]:
    """Return the page's outbound <a href> links, absolute-resolved and deduplicated.

    Each item is {"url", "anchor_text", "rel_or_context"}. Order is document order
    of first appearance. Fragment-only, javascript:, mailto:, tel:, data: and about:
    hrefs are dropped. A <base href> in the document overrides `base_url` for
    resolution, per the HTML spec.

    `max_links` caps the result so a link-farm page cannot explode the cache; the
    scan stops as soon as the cap is reached.
    """
    if isinstance(raw, bytes):
        enc = _detect_encoding(raw, content_type)
        try:
            raw = raw.decode(enc, errors="replace")
        except (LookupError, UnicodeDecodeError):
            raw = raw.decode("utf-8", errors="replace")

    # Strip the blocks html_to_text also strips, BEFORE looking for anchors:
    # an <a href> inside a JS string literal or an HTML comment is not an
    # outbound link of the page, and harvesting it manufactures URLs that were
    # never on it. (Caught by tests/test_links.py.)
    raw = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.DOTALL | re.IGNORECASE)
    raw = re.sub(r"<!--.*?-->", " ", raw, flags=re.DOTALL)

    effective_base = base_url
    bm = _BASE_RE.search(raw[:20_000])
    if bm:
        declared = (bm.group(1) or bm.group(2) or bm.group(3) or "").strip()
        if declared:
            effective_base = urllib.parse.urljoin(base_url, html.unescape(declared))

    out: list[dict] = []
    seen: set[str] = set()
    for m in _A_TAG_RE.finditer(raw):
        attrs, inner = m.group(1), m.group(2)
        href = html.unescape(_attr(_HREF_RE, attrs))
        if not href:
            continue
        href = href.strip()
        if not href or href.startswith("#"):
            continue
        if href.lower().startswith(_SKIP_SCHEMES):
            continue
        url = urllib.parse.urljoin(effective_base, href) if effective_base else href
        if url in seen:
            continue
        anchor = re.sub(r"<[^>]+>", " ", inner)
        anchor = re.sub(r"\s+", " ", html.unescape(anchor)).strip()[:MAX_ANCHOR_CHARS]
        rel = _attr(_REL_RE, attrs) or _attr(_TYPE_RE, attrs)
        seen.add(url)
        out.append({
            "url": url,
            "anchor_text": anchor,
            "rel_or_context": " ".join(x for x in (rel, context) if x).strip(),
        })
        if len(out) >= max_links:
            break
    return out


LINKS_TSV_HEADER = "url\tanchor_text\trel_or_context"


def links_to_tsv(links: list[dict]) -> str:
    """Serialise extract_links() output as a TSV sidecar body (header + rows)."""
    def clean(s: str) -> str:
        return re.sub(r"[\t\r\n]+", " ", s or "").strip()

    rows = [LINKS_TSV_HEADER]
    for link in links:
        rows.append(
            f"{clean(link.get('url', ''))}\t"
            f"{clean(link.get('anchor_text', ''))}\t"
            f"{clean(link.get('rel_or_context', ''))}"
        )
    return "\n".join(rows) + "\n"


def html_to_text(
    raw: bytes | str,
    max_chars: int = 120_000,
    content_type: str = "",
    links_out: list | None = None,
    base_url: str = "",
    link_context: str = "",
) -> str:
    """Strip <script>/<style> blocks, all tags, unescape HTML entities, collapse whitespace.

    Accepts bytes (charset auto-detected from BOM, <meta> tags, and Content-Type header)
    or a pre-decoded str.

    The return value is unchanged. Passing a list as `links_out` additionally collects
    the page's outbound links into it (see extract_links); callers that do not pass one
    behave exactly as before.
    """
    if isinstance(raw, bytes):
        enc = _detect_encoding(raw, content_type)
        try:
            raw = raw.decode(enc, errors="replace")
        except (LookupError, UnicodeDecodeError):
            raw = raw.decode("utf-8", errors="replace")

    if links_out is not None:
        try:
            links_out.extend(
                extract_links(raw, base_url=base_url, context=link_context)
            )
        except Exception:
            pass  # link capture must never break text extraction

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
