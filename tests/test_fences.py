"""Tests for the shared fence parser used by the MDF rules."""

from mdlint.fences import FenceBlock, fence_marker_span, fenced_line_numbers, iter_fence_blocks


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


def test_tab_between_marker_and_info_string_is_not_part_of_the_language():
    lines = ["```\tpython", "code", "```"]

    blocks = list(iter_fence_blocks(lines))

    assert blocks == [FenceBlock(marker="`", length=3, info="python", open_line=1, close_line=3)]


def test_closing_fence_indentation_is_independent_of_the_opening_fences():
    """A closer's own indentation (0-3 spaces) is all that matters, per CommonMark.

    The opening fence here has no indentation while its closer has two spaces;
    the mismatch must not stop the closer from closing the block.
    """
    lines = ["```python", "code", "  ```"]

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


def test_fenced_line_numbers_covers_the_open_and_close_lines_inclusive():
    lines = ["prose", "```python", "code", "```", "prose"]

    assert fenced_line_numbers(lines) == {2, 3, 4}


def test_fenced_line_numbers_extends_to_end_of_file_for_an_unclosed_fence():
    lines = ["prose", "```python", "code"]

    assert fenced_line_numbers(lines) == {2, 3}


def test_fenced_line_numbers_covers_multiple_blocks():
    lines = ["```", "one", "```", "text", "~~~", "two", "~~~"]

    assert fenced_line_numbers(lines) == {1, 2, 3, 5, 6, 7}


def test_fenced_line_numbers_empty_for_a_document_with_no_fences():
    assert fenced_line_numbers(["plain text", "more text"]) == set()


def test_longer_closing_run_closes_a_shorter_opening_fence():
    lines = ["```python", "code", "`````"]

    blocks = list(iter_fence_blocks(lines))

    assert blocks == [FenceBlock(marker="`", length=3, info="python", open_line=1, close_line=3)]


def test_closing_fence_may_have_trailing_whitespace():
    lines = ["~~~text", "content", "~~~  \t"]

    blocks = list(iter_fence_blocks(lines))

    assert blocks == [FenceBlock(marker="~", length=3, info="text", open_line=1, close_line=3)]


def test_whitespace_only_info_string_is_empty():
    lines = ["```   ", "content", "```"]

    blocks = list(iter_fence_blocks(lines))

    assert blocks == [FenceBlock(marker="`", length=3, info="", open_line=1, close_line=3)]


def test_shorter_fence_inside_a_longer_one_is_content_not_a_nested_block():
    lines = ["````markdown", "```python", "print('hi')", "```", "````"]

    blocks = list(iter_fence_blocks(lines))

    assert blocks == [FenceBlock(marker="`", length=4, info="markdown", open_line=1, close_line=5)]


def test_tilde_fence_is_not_closed_by_a_backtick_line():
    lines = ["~~~text", "```", "content", "~~~"]

    blocks = list(iter_fence_blocks(lines))

    assert blocks == [FenceBlock(marker="~", length=3, info="text", open_line=1, close_line=4)]


def test_two_marker_run_is_not_a_fence():
    assert list(iter_fence_blocks(["``", "text", "``", "~~", "text", "~~"])) == []


def test_empty_document_yields_nothing():
    assert list(iter_fence_blocks([])) == []


def test_fence_marker_span_accounts_for_indentation():
    assert fence_marker_span("  ~~~~text") == (2, 6)


def test_fence_marker_span_is_purely_lexical_about_the_info_string():
    """fence_marker_span only locates the marker run; it doesn't validate the info.

    Callers get their fence lines from iter_fence_blocks, which already rejects
    a backtick fence whose info contains a backtick.
    """
    assert fence_marker_span("```a`b") == (0, 3)


def test_fenced_line_numbers_ignores_prose_that_only_looks_like_a_fence():
    lines = ["``` not `a` fence", "text", "```python", "code", "```"]

    assert fenced_line_numbers(lines) == {3, 4, 5}


def test_closing_run_longer_than_a_tilde_opener_closes_it():
    lines = ["~~~text", "content", "~~~~~~"]

    blocks = list(iter_fence_blocks(lines))

    assert blocks == [FenceBlock(marker="~", length=3, info="text", open_line=1, close_line=3)]


def test_info_string_may_be_an_attribute_block():
    lines = ["``` {.python}", "code", "```"]

    blocks = list(iter_fence_blocks(lines))

    assert blocks == [FenceBlock(marker="`", length=3, info="{.python}", open_line=1, close_line=3)]


def test_a_closing_line_with_an_info_string_at_eof_leaves_the_fence_unclosed():
    lines = ["```", "content", "```python"]

    blocks = list(iter_fence_blocks(lines))

    assert blocks == [FenceBlock(marker="`", length=3, info="", open_line=1, close_line=None)]


def test_fenced_line_numbers_covers_an_outer_fence_that_contains_a_shorter_one():
    lines = ["````markdown", "```", "inner", "```", "````", "prose"]

    assert fenced_line_numbers(lines) == {1, 2, 3, 4, 5}


def test_fenced_line_numbers_is_not_desynced_by_a_tilde_line_inside_a_backtick_fence():
    lines = ["```python", "~~~", "code", "```", "prose", "~~~text", "more", "~~~"]

    assert fenced_line_numbers(lines) == {1, 2, 3, 4, 6, 7, 8}


def test_tab_indented_fence_is_not_a_fence():
    """A tab counts as four columns of indentation, so it can't open a fence."""
    lines = ["\t```python", "code", "\t```"]

    assert list(iter_fence_blocks(lines)) == []


def test_tab_indented_line_does_not_close_an_open_fence():
    lines = ["```python", "code", "\t```"]

    blocks = list(iter_fence_blocks(lines))

    assert blocks == [FenceBlock(marker="`", length=3, info="python", open_line=1, close_line=None)]
