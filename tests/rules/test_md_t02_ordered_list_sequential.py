"""Tests for MDT02 — ordered list numbers must increase sequentially by one."""

from mdlint.rules.md_t02_ordered_list_sequential import RULE_ID, check, fix


def test_passes_for_sequential_numbering_from_one():
    lines = ["1. one", "2. two", "3. three"]

    assert check("doc.md", lines) == []


def test_passes_for_a_list_that_starts_at_a_number_other_than_one():
    lines = ["5. five", "6. six", "7. seven"]

    assert check("doc.md", lines) == []


def test_fails_when_a_number_is_skipped():
    lines = ["1. one", "2. two", "4. four"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].rule_id == RULE_ID
    assert violations[0].line == 3


def test_fails_when_a_number_repeats():
    lines = ["1. one", "1. one again"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].line == 2


def test_passes_for_a_single_item():
    assert check("doc.md", ["1. only item"]) == []


def test_document_with_no_ordered_items_has_no_violations():
    assert check("doc.md", ["plain text", "", "more text"]) == []


def test_blank_lines_inside_a_loose_list_dont_break_the_sequence():
    lines = ["1. one", "", "2. two", "", "3. three"]

    assert check("doc.md", lines) == []


def test_unrelated_content_between_lists_resets_the_sequence():
    lines = ["1. one", "2. two", "", "some paragraph", "", "1. new list", "2. continues"]

    assert check("doc.md", lines) == []


def test_nested_ordered_lists_are_tracked_independently_per_indent():
    lines = ["1. top", "  1. nested", "  2. nested", "2. top"]

    assert check("doc.md", lines) == []


def test_ignores_ordered_items_inside_fenced_code_blocks():
    lines = ["1. one", "```", "5. not real", "```", "2. two"]

    assert check("doc.md", lines) == []


def test_fix_renumbers_a_skipped_item():
    lines = ["1. one", "2. two", "4. four"]

    fixed = fix(lines)

    assert fixed == ["1. one", "2. two", "3. four"]
    assert check("doc.md", fixed) == []


def test_fix_renumbers_a_repeated_item():
    lines = ["1. one", "1. one again"]

    assert fix(lines) == ["1. one", "2. one again"]


def test_fix_keeps_the_lists_own_starting_number():
    lines = ["5. five", "5. still five"]

    assert fix(lines) == ["5. five", "6. still five"]


def test_fix_handles_nested_indents_independently():
    lines = ["1. top", "  1. nested", "  3. nested", "3. top"]

    fixed = fix(lines)

    assert fixed == ["1. top", "  1. nested", "  2. nested", "2. top"]
    assert check("doc.md", fixed) == []


def test_fix_is_a_noop_when_already_sequential():
    lines = ["1. one", "2. two", "3. three"]

    assert fix(lines) == lines
