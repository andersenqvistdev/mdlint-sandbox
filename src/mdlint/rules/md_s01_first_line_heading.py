"""MDS01 — the first line of a document should be a top-level heading."""

from mdlint.headings import iter_headings
from mdlint.rules import Rule, register
from mdlint.violation import Violation

RULE_ID = "MDS01"

_FRONT_MATTER_DELIMS = ("---", "+++")


def _skip_front_matter(lines: list[str]) -> int:
    """Return the index to resume scanning at, past a leading front-matter block.

    YAML (---) and TOML (+++) front matter must open on the document's literal
    first line to count; an unterminated block is left alone so the original
    line is still checked (and flagged) rather than silently skipped.
    """
    if not lines:
        return 0
    delim = lines[0].strip()
    if delim not in _FRONT_MATTER_DELIMS:
        return 0
    closing = next((i for i in range(1, len(lines)) if lines[i].strip() == delim), None)
    return closing + 1 if closing is not None else 0


def check(file: str, lines: list[str]) -> list[Violation]:
    """Flag a document whose first non-blank line isn't an H1 heading."""
    if lines and lines[0].startswith("\ufeff"):
        lines = [lines[0][1:], *lines[1:]]
    start = _skip_front_matter(lines)
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
