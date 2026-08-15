"""Tests for the rule registry in mdlint.rules."""

import pytest

from mdlint.rules import Rule, all_rules, register


def test_all_rules_returns_every_registered_rule():
    rules = all_rules()

    assert len(rules) == 13
    assert {rule.id for rule in rules} == {
        "MDL01",
        "MDL02",
        "MDL03",
        "MDS01",
        "MDS02",
        "MDS03",
        "MDT01",
        "MDT02",
        "MDT03",
        "MDW01",
        "MDW02",
        "MDW03",
        "MDW04",
    }


def test_register_rejects_duplicate_rule_id():
    existing = all_rules()[0]

    with pytest.raises(ValueError, match="duplicate rule id"):
        register(Rule(id=existing.id, name="duplicate", check=existing.check))
