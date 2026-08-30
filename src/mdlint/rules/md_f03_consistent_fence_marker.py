"""MDF03 — fence marker style must be consistent within a file.

The first fence encountered (backtick ```` ``` ```` or tilde ``~~~``)
establishes the file's expected marker; every later fence opened with the
other character is flagged, regardless of nesting.
"""

from mdlint.fences import fence_marker_span, iter_fence_blocks
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


def fix(lines: list[str]) -> list[str]:
    """Rewrite every fence marker to match the file's first fence marker."""
    blocks = list(iter_fence_blocks(lines))
    if len(blocks) < 2:
        return lines
    expected_marker = blocks[0].marker
    fixed = list(lines)
    for block in blocks[1:]:
        if block.marker == expected_marker:
            continue
        fence_lines = [block.open_line]
        if block.close_line is not None:
            fence_lines.append(block.close_line)
        for fence_line in fence_lines:
            idx = fence_line - 1
            line = fixed[idx]
            span = fence_marker_span(line)
            if span is None:
                continue
            start, end = span
            marker_run = expected_marker * (end - start)
            fixed[idx] = line[:start] + marker_run + line[end:]
    return fixed


register(Rule(id=RULE_ID, name="consistent-fence-marker", check=check, fix=fix))
