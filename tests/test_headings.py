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


def test_ignores_hashes_indented_four_or_more_spaces():
    # Four-plus spaces of indentation makes a line an indented code block per
    # CommonMark, so a leading "#" there is code, not a heading.
    lines = ["# Title", "    #### indented, not a heading", "## Section"]

    headings = list(iter_headings(lines))

    assert headings == [
        Heading(level=1, text="Title", line=1),
        Heading(level=2, text="Section", line=3),
    ]
