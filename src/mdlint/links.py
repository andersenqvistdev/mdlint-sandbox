"""Inline link extraction shared by the link rules (MDL family).

Fenced code blocks and inline code spans are skipped so that link-like or
URL-like text inside code isn't mistaken for real markdown syntax.
"""

import re
from collections.abc import Iterator
from dataclasses import dataclass

_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_LINK_RE = re.compile(r"!?\[([^\]]*)\]\(([^)\s]*)(?:\s+[^)]*)?\)")
_LINK_REF_DEF_RE = re.compile(r"^( {0,3}\[[^\]]+\]:[ \t]*)(<[^<>\s]*>|[^\s]+)")


@dataclass(frozen=True)
class Link:
    """A single inline markdown link (or image) found in a document."""

    text: str
    target: str
    line: int
    is_image: bool


def mask_code_spans(line: str) -> str:
    """Replace inline code span contents with spaces, preserving line length."""
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
                end = close + run_len
                result.append(" " * (end - run_start))
                i = end
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


def mask_link_reference_definitions(line: str) -> str:
    """Blank the destination of a ``[label]: target`` line, preserving length.

    A link reference definition's destination isn't a bare URL in prose —
    it's the same kind of link target an inline ``[text](url)`` already
    carries — so callers that hunt for unwrapped URLs must not flag it.
    """
    match = _LINK_REF_DEF_RE.match(line)
    if not match:
        return line
    start, end = match.span(2)
    return line[:start] + " " * (end - start) + line[end:]


def iter_masked_lines(lines: list[str]) -> Iterator[tuple[int, str]]:
    """Yield (line number, line) for non-fenced lines with code spans blanked."""
    fence_char: str | None = None
    for lineno, raw_line in enumerate(lines, start=1):
        fence_match = _FENCE_RE.match(raw_line)
        if fence_match:
            marker_char = fence_match.group(1)[0]
            fence_char = None if fence_char == marker_char else marker_char
            continue
        if fence_char is not None:
            continue
        yield lineno, mask_code_spans(raw_line)


def iter_links(lines: list[str]) -> Iterator[Link]:
    """Yield a Link for each inline markdown link/image in lines, in order."""
    for lineno, masked in iter_masked_lines(lines):
        for match in _LINK_RE.finditer(masked):
            yield Link(
                text=match.group(1),
                target=match.group(2),
                line=lineno,
                is_image=match.group(0).startswith("!"),
            )
