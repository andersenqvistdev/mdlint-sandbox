"""Tests for MDT03 — table rows must have as many columns as the header."""

from mdlint.rules.md_t03_table_column_count import RULE_ID, check


def test_passes_for_a_well_formed_table():
    lines = [
        "| A | B |",
        "| --- | --- |",
        "| 1 | 2 |",
        "| 3 | 4 |",
    ]

    assert check("doc.md", lines) == []


def test_passes_for_a_table_with_only_a_header_and_delimiter():
    lines = ["| A | B |", "| --- | --- |"]

    assert check("doc.md", lines) == []


def test_fails_when_a_row_has_fewer_columns_than_the_header():
    lines = [
        "| A | B | C |",
        "| --- | --- | --- |",
        "| 1 | 2 |",
    ]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].rule_id == RULE_ID
    assert violations[0].line == 3


def test_fails_when_a_row_has_more_columns_than_the_header():
    lines = [
        "| A | B |",
        "| --- | --- |",
        "| 1 | 2 | 3 |",
    ]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].line == 3


def test_flags_each_mismatched_row_independently():
    lines = [
        "| A | B |",
        "| --- | --- |",
        "| 1 |",
        "| 2 | 3 | 4 |",
    ]

    violations = check("doc.md", lines)

    assert [v.line for v in violations] == [3, 4]


def test_handles_tables_without_leading_or_trailing_pipes():
    lines = [
        "A | B",
        "--- | ---",
        "1 | 2 | 3",
    ]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].line == 3


def test_ignores_pipes_outside_a_table():
    lines = ["just | some | text", "", "no delimiter row follows"]

    assert check("doc.md", lines) == []


def test_ignores_tables_inside_fenced_code_blocks():
    lines = [
        "```",
        "| A | B |",
        "| --- | --- |",
        "| 1 | 2 | 3 |",
        "```",
    ]

    assert check("doc.md", lines) == []


def test_ignores_tables_inside_tilde_fenced_code_blocks():
    lines = [
        "~~~",
        "| A | B |",
        "| --- | --- |",
        "| 1 | 2 | 3 |",
        "~~~",
    ]

    assert check("doc.md", lines) == []


def test_escaped_pipe_inside_a_cell_is_not_a_column_separator():
    lines = [
        "| A | B |",
        "| --- | --- |",
        r"| esc\|aped | 2 |",
    ]

    assert check("doc.md", lines) == []


def test_recognizes_delimiter_rows_with_alignment_colons():
    lines = [
        "| A | B | C |",
        "| :--- | :---: | ---: |",
        "| 1 | 2 |",
    ]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].line == 3


def test_ignores_a_block_whose_delimiter_row_column_count_differs_from_the_header():
    lines = [
        "| A | B | C |",
        "| --- | --- |",
        "| 1 | 2 | 3 |",
    ]

    assert check("doc.md", lines) == []


def test_pipe_inside_a_code_span_is_not_a_column_separator():
    lines = [
        "| A | B |",
        "| --- | --- |",
        "| `a|b` | 2 |",
    ]

    assert check("doc.md", lines) == []


def test_mismatched_row_with_a_code_span_pipe_is_still_flagged():
    lines = [
        "| A | B |",
        "| --- | --- |",
        "| `a|b|c` |",
    ]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].line == 3


def test_double_backtick_code_span_containing_a_single_backtick_and_a_pipe():
    lines = [
        "| A | B |",
        "| --- | --- |",
        "| `` a`|b `` | 2 |",
    ]

    assert check("doc.md", lines) == []


def test_unmatched_backtick_run_is_treated_as_literal_text():
    lines = [
        "| A | B |",
        "| --- | --- |",
        "| `a | 2 |",
    ]

    assert check("doc.md", lines) == []


def test_checks_multiple_tables_independently():
    lines = [
        "| A | B |",
        "| --- | --- |",
        "| 1 | 2 |",
        "",
        "| X | Y |",
        "| --- | --- |",
        "| 1 | 2 | 3 |",
    ]

    violations = check("doc.md", lines)

    assert [v.line for v in violations] == [7]
