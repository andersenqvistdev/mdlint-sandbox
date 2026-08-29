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


def test_passes_for_a_delimiter_row_with_alignment_colons():
    lines = [
        "| A | B |",
        "| :--- | ---: |",
        "| 1 | 2 |",
    ]

    assert check("doc.md", lines) == []


def test_escaped_pipes_inside_a_cell_are_not_treated_as_separators():
    lines = [
        "| A | B |",
        "| --- | --- |",
        r"| pipe \| here | 2 |",
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
