"""Tests for MDF01 — fenced code blocks must declare a language."""

from mdlint.rules.md_f01_fence_language_required import RULE_ID, check


def test_passes_when_fence_declares_a_language():
    lines = ["```python", "print('hi')", "```"]

    assert check("doc.md", lines) == []


def test_fails_when_fence_has_no_language():
    lines = ["```", "print('hi')", "```"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].rule_id == RULE_ID
    assert violations[0].line == 1


def test_document_with_no_fences_has_no_violations():
    assert check("doc.md", ["plain text", "more text"]) == []


def test_flags_each_bare_fence_independently():
    lines = ["```", "one", "```", "```python", "two", "```", "```", "three", "```"]

    violations = check("doc.md", lines)

    assert [v.line for v in violations] == [1, 7]


def test_flags_a_bare_unclosed_fence_too():
    lines = ["```", "print('hi')"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].line == 1


def test_tilde_fence_with_language_passes():
    assert check("doc.md", ["~~~python", "code", "~~~"]) == []


def test_indented_bare_fence_is_still_flagged():
    lines = ["  ```", "code", "  ```"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].line == 1


def test_four_space_indented_bare_fence_is_indented_code_not_a_fence():
    """Four spaces of indentation is an indented code block, out of scope for MDF01."""
    lines = ["    ```", "not a fence", "    ```"]

    assert check("doc.md", lines) == []


def test_bare_fence_after_a_sample_block_is_flagged_at_its_own_open_line():
    """A closing line with an info string must not desync where later opens land.

    Regression for a bug where the bare fence at line 7 was misread as line 9's
    open (or worse, the closer at line 9 was mistaken for the opener), moving
    the violation to the wrong line or losing it entirely.
    """
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

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].line == 7
