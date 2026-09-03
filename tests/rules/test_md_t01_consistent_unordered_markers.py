"""Tests for MDT01 — unordered list markers must be consistent."""

import mdlint.rules.md_t01_consistent_unordered_markers as md_t01_module
from mdlint.rules.md_t01_consistent_unordered_markers import RULE_ID, check, fix


def test_fix_skips_an_item_whose_marker_span_cannot_be_located(monkeypatch):
    """Guards the defensive branch in fix() against a stale/mismatched span helper."""
    lines = ["- one", "* two"]
    monkeypatch.setattr(md_t01_module, "unordered_marker_span", lambda line: None)

    assert fix(lines) == lines


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


def test_flags_a_nested_item_using_a_different_marker_than_the_top_level():
    lines = ["- one", "  * nested"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].line == 2


def test_ignores_thematic_breaks_and_fenced_code():
    lines = ["- one", "---", "```", "* two", "```", "- three"]

    assert check("doc.md", lines) == []


def test_fix_rewrites_inconsistent_markers_to_match_the_first():
    lines = ["- one", "* two", "+ three"]

    fixed = fix(lines)

    assert fixed == ["- one", "- two", "- three"]
    assert check("doc.md", fixed) == []


def test_fix_preserves_indentation_and_trailing_content():
    lines = ["- one", "  * nested item"]

    assert fix(lines) == ["- one", "  - nested item"]


def test_fix_is_a_noop_when_already_consistent():
    lines = ["- one", "- two"]

    assert fix(lines) == lines


def test_fix_is_a_noop_for_a_single_item():
    assert fix(["* only item"]) == ["* only item"]
