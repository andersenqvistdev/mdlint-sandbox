"""MDS02 — heading levels must not skip a level when increasing.

Dropping back down (e.g. H3 followed by H1) is always fine; only jumps that
skip a level on the way up are flagged.
"""

from mdlint.headings import iter_headings
from mdlint.rules import Rule, register
from mdlint.violation import Violation

RULE_ID = "MDS02"


def check(file: str, lines: list[str]) -> list[Violation]:
    """Flag headings that increase by more than one level from the previous heading."""
    violations = []
    previous_level = None
    for heading in iter_headings(lines):
        if previous_level is not None and heading.level > previous_level + 1:
            violations.append(
                Violation(
                    file=file,
                    line=heading.line,
                    rule_id=RULE_ID,
                    message=(
                        f"heading level jumps from H{previous_level} to "
                        f"H{heading.level}; increment by one level at a time"
                    ),
                )
            )
        previous_level = heading.level
    return violations


register(Rule(id=RULE_ID, name="heading-increment", check=check))
