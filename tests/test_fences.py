"""Tests for the shared fence parser used by the MDF rules."""

from mdlint.fences import FenceBlock, fence_marker_span, iter_fence_blocks


def test_fence_marker_span_returns_none_for_non_fence_line():
    assert fence_marker_span("just a sentence.") is None


def test_fence_marker_span_returns_the_marker_run():
    assert fence_marker_span("```python") == (0, 3)


def test_extracts_a_single_closed_fence_with_language():
    lines = ["```python", "print('hi')", "```"]

    blocks = list(iter_fence_blocks(lines))

    assert blocks == [FenceBlock(marker="`", length=3, info="python", open_line=1, close_line=3)]


def test_extracts_a_fence_with_no_language():
    lines = ["```", "plain text", "```"]

    blocks = list(iter_fence_blocks(lines))

    assert blocks == [FenceBlock(marker="`", length=3, info="", open_line=1, close_line=3)]


def test_unclosed_fence_has_close_line_none():
    lines = ["```python", "print('hi')"]

    blocks = list(iter_fence_blocks(lines))

    assert blocks == [FenceBlock(marker="`", length=3, info="python", open_line=1, close_line=None)]


def test_tilde_fences_are_recognized():
    lines = ["~~~text", "content", "~~~"]

    blocks = list(iter_fence_blocks(lines))

    assert blocks == [FenceBlock(marker="~", length=3, info="text", open_line=1, close_line=3)]


def test_backtick_fence_is_not_closed_by_a_tilde_line():
    lines = ["```python", "~~~", "print('hi')", "```"]

    blocks = list(iter_fence_blocks(lines))

    assert blocks == [FenceBlock(marker="`", length=3, info="python", open_line=1, close_line=4)]


def test_closing_fence_must_be_at_least_as_long_as_opening():
    lines = ["````python", "```", "content", "````"]

    blocks = list(iter_fence_blocks(lines))

    assert blocks == [FenceBlock(marker="`", length=4, info="python", open_line=1, close_line=4)]


def test_extracts_multiple_sequential_fences():
    lines = ["```python", "one", "```", "text", "~~~text", "two", "~~~"]

    blocks = list(iter_fence_blocks(lines))

    assert blocks == [
        FenceBlock(marker="`", length=3, info="python", open_line=1, close_line=3),
        FenceBlock(marker="~", length=3, info="text", open_line=5, close_line=7),
    ]


def test_document_with_no_fences_yields_nothing():
    assert list(iter_fence_blocks(["plain text", "more text"])) == []


def test_closing_line_with_info_string_does_not_close_the_fence():
    """A line with an info string is content, per CommonMark's closing-fence rule."""
    lines = ["```markdown", "Some sample text.", "```python", "more sample text", "```"]

    blocks = list(iter_fence_blocks(lines))

    assert blocks == [FenceBlock(marker="`", length=3, info="markdown", open_line=1, close_line=5)]


def test_bare_fence_after_a_sample_block_is_still_a_real_open_and_close():
    """Fences remain correctly paired for everything that follows a desync-prone block."""
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

    blocks = list(iter_fence_blocks(lines))

    assert blocks == [
        FenceBlock(marker="`", length=3, info="markdown", open_line=1, close_line=5),
        FenceBlock(marker="`", length=3, info="", open_line=7, close_line=9),
    ]


def test_backtick_in_a_backtick_fences_info_string_is_not_a_fence_line():
    """CommonMark forbids backticks in a backtick fence's info string.

    A prose line that happens to start with three backticks and also contains
    a backtick later on (e.g. documentation about fences) must not open a
    phantom block.
    """
    lines = [
        "```` ```python ```` rather than a bare ```` ``` ````).",
        "```python",
        "real code",
        "```",
    ]

    blocks = list(iter_fence_blocks(lines))

    assert blocks == [FenceBlock(marker="`", length=3, info="python", open_line=2, close_line=4)]


def test_tilde_fence_info_string_may_contain_backticks():
    lines = ["~~~ `inline code` in info", "content", "~~~"]

    blocks = list(iter_fence_blocks(lines))

    assert blocks == [
        FenceBlock(marker="~", length=3, info="`inline code` in info", open_line=1, close_line=3)
    ]


def test_fence_indented_by_up_to_three_spaces_is_recognized():
    lines = ["   ```python", "code", "   ```"]

    blocks = list(iter_fence_blocks(lines))

    assert blocks == [FenceBlock(marker="`", length=3, info="python", open_line=1, close_line=3)]


def test_fence_indented_by_four_or_more_spaces_is_not_a_fence():
    """Four spaces of indentation makes this an indented code block, not a fence.

    Per CommonMark, only 0-3 spaces of leading indentation permit a fence; a
    fourth space means the line is indented code and must not be mistaken for
    a fence opener or closer.
    """
    lines = ["    ```", "not a real fence, this is indented code", "    ```"]

    assert list(iter_fence_blocks(lines)) == []
