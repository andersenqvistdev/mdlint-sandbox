"""Tests for MDL03 — bare URLs outside code spans must be wrapped."""

from mdlint.rules.md_l03_no_bare_urls import RULE_ID, check


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
