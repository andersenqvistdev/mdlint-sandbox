# Rule reference

Every rule mdlint implements, grouped by family. Each entry shows the rule
id, what it checks, and an example of markdown that passes and one that
fails.

Rule ids follow `MD<family><nn>`: `MDS` (structure), `MDW` (whitespace),
`MDL` (link), `MDF` (fence), `MDT` (list/table). A rule ships with its
check, a passing test, a failing test, and the row below — see
`.company/vision.md` for the convention and `tests/rules/` for the tests
backing each example.

## Structure (`MDS`)

### MDS01 — first-line-heading

The first non-blank line of a document must be a top-level (`#`) heading.

Passing:

```markdown
# Getting started

Install the package, then run the CLI.
```

Failing:

```markdown
## Getting started

Install the package, then run the CLI.
```

`docs/example.md:1: MDS01 first line should be a top-level (H1) heading`

### MDS02 — heading-increment

Heading levels must not skip a level on the way up. Dropping back down (e.g.
H3 followed by H1) is always fine.

Passing:

```markdown
# Guide

## Setup

### Requirements
```

Failing:

```markdown
# Guide

### Requirements
```

`docs/example.md:3: MDS02 heading level jumps from H1 to H3; increment by one level at a time`

### MDS03 — no-duplicate-siblings

Sibling headings (same parent, same level) must not repeat the same text.
Headings with identical text under *different* parents are unrelated and
not flagged.

Passing:

```markdown
# Guide

## Installation

## Configuration
```

Failing:

```markdown
# Guide

## Installation

## Installation
```

`docs/example.md:5: MDS03 duplicate sibling heading: 'Installation'`

## Whitespace (`MDW`)

### MDW01 — no-trailing-spaces

Lines must not end with trailing space characters.

Passing:

```markdown
This line has no trailing whitespace.
```

Failing (the second line below ends with two trailing spaces):

```markdown
This line has trailing whitespace.  
```

`docs/example.md:1: MDW01 line has trailing space(s)`

### MDW02 — no-hard-tabs

Lines must not contain hard tab characters; use spaces for indentation.

Passing:

```markdown
    Indented with four spaces.
```

Failing (the line below is indented with a tab character):

```markdown
	Indented with a tab.
```

`docs/example.md:1: MDW02 line contains a hard tab; use spaces for indentation`

### MDW03 — no-consecutive-blank-lines

Documents must not contain two or more consecutive blank lines; collapse
runs down to a single blank line.

Passing:

```markdown
Paragraph one.

Paragraph two.
```

Failing:

```markdown
Paragraph one.


Paragraph two.
```

`docs/example.md:3: MDW03 consecutive blank lines; collapse to a single blank line`

### MDW04 — final-newline

A document must end with exactly one trailing newline — not zero, not
several.

Passing (file bytes, `␊` marking a newline):

```text
# Title␊
␊
Body text.␊
```

Failing — missing the final newline:

```text
# Title␊
␊
Body text.
```

`docs/example.md:3: MDW04 file does not end with a newline`

Failing — extra trailing blank lines:

```text
# Title␊
␊
Body text.␊
␊
␊
```

`docs/example.md:5: MDW04 file ends with extra blank line(s); expected a single trailing newline`

## Link (`MDL`)

### MDL01 — link-target-exists

Relative link and image targets must resolve to a file on disk. URLs with a
scheme (`https://`, `mailto:`, ...), absolute paths, and same-document
anchors (`#section`) are out of scope.

Passing (assuming `CHANGELOG.md` exists next to the linting document):

```markdown
See the [changelog](CHANGELOG.md) for release notes.
```

Failing (assuming `MISSING.md` does not exist):

```markdown
See the [changelog](MISSING.md) for release notes.
```

`docs/example.md:1: MDL01 link target 'MISSING.md' does not exist on disk`

### MDL02 — no-empty-link-text

Link text must not be empty or whitespace-only. Empty image alt text
(`![](img.png)`) is exempt — it marks a decorative image, not a broken
link.

Passing:

```markdown
Read the [mdlint documentation](https://example.com/docs).
```

Failing:

```markdown
Read the [](https://example.com/docs).
```

`docs/example.md:1: MDL02 link to 'https://example.com/docs' has empty link text`

### MDL03 — no-bare-urls

A raw URL outside of link syntax or a code span must be wrapped — either as
an autolink (`<https://example.com>`) or a markdown link.

Passing:

```markdown
See <https://example.com> for details.
```

Failing:

```markdown
See https://example.com for details.
```

`docs/example.md:1: MDL03 bare URL 'https://example.com' should be wrapped in <> or a markdown link`

## Fence (`MDF`)

### MDF01 — fence-language-required

Every fenced code block must declare a language in its info string (e.g.
```` ```python ```` rather than a bare ```` ``` ````).

Passing:

````markdown
```python
print("hello")
```
````

Failing:

````markdown
```
print("hello")
```
````

`docs/example.md:1: MDF01 fenced code block does not declare a language`

### MDF02 — fence-closed

Every fence opened in a document must be closed before the end of the file.
An unclosed fence silently swallows everything after it into a single code
block.

Passing:

````markdown
```python
print("hello")
```
````

Failing (the fence below is opened but never closed):

````text
```python
print("hello")
````

`docs/example.md:1: MDF02 fenced code block is never closed`

### MDF03 — consistent-fence-marker

The first fence character (backtick or tilde) encountered in a document sets
the expected marker; every later fence opened with the other character is
flagged.

Passing:

````markdown
```python
one
```

```text
two
```
````

Failing:

````markdown
```python
one
```

~~~text
two
~~~
````

``docs/example.md:5: MDF03 fence marker '~' is inconsistent; file uses '`'``

## List and table (`MDT`)

### MDT01 — consistent-unordered-markers

The first bullet marker (`-`, `*`, or `+`) encountered in a document sets
the expected marker; every later bullet using a different marker is
flagged, regardless of list or nesting level.

Passing:

```markdown
- one
- two
- three
```

Failing:

```markdown
- one
* two
- three
```

`docs/example.md:2: MDT01 list marker '*' is inconsistent; file uses '-'`

### MDT02 — ordered-list-sequential

Ordered list numbers must increase sequentially by one, tracked
independently per indentation level. A list may start at any number, but
each following item must be exactly one more than the previous.

Passing:

```markdown
1. one
2. two
3. three
```

Failing:

```markdown
1. one
3. two
4. three
```

`docs/example.md:2: MDT02 ordered list item is numbered 3; expected 2 to continue the sequence`

### MDT03 — table-column-count

Every row in a table must have as many columns as the header row.

Passing:

```markdown
| Name | Version |
| ---- | ------- |
| mdlint | 0.1.0 |
```

Failing:

```markdown
| Name | Version |
| ---- | ------- |
| mdlint | 0.1.0 | stable |
```

`docs/example.md:3: MDT03 table row has 3 column(s); expected 2 to match the header`
