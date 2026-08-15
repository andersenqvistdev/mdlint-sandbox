"""Tests for MDW01 — lines must not end with trailing space characters."""

from mdlint.rules.md_w01_no_trailing_spaces import RULE_ID, check


def test_passes_for_lines_with_no_trailing_whitespace():
    lines = ["# Title", "", "body text"]

    assert check("doc.md", lines) == []


def test_fails_for_a_line_with_a_trailing_space():
    lines = ["body text ", "clean line"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].rule_id == RULE_ID
    assert violations[0].line == 1


def test_fails_for_a_line_with_multiple_trailing_spaces():
    violations = check("doc.md", ["body text   "])

    assert len(violations) == 1
    assert violations[0].line == 1


def test_flags_each_offending_line_independently():
    lines = ["one ", "two", "three  "]

    violations = check("doc.md", lines)

    assert [v.line for v in violations] == [1, 3]


def test_ignores_trailing_tabs():
    assert check("doc.md", ["body text\t"]) == []


def test_empty_document_has_no_violations():
    assert check("doc.md", []) == []
