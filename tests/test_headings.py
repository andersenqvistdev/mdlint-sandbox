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


def test_ignores_headings_inside_tilde_fenced_code_blocks():
    lines = ["# Title", "~~~", "# not a heading", "~~~", "## Real"]

    headings = list(iter_headings(lines))

    assert headings == [
        Heading(level=1, text="Title", line=1),
        Heading(level=2, text="Real", line=5),
    ]


def test_backtick_and_tilde_fences_do_not_close_each_other():
    # A ``` fence stays open across a ~~~ line (and vice versa): only a
    # matching fence character closes it.
    lines = ["# Title", "```", "~~~", "# not a heading", "```", "## Real"]

    headings = list(iter_headings(lines))

    assert headings == [
        Heading(level=1, text="Title", line=1),
        Heading(level=2, text="Real", line=6),
    ]


def test_requires_space_after_hashes():
    headings = list(iter_headings(["#not-a-heading", "#: also not one"]))

    assert headings == []
