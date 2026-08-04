"""Tests for MDS02 — heading levels must not skip a level when increasing."""

from mdlint.rules.md_s02_heading_increment import RULE_ID, check


def test_passes_for_sequential_increments():
    lines = ["# Title", "## Section", "### Sub"]

    assert check("doc.md", lines) == []


def test_passes_when_dropping_back_down_levels():
    lines = ["# Title", "## Section", "### Sub", "# Next Title", "## Section"]

    assert check("doc.md", lines) == []


def test_fails_when_a_level_is_skipped():
    lines = ["# Title", "### Too deep"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].rule_id == RULE_ID
    assert violations[0].line == 2


def test_first_heading_alone_never_violates():
    assert check("doc.md", ["### Only heading"]) == []
