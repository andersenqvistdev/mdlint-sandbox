"""Tests for MDL03 — bare URLs outside code spans must be wrapped."""

from mdlint.rules.md_l03_no_bare_urls import RULE_ID, check, fix


def test_passes_for_plain_text_with_no_url():
    assert check("doc.md", ["just some text"]) == []


def test_fails_for_a_bare_http_url():
    lines = ["see http://example.com for details"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].rule_id == RULE_ID
    assert violations[0].line == 1


def test_fails_for_a_bare_https_url():
    violations = check("doc.md", ["https://example.com/path"])

    assert len(violations) == 1


def test_passes_for_an_autolink():
    assert check("doc.md", ["see <https://example.com> for details"]) == []


def test_passes_for_a_markdown_link():
    assert check("doc.md", ["see [example](https://example.com) for details"]) == []


def test_ignores_urls_inside_inline_code_spans():
    assert check("doc.md", ["run `curl https://example.com`"]) == []


def test_ignores_urls_inside_fenced_code_blocks():
    lines = ["```", "https://example.com", "```"]

    assert check("doc.md", lines) == []


def test_strips_trailing_punctuation_from_the_flagged_url():
    violations = check("doc.md", ["visit https://example.com."])

    assert len(violations) == 1
    assert "https://example.com" in violations[0].message
    assert "https://example.com." not in violations[0].message


def test_flags_each_bare_url_independently():
    lines = ["https://a.example.com", "<https://b.example.com>", "https://c.example.com"]

    violations = check("doc.md", lines)

    assert [v.line for v in violations] == [1, 3]


def test_fix_wraps_a_bare_url_in_angle_brackets():
    lines = ["see https://example.com for details"]

    fixed = fix(lines)

    assert fixed == ["see <https://example.com> for details"]
    assert check("doc.md", fixed) == []


def test_fix_leaves_lines_without_bare_urls_untouched():
    lines = ["see [example](https://example.com)", "no urls here"]

    assert fix(lines) == lines


def test_fix_preserves_trailing_punctuation_outside_the_wrap():
    lines = ["visit https://example.com."]

    assert fix(lines) == ["visit <https://example.com>."]
