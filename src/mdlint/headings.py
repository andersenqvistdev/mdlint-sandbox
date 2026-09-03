"""ATX and setext heading extraction shared by the structure rules (MDS family).

Fenced code blocks are skipped so that a line like ``# not a heading``
inside a ``` fence isn't mistaken for a heading. Setext headings (a line of
title text immediately followed by a line of only ``=`` or ``-`` characters)
are also recognized, following CommonMark's rules for what does and doesn't
count as a valid underline.

Fence boundaries are detected via :func:`mdlint.fences.iter_fence_blocks`
rather than a second, ad-hoc regex scan here — an earlier local
implementation closed a fence on any same-marker line long enough,
regardless of trailing content, which let a line like ` ```python ` (info
string on what should be an unadorned closer) wrongly close a fence and
exposed the "headings" hidden inside it.
"""

import re
from collections.abc import Iterator
from dataclasses import dataclass

from mdlint.fences import iter_fence_blocks

_ATX_RE = re.compile(r"^ {0,3}(#{1,6})(?:\s+(.*))?$")
_TRAILING_HASHES_RE = re.compile(r"(?:^|\s)#+\s*$")
_SETEXT_UNDERLINE_RE = re.compile(r"^ {0,3}(=+|-+)[ \t]*$")
_LIST_ITEM_RE = re.compile(r"^ {0,3}([-*+]|\d{1,9}[.)])(\s+)\S")


def _fenced_line_numbers(lines: list[str]) -> set[int]:
    """Return every 1-based line number that falls inside a fenced code block."""
    fenced: set[int] = set()
    for block in iter_fence_blocks(lines):
        end = block.close_line if block.close_line is not None else len(lines)
        fenced.update(range(block.open_line, end + 1))
    return fenced


@dataclass(frozen=True)
class Heading:
    """A single ATX or setext heading found in a document."""

    level: int
    text: str
    line: int


def iter_headings(lines: list[str]) -> Iterator[Heading]:
    """Yield a Heading for each ATX or setext heading in lines, in document order."""
    fenced_lines = _fenced_line_numbers(lines)
    paragraph_start: int | None = None
    paragraph_texts: list[str] = []
    for lineno, raw_line in enumerate(lines, start=1):
        if lineno in fenced_lines:
            paragraph_start = None
            paragraph_texts = []
            continue
        heading_match = _ATX_RE.match(raw_line)
        if heading_match:
            level = len(heading_match.group(1))
            text = _TRAILING_HASHES_RE.sub("", heading_match.group(2) or "").strip()
            yield Heading(level=level, text=text, line=lineno)
            paragraph_start = None
            paragraph_texts = []
            continue
        if raw_line.strip() == "":
            paragraph_start = None
            paragraph_texts = []
            continue
        setext_match = _SETEXT_UNDERLINE_RE.match(raw_line)
        if setext_match:
            if paragraph_start is not None:
                level = 1 if setext_match.group(1)[0] == "=" else 2
                text = " ".join(paragraph_texts).strip()
                yield Heading(level=level, text=text, line=paragraph_start)
                paragraph_start = None
                paragraph_texts = []
                continue
            elif setext_match.group(1)[0] == "-" and len(setext_match.group(1)) >= 3:
                continue
            # else: fall through — lone `-`/`--` or a run of `=` with nothing
            # above are just ordinary paragraph text per CommonMark.
        list_match = _LIST_ITEM_RE.match(raw_line)
        if list_match:
            paragraph_start = None
            paragraph_texts = []
            continue
        if paragraph_start is None:
            paragraph_start = lineno
            paragraph_texts = [raw_line.strip()]
        else:
            paragraph_texts.append(raw_line.strip())
