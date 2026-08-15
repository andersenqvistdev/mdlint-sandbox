"""MDW03 — documents must not contain consecutive blank lines.

``lines`` follows the CLI's ``split("\\n")`` convention (see
``md_w04_final_newline``): when the source text ends with a newline, that
split appends one trailing empty string marking "end of file", not a real
blank line. That marker is trimmed before scanning so a normally-terminated
file isn't misread as ending in an extra blank line.
"""

from mdlint.rules import Rule, register
from mdlint.violation import Violation

RULE_ID = "MDW03"


def _content_lines(lines: list[str]) -> list[str]:
    if lines and lines[-1] == "":
        return lines[:-1]
    return lines


def check(file: str, lines: list[str]) -> list[Violation]:
    """Flag each blank line beyond the first in a run of consecutive blank lines."""
    violations = []
    run_length = 0
    for lineno, line in enumerate(_content_lines(lines), start=1):
        if line.strip() == "":
            run_length += 1
            if run_length > 1:
                violations.append(
                    Violation(
                        file=file,
                        line=lineno,
                        rule_id=RULE_ID,
                        message="consecutive blank lines; collapse to a single blank line",
                    )
                )
        else:
            run_length = 0
    return violations


register(Rule(id=RULE_ID, name="no-consecutive-blank-lines", check=check))
