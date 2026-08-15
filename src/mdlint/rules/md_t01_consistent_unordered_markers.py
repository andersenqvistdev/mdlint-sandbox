"""MDT01 — unordered list markers must be consistent within a document.

The first bullet marker (``-``, ``*``, or ``+``) encountered establishes the
file's expected marker; every later bullet item using a different marker is
flagged, regardless of which list or nesting level it belongs to.
"""

from mdlint.lists import iter_unordered_list_items
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


register(Rule(id=RULE_ID, name="consistent-unordered-markers", check=check))
