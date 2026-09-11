"""Inline link extraction shared by the link rules (MDL family).

Fenced code blocks and inline code spans are skipped so that link-like or
URL-like text inside code isn't mistaken for real markdown syntax. Fence
boundaries are detected via :func:`mdlint.fences.fenced_line_numbers` rather
than a same-marker toggle, which desyncs (and starts linting fence content
as prose) as soon as a fence contains a line opening with the other marker
character.
"""

import re
from collections.abc import Iterator
from dataclasses import dataclass

from mdlint.fences import fenced_line_numbers

_LINK_RE = re.compile(r"!?\[([^\]]*)\]\(([^)\s]*)(?:\s+[^)]*)?\)")


@dataclass(frozen=True)
class Link:
    """A single inline markdown link (or image) found in a document."""

    text: str
    target: str
    line: int
    is_image: bool


def mask_code_spans(line: str) -> str:
    """Blank inline code span syntax, preserving line length and content emptiness.

    The backtick delimiters are replaced with spaces so their content can't be
    mistaken for markdown syntax (a stray ``]`` or ``(`` inside a span). The
    content itself is replaced character-by-character (non-whitespace -> ``x``,
    whitespace kept as-is) rather than blanked outright: blanking it entirely
    would make link text that's just a code span (`` [`x`](y) ``) look empty to
    MDL02, and would let a URL that spans a masked-to-spaces run still read as
    "no content" instead of "content that happens not to be a bare URL".
    """
    result = []
    i = 0
    n = len(line)
    while i < n:
        if line[i] == "`":
            run_start = i
            while i < n and line[i] == "`":
                i += 1
            run_len = i - run_start
            close = _find_closing_run(line, i, run_len)
            if close is not None:
                content_start = i
                content = line[content_start:close]
                masked_content = "".join(" " if c.isspace() else "x" for c in content)
                result.append(" " * run_len)
                result.append(masked_content)
                result.append(" " * run_len)
                i = close + run_len
                continue
            result.append("`" * run_len)
            continue
        result.append(line[i])
        i += 1
    return "".join(result)


def _find_closing_run(line: str, start: int, run_len: int) -> int | None:
    """Return the start index of the next backtick run of exactly run_len."""
    i = start
    n = len(line)
    while i < n:
        if line[i] == "`":
            j = i
            while j < n and line[j] == "`":
                j += 1
            if j - i == run_len:
                return i
            i = j
        else:
            i += 1
    return None


def mask_links(line: str) -> str:
    """Replace inline link/image syntax with spaces, preserving line length."""
    return _LINK_RE.sub(lambda m: " " * len(m.group(0)), line)


def iter_masked_lines(lines: list[str]) -> Iterator[tuple[int, str]]:
    """Yield (line number, line) for non-fenced lines with code spans blanked."""
    fenced_lines = fenced_line_numbers(lines)
    for lineno, raw_line in enumerate(lines, start=1):
        if lineno in fenced_lines:
            continue
        yield lineno, mask_code_spans(raw_line)


def iter_links(lines: list[str]) -> Iterator[Link]:
    """Yield a Link for each inline markdown link/image in lines, in order.

    Link syntax is located in the masked line so link-like text inside code
    spans isn't mistaken for a real link, but the text and target are sliced
    from the raw line at the same offsets: mask_code_spans preserves length,
    so a link whose visible text merely contains a code span (e.g.
    ``[`foo`](foo.md)``) still yields its real text instead of blanks.
    """
    for lineno, masked in iter_masked_lines(lines):
        raw_line = lines[lineno - 1]
        for match in _LINK_RE.finditer(masked):
            yield Link(
                text=raw_line[match.start(1) : match.end(1)],
                target=raw_line[match.start(2) : match.end(2)],
                line=lineno,
                is_image=match.group(0).startswith("!"),
            )
