# mdlint

A fast, dependency-light Markdown linter with a rule-per-check architecture.
Each rule is implemented, tested, and documented independently — see
[`docs/rules.md`](docs/rules.md) for the full rule reference.

## Install

Requires Python 3.11+.

```bash
pip install -e ".[dev]"
```

This installs the `mdlint` console script along with the dev dependencies
(`pytest`, `pytest-cov`, `ruff`) needed to run the test suite.

## Usage

```bash
mdlint FILE.md [FILE.md ...]
```

Pass one or more Markdown files. mdlint prints one line per violation and
exits with a status code that reflects what it found:

```text
docs/example.md:3: MDW01 line has trailing space(s)
docs/example.md:7: MDS02 heading level jumps from H1 to H3; increment by one level at a time
```

Each line has the form `FILE:LINE: RULE_ID message`.

### Exit codes

| Code | Meaning |
|------|---------|
| `0`  | No violations found |
| `1`  | One or more violations found |
| `2`  | A file couldn't be read, or the config file is invalid |

### Options

| Flag | Description |
|------|-------------|
| `--fix` | Apply safe autofixes in place before reporting remaining violations |
| `--format {text,json}` | Output format (default: `text`) |
| `--ignore PATTERN` | Glob pattern to skip; may be passed more than once |
| `--config PATH` | Path to the config file (default: `.mdlintrc` in the current directory) |

### Autofix

```bash
mdlint --fix docs/*.md
```

`--fix` only rewrites violations that have one unambiguous, safe correction
(e.g. normalizing list markers or wrapping a bare URL). Violations without a
safe fix — like a missing top-level heading — are left for you to fix by hand
and are still reported.

### JSON output

```bash
mdlint --format json docs/*.md
```

```json
{
  "violations": [
    {"file": "docs/example.md", "line": 3, "rule_id": "MDW01", "message": "line has trailing space(s)"}
  ],
  "errors": []
}
```

### Ignoring files

```bash
mdlint --ignore "CHANGELOG.md" --ignore "vendor/*" docs/**/*.md
```

`--ignore` matches against both the full path and the file's base name, so a
bare filename pattern like `CHANGELOG.md` matches regardless of which
directory it's passed in.

## Configuration

By default, every registered rule runs. To run a subset, add a `.mdlintrc`
file (JSON) to the directory you run `mdlint` from:

```json
{
  "enabled": ["MDS01", "MDS02", "MDW01", "MDW02"]
}
```

Only the listed rule ids run. Omit `.mdlintrc` (or omit the `"enabled"` key)
to run every rule. Use `--config PATH` to point at a config file in a
different location.

## Rules

mdlint currently implements 13 rules across three families — structure
(`MDS`), whitespace (`MDW`), link (`MDL`), and list/table (`MDT`). See
[`docs/rules.md`](docs/rules.md) for every rule with a passing and failing
example.

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
ruff format --check .
```
