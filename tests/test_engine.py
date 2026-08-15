"""Tests for the rule engine that aggregates every registered rule."""

from mdlint.engine import lint_lines
from mdlint.rules import all_rules


def test_registers_all_three_structure_rules():
    ids = {rule.id for rule in all_rules()}

    assert {"MDS01", "MDS02", "MDS03"} <= ids


def test_registers_all_three_link_rules():
    ids = {rule.id for rule in all_rules()}

    assert {"MDL01", "MDL02", "MDL03"} <= ids


def test_clean_document_has_no_violations():
    lines = ["# Title", "", "## Section"]

    assert lint_lines("doc.md", lines) == []


def test_aggregates_violations_from_multiple_rules_sorted_by_line():
    lines = ["Not a heading", "# Title", "### Too deep"]

    violations = lint_lines("doc.md", lines)

    assert [v.rule_id for v in violations] == ["MDS01", "MDS02"]
    assert [v.line for v in violations] == [1, 3]
    assert all(v.file == "doc.md" for v in violations)
