"""MDW01 — lines must not end with trailing space characters."""

import re

from mdlint.rules import Rule, register
from mdlint.violation import Violation

RULE_ID = "MDW01"

_TRAILING_SPACE_RE = re.compile(r" +$")


def check(file: str, lines: list[str]) -> list[Violation]:
    """Flag lines that end with one or more trailing space characters."""
    violations = []
    for lineno, line in enumerate(lines, start=1):
        if _TRAILING_SPACE_RE.search(line):
            violations.append(
                Violation(
                    file=file,
                    line=lineno,
                    rule_id=RULE_ID,
                    message="line has trailing space(s)",
                )
            )
    return violations


register(Rule(id=RULE_ID, name="no-trailing-spaces", check=check))
