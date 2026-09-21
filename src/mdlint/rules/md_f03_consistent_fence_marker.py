"""MDF03 — fence marker style must be consistent within a file.

The first fence encountered (backtick ```` ``` ```` or tilde ``~~~``)
establishes the file's expected marker; every later fence opened with the
other character is flagged, regardless of nesting.
"""

from mdlint.fences import FenceBlock, fence_marker_span, iter_fence_blocks
from mdlint.rules import Rule, register
from mdlint.violation import Violation

RULE_ID = "MDF03"


def check(file: str, lines: list[str]) -> list[Violation]:
    """Flag fence markers that differ from the file's first fence marker."""
    violations = []
    expected_marker = None
    for block in iter_fence_blocks(lines):
        if expected_marker is None:
            expected_marker = block.marker
            continue
        if block.marker != expected_marker:
            violations.append(
                Violation(
                    file=file,
                    line=block.open_line,
                    rule_id=RULE_ID,
                    message=(
                        f"fence marker {block.marker!r} is inconsistent; "
                        f"file uses {expected_marker!r}"
                    ),
                )
            )
    return violations


def _can_convert(lines: list[str], block: FenceBlock, marker: str) -> bool:
    """Return whether rewriting block to marker keeps its extent unchanged.

    A conversion is unsafe when it would make the block's own content end it
    early (an interior line that becomes a valid closer once the marker
    matches), or when the info string stops being legal (a backtick fence's
    info may not contain a backtick). Such blocks are left for a human.
    """
    if marker == "`" and "`" in block.info:
        return False
    end = block.close_line if block.close_line is not None else len(lines) + 1
    for line in lines[block.open_line : end - 1]:
        span = fence_marker_span(line)
        if span is None:
            continue
        start, stop = span
        if line[start] == marker and stop - start >= block.length and not line[stop:].strip():
            return False
    return True


def fix(lines: list[str]) -> list[str]:
    """Rewrite fence markers to match the file's first fence marker.

    Blocks whose conversion would change where the fence ends (see
    :func:`_can_convert`) are left untouched and stay reported by the rule.
    """
    blocks = list(iter_fence_blocks(lines))
    if len(blocks) < 2:
        return lines
    expected_marker = blocks[0].marker
    fixed = list(lines)
    for block in blocks[1:]:
        if block.marker == expected_marker or not _can_convert(lines, block, expected_marker):
            continue
        fence_lines = [block.open_line]
        if block.close_line is not None:
            fence_lines.append(block.close_line)
        for fence_line in fence_lines:
            idx = fence_line - 1
            line = fixed[idx]
            start, end = fence_marker_span(line)
            marker_run = expected_marker * (end - start)
            fixed[idx] = line[:start] + marker_run + line[end:]
    return fixed


register(Rule(id=RULE_ID, name="consistent-fence-marker", check=check, fix=fix))
