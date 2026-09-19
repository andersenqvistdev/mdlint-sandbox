"""Tests for MDS01 — first line should be a top-level heading."""

from mdlint.rules.md_s01_first_line_heading import RULE_ID, check


def test_passes_when_first_line_is_h1():
    lines = ["# Title", "", "body"]

    assert check("doc.md", lines) == []


def test_passes_when_h1_follows_leading_blank_lines():
    lines = ["", "  ", "# Title"]

    assert check("doc.md", lines) == []


def test_fails_when_first_line_is_not_a_heading():
    lines = ["Some intro text", "", "# Title"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].rule_id == RULE_ID
    assert violations[0].line == 1


def test_fails_when_first_heading_is_not_top_level():
    lines = ["## Section", "body"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].line == 1


def test_empty_document_has_no_violations():
    assert check("doc.md", []) == []


def test_document_with_only_blank_lines_has_no_violations():
    assert check("doc.md", ["", "   ", "\t"]) == []


def test_passes_when_first_line_h1_has_trailing_closing_hashes():
    lines = ["# Title #", "body"]

    assert check("doc.md", lines) == []


def test_fails_when_document_opens_with_a_fenced_code_block():
    # The fence's "# not a heading" line must not be mistaken for a real H1,
    # even though it is textually the first non-blank line.
    lines = ["```", "# not a heading", "```", "# Title"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].rule_id == RULE_ID
    assert violations[0].line == 1


def test_passes_when_first_line_is_a_bare_hash_with_no_text():
    # "#" alone is still a valid (if empty) top-level ATX heading.
    lines = ["#", "body"]

    assert check("doc.md", lines) == []


def test_passes_when_utf8_bom_precedes_h1():
    lines = ["﻿# Title", "body"]

    assert check("doc.md", lines) == []


def test_fails_when_utf8_bom_precedes_non_heading_text():
    lines = ["﻿Some intro text", "", "# Title"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].line == 1


def test_passes_when_h1_follows_yaml_front_matter():
    lines = ["---", "title: Example", "tags: [a, b]", "---", "", "# Title", "body"]

    assert check("doc.md", lines) == []


def test_passes_when_h1_follows_toml_front_matter():
    lines = ["+++", 'title = "Example"', "+++", "# Title"]

    assert check("doc.md", lines) == []


def test_fails_when_non_heading_follows_front_matter():
    lines = ["---", "title: Example", "---", "Some intro text", "", "# Title"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].line == 4


def test_fails_on_original_first_line_when_front_matter_is_unterminated():
    # No closing "---" — this is not front matter, just a thematic break /
    # setext underline that happens to open the file, so it is still checked
    # (and flagged) as the document's first line.
    lines = ["---", "title: Example", "# Title"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].line == 1


def test_passes_when_first_line_is_a_setext_h1():
    lines = ["Title", "=====", "body"]

    assert check("doc.md", lines) == []


def test_fails_when_first_line_is_a_setext_h2():
    # A setext underline of "-" produces an H2, not the required top-level H1.
    lines = ["Title", "-----", "body"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].line == 1


def test_front_matter_delimiter_must_be_the_literal_first_line():
    # A "---" that only appears after leading blank lines is not front
    # matter (Jekyll/Hugo require it to open the file) and is correctly
    # flagged as a non-heading first line.
    lines = ["", "---", "title: Example", "---", "# Title"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].line == 2


def test_passes_when_document_is_only_front_matter_with_no_body():
    # No content follows the closing delimiter, so there is no non-heading
    # line to flag — same as an empty document, not a violation.
    lines = ["---", "title: Example", "---"]

    assert check("doc.md", lines) == []


def test_passes_when_h1_follows_front_matter_opened_after_a_utf8_bom():
    lines = ["﻿---", "title: Example", "---", "", "# Title", "body"]

    assert check("doc.md", lines) == []


def test_fails_when_first_line_has_seven_hashes():
    # Seven '#' characters exceed CommonMark's H6 cap, so this line is
    # ordinary paragraph text, not a (invalid) heading — and must still be
    # flagged as a non-heading first line rather than silently accepted.
    lines = ["####### Not a heading", "# Title"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].line == 1


def test_fails_when_document_opens_with_an_indented_code_block_and_underline():
    # "    indented code" + "=====" is a code block plus an ordinary
    # paragraph per CommonMark, not a setext H1 — so the first line is
    # correctly flagged as not a heading, not silently accepted as one.
    lines = ["    indented code", "====="]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].line == 1
