"""MDL03 — bare URLs outside code spans must be wrapped.

A raw ``https://example.com`` dropped into prose renders inconsistently
across viewers; it should be an autolink (``<https://example.com>``) or a
markdown link (``[text](https://example.com)``).
"""

import re

from mdlint.links import iter_masked_lines, mask_links
from mdlint.rules import Rule, register
from mdlint.violation import Violation

RULE_ID = "MDL03"

_AUTOLINK_RE = re.compile(r"<[a-zA-Z][a-zA-Z0-9+.-]*:[^\s<>]+>")
_BARE_URL_RE = re.compile(r"https?://[^\s<>]+")
_TRAILING_PUNCTUATION = ").,;:!?]}\"'"


def check(file: str, lines: list[str]) -> list[Violation]:
    """Flag http(s) URLs that aren't wrapped in <> or markdown link syntax."""
    violations = []
    for lineno, masked in iter_masked_lines(lines):
        cleaned = mask_links(masked)
        cleaned = _AUTOLINK_RE.sub(lambda m: " " * len(m.group(0)), cleaned)
        for match in _BARE_URL_RE.finditer(cleaned):
            url = match.group(0).rstrip(_TRAILING_PUNCTUATION)
            if not url:
                continue
            violations.append(
                Violation(
                    file=file,
                    line=lineno,
                    rule_id=RULE_ID,
                    message=f"bare URL {url!r} should be wrapped in <> or a markdown link",
                )
            )
    return violations


def fix(lines: list[str]) -> list[str]:
    """Wrap every bare http(s) URL in <> so it becomes an autolink."""
    fixed = list(lines)
    for lineno, masked in iter_masked_lines(lines):
        cleaned = mask_links(masked)
        cleaned = _AUTOLINK_RE.sub(lambda m: " " * len(m.group(0)), cleaned)
        idx = lineno - 1
        line = fixed[idx]
        pieces = []
        pos = 0
        for match in _BARE_URL_RE.finditer(cleaned):
            url = match.group(0).rstrip(_TRAILING_PUNCTUATION)
            if not url:
                continue
            start = match.start()
            end = start + len(url)
            pieces.append(line[pos:start])
            pieces.append(f"<{line[start:end]}>")
            pos = end
        if not pieces:
            continue
        pieces.append(line[pos:])
        fixed[idx] = "".join(pieces)
    return fixed


register(Rule(id=RULE_ID, name="no-bare-urls", check=check, fix=fix))
