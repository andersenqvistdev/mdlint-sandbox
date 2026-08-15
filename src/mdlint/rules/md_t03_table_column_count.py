"""MDT03 — every row in a table must have as many columns as the header.

A table is a header row immediately followed by a delimiter row (cells made
only of ``-``, and optional ``:`` for alignment). Once a table is found, the
header's column count is the expected count for every following row until a
blank line, non-pipe line, or end of file closes the table. Fenced code
blocks are skipped so pipes inside a fence aren't mistaken for a table.
"""

import re

from mdlint.rules import Rule, register
from mdlint.violation import Violation

RULE_ID = "MDT03"

_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_PIPE_SPLIT_RE = re.compile(r"(?<!\\)\|")
_DELIMITER_CELL_RE = re.compile(r"^:?-+:?$")


def _split_row(line: str) -> list[str]:
    cells = _PIPE_SPLIT_RE.split(line.strip())
    if cells and cells[0] == "":
        cells = cells[1:]
    if cells and cells[-1] == "":
        cells = cells[:-1]
    return cells


def _is_delimiter_row(cells: list[str]) -> bool:
    return bool(cells) and all(_DELIMITER_CELL_RE.match(cell.strip()) for cell in cells)


def check(file: str, lines: list[str]) -> list[Violation]:
    """Flag table rows whose column count doesn't match the header row."""
    violations = []
    fence_char: str | None = None
    total = len(lines)
    index = 0
    while index < total:
        raw_line = lines[index]
        fence_match = _FENCE_RE.match(raw_line)
        if fence_match:
            marker_char = fence_match.group(1)[0]
            fence_char = None if fence_char == marker_char else marker_char
            index += 1
            continue
        if fence_char is not None:
            index += 1
            continue

        is_table_start = (
            "|" in raw_line
            and index + 1 < total
            and "|" in lines[index + 1]
            and _is_delimiter_row(_split_row(lines[index + 1]))
        )
        if is_table_start:
            column_count = len(_split_row(raw_line))
            body_index = index + 2
            while (
                body_index < total and lines[body_index].strip() != "" and "|" in lines[body_index]
            ):
                row_cells = _split_row(lines[body_index])
                if len(row_cells) != column_count:
                    violations.append(
                        Violation(
                            file=file,
                            line=body_index + 1,
                            rule_id=RULE_ID,
                            message=(
                                f"table row has {len(row_cells)} column(s); "
                                f"expected {column_count} to match the header"
                            ),
                        )
                    )
                body_index += 1
            index = body_index
            continue

        index += 1
    return violations


register(Rule(id=RULE_ID, name="table-column-count", check=check))
