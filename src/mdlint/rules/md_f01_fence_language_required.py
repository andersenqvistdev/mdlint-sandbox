"""MDF01 — every fenced code block must declare a language.

A fence opened with a bare ```` ``` ```` gives readers and syntax
highlighters nothing to go on; the info string (e.g. ```` ```python ````)
should name the language.
"""

from mdlint.fences import iter_fence_blocks
from mdlint.rules import Rule, register
from mdlint.violation import Violation

RULE_ID = "MDF01"


def check(file: str, lines: list[str]) -> list[Violation]:
    """Flag fences whose opening line has no language in its info string."""
    violations = []
    for block in iter_fence_blocks(lines):
        if block.info:
            continue
        violations.append(
            Violation(
                file=file,
                line=block.open_line,
                rule_id=RULE_ID,
                message="fenced code block does not declare a language",
            )
        )
    return violations


register(Rule(id=RULE_ID, name="fence-language-required", check=check))
