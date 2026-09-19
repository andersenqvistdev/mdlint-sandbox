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


def test_sequence_tracked_across_mixed_delimiter_styles():
    """The '.' and ')' delimiters share one sequence per indent; the rule
    only cares about the number, not which delimiter marks it."""
    lines = ["1. one", "2) two", "3. three"]

    assert check("doc.md", lines) == []


def test_ignores_ordered_items_inside_fenced_code_blocks():
    lines = ["1. one", "```", "5. not real", "```", "2. two"]

    assert check("doc.md", lines) == []


def test_ignores_ordered_items_inside_tilde_fenced_code_blocks():
    lines = ["1. one", "~~~", "5. not real", "~~~", "2. two"]

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


def test_indented_continuation_paragraph_does_not_break_the_sequence():
    lines = [
        "1. First item.",
        "",
        "   Continuation paragraph for item 1.",
        "",
        "3. Should be 2.",
    ]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].line == 5
    assert "expected 2" in violations[0].message


def test_less_indented_content_still_resets_the_sequence():
    lines = ["  1. one", "  2. two", "not indented enough to continue", "  1. new list"]

    assert check("doc.md", lines) == []


def test_ignores_a_nested_ordered_item_under_a_wide_ordered_marker():
    """Known limitation: same absolute-vs-relative indent gap as MDT01's
    "nested under a wide ordered marker" case. A two-digit ordered marker
    ("10. ") is 4 columns wide, so a properly nested ordered item aligned
    under it also lands at 4+ spaces and is read as an indented code block,
    leaving its numbering unchecked."""
    lines = ["10. one", "    1. nested a", "    3. nested b"]

    assert check("doc.md", lines) == []


def test_fix_renumbers_across_an_indented_continuation_paragraph():
    lines = [
        "1. First item.",
        "",
        "   Continuation paragraph for item 1.",
        "",
        "3. Should be 2.",
    ]

    fixed = fix(lines)

    assert fixed[-1] == "2. Should be 2."
    assert check("doc.md", fixed) == []


def test_fix_is_a_noop_when_already_sequential():
    lines = ["1. one", "2. two", "3. three"]

    assert fix(lines) == lines


def test_fix_resets_after_unrelated_content_and_skips_blank_lines():
    lines = ["1. one", "", "3. two", "text", "5. new", "7. new too"]

    fixed = fix(lines)

    assert fixed == ["1. one", "", "2. two", "text", "5. new", "6. new too"]
    assert check("doc.md", fixed) == []


def test_leading_zero_numbers_are_compared_numerically():
    """ "01." parses to the number 1, so a zero-padded sequence is sequential
    exactly when its numeric values are, regardless of the padding width."""
    lines = ["01. one", "02. two", "03. three"]

    assert check("doc.md", lines) == []


def test_leading_zero_numbers_still_flag_a_numeric_skip():
    lines = ["01. one", "03. two"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].line == 2
    assert "expected 2" in violations[0].message


def test_fix_drops_leading_zero_padding_when_renumbering():
    """Known limitation: fix() writes the expected number's plain decimal
    form, so renumbering a zero-padded item loses its original padding
    width instead of preserving it (e.g. "03." becomes "2.", not "02.")."""
    lines = ["01. one", "03. two"]

    assert fix(lines) == ["01. one", "2. two"]
