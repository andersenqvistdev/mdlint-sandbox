"""MDS03 — sibling headings (same parent, same level) must not repeat text.

Headings with the same text under *different* parents are unrelated and are
not flagged; only repeats within the same section are duplicates.
"""

from mdlint.headings import iter_headings
from mdlint.rules import Rule, register
from mdlint.violation import Violation

RULE_ID = "MDS03"


def check(file: str, lines: list[str]) -> list[Violation]:
    """Flag a heading whose text repeats an earlier sibling under the same parent."""
    violations = []
    ancestors: list[tuple[int, str]] = []
    children_seen: dict[tuple[tuple[int, str], ...], set[str]] = {}
    for heading in iter_headings(lines):
        while ancestors and ancestors[-1][0] >= heading.level:
            ancestors.pop()
        parent_key = tuple(ancestors)
        siblings = children_seen.setdefault(parent_key, set())
        if heading.text in siblings:
            violations.append(
                Violation(
                    file=file,
                    line=heading.line,
                    rule_id=RULE_ID,
                    message=f"duplicate sibling heading: {heading.text!r}",
                )
            )
        else:
            siblings.add(heading.text)
        ancestors.append((heading.level, heading.text))
    return violations


register(Rule(id=RULE_ID, name="no-duplicate-siblings", check=check))
