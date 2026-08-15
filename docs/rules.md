# Rule reference

Every rule lives in its own module under `src/mdlint/rules/` and ships with a
dedicated test file under `tests/rules/`. Rule IDs follow `MD<family><nn>`:
`S` for structure, `L` for link, `T` for list/table.

Each entry below shows a minimal passing input and a minimal failing input
(with the violation `mdlint` reports for it). Examples are excerpts focused
on one rule; linting them as a standalone file may also trigger MDS01 (first
line should be an H1) since they don't open with a top-level heading.

## MDS01 — first-line-heading

The first non-blank line of a document must be a top-level (H1) heading.

**Passing:**

```markdown
# Title

Some content.
```

**Failing:**

```markdown
Some content without a heading.
```

```text
doc.md:1: MDS01 first line should be a top-level (H1) heading
```

## MDS02 — heading-increment

Heading levels must not skip a level when increasing. Dropping back down
(e.g. H3 followed by H1) is always fine; only upward jumps that skip a level
are flagged.

**Passing:**

```markdown
# Title

## Section

### Subsection
```

**Failing:**

```markdown
# Title

### Too deep
```

```text
doc.md:3: MDS02 heading level jumps from H1 to H3; increment by one level at a time
```

## MDS03 — no-duplicate-siblings

Sibling headings (same parent, same level) must not repeat text. Headings
with the same text under *different* parents are unrelated and not flagged.

**Passing:**

```markdown
# Title

## Section

## Another Section
```

**Failing:**

```markdown
# Title

## Section

## Section
```

```text
doc.md:5: MDS03 duplicate sibling heading: 'Section'
```

## MDL01 — link-target-exists

Relative link and image targets must resolve to a file on disk. URLs with a
scheme (`https://`, `mailto:`, ...), absolute paths, and bare same-document
anchors (`#section`) are out of scope.

**Passing:**

```markdown
See [the license](README.md) for details.
```

**Failing:**

```markdown
See [the license](MISSING.md) for details.
```

```text
doc.md:1: MDL01 link target 'MISSING.md' does not exist on disk
```

## MDL02 — no-empty-link-text

A link's visible text must not be empty or whitespace-only. Image alt text is
exempt — an empty alt (`![](img.png)`) marks a decorative image and is valid.

**Passing:**

```markdown
See the [project README](README.md) for details.
```

**Failing:**

```markdown
See the [](README.md) for details.
```

```text
doc.md:1: MDL02 link to 'README.md' has empty link text
```

## MDL03 — no-bare-urls

An `http(s)://` URL outside a code span must be wrapped as an autolink
(`<https://example.com>`) or a markdown link, not dropped into prose bare.

**Passing:**

```markdown
See <https://example.com> for details.
```

**Failing:**

```markdown
See https://example.com for details.
```

```text
doc.md:1: MDL03 bare URL 'https://example.com' should be wrapped in <> or a markdown link
```

## MDT01 — consistent-unordered-markers

Unordered list markers (`-`, `*`, `+`) must be consistent within a document.
The first bullet marker encountered sets the file's expected marker.

**Passing:**

```markdown
- one
- two
- three
```

**Failing:**

```markdown
- one
* two
```

```text
doc.md:2: MDT01 list marker '*' is inconsistent; file uses '-'
```

## MDT02 — ordered-list-sequential

Ordered list numbers must increase sequentially by one. A list may start at
any number, but each following item at the same indentation must be exactly
one more than the previous.

**Passing:**

```markdown
1. one
2. two
3. three
```

**Failing:**

```markdown
1. one
3. two
```

```text
doc.md:2: MDT02 ordered list item is numbered 3; expected 2 to continue the sequence
```

## MDT03 — table-column-count

Every row in a table must have as many columns as the header row. A table is
a header row immediately followed by a delimiter row (`---`-style cells).

**Passing:**

```markdown
| A | B |
| - | - |
| 1 | 2 |
```

**Failing:**

```markdown
| A | B |
| - | - |
| 1 |
```

```text
doc.md:3: MDT03 table row has 1 column(s); expected 2 to match the header
```
