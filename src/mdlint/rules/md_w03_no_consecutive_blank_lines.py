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


def fix(lines: list[str]) -> list[str]:
    """Collapse each run of consecutive blank lines down to its first line.

    The trailing "" end-of-file marker (see the module docstring) is
    preserved as-is rather than treated as part of a blank run, so fixing
    never changes whether the file ends with a final newline.
    """
    has_eof_marker = bool(lines) and lines[-1] == ""
    fixed = []
    in_blank_run = False
    for line in _content_lines(lines):
        blank = line.strip() == ""
        if blank and in_blank_run:
            continue
        in_blank_run = blank
        fixed.append(line)
    if has_eof_marker:
        fixed.append("")
    return fixed


register(Rule(id=RULE_ID, name="no-consecutive-blank-lines", check=check, fix=fix))
