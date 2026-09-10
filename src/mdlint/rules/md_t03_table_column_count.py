r"""MDT03 — every row in a table must have as many columns as the header.

A table is a header row immediately followed by a delimiter row (cells made
only of ``-``, and optional ``:`` for alignment) whose cell count matches the
header's — per GFM, a delimiter row with a different cell count doesn't form
a table at all, so that line pair is left alone rather than misread as a
table with a mismatched second row. Once a table is found, the header's
column count is the expected count for every following row until a blank
line, non-pipe line, or end of file closes the table. Fenced code blocks are
skipped so pipes inside a fence aren't mistaken for a table; fence
boundaries are detected via :func:`mdlint.fences.fenced_line_numbers` rather
than a same-marker toggle, which desyncs (and starts linting fence content
as a table) as soon as a fence contains a line opening with the other
marker character.

Per GFM, a ``|`` inside a backtick code span (or escaped with ``\|``) is cell
content, not a column separator — ``_split_row`` walks the line rather than
regex-splitting on every ``|`` so a cell like `` `a|b` `` isn't miscounted as
two columns. ``\\`` (an escaped backslash) is consumed as its own two-char
literal so a following ``|`` is left as a real separator, rather than being
swallowed as if it were escaped by the leftover backslash.
"""

import re

from mdlint.fences import fenced_line_numbers
from mdlint.rules import Rule, register
from mdlint.violation import Violation

RULE_ID = "MDT03"

_BACKTICK_RUN_RE = re.compile(r"`+")
_DELIMITER_CELL_RE = re.compile(r"^:?-+:?$")


def _find_backtick_closer(text: str, start: int, run_length: int) -> int | None:
    """Return the index just past the next backtick run of run_length, or None.

    Per CommonMark, a code span's closer is the *first* backtick run after
    the opener whose length equals the opener's — a shorter or longer run
    doesn't close it and is skipped over.
    """
    index = start
    length = len(text)
    while index < length:
        if text[index] != "`":
            index += 1
            continue
        run_end = _BACKTICK_RUN_RE.match(text, index).end()
        if run_end - index == run_length:
            return run_end
        index = run_end
    return None


def _split_row(line: str) -> list[str]:
    """Split a table row into cells on ``|`` outside code spans/escapes."""
    stripped = line.strip()
    length = len(stripped)
    cells: list[str] = []
    current: list[str] = []
    index = 0
    while index < length:
        char = stripped[index]
        if char == "\\" and index + 1 < length and stripped[index + 1] in "\\|":
            current.append(stripped[index : index + 2])
            index += 2
            continue
        if char == "`":
            run_end = _BACKTICK_RUN_RE.match(stripped, index).end()
            run_length = run_end - index
            closer = _find_backtick_closer(stripped, run_end, run_length)
            end = closer if closer is not None else run_end
            current.append(stripped[index:end])
            index = end
            continue
        if char == "|":
            cells.append("".join(current))
            current = []
            index += 1
            continue
        current.append(char)
        index += 1
    cells.append("".join(current))
    if cells and cells[0] == "":
        cells = cells[1:]
    if cells and cells[-1] == "":
        cells = cells[:-1]
    return cells


def _is_delimiter_row(cells: list[str], column_count: int) -> bool:
    return (
        bool(cells)
        and len(cells) == column_count
        and all(_DELIMITER_CELL_RE.match(cell.strip()) for cell in cells)
    )


def check(file: str, lines: list[str]) -> list[Violation]:
    """Flag table rows whose column count doesn't match the header row."""
    violations = []
    fenced_lines = fenced_line_numbers(lines)
    total = len(lines)
    index = 0
    while index < total:
        raw_line = lines[index]
        if index + 1 in fenced_lines:
            index += 1
            continue

        column_count = len(_split_row(raw_line))
        is_table_start = (
            "|" in raw_line
            and index + 1 < total
            and "|" in lines[index + 1]
            and _is_delimiter_row(_split_row(lines[index + 1]), column_count)
        )
        if is_table_start:
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
