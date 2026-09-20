"""Executes the MDT01-03 examples in docs/rules.md against the real rules.

tests/test_docs.py only checks that every rule has a non-empty Passing and
Failing block; nothing checks the blocks actually behave as labelled. For the
list/table family (G6) that would let an example rot silently — e.g. a rule
tweak that stops flagging the documented Failing input — while the docs keep
claiming it fails. Each documented example is run through the rule and the
documented diagnostic line is compared to what the rule really reports.
"""

import re
from pathlib import Path

import pytest

from mdlint.rules import all_rules

REPO_ROOT = Path(__file__).resolve().parent.parent
LIST_TABLE_RULE_IDS = ("MDT01", "MDT02", "MDT03")
FENCE_RE = re.compile(r"```markdown\n(.*?)\n```", re.DOTALL)
DIAGNOSTIC_RE = re.compile(r"^`docs/example\.md:(\d+): (MDT\d{2}) (.+)`$", re.MULTILINE)


def _section(rule_id: str) -> str:
    text = (REPO_ROOT / "docs" / "rules.md").read_text()
    body = re.split(rf"^### {rule_id} ", text, flags=re.MULTILINE)[1]
    return re.split(r"^#{2,3} ", body, flags=re.MULTILINE)[0]


def _examples(rule_id: str) -> tuple[list[str], list[str], tuple[int, str, str]]:
    section = _section(rule_id)
    passing_part, failing_part = section.split("Failing:", 1)
    passing = FENCE_RE.search(passing_part).group(1).split("\n")
    failing = FENCE_RE.search(failing_part).group(1).split("\n")
    line, doc_rule_id, message = DIAGNOSTIC_RE.search(failing_part).groups()
    return passing, failing, (int(line), doc_rule_id, message)


def _rule(rule_id: str):
    return next(rule for rule in all_rules() if rule.id == rule_id)


@pytest.mark.parametrize("rule_id", LIST_TABLE_RULE_IDS)
def test_documented_passing_example_has_no_violations(rule_id):
    passing, _, _ = _examples(rule_id)

    assert list(_rule(rule_id).check("docs/example.md", passing)) == []


@pytest.mark.parametrize("rule_id", LIST_TABLE_RULE_IDS)
def test_documented_failing_example_reports_exactly_the_documented_diagnostic(rule_id):
    _, failing, (line, doc_rule_id, message) = _examples(rule_id)

    violations = list(_rule(rule_id).check("docs/example.md", failing))

    assert [(v.line, v.rule_id, v.message) for v in violations] == [(line, doc_rule_id, message)]


@pytest.mark.parametrize("rule_id", ("MDT01", "MDT02"))
def test_documented_autofix_turns_the_failing_example_into_a_clean_one(rule_id):
    """MDT01/MDT02 are documented as **Autofix: yes**; prove the claim."""
    _, failing, _ = _examples(rule_id)
    rule = _rule(rule_id)

    fixed = rule.fix(failing)

    assert fixed != failing
    assert list(rule.check("docs/example.md", fixed)) == []


def test_mdt03_is_documented_as_report_only_and_has_no_fix():
    assert "Autofix: yes" not in _section("MDT03")
    assert _rule("MDT03").fix is None
