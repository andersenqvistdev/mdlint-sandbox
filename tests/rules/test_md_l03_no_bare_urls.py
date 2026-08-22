"""Tests for MDL03 — bare URLs outside code spans must be wrapped."""

from mdlint.rules.md_l03_no_bare_urls import RULE_ID, check, fix


def test_passes_for_markdown_links():
    assert check("doc.md", ["See [the site](https://example.com) for more."]) == []


def test_passes_for_autolinks():
    assert check("doc.md", ["See <https://example.com> for more."]) == []


def test_fails_for_a_bare_url_in_prose():
    lines = ["Visit https://example.com for more."]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].rule_id == RULE_ID
    assert violations[0].line == 1


def test_ignores_bare_urls_inside_code_spans():
    assert check("doc.md", ["Run `curl https://example.com` to fetch it."]) == []


def test_ignores_bare_urls_inside_fenced_code_blocks():
    lines = ["```", "curl https://example.com", "```"]

    assert check("doc.md", lines) == []


def test_strips_trailing_punctuation_from_the_reported_url():
    violations = check("doc.md", ["See https://example.com."])

    assert violations[0].message.startswith("bare URL 'https://example.com'")


def test_flags_multiple_bare_urls_on_one_line():
    lines = ["http://a.example.com and https://b.example.com"]

    violations = check("doc.md", lines)

    assert len(violations) == 2


def test_fix_wraps_a_bare_url_in_angle_brackets():
    lines = ["Visit https://example.com for more."]

    fixed = fix(lines)

    assert fixed == ["Visit <https://example.com> for more."]
    assert check("doc.md", fixed) == []


def test_fix_keeps_trailing_punctuation_outside_the_brackets():
    lines = ["See https://example.com."]

    assert fix(lines) == ["See <https://example.com>."]


def test_fix_wraps_multiple_bare_urls_on_one_line():
    lines = ["http://a.example.com and https://b.example.com"]

    fixed = fix(lines)

    assert fixed == ["<http://a.example.com> and <https://b.example.com>"]
    assert check("doc.md", fixed) == []


def test_fix_is_a_noop_when_there_are_no_bare_urls():
    lines = ["See [the site](https://example.com) for more."]

    assert fix(lines) == lines


def test_ignores_link_reference_definition_targets():
    lines = ['[ref]: https://example.com "Title"']

    assert check("doc.md", lines) == []


def test_ignores_angle_bracketed_link_reference_definition_targets():
    lines = ["[ref]: <https://example.com>"]

    assert check("doc.md", lines) == []


def test_still_flags_bare_urls_after_a_link_reference_definition_line():
    lines = ["[ref]: https://example.com", "Visit https://bad.example.com now."]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].line == 2


def test_fix_does_not_touch_link_reference_definition_targets():
    lines = ['[ref]: https://example.com "Title"']

    assert fix(lines) == lines
