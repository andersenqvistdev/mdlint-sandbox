"""Violation record shared by all mdlint rules."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Violation:
    """A single rule violation found in a document."""

    file: str
    line: int
    rule_id: str
    message: str
