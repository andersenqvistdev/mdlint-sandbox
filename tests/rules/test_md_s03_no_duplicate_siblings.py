"""Tests for MDS03 — sibling headings must not repeat text."""

from mdlint.rules.md_s03_no_duplicate_siblings import RULE_ID, check


def test_passes_for_unique_siblings():
    lines = ["# Title", "## Alpha", "## Beta"]

    assert check("doc.md", lines) == []


def test_passes_for_same_text_under_different_parents():
    lines = ["# One", "## Overview", "# Two", "## Overview"]

    assert check("doc.md", lines) == []


def test_fails_for_duplicate_sibling_headings():
    lines = ["# Title", "## Alpha", "## Alpha"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].rule_id == RULE_ID
    assert violations[0].line == 3


def test_fails_for_duplicate_top_level_headings():
    lines = ["# Title", "# Title"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].line == 2


def test_passes_for_a_single_heading():
    assert check("doc.md", ["# Only heading"]) == []


def test_detects_duplicate_siblings_even_after_a_skipped_level():
    # "### Sub" jumps straight from H1 to H3 (MDS02's concern, not this rule's),
    # but the two "Sub" headings are still siblings under "Title" and must be
    # caught as duplicates.
    lines = ["# Title", "### Sub", "### Sub"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].line == 3


def test_duplicate_matching_is_case_sensitive():
    # "Alpha" and "alpha" are different headings; only exact-text repeats
    # under the same parent are flagged.
    lines = ["# Title", "## Alpha", "## alpha"]

    assert check("doc.md", lines) == []


def test_duplicate_matching_ignores_closing_hash_decoration():
    # "## Alpha #" and "## Alpha" render identically once the optional
    # closing hashes are stripped, so they must be treated as duplicates.
    lines = ["# Title", "## Alpha #", "## Alpha"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].line == 3
