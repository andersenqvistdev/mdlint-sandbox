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


def test_indented_fence_can_be_unclosed_too():
    lines = ["  ```python", "content"]

    violations = check("doc.md", lines)

    assert len(violations) == 1
    assert violations[0].line == 1


def test_fence_alone_with_no_content_lines_is_still_unclosed():
    """A fence opened on the file's last line, with no body at all, still counts."""
    violations = check("doc.md", ["```"])

    assert len(violations) == 1
    assert violations[0].line == 1


def test_four_space_indented_fence_is_indented_code_not_a_fence():
    """Four spaces of indentation is an indented code block, out of scope for MDF02."""
    lines = ["    ```python", "content"]

    assert check("doc.md", lines) == []


def test_balanced_fences_with_an_info_string_on_the_closing_line_report_nothing():
    """A closing-looking line with an info string is content, not a real close.

    The real closing fence is the bare ``` two lines later, so the block is
    balanced and MDF02 must not report an unclosed fence.
    """
    lines = ["```markdown", "Some sample text.", "```python", "more sample text", "```"]

    assert check("doc.md", lines) == []


def test_bare_fence_after_a_sample_block_with_info_string_is_still_paired():
    """Fence pairing must not desync after a block containing a fence-like line.

    Regression for a bug where a closing line with an info string wrongly
    closed the first fence, causing every fence after it to be misread —
    reporting real closing fences as false unclosed opens.
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

    assert check("doc.md", lines) == []


def test_empty_document_has_no_violations():
    assert check("doc.md", []) == []


def test_longer_closing_run_closes_a_tilde_fence():
    assert check("doc.md", ["~~~text", "content", "~~~~~~"]) == []


def test_closing_fence_may_carry_trailing_whitespace():
    assert check("doc.md", ["```python", "content", "```  \t"]) == []


def test_unclosed_outer_fence_is_reported_even_when_an_inner_fence_is_closed():
    """The inner ``` pair is content of the four-backtick block, which never ends."""
    violations = check("doc.md", ["````text", "```", "inner", "```"])

    assert [v.line for v in violations] == [1]


def test_opposite_marker_lines_do_not_close_an_open_fence():
    violations = check("doc.md", ["```python", "~~~", "content", "~~~"])

    assert [v.line for v in violations] == [1]


def test_closing_line_with_an_info_string_at_eof_leaves_the_fence_unclosed():
    violations = check("doc.md", ["```", "content", "```python"])

    assert [v.line for v in violations] == [1]


def test_prose_line_starting_with_backticks_and_containing_one_is_not_an_unclosed_fence():
    assert check("doc.md", ["``` is how a fence starts with `x`", "plain text"]) == []


def test_violation_carries_the_file_and_message():
    violations = check("docs/a.md", ["```python", "content"])

    assert violations[0].file == "docs/a.md"
    assert violations[0].message == "fenced code block is never closed"
