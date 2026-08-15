"""Tests for MDW04 — a document must end with exactly one trailing newline.

``lines`` mirrors the CLI's ``text.split("\\n")`` output, not
``str.splitlines()``: joining fixtures with "\\n" must reconstruct the exact
text under test, since that round trip is how the rule tells a missing
newline apart from one trailing newline apart from several.
"""

from mdlint.rules.md_w04_final_newline import RULE_ID, check


def test_passes_for_a_single_trailing_newline():
    # "# Title\n\n## Section\n"
    lines = ["# Title", "", "## Section", ""]

    assert check("doc.md", lines) == []


def test_fails_when_the_file_has_no_trailing_newline():
    # "# Title"
    lines = ["# Title"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].rule_id == RULE_ID
    assert violations[0].line == 1


def test_fails_when_a_multiline_file_has_no_trailing_newline():
    # "# Title\nbody"
    lines = ["# Title", "body"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].line == 2


def test_fails_when_the_file_ends_with_an_extra_blank_line():
    # "# Title\n\n"
    lines = ["# Title", "", ""]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].line == 2


def test_fails_when_the_file_ends_with_several_extra_blank_lines():
    # "# Title\n\n\n"
    lines = ["# Title", "", "", ""]

    violations = check("doc.md", lines)

    assert len(violations) == 1


def test_empty_file_has_no_violations():
    assert check("doc.md", [""]) == []


def test_file_that_is_only_a_newline_has_no_violations():
    # "\n"
    assert check("doc.md", ["", ""]) == []
