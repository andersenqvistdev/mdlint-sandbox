"""MDL01 — relative link targets must exist on disk.

Only relative targets are checked: URLs with a scheme (``https://``,
``mailto:``, ...) and absolute paths are out of scope, as is a bare
same-document anchor like ``#section``.
"""

import re
from pathlib import Path

from mdlint.links import iter_links
from mdlint.rules import Rule, register
from mdlint.violation import Violation

RULE_ID = "MDL01"

_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


def check(file: str, lines: list[str]) -> list[Violation]:
    """Flag relative link/image targets that don't resolve to a file on disk."""
    violations = []
    base_dir = Path(file).parent
    for link in iter_links(lines):
        target = link.target.split("#", 1)[0].split("?", 1)[0]
        if not target or _SCHEME_RE.match(target) or target.startswith("/"):
            continue
        if not (base_dir / target).exists():
            violations.append(
                Violation(
                    file=file,
                    line=link.line,
                    rule_id=RULE_ID,
                    message=f"link target {link.target!r} does not exist on disk",
                )
            )
    return violations


register(Rule(id=RULE_ID, name="link-target-exists", check=check))
