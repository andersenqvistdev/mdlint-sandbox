"""Fenced code block extraction shared by the fence rules (MDF family).

A fence opens with a line of three or more backticks or tildes (indented by
at most three spaces) and closes with a line using the same character, at
least as long as the opening run, and carrying no info string — a closing
line with an info string (e.g. ```` ```python ````) is not a close, so it is
left as content inside the still-open block. A backtick fence's info string
may also not itself contain a backtick, per CommonMark; a line that looks
like an opening backtick fence but whose info string contains a backtick is
not a fence at all. A fence that never finds a matching closing line stays
open through the end of the document.
"""

import re
from collections.abc import Iterator
from dataclasses import dataclass

_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})[ \t]*(.*?)[ \t]*$")


@dataclass(frozen=True)
class FenceBlock:
    """A single fenced code block found in a document."""

    marker: str
    length: int
    info: str
    open_line: int
    close_line: int | None


def iter_fence_blocks(lines: list[str]) -> Iterator[FenceBlock]:
    """Yield a FenceBlock for each fenced code block in lines, in order.

    Only lines outside any currently-open fence are considered as candidate
    opening fences, so a fence's own body can never be mistaken for another
    fence boundary. A closing line must use the same marker character as the
    fence it closes, be at least as long, and carry no info string; anything
    else is left inside the block as content. A candidate opening backtick
    fence whose info string contains a backtick is not a fence either, since
    CommonMark forbids backticks in a backtick fence's info string; that line
    is left as ordinary content.
    """
    open_marker: str | None = None
    open_length = 0
    open_line = 0
    open_info = ""

    for lineno, raw_line in enumerate(lines, start=1):
        match = _FENCE_RE.match(raw_line)
        if not match:
            continue
        marker = match.group(1)[0]
        length = len(match.group(1))
        info = match.group(2)

        if open_marker is None:
            if marker == "`" and "`" in info:
                continue
            open_marker = marker
            open_length = length
            open_line = lineno
            open_info = info
            continue

        if marker == open_marker and length >= open_length:
            if info:
                continue
            yield FenceBlock(
                marker=open_marker,
                length=open_length,
                info=open_info,
                open_line=open_line,
                close_line=lineno,
            )
            open_marker = None

    if open_marker is not None:
        yield FenceBlock(
            marker=open_marker,
            length=open_length,
            info=open_info,
            open_line=open_line,
            close_line=None,
        )


def fence_marker_span(line: str) -> tuple[int, int] | None:
    """Return the (start, end) span of a fence's marker run, or None."""
    match = _FENCE_RE.match(line)
    if not match:
        return None
    return match.span(1)
