"""Tests for MDW03 — documents must not contain consecutive blank lines.

Fixtures end each non-empty document with a trailing "" element, mirroring
the CLI's split("\\n") output for a file that ends with a newline (see
md_w04_final_newline). That trailing marker must never itself be counted as
a blank line.
"""

from mdlint.rules.md_w03_no_consecutive_blank_lines import RULE_ID, check


def test_passes_for_single_blank_lines_between_sections():
    lines = ["# Title", "", "## Section", "", "body", ""]

    assert check("doc.md", lines) == []


def test_fails_for_two_consecutive_blank_lines():
    lines = ["# Title", "", "", "## Section", ""]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].rule_id == RULE_ID
    assert violations[0].line == 3


def test_fails_for_each_blank_line_beyond_the_first_in_a_run():
    lines = ["# Title", "", "", "", "body", ""]

    violations = check("doc.md", lines)

    assert [v.line for v in violations] == [3, 4]


def test_whitespace_only_lines_count_as_blank():
    lines = ["# Title", "", "   ", "body", ""]

    violations = check("doc.md", lines)

    assert [v.line for v in violations] == [3]


def test_trailing_newline_marker_is_not_a_blank_line():
    lines = ["# Title", "", "body", ""]

    assert check("doc.md", lines) == []


def test_a_real_trailing_blank_line_is_not_flagged_alone():
    lines = ["# Title", "body", "", ""]

    assert check("doc.md", lines) == []


def test_empty_document_has_no_violations():
    assert check("doc.md", [""]) == []


def test_file_without_a_trailing_newline_marker_is_still_checked():
    lines = ["# Title", "", "", "body"]

    violations = check("doc.md", lines)

    assert [v.line for v in violations] == [3]
