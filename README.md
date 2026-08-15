# mdlint

A fast, dependency-light Markdown linter with a rule-per-check architecture.

> Status: under construction. See `.company/vision.md` for the goal set.

## Install

```bash
pip install -e ".[dev]"
```

This installs the `mdlint` console script along with the dev dependencies
(`pytest`, `pytest-cov`, `ruff`) used to run the test suite and linter.

## Usage

Run `mdlint` against one or more Markdown files:

```bash
mdlint README.md docs/*.md
```

Each violation is printed on its own line as `file:line: RULE_ID message`:

```text
README.md:1: MDS01 first line should be a top-level (H1) heading
```

Exit codes:

| Code | Meaning |
|------|---------|
| `0`  | No violations found |
| `1`  | One or more violations found |
| `2`  | A file could not be read (missing, unreadable, not valid UTF-8) |

## Rules

Every lint rule mdlint currently implements — with a passing and a failing
example for each — is documented in [`docs/rules.md`](docs/rules.md).

<!-- canary: verifies the PR path end to end -->
