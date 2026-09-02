"""Tests for MDF02 — fenced code blocks must be closed."""

from mdlint.rules.md_f02_fence_closed import RULE_ID, check


def test_passes_when_fence_is_closed():
    lines = ["```python", "print('hi')", "```"]

    assert check("doc.md", lines) == []


def test_fails_when_fence_is_never_closed():
    lines = ["```python", "print('hi')"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].rule_id == RULE_ID
    assert violations[0].line == 1


def test_document_with_no_fences_has_no_violations():
    assert check("doc.md", ["plain text", "more text"]) == []


def test_closed_fence_followed_by_unclosed_fence():
    lines = ["```python", "one", "```", "```text", "two"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].line == 4


def test_shorter_closing_run_does_not_close_a_longer_opening_fence():
    lines = ["````python", "```", "content"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].line == 1


def test_tilde_fence_can_be_unclosed_too():
    lines = ["~~~text", "content"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].line == 1


def test_balanced_fences_with_closing_info_string_report_nothing():
    # Regression for the fence-pairing desync: every fence in this document
    # is properly paired, including one closed by a line that superficially
    # looks like an opener. No unclosed-fence violation should be reported.
    lines = [
        "```markdown",
        "Some sample text.",
        "```python",
        "more sample text",
        "```",
        "",
        "```",
        "a genuinely undeclared block",
        "```",
    ]

    assert check("doc.md", lines) == []
