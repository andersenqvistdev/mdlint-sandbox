"""Rule registry.

Rules are additive: a new rule is a new module that calls ``register()`` at
import time. Adding one must never require changing another rule's code.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from mdlint.violation import Violation

RuleCheck = Callable[[str, list[str]], Iterable[Violation]]


@dataclass(frozen=True)
class Rule:
    """A single lint rule: a stable id, a name, and its check function."""

    id: str
    name: str
    check: RuleCheck


_REGISTRY: dict[str, Rule] = {}


def register(rule: Rule) -> Rule:
    """Add a rule to the registry. Raises if its id is already taken."""
    if rule.id in _REGISTRY:
        raise ValueError(f"duplicate rule id: {rule.id}")
    _REGISTRY[rule.id] = rule
    return rule


def all_rules() -> list[Rule]:
    """Return every registered rule, in registration order."""
    return list(_REGISTRY.values())


# Importing each rule module triggers its register() call. This is the only
# place that needs to know a new rule module exists.
from mdlint.rules import (  # noqa: E402
    md_l01_link_target_exists,  # noqa: F401
    md_l02_no_empty_link_text,  # noqa: F401
    md_l03_no_bare_urls,  # noqa: F401
    md_s01_first_line_heading,  # noqa: F401
    md_s02_heading_increment,  # noqa: F401
    md_s03_no_duplicate_siblings,  # noqa: F401
    md_t01_consistent_unordered_markers,  # noqa: F401
    md_t02_ordered_list_sequential,  # noqa: F401
    md_t03_table_column_count,  # noqa: F401
    md_w01_no_trailing_spaces,  # noqa: F401
    md_w02_no_hard_tabs,  # noqa: F401
    md_w03_no_consecutive_blank_lines,  # noqa: F401
    md_w04_final_newline,  # noqa: F401
)
