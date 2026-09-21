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


def test_fails_when_an_unclosed_trailing_fence_uses_a_different_marker():
    """MDF03 must also flag a mismatched marker on a fence that MDF02 already
    reports as unclosed — the two rules are independent and both apply.
    """
    lines = ["```python", "one", "```", "~~~text", "two"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].rule_id == RULE_ID
    assert violations[0].line == 4


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


def test_violation_message_names_both_markers():
    violations = check("doc.md", ["```python", "one", "```", "~~~text", "two", "~~~"])

    assert violations[0].file == "doc.md"
    assert violations[0].message == "fence marker '~' is inconsistent; file uses '`'"


def test_tilde_first_makes_backtick_the_inconsistent_marker():
    violations = check("doc.md", ["~~~text", "one", "~~~", "```python", "two", "```"])

    assert [v.line for v in violations] == [4]
    assert violations[0].message == "fence marker '`' is inconsistent; file uses '~'"


def test_marker_lines_inside_another_fence_are_content_not_fences():
    lines = ["```markdown", "~~~python", "print('hi')", "~~~", "```"]

    assert check("doc.md", lines) == []


def test_prose_line_with_backtick_in_info_does_not_set_the_expected_marker():
    lines = ["``` not a fence `x`", "~~~text", "one", "~~~"]

    assert check("doc.md", lines) == []


def test_fix_leaves_a_block_alone_when_its_content_would_close_it_after_conversion():
    """Converting ~~~ to ``` would let the inner ``` line end the block early."""
    lines = ["```python", "a", "```", "~~~markdown", "```", "inner", "```", "~~~"]

    fixed = fix(lines)

    assert fixed == lines
    assert [v.line for v in check("doc.md", fixed)] == [4]


def test_fix_converts_a_block_whose_nested_fence_lines_use_the_other_marker_and_are_shorter():
    lines = ["~~~text", "a", "~~~", "````markdown", "```", "inner", "```", "````"]

    fixed = fix(lines)

    assert fixed == ["~~~text", "a", "~~~", "~~~~markdown", "```", "inner", "```", "~~~~"]
    assert check("doc.md", fixed) == []


def test_fix_leaves_a_tilde_fence_whose_info_string_has_a_backtick_alone():
    """A backtick in the info string is illegal on a backtick fence, so skip the block."""
    lines = ["```python", "a", "```", "~~~ `x`", "b", "~~~"]

    assert fix(lines) == lines


def test_fix_still_converts_other_blocks_when_one_is_skipped():
    lines = [
        "```python",
        "a",
        "```",
        "~~~markdown",
        "```",
        "~~~",
        "~~~text",
        "b",
        "~~~",
    ]

    fixed = fix(lines)

    assert fixed == [
        "```python",
        "a",
        "```",
        "~~~markdown",
        "```",
        "~~~",
        "```text",
        "b",
        "```",
    ]


def test_fix_skips_an_unclosed_block_whose_remaining_content_would_close_it():
    lines = ["```python", "a", "```", "~~~text", "```"]

    assert fix(lines) == lines


def test_fix_is_idempotent():
    lines = ["```python", "one", "```", "~~~text", "two", "~~~"]

    once = fix(lines)

    assert fix(once) == once


def test_fix_does_not_mutate_its_input():
    lines = ["```python", "one", "```", "~~~text", "two", "~~~"]
    snapshot = list(lines)

    fix(lines)

    assert lines == snapshot


def test_fix_of_an_empty_document_is_a_noop():
    assert fix([]) == []


def test_fence_length_does_not_affect_marker_consistency():
    lines = ["```python", "a", "```", "````text", "b", "````"]

    assert check("doc.md", lines) == []


def test_indentation_does_not_affect_marker_consistency():
    lines = ["```python", "a", "```", "  ```text", "b", "  ```"]

    assert check("doc.md", lines) == []


def test_tilde_fence_with_backticks_in_its_info_still_sets_the_expected_marker():
    lines = ["~~~ `x`", "a", "~~~", "```python", "b", "```"]

    violations = check("doc.md", lines)

    assert [v.line for v in violations] == [4]
    assert violations[0].message == "fence marker '`' is inconsistent; file uses '~'"


def test_fix_preserves_trailing_whitespace_on_the_closing_line():
    lines = ["```python", "a", "```", "~~~text", "b", "~~~  "]

    assert fix(lines) == ["```python", "a", "```", "```text", "b", "```  "]


def test_fix_preserves_a_closing_run_longer_than_the_opening_run():
    lines = ["```python", "a", "```", "~~~text", "b", "~~~~~~"]

    fixed = fix(lines)

    assert fixed == ["```python", "a", "```", "```text", "b", "``````"]
    assert check("doc.md", fixed) == []


def test_fix_converts_every_inconsistent_block_in_a_three_block_file():
    lines = ["```a", "x", "```", "~~~b", "y", "~~~", "~~~~c", "z", "~~~~"]

    fixed = fix(lines)

    assert fixed == ["```a", "x", "```", "```b", "y", "```", "````c", "z", "````"]
    assert check("doc.md", fixed) == []


def test_fix_converts_backtick_fences_to_tilde_when_tilde_comes_first():
    lines = ["~~~text", "a", "~~~", "```python", "b", "```"]

    fixed = fix(lines)

    assert fixed == ["~~~text", "a", "~~~", "~~~python", "b", "~~~"]
    assert check("doc.md", fixed) == []


def test_fix_leaves_non_fence_lines_untouched():
    lines = ["# Title", "", "```python", "a", "```", "", "prose", "~~~text", "b", "~~~"]

    fixed = fix(lines)

    assert fixed[:3] == lines[:3]
    assert fixed[5:7] == lines[5:7]


def test_fix_converts_a_block_whose_interior_line_looks_like_a_closer_but_carries_an_info_string():
    """An interior ```python line can't close a converted block, so conversion is safe."""
    lines = ["```text", "a", "```", "~~~text", "```python", "b", "~~~"]

    fixed = fix(lines)

    assert fixed == ["```text", "a", "```", "```text", "```python", "b", "```"]
    assert check("doc.md", fixed) == []


def test_fix_leaves_a_block_alone_when_a_longer_interior_run_would_close_it_after_conversion():
    lines = ["```text", "a", "```", "~~~", "````", "b", "~~~"]

    assert fix(lines) == lines
    assert [v.line for v in check("doc.md", lines)] == [4]


def test_tab_indented_fence_does_not_set_the_expected_marker():
    lines = ["\t```python", "code", "\t```", "~~~text", "b", "~~~"]

    assert check("doc.md", lines) == []
