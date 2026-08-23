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
