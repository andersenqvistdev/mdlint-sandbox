"""Tests for MDS03 — sibling headings must not repeat text."""

from mdlint.rules.md_s03_no_duplicate_siblings import RULE_ID, check


def test_passes_for_unique_siblings():
    lines = ["# Title", "## Alpha", "## Beta"]

    assert check("doc.md", lines) == []


def test_passes_for_same_text_under_different_parents():
    lines = ["# One", "## Overview", "# Two", "## Overview"]

    assert check("doc.md", lines) == []


def test_fails_for_duplicate_sibling_headings():
    lines = ["# Title", "## Alpha", "## Alpha"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].rule_id == RULE_ID
    assert violations[0].line == 3


def test_fails_for_duplicate_top_level_headings():
    lines = ["# Title", "# Title"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].line == 2
