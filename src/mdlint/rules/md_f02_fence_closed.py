"""MDF02 — every fenced code block must be closed.

A fence left open swallows the rest of the document into a single code
block, silently hiding whatever headings, lists, or links follow it.
"""

from mdlint.fences import iter_fence_blocks
from mdlint.rules import Rule, register
from mdlint.violation import Violation

RULE_ID = "MDF02"


def check(file: str, lines: list[str]) -> list[Violation]:
    """Flag fences that are never closed before the end of the document."""
    violations = []
    for block in iter_fence_blocks(lines):
        if block.close_line is not None:
            continue
        violations.append(
            Violation(
                file=file,
                line=block.open_line,
                rule_id=RULE_ID,
                message="fenced code block is never closed",
            )
        )
    return violations


register(Rule(id=RULE_ID, name="fence-closed", check=check))
