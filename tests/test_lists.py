"""Tests for the shared list item parser used by the MDT rules."""

from mdlint.lists import (
    OrderedListItem,
    UnorderedListItem,
    iter_ordered_list_items,
    iter_unordered_list_items,
    ordered_number_span,
    unordered_marker_span,
)


def test_unordered_marker_span_returns_none_for_non_list_line():
    assert unordered_marker_span("just a sentence.") is None


def test_ordered_number_span_returns_none_for_non_list_line():
    assert ordered_number_span("just a sentence.") is None


def test_extracts_unordered_items_with_marker_and_line():
    lines = ["- one", "* two", "+ three"]

    items = list(iter_unordered_list_items(lines))

    assert items == [
        UnorderedListItem(marker="-", line=1),
        UnorderedListItem(marker="*", line=2),
        UnorderedListItem(marker="+", line=3),
    ]


def test_ignores_bare_thematic_breaks():
    assert list(iter_unordered_list_items(["---", "***", "___"])) == []


def test_ignores_spaced_thematic_breaks():
    assert list(iter_unordered_list_items(["* * *", "- - -", "_ _ _"])) == []


def test_ignores_unordered_items_inside_fenced_code_blocks():
    lines = ["- real", "```", "- not real", "```", "- also real"]

    items = list(iter_unordered_list_items(lines))

    assert [item.line for item in items] == [1, 5]


def test_ignores_a_bullet_indented_four_or_more_spaces_as_indented_code():
    assert list(iter_unordered_list_items(["    - looks like a bullet"])) == []


def test_extracts_ordered_items_with_number_indent_and_line():
    lines = ["1. one", "  2. two"]

    items = list(iter_ordered_list_items(lines))

    assert items == [
        OrderedListItem(number=1, indent=0, line=1),
        OrderedListItem(number=2, indent=2, line=2),
    ]


def test_accepts_both_period_and_paren_delimiters():
    lines = ["1. one", "2) two"]

    items = list(iter_ordered_list_items(lines))

    assert [item.number for item in items] == [1, 2]


def test_ignores_ordered_items_inside_fenced_code_blocks():
    lines = ["1. real", "~~~", "2. not real", "~~~", "2. also real"]

    items = list(iter_ordered_list_items(lines))

    assert [item.line for item in items] == [1, 5]


def test_ignores_a_number_indented_four_or_more_spaces_as_indented_code():
    assert list(iter_ordered_list_items(["    1. looks like an item"])) == []
