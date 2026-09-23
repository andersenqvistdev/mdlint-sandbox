"""Tests for MDL02 — link text must not be empty."""

from mdlint.rules.md_l02_no_empty_link_text import RULE_ID, check


def test_passes_for_normal_link_text():
    assert check("doc.md", ["[docs](guide.md)"]) == []


def test_fails_for_empty_link_text():
    lines = ["[](guide.md)"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].rule_id == RULE_ID
    assert violations[0].line == 1


def test_fails_for_whitespace_only_link_text():
    violations = check("doc.md", ["[   ](guide.md)"])

    assert len(violations) == 1


def test_passes_for_empty_image_alt_text():
    assert check("doc.md", ["![](decorative.png)"]) == []


def test_flags_each_empty_link_independently():
    lines = ["[](a.md)", "[real](b.md)", "[](c.md)"]

    violations = check("doc.md", lines)

    assert [v.line for v in violations] == [1, 3]


def test_passes_when_link_text_is_a_code_span():
    lines = ["See [`exists.md`](exists.md) and [**bold**](exists.md) and [plain](exists.md)."]

    assert check("doc.md", lines) == []
