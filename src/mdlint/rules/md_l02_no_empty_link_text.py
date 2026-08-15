"""MDL02 — link text must not be empty.

Image alt text is exempt: an empty alt (``![](img.png)``) marks a
decorative image and is valid markdown, not a broken link.
"""

from mdlint.links import iter_links
from mdlint.rules import Rule, register
from mdlint.violation import Violation

RULE_ID = "MDL02"


def check(file: str, lines: list[str]) -> list[Violation]:
    """Flag links whose visible text is empty or whitespace-only."""
    violations = []
    for link in iter_links(lines):
        if link.is_image:
            continue
        if link.text.strip() == "":
            violations.append(
                Violation(
                    file=file,
                    line=link.line,
                    rule_id=RULE_ID,
                    message=f"link to {link.target!r} has empty link text",
                )
            )
    return violations


register(Rule(id=RULE_ID, name="no-empty-link-text", check=check))
