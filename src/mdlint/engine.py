"""Runs every registered rule against a document's lines."""

from mdlint.rules import all_rules
from mdlint.violation import Violation


def lint_lines(file: str, lines: list[str]) -> list[Violation]:
    """Run every registered rule against lines, sorted by line then rule id."""
    violations: list[Violation] = []
    for rule in all_rules():
        violations.extend(rule.check(file, lines))
    return sorted(violations, key=lambda v: (v.line, v.rule_id))
