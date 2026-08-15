"""Tests for the shared inline-link parser used by the MDL rules."""

from mdlint.links import Link, iter_links, mask_code_spans, mask_links


def test_extracts_links_with_text_target_and_line():
    lines = ["See [docs](guide.md) for more.", "Second [line](other.md)."]

    links = list(iter_links(lines))

    assert links == [
        Link(text="docs", target="guide.md", line=1, is_image=False),
        Link(text="line", target="other.md", line=2, is_image=False),
    ]


def test_marks_image_syntax_as_image():
    links = list(iter_links(["![alt text](img.png)"]))

    assert links == [Link(text="alt text", target="img.png", line=1, is_image=True)]


def test_ignores_links_inside_fenced_code_blocks():
    lines = ["[real](real.md)", "```", "[fake](fake.md)", "```", "[also real](x.md)"]

    links = list(iter_links(lines))

    assert [link.target for link in links] == ["real.md", "x.md"]


def test_ignores_links_inside_inline_code_spans():
    links = list(iter_links(["Use `[not](a.md)` literally, not [this](b.md)"]))

    assert [link.target for link in links] == ["b.md"]


def test_mask_code_spans_preserves_line_length():
    line = "before `code span` after"

    masked = mask_code_spans(line)

    assert len(masked) == len(line)
    assert "code span" not in masked
    assert masked.startswith("before ")
    assert masked.endswith(" after")


def test_mask_links_blanks_link_syntax_but_preserves_length():
    line = "See [docs](guide.md) now"

    masked = mask_links(line)

    assert len(masked) == len(line)
    assert "guide.md" not in masked
    assert masked.startswith("See ")
    assert masked.endswith(" now")


def test_drops_optional_link_title():
    links = list(iter_links(['[docs](guide.md "Guide")']))

    assert links == [Link(text="docs", target="guide.md", line=1, is_image=False)]


def test_mask_code_spans_leaves_unclosed_backtick_runs_untouched():
    line = "`a ``b"

    masked = mask_code_spans(line)

    assert masked == line
    assert len(masked) == len(line)
