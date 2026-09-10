"""MDW04 — a document must end with exactly one trailing newline.

The CLI reads files with ``text.split("\\n")`` rather than
``str.splitlines()``, so ``"\\n".join(lines)`` reconstructs the original text
exactly. That round trip is what lets this rule tell "no trailing newline"
apart from "one trailing newline" apart from "several trailing newlines" —
information plain ``splitlines()`` output discards. Every other rule in this
package only cares about line content, so this is the one place the
distinction matters.
"""

from mdlint.rules import Rule, register
from mdlint.violation import Violation

RULE_ID = "MDW04"


def check(file: str, lines: list[str]) -> list[Violation]:
    """Flag documents missing a final newline or ending in extra blank lines."""
    text = "\n".join(lines)
    if text == "":
        return []
    if not text.endswith("\n"):
        return [
            Violation(
                file=file,
                line=len(lines),
                rule_id=RULE_ID,
                message="file does not end with a newline",
            )
        ]
    if text.endswith("\n\n"):
        return [
            Violation(
                file=file,
                line=len(lines) - 1,
                rule_id=RULE_ID,
                message="file ends with extra blank line(s); expected a single trailing newline",
            )
        ]
    return []


def fix(lines: list[str]) -> list[str]:
    """Normalize the document to end with exactly one trailing newline."""
    text = "\n".join(lines)
    if text == "" or text.endswith("\n") and not text.endswith("\n\n"):
        return lines
    if not text.endswith("\n"):
        return [*lines, ""]
    trimmed = list(lines)
    while len(trimmed) >= 2 and trimmed[-1] == "" and trimmed[-2] == "":
        trimmed.pop()
    return trimmed


register(Rule(id=RULE_ID, name="final-newline", check=check, fix=fix))
