"""Tests for MDS01 — first line should be a top-level heading."""

from mdlint.rules.md_s01_first_line_heading import RULE_ID, check


def test_passes_when_first_line_is_h1():
    lines = ["# Title", "", "body"]

    assert check("doc.md", lines) == []


def test_passes_when_h1_follows_leading_blank_lines():
    lines = ["", "  ", "# Title"]

    assert check("doc.md", lines) == []


def test_fails_when_first_line_is_not_a_heading():
    lines = ["Some intro text", "", "# Title"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].rule_id == RULE_ID
    assert violations[0].line == 1


def test_fails_when_first_heading_is_not_top_level():
    lines = ["## Section", "body"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].line == 1


def test_empty_document_has_no_violations():
    assert check("doc.md", []) == []


def test_document_with_only_blank_lines_has_no_violations():
    assert check("doc.md", ["", "   ", "\t"]) == []


def test_passes_when_first_line_h1_has_trailing_closing_hashes():
    lines = ["# Title #", "body"]

    assert check("doc.md", lines) == []
