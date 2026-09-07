"""MDS01 — the first line of a document should be a top-level heading."""

from mdlint.headings import front_matter_end, iter_headings
from mdlint.rules import Rule, register
from mdlint.violation import Violation

RULE_ID = "MDS01"


def check(file: str, lines: list[str]) -> list[Violation]:
    """Flag a document whose first non-blank line isn't an H1 heading."""
    start = front_matter_end(lines)
    headings = list(iter_headings(lines))
    for lineno, line in enumerate(lines[start:], start=start + 1):
        if line.strip() == "":
            continue
        first = next((h for h in headings if h.line == lineno), None)
        if first is not None and first.level == 1:
            return []
        return [
            Violation(
                file=file,
                line=lineno,
                rule_id=RULE_ID,
                message="first line should be a top-level (H1) heading",
            )
        ]
    return []


register(Rule(id=RULE_ID, name="first-line-heading", check=check))
