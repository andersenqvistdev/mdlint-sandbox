"""Tests for the shared ATX heading parser used by the MDS rules."""

from mdlint.headings import Heading, iter_headings


def test_extracts_atx_headings_with_levels_and_lines():
    lines = ["# Title", "body text", "## Section", "### Sub"]

    headings = list(iter_headings(lines))

    assert headings == [
        Heading(level=1, text="Title", line=1),
        Heading(level=2, text="Section", line=3),
        Heading(level=3, text="Sub", line=4),
    ]


def test_strips_trailing_closing_hashes():
    headings = list(iter_headings(["## Section ##"]))

    assert headings == [Heading(level=2, text="Section", line=1)]


def test_ignores_headings_inside_fenced_code_blocks():
    lines = ["# Title", "```", "# not a heading", "```", "## Real"]

    headings = list(iter_headings(lines))

    assert headings == [
        Heading(level=1, text="Title", line=1),
        Heading(level=2, text="Real", line=5),
    ]


def test_requires_space_after_hashes():
    headings = list(iter_headings(["#not-a-heading", "#: also not one"]))

    assert headings == []


def test_shorter_fence_does_not_close_a_longer_opening_fence():
    lines = [
        "# Title",
        "````",
        "# not a heading",
        "```",
        "# still not a heading",
        "````",
        "## Real",
    ]

    headings = list(iter_headings(lines))

    assert headings == [
        Heading(level=1, text="Title", line=1),
        Heading(level=2, text="Real", line=7),
    ]


def test_mismatched_fence_character_does_not_close_the_fence():
    lines = ["# Title", "```", "# not a heading", "~~~", "# still not a heading", "```", "## Real"]

    headings = list(iter_headings(lines))

    assert headings == [
        Heading(level=1, text="Title", line=1),
        Heading(level=2, text="Real", line=7),
    ]


def test_setext_level_one_heading():
    lines = ["Setext title", "============"]

    headings = list(iter_headings(lines))

    assert headings == [Heading(level=1, text="Setext title", line=1)]


def test_setext_level_two_heading():
    lines = ["Setext title", "------------"]

    headings = list(iter_headings(lines))

    assert headings == [Heading(level=2, text="Setext title", line=1)]


def test_setext_heading_preceded_by_blank_line_is_recognized():
    lines = ["intro", "", "Setext title", "============"]

    headings = list(iter_headings(lines))

    assert headings == [Heading(level=1, text="Setext title", line=3)]


def test_bare_thematic_break_with_nothing_above_is_not_a_heading():
    lines = ["Foo", "", "---"]

    headings = list(iter_headings(lines))

    assert headings == []


def test_multiline_paragraph_collapses_into_one_heading_at_first_line():
    lines = ["Line one", "Line two", "========"]

    headings = list(iter_headings(lines))

    assert headings == [Heading(level=1, text="Line one Line two", line=1)]


def test_setext_underline_inside_fenced_code_block_is_ignored():
    lines = ["Title", "=====", "```", "not code", "-----", "```"]

    headings = list(iter_headings(lines))

    assert headings == [Heading(level=1, text="Title", line=1)]


def test_table_delimiter_row_is_not_mistaken_for_underline():
    lines = ["| a | b |", "| --- | --- |", "| 1 | 2 |"]

    headings = list(iter_headings(lines))

    assert headings == []


def test_list_item_after_paragraph_text_is_not_treated_as_underline():
    lines = ["Paragraph text", "- item"]

    headings = list(iter_headings(lines))

    assert headings == []
