"""
test_links.py — outbound-link preservation in the text extractor.

Runs under pytest (`uv run --project source-collection pytest tests/`) and also
standalone (`python tests/test_links.py`) so it needs no test dependency.

No network: every case feeds bytes/str straight to the pure functions in lib/text.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from source_collection.lib.text import (  # noqa: E402
    MAX_LINKS,
    extract_links,
    html_to_text,
    links_to_tsv,
)

BASE = "https://www.dnc.ac.jp/kyotsu/kako_shiken_jouhou/r4/"

# Shaped after the real DNC year landing page: the scope document is a relative
# link to a PDF served from an /albums/ query-string path.
PAGE = b"""<html><head><meta charset="utf-8"><title>R4</title></head><body>
<a href="../../index.html">\xe3\x83\x88\xe3\x83\x83\xe3\x83\x97</a>
<a href="/albums/abm.php?d=570&amp;f=abm00002411.pdf" type="application/pdf">
  \xe5\x87\xba\xe9\xa1\x8c\xe6\x95\x99\xe7\xa7\x91\xe3\x83\xbb\xe7\xa7\x91\xe7\x9b\xae</a>
<a href="#top">page top</a>
<a href="javascript:void(0)">menu</a>
<a href="mailto:x@example.jp">contact</a>
<a href="../../index.html">\xe3\x83\x88\xe3\x83\x83\xe3\x83\x97 (dup)</a>
<a>no href</a>
<script>var a = '<a href="/trap.pdf">no</a>';</script>
</body></html>"""


def test_absolute_resolution_and_filtering():
    links = extract_links(PAGE, base_url=BASE)
    urls = [x["url"] for x in links]
    assert urls == [
        "https://www.dnc.ac.jp/kyotsu/index.html",
        "https://www.dnc.ac.jp/albums/abm.php?d=570&f=abm00002411.pdf",
    ], urls
    # fragment-only / javascript: / mailto: dropped, duplicate collapsed
    assert not any("#top" in u or u.startswith(("javascript:", "mailto:")) for u in urls)
    # anchor text is unescaped, tag-stripped and whitespace-collapsed
    assert links[1]["anchor_text"] == "出題教科・科目"
    assert links[1]["rel_or_context"] == "application/pdf"


def test_rel_attribute_and_context():
    links = extract_links(
        '<a href="/a.pdf" rel="noopener">A</a>', base_url="https://x.test/", context="direct"
    )
    assert links[0]["rel_or_context"] == "noopener direct"


def test_base_href_overrides_page_url():
    raw = '<html><head><base href="https://cdn.test/docs/"></head><body><a href="s.pdf">S</a>'
    links = extract_links(raw, base_url="https://x.test/page/")
    assert links[0]["url"] == "https://cdn.test/docs/s.pdf"


def test_cap_bounds_a_link_farm():
    farm = "".join(f'<a href="/p{i}">p{i}</a>' for i in range(MAX_LINKS + 250))
    assert len(extract_links(farm, base_url="https://x.test/")) == MAX_LINKS
    assert len(extract_links(farm, base_url="https://x.test/", max_links=10)) == 10


def test_html_to_text_return_value_is_unchanged():
    """The additive kwargs must not perturb the existing extraction contract."""
    before = html_to_text(PAGE, content_type="text/html")
    sink: list = []
    after = html_to_text(PAGE, content_type="text/html", links_out=sink, base_url=BASE)
    assert before == after
    assert "abm00002411.pdf" not in before  # the href never reached the text
    assert any("abm00002411.pdf" in x["url"] for x in sink)


def test_html_to_text_without_links_out_collects_nothing():
    assert html_to_text(PAGE, content_type="text/html") == html_to_text(PAGE)


def test_tsv_is_well_formed_and_tab_safe():
    links = [{"url": "https://x.test/a", "anchor_text": "has\ttab\nand nl", "rel_or_context": ""}]
    tsv = links_to_tsv(links)
    lines = tsv.rstrip("\n").split("\n")
    assert lines[0] == "url\tanchor_text\trel_or_context"
    assert len(lines) == 2
    assert lines[1].count("\t") == 2  # embedded tab/newline neutralised
    assert links_to_tsv([]).rstrip("\n") == "url\tanchor_text\trel_or_context"


def test_bytes_and_str_agree():
    assert extract_links(PAGE, base_url=BASE) == extract_links(
        PAGE.decode("utf-8"), base_url=BASE
    )


def test_runner_writes_the_sidecar_and_leaves_the_md_alone(tmp_path=None):
    """End-to-end through run(), with the network stage stubbed out."""
    import tempfile

    from source_collection import fetch as F

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "sources.txt").write_text(
            f"---\ncitekey: jptest\ntitle: JP year page\nurl: {BASE}\n", encoding="utf-8"
        )

        def stub_direct(entry, url, rl, spn2, raw_dir, *, links=None):
            return (
                html_to_text(PAGE, content_type="text/html", links_out=links,
                             base_url=url, link_context="direct"),
                "live",
                "direct",
            )

        real = F._STAGES["direct"]
        F._STAGES["direct"] = stub_direct
        try:
            F.run(
                sources_path=root / "sources.txt",
                cache_dir=root / "cache",
                raw_dir=root / "raw",
                pipeline=["direct"],
                use_spn2=False,
                enrich=False,
                pending_file=root / "pending.txt",
            )
        finally:
            F._STAGES["direct"] = real

        md = (root / "cache" / "jptest.md").read_text(encoding="utf-8")
        sidecar = (root / "cache" / "jptest.links.tsv").read_text(encoding="utf-8")

    # the cleaned-text file is untouched by the change …
    assert md.startswith("# JP year page\nSource: ")
    assert "abm00002411.pdf" not in md
    assert "links.tsv" not in md
    # … and the href we used to lose is now on disk, next to it
    assert "https://www.dnc.ac.jp/albums/abm.php?d=570&f=abm00002411.pdf" in sidecar
    assert sidecar.splitlines()[0] == "url\tanchor_text\trel_or_context"


def test_no_sidecar_when_a_page_has_no_links():
    import tempfile

    from source_collection import fetch as F

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "sources.txt").write_text(
            "---\ncitekey: nolinks\nurl: https://x.test/plain\n", encoding="utf-8"
        )

        def stub(entry, url, rl, spn2, raw_dir, *, links=None):
            return "plain text, no anchors", "live", "direct"

        real = F._STAGES["direct"]
        F._STAGES["direct"] = stub
        try:
            F.run(sources_path=root / "sources.txt", cache_dir=root / "cache",
                  raw_dir=root / "raw", pipeline=["direct"], use_spn2=False,
                  enrich=False, pending_file=root / "pending.txt")
        finally:
            F._STAGES["direct"] = real

        assert (root / "cache" / "nolinks.md").exists()
        assert not (root / "cache" / "nolinks.links.tsv").exists()


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {fn.__name__}: {exc}")
    print(f"\n{len(fns) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
