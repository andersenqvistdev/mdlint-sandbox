"""Tests for MDS02 — heading levels must not skip a level when increasing."""

from mdlint.rules.md_s02_heading_increment import RULE_ID, check


def test_passes_for_sequential_increments():
    lines = ["# Title", "## Section", "### Sub"]

    assert check("doc.md", lines) == []


def test_passes_when_dropping_back_down_levels():
    lines = ["# Title", "## Section", "### Sub", "# Next Title", "## Section"]

    assert check("doc.md", lines) == []


def test_fails_when_a_level_is_skipped():
    lines = ["# Title", "### Too deep"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].rule_id == RULE_ID
    assert violations[0].line == 2


def test_first_heading_alone_never_violates():
    assert check("doc.md", ["### Only heading"]) == []


def test_document_with_no_headings_has_no_violations():
    assert check("doc.md", ["plain text", "", "more text"]) == []


def test_flags_each_skipped_jump_independently():
    lines = ["# Title", "### Too deep", "##### Way too deep"]

    violations = check("doc.md", lines)

    assert [v.line for v in violations] == [2, 3]


def test_ignores_skipped_levels_inside_fenced_code_blocks():
    lines = ["# Title", "```", "##### not a real heading", "```", "## Section"]

    assert check("doc.md", lines) == []


def test_passes_for_setext_h1_followed_by_setext_h2():
    lines = ["Title", "=====", "", "Section", "-------"]

    assert check("doc.md", lines) == []


def test_fails_when_setext_h1_is_followed_by_a_skipped_atx_level():
    lines = ["Title", "=====", "", "### Too deep"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].line == 4


def test_fails_when_a_level_is_skipped_after_a_utf8_bom():
    # A BOM-prefixed first line must not hide the leading "# Title" heading
    # from this rule's level tracking (regression: previously the BOM broke
    # the ATX regex match, so the H1 -> H3 jump went undetected).
    lines = ["﻿# Title", "### Too deep"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].line == 2


def test_front_matter_closing_delimiter_does_not_create_a_phantom_heading():
    # Without front-matter awareness, "---" after "x: y" reads as a setext H2
    # underline, so the real first heading ("#### Deep") would falsely look
    # like a jump from H2 to H4 instead of the document's very first heading.
    lines = ["---", "x: y", "---", "#### Deep"]

    assert check("doc.md", lines) == []
