"""Tests for MDT01 — unordered list markers must be consistent."""

from mdlint.rules.md_t01_consistent_unordered_markers import RULE_ID, check


def test_passes_when_all_items_use_the_same_marker():
    lines = ["- one", "- two", "- three"]

    assert check("doc.md", lines) == []


def test_passes_for_a_single_item():
    assert check("doc.md", ["* only item"]) == []


def test_document_with_no_list_items_has_no_violations():
    assert check("doc.md", ["plain text", "", "more text"]) == []


def test_fails_when_a_later_item_uses_a_different_marker():
    lines = ["- one", "* two"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].rule_id == RULE_ID
    assert violations[0].line == 2


def test_flags_each_inconsistent_marker_independently():
    lines = ["- one", "* two", "+ three"]

    violations = check("doc.md", lines)

    assert [v.line for v in violations] == [2, 3]


def test_ignores_thematic_breaks_and_fenced_code():
    lines = ["- one", "---", "```", "* two", "```", "- three"]

    assert check("doc.md", lines) == []
