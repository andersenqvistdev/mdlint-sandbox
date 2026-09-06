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


def test_closing_fence_with_an_info_string_does_not_close_the_fence():
    # CommonMark requires a closing fence to carry no info string; a line
    # like "```bash" after an already-open fence is just more fence content,
    # not a valid closer, so "### C" stays hidden inside the (still-open)
    # fence rather than surfacing as a heading.
    lines = ["# A", "```", "bash", "```bash", "### C"]

    headings = list(iter_headings(lines))

    assert headings == [Heading(level=1, text="A", line=1)]


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


def test_yaml_front_matter_closing_delimiter_is_not_a_phantom_setext_heading():
    # Without front-matter awareness, the closing "---" reads as a setext
    # underline for "tags: [a, b]", yielding a bogus H2 that confuses
    # MDS02 (a false level to jump from) and MDS03 (a false sibling).
    lines = ["---", "title: Example", "tags: [a, b]", "---", "", "# Title"]

    headings = list(iter_headings(lines))

    assert headings == [Heading(level=1, text="Title", line=6)]


def test_toml_front_matter_closing_delimiter_is_not_a_phantom_setext_heading():
    lines = ["+++", 'title = "Example"', "+++", "# Title"]

    headings = list(iter_headings(lines))

    assert headings == [Heading(level=1, text="Title", line=4)]


def test_unterminated_front_matter_is_scanned_normally():
    # No closing "---" — this isn't front matter, so its lines are still
    # scanned like any other content.
    lines = ["---", "title: Example", "# Title"]

    headings = list(iter_headings(lines))

    assert headings == [Heading(level=1, text="Title", line=3)]


def test_front_matter_delimiter_must_be_the_literal_first_line():
    # A "---" preceded by a blank line doesn't qualify as front matter
    # (Jekyll/Hugo require it to open the file), so its "---" lines are
    # scanned normally — including the closing delimiter reading as a
    # setext underline for the preceding text, same as any other document.
    lines = ["", "---", "title: Example", "---", "# Title"]

    headings = list(iter_headings(lines))

    assert headings == [
        Heading(level=2, text="title: Example", line=3),
        Heading(level=1, text="Title", line=5),
    ]
