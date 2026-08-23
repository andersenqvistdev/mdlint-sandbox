"""ATX heading extraction shared by the structure rules (MDS family).

Fenced code blocks are skipped so that a line like ``# not a heading``
inside a ``` fence isn't mistaken for a heading.
"""

import re
from collections.abc import Iterator
from dataclasses import dataclass

_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_ATX_RE = re.compile(r"^ {0,3}(#{1,6})(?:\s+(.*))?$")
_TRAILING_HASHES_RE = re.compile(r"(?:^|\s)#+\s*$")


@dataclass(frozen=True)
class Heading:
    """A single ATX heading found in a document."""

    level: int
    text: str
    line: int


def iter_headings(lines: list[str]) -> Iterator[Heading]:
    """Yield a Heading for each ATX heading in lines, in document order."""
    fence_char: str | None = None
    fence_len = 0
    for lineno, raw_line in enumerate(lines, start=1):
        fence_match = _FENCE_RE.match(raw_line)
        if fence_match:
            marker = fence_match.group(1)
            if fence_char is None:
                fence_char, fence_len = marker[0], len(marker)
            elif marker[0] == fence_char and len(marker) >= fence_len:
                fence_char = None
            continue
        if fence_char is not None:
            continue
        heading_match = _ATX_RE.match(raw_line)
        if not heading_match:
            continue
        level = len(heading_match.group(1))
        text = _TRAILING_HASHES_RE.sub("", heading_match.group(2) or "").strip()
        yield Heading(level=level, text=text, line=lineno)
