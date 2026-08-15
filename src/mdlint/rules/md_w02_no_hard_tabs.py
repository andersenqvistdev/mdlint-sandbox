"""MDW02 — lines must not contain hard tab characters."""

from mdlint.rules import Rule, register
from mdlint.violation import Violation

RULE_ID = "MDW02"


def check(file: str, lines: list[str]) -> list[Violation]:
    """Flag lines containing a hard tab character."""
    violations = []
    for lineno, line in enumerate(lines, start=1):
        if "\t" in line:
            violations.append(
                Violation(
                    file=file,
                    line=lineno,
                    rule_id=RULE_ID,
                    message="line contains a hard tab; use spaces for indentation",
                )
            )
    return violations


register(Rule(id=RULE_ID, name="no-hard-tabs", check=check))
