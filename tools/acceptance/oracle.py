"""Structural ground truth for Markdown documents, from a reference CommonMark parser.

This module deliberately knows NOTHING about mdlint. It answers only questions of
the form "what does CommonMark say this document contains?" — fenced code blocks,
headings, inline links. The acceptance checker compares mdlint's reported
violations against these answers.

That separation is the whole point. mdlint's own test suite was written by the same
process that wrote mdlint, so it certifies mdlint's bugs as correct behaviour. A
reference implementation cannot: markdown-it-py has no knowledge of, and no stake
in, how mdlint chose to parse anything.

markdown-it-py is NOT a runtime dependency of mdlint. It is installed only for the
acceptance job (the ``acceptance`` optional extra), so mdlint itself stays
dependency-light as advertised.
"""

from __future__ import annotations

from markdown_it import MarkdownIt

# "commonmark" preset = strict CommonMark, no GFM extensions. Strictness matters:
# the checker must not fail mdlint for declining to implement a non-standard
# extension, only for disagreeing about actual CommonMark.
_PARSER = MarkdownIt("commonmark")


def _tokens(text: str) -> list:
    return _PARSER.parse(text)


def fenced_blocks(text: str) -> list[dict]:
    """Every fenced code block, as CommonMark understands it.

    ``line`` is the 1-based line on which the block OPENS. ``info`` is the info
    string (the "language"), stripped. ``marker`` is the fence character run.
    """
    blocks = []
    for tok in _tokens(text):
        if tok.type != "fence" or tok.map is None:
            continue
        blocks.append(
            {
                "line": tok.map[0] + 1,
                "info": (tok.info or "").strip(),
                "marker": tok.markup,
            }
        )
    return blocks


def headings(text: str) -> list[dict]:
    """Every heading, ATX (``# x``) and setext (``x`` over ``===``) alike.

    Setext headings are the reason this exists: they are ordinary CommonMark and
    a linter that cannot see them will both invent violations and miss real ones.
    ``text`` is the rendered inline content (markup stripped), the same shape of
    "what a reader actually sees" that ``_plain_text`` produces for link text.
    """
    tokens = _tokens(text)
    out = []
    for i, tok in enumerate(tokens):
        if tok.type != "heading_open" or tok.map is None:
            continue
        inline = tokens[i + 1] if i + 1 < len(tokens) else None
        content = _plain_text(inline.children or []) if inline and inline.type == "inline" else ""
        out.append({"line": tok.map[0] + 1, "level": int(tok.tag[1:]), "text": content.strip()})
    return out


def _plain_text(children) -> str:
    """Rendered text of an inline run, with markup removed.

    A code span contributes its CONTENT, because that is what a reader sees. This
    is exactly where mdlint goes wrong: it blanks code spans before parsing links,
    so ``[`docs/x.md`](x.md)`` looks like it has empty link text.
    """
    parts = []
    for child in children:
        if child.type in ("text", "code_inline"):
            parts.append(child.content)
        elif child.type == "softbreak":
            parts.append(" ")
        elif child.type == "hardbreak":
            parts.append(" ")
    return "".join(parts)


def inline_links(text: str) -> list[dict]:
    """Every inline link, with the text a reader actually sees and its destination.

    Images are excluded: an empty alt text is valid, meaningful CommonMark (a
    decorative image), not a defect — mdlint agrees on that point.
    """
    links = []
    for tok in _tokens(text):
        if tok.type != "inline" or not tok.children:
            continue
        depth = 0
        buf: list = []
        href = ""
        for child in tok.children:
            if child.type == "link_open":
                if depth == 0:
                    href = child.attrGet("href") or ""
                    buf = []
                depth += 1
            elif child.type == "link_close":
                depth -= 1
                if depth == 0:
                    links.append({"text": _plain_text(buf), "href": href})
            elif depth > 0:
                buf.append(child)
    return links


def empty_text_link_targets(text: str) -> set[str]:
    """Destinations of links whose visible text is empty — the true MDL02 set."""
    return {link["href"] for link in inline_links(text) if link["text"].strip() == ""}


def undeclared_fence_lines(text: str) -> set[int]:
    """Opening lines of fenced blocks with no language — the true MDF01 set."""
    return {b["line"] for b in fenced_blocks(text) if b["info"] == ""}


def _is_closing_line(line: str, marker: str) -> bool:
    """True when line is a valid CommonMark closer for a fence opened with marker.

    A closer needs 0-3 leading spaces, a run of the same character at least as
    long as the opener, and nothing but whitespace after that run (an info
    string there makes it content, not a close).
    """
    stripped = line.lstrip(" ")
    if len(line) - len(stripped) > 3:
        return False
    char = marker[0]
    run_len = len(stripped) - len(stripped.lstrip(char))
    if run_len < len(marker):
        return False
    return stripped[run_len:].strip() == ""


def unclosed_fence_lines(text: str) -> set[int]:
    """Opening lines of fenced blocks with no matching closer — the true MDF02 set.

    CommonMark lets a fence run to EOF with no closer, and ``tok.map`` covers
    that case identically to an explicit close. So this checks the raw line at
    the block's end directly, rather than trusting that the parser found one.
    """
    lines = text.split("\n")
    unclosed = set()
    for tok in _tokens(text):
        if tok.type != "fence" or tok.map is None:
            continue
        end = tok.map[1]
        last_line = lines[end - 1] if 0 <= end - 1 < len(lines) else ""
        if not _is_closing_line(last_line, tok.markup):
            unclosed.add(tok.map[0] + 1)
    return unclosed


def heading_jump_lines(text: str) -> set[int]:
    """Lines of headings that skip a level — the true MDS02 set.

    The first heading establishes the baseline and can never be a jump.
    """
    jumps = set()
    previous = None
    for head in headings(text):
        if previous is not None and head["level"] - previous > 1:
            jumps.add(head["line"])
        previous = head["level"]
    return jumps


def duplicate_sibling_lines(text: str) -> set[int]:
    """Lines of headings that repeat an earlier sibling's text — the true MDS03 set.

    A sibling is a heading at the same level under the same chain of ancestors;
    the same text under a different parent is unrelated and not a duplicate.
    """
    duplicates = set()
    ancestors: list[tuple[int, str]] = []
    children_seen: dict[tuple[tuple[int, str], ...], set[str]] = {}
    for head in headings(text):
        while ancestors and ancestors[-1][0] >= head["level"]:
            ancestors.pop()
        siblings = children_seen.setdefault(tuple(ancestors), set())
        if head["text"] in siblings:
            duplicates.add(head["line"])
        else:
            siblings.add(head["text"])
        ancestors.append((head["level"], head["text"]))
    return duplicates


def starts_with_h1(text: str) -> bool:
    """True when the document's first heading is a level-1 heading on its first block.

    Used only to detect MDS01 FALSE POSITIVES — documents that plainly do open with
    a top-level heading and must therefore never be reported.
    """
    heads = headings(text)
    if not heads:
        return False
    return heads[0]["level"] == 1
