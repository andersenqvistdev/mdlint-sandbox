"""Tests for MDF03 — fence marker style must be consistent."""

from mdlint.rules.md_f03_consistent_fence_marker import RULE_ID, check, fix


def test_passes_when_all_fences_use_the_same_marker():
    lines = ["```python", "one", "```", "```text", "two", "```"]

    assert check("doc.md", lines) == []


def test_passes_for_a_single_fence():
    assert check("doc.md", ["```python", "one", "```"]) == []


def test_document_with_no_fences_has_no_violations():
    assert check("doc.md", ["plain text", "more text"]) == []


def test_fails_when_a_later_fence_uses_a_different_marker():
    lines = ["```python", "one", "```", "~~~text", "two", "~~~"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].rule_id == RULE_ID
    assert violations[0].line == 4


def test_flags_each_inconsistent_fence_independently():
    lines = ["```python", "a", "```", "~~~", "b", "~~~", "```", "c", "```", "~~~", "d", "~~~"]

    violations = check("doc.md", lines)

    assert [v.line for v in violations] == [4, 10]


def test_fix_rewrites_inconsistent_markers_to_match_the_first():
    lines = ["```python", "one", "```", "~~~text", "two", "~~~"]

    fixed = fix(lines)

    assert fixed == ["```python", "one", "```", "```text", "two", "```"]
    assert check("doc.md", fixed) == []


def test_fix_preserves_marker_length_and_info_string():
    lines = ["````python", "one", "````", "~~~~text", "two", "~~~~"]

    fixed = fix(lines)

    assert fixed == ["````python", "one", "````", "````text", "two", "````"]


def test_fix_leaves_an_unclosed_inconsistent_fence_openable_line_fixed():
    lines = ["```python", "one", "```", "~~~text", "two"]

    fixed = fix(lines)

    assert fixed == ["```python", "one", "```", "```text", "two"]


def test_fix_is_a_noop_when_already_consistent():
    lines = ["```python", "one", "```"]

    assert fix(lines) == lines


def test_fix_is_a_noop_for_a_single_fence():
    assert fix(["~~~text", "one", "~~~"]) == ["~~~text", "one", "~~~"]


def test_fix_preserves_leading_indentation_of_an_indented_fence():
    lines = ["```python", "one", "```", "  ~~~text", "two", "  ~~~"]

    fixed = fix(lines)

    assert fixed == ["```python", "one", "```", "  ```text", "two", "  ```"]
    assert check("doc.md", fixed) == []


def test_fix_skips_a_later_block_that_already_matches_the_expected_marker():
    lines = ["```python", "a", "```", "~~~", "b", "~~~", "```", "c", "```"]

    fixed = fix(lines)

    assert fixed == ["```python", "a", "```", "```", "b", "```", "```", "c", "```"]
    assert check("doc.md", fixed) == []
