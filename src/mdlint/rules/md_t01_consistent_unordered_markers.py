"""MDT01 — unordered list markers must be consistent within a document.

The first bullet marker (``-``, ``*``, or ``+``) encountered establishes the
file's expected marker; every later bullet item using a different marker is
flagged, regardless of which list or nesting level it belongs to.
"""

from mdlint.lists import iter_unordered_list_items, unordered_marker_span
from mdlint.rules import Rule, register
from mdlint.violation import Violation

RULE_ID = "MDT01"


def check(file: str, lines: list[str]) -> list[Violation]:
    """Flag unordered list markers that differ from the file's first marker."""
    violations = []
    expected_marker = None
    for item in iter_unordered_list_items(lines):
        if expected_marker is None:
            expected_marker = item.marker
            continue
        if item.marker != expected_marker:
            violations.append(
                Violation(
                    file=file,
                    line=item.line,
                    rule_id=RULE_ID,
                    message=(
                        f"list marker {item.marker!r} is inconsistent; "
                        f"file uses {expected_marker!r}"
                    ),
                )
            )
    return violations


def fix(lines: list[str]) -> list[str]:
    """Rewrite every bullet marker to match the file's first marker."""
    items = list(iter_unordered_list_items(lines))
    if len(items) < 2:
        return lines
    expected_marker = items[0].marker
    fixed = list(lines)
    for item in items[1:]:
        if item.marker == expected_marker:
            continue
        span = unordered_marker_span(fixed[item.line - 1])
        if span is None:
            continue
        start, end = span
        line = fixed[item.line - 1]
        fixed[item.line - 1] = line[:start] + expected_marker + line[end:]
    return fixed


register(Rule(id=RULE_ID, name="consistent-unordered-markers", check=check, fix=fix))
