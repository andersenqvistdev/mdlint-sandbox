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


def test_closing_fence_with_info_string_does_not_close():
    # A line that looks like a closer but carries an info string is not a
    # close per CommonMark; the fence stays open and content continues.
    lines = ["```markdown", "Some sample text.", "```python", "more sample text", "```"]

    blocks = list(iter_fence_blocks(lines))

    assert blocks == [FenceBlock(marker="`", length=3, info="markdown", open_line=1, close_line=5)]


def test_fences_stay_paired_after_a_closer_with_info_string():
    # The full acceptance-corpus scenario: a sample block containing an
    # illustrative fence line with an info string must not desync fence
    # tracking for the rest of the document. Both blocks stay balanced and
    # the second (bare) fence is a genuine, separate opening.
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


def test_backtick_fence_info_string_cannot_contain_a_backtick():
    # A prose line starting with three-or-more backticks followed by a
    # backtick elsewhere on the line (e.g. `` ```like `this` `` in running
    # text) is not a valid opening fence per CommonMark and must not open
    # a phantom block.
    lines = ["```prose with a `backtick` in it", "this is just a paragraph"]

    assert list(iter_fence_blocks(lines)) == []


def test_tilde_fence_info_string_may_contain_a_backtick():
    # The backtick restriction is specific to backtick fences.
    lines = ["~~~text with a `backtick`", "content", "~~~"]

    blocks = list(iter_fence_blocks(lines))

    assert blocks == [
        FenceBlock(marker="~", length=3, info="text with a `backtick`", open_line=1, close_line=3)
    ]
