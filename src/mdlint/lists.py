"""List item extraction shared by the list rules (MDT family).

Fenced code blocks are skipped so that a line like ``- not a list item``
inside a ``` fence isn't mistaken for a list item.
"""

import re
from collections.abc import Iterator
from dataclasses import dataclass

_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_UNORDERED_RE = re.compile(r"^( {0,3})([-*+])(\s+)\S")
_ORDERED_RE = re.compile(r"^( {0,3})(\d{1,9})([.)])(\s+)\S")


@dataclass(frozen=True)
class UnorderedListItem:
    """A single unordered (bullet) list item found in a document."""

    marker: str
    line: int


@dataclass(frozen=True)
class OrderedListItem:
    """A single ordered (numbered) list item found in a document."""

    number: int
    indent: int
    line: int


def iter_unordered_list_items(lines: list[str]) -> Iterator[UnorderedListItem]:
    """Yield an UnorderedListItem for each bullet list item in lines, in order.

    A bare thematic break (e.g. ``---`` or ``***``) has no content after the
    marker and is not matched.
    """
    fence_char: str | None = None
    for lineno, raw_line in enumerate(lines, start=1):
        fence_match = _FENCE_RE.match(raw_line)
        if fence_match:
            marker_char = fence_match.group(1)[0]
            fence_char = None if fence_char == marker_char else marker_char
            continue
        if fence_char is not None:
            continue
        match = _UNORDERED_RE.match(raw_line)
        if not match:
            continue
        yield UnorderedListItem(marker=match.group(2), line=lineno)


def iter_ordered_list_items(lines: list[str]) -> Iterator[OrderedListItem]:
    """Yield an OrderedListItem for each numbered list item in lines, in order."""
    fence_char: str | None = None
    for lineno, raw_line in enumerate(lines, start=1):
        fence_match = _FENCE_RE.match(raw_line)
        if fence_match:
            marker_char = fence_match.group(1)[0]
            fence_char = None if fence_char == marker_char else marker_char
            continue
        if fence_char is not None:
            continue
        match = _ORDERED_RE.match(raw_line)
        if not match:
            continue
        yield OrderedListItem(number=int(match.group(2)), indent=len(match.group(1)), line=lineno)
