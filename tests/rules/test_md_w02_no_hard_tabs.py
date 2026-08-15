"""Tests for MDW02 — lines must not contain hard tab characters."""

from mdlint.rules.md_w02_no_hard_tabs import RULE_ID, check


def test_passes_for_lines_with_no_tabs():
    lines = ["# Title", "", "    indented with spaces"]

    assert check("doc.md", lines) == []


def test_fails_for_a_leading_tab():
    violations = check("doc.md", ["\tindented with a tab"])

    assert len(violations) == 1
    assert violations[0].rule_id == RULE_ID
    assert violations[0].line == 1


def test_fails_for_a_tab_anywhere_in_the_line():
    violations = check("doc.md", ["col1\tcol2"])

    assert len(violations) == 1
    assert violations[0].line == 1


def test_flags_each_offending_line_independently():
    lines = ["\tone", "two", "\tthree"]

    violations = check("doc.md", lines)

    assert [v.line for v in violations] == [1, 3]


def test_empty_document_has_no_violations():
    assert check("doc.md", []) == []
