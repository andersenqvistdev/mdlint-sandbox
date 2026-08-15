"""MDT02 — ordered list numbers must increase sequentially by one.

Each indentation level is tracked independently so nested ordered lists get
their own sequence. A list may start at any number, but every following item
at the same indent must be exactly one more than the previous. Blank lines
inside a list don't break the sequence; any other non-list content does, so a
later, unrelated list is free to start its own count.
"""

from mdlint.lists import iter_ordered_list_items, ordered_number_span
from mdlint.rules import Rule, register
from mdlint.violation import Violation

RULE_ID = "MDT02"


def check(file: str, lines: list[str]) -> list[Violation]:
    """Flag ordered list items whose number isn't one more than the previous."""
    violations = []
    expected_by_indent: dict[int, int] = {}
    item_by_line = {item.line: item for item in iter_ordered_list_items(lines)}

    for lineno, raw_line in enumerate(lines, start=1):
        item = item_by_line.get(lineno)
        if item is not None:
            expected = expected_by_indent.get(item.indent)
            if expected is not None and item.number != expected:
                violations.append(
                    Violation(
                        file=file,
                        line=item.line,
                        rule_id=RULE_ID,
                        message=(
                            f"ordered list item is numbered {item.number}; "
                            f"expected {expected} to continue the sequence"
                        ),
                    )
                )
            expected_by_indent[item.indent] = item.number + 1
            for indent in [i for i in expected_by_indent if i > item.indent]:
                del expected_by_indent[indent]
        elif raw_line.strip() == "":
            continue
        else:
            expected_by_indent.clear()
    return violations


def fix(lines: list[str]) -> list[str]:
    """Renumber ordered list items so each sequence increases by one."""
    fixed = list(lines)
    expected_by_indent: dict[int, int] = {}
    item_by_line = {item.line: item for item in iter_ordered_list_items(lines)}

    for lineno, raw_line in enumerate(lines, start=1):
        item = item_by_line.get(lineno)
        if item is not None:
            expected = expected_by_indent.get(item.indent, item.number)
            if item.number != expected:
                span = ordered_number_span(fixed[lineno - 1])
                if span is not None:
                    start, end = span
                    line = fixed[lineno - 1]
                    fixed[lineno - 1] = line[:start] + str(expected) + line[end:]
            expected_by_indent[item.indent] = expected + 1
            for indent in [i for i in expected_by_indent if i > item.indent]:
                del expected_by_indent[indent]
        elif raw_line.strip() == "":
            continue
        else:
            expected_by_indent.clear()
    return fixed


register(Rule(id=RULE_ID, name="ordered-list-sequential", check=check, fix=fix))
