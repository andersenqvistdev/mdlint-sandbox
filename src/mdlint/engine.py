"""Runs every registered rule against a document's lines."""

from mdlint.rules import Rule, all_rules
from mdlint.violation import Violation


def lint_lines(file: str, lines: list[str], rules: list[Rule] | None = None) -> list[Violation]:
    """Run the given rules (default: every registered rule) against lines.

    Violations are sorted by line then rule id.
    """
    if rules is None:
        rules = all_rules()
    violations: list[Violation] = []
    for rule in rules:
        violations.extend(rule.check(file, lines))
    return sorted(violations, key=lambda v: (v.line, v.rule_id))


def apply_fixes(lines: list[str], rules: list[Rule] | None = None) -> list[str]:
    """Apply every fixable rule's fix in turn, returning the resulting lines.

    Rules without a fix are left for ``lint_lines`` to report as usual.
    """
    if rules is None:
        rules = all_rules()
    fixed = lines
    for rule in rules:
        if rule.fix is not None:
            fixed = rule.fix(fixed)
    return fixed
