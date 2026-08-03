# mdlint — Vision

## Mission

A fast, dependency-light Markdown linter with a rule-per-check architecture.
Each rule is independently implemented, independently tested, and independently
documented.

## Why this project exists

This is a **platform test vehicle** for the Forge framework. It measures
product-build autonomy — the daemon's ability to build software for a user —
as distinct from the self-maintenance autonomy measured on forge-framework
itself. See `.planning/EXPERIMENT.md` for the pre-registered protocol.

The product is real and should work. The measurement is the point.

## Product shape

`mdlint` walks Markdown files, applies a registry of independent rules, and
reports violations with file, line, rule ID, and message. Rules are additive:
adding a rule must never require changing another rule.

<!-- MACHINE-READABLE GOALS -->
<!-- The goal parser needs the exact "### Period:" header and a pipe-table
     with Gn IDs in the format: | Gn: Name | Description | Success metric | Owner |
     "dependsOn: Gn" inside the Description column gates scheduling so the rule
     families are not attempted before the core engine exists. -->

### Period: 2026-Q3 [status: active]

| Goal | Description | Success metric | Owner |
|------|-------------|----------------|-------|
| G1: Core engine | CLI entry point, file walker, rule registry, violation reporting | `mdlint FILE.md` prints violations with file, line, rule ID and message, exits 1 when any violation is found and 0 when clean | cli-developer |
| G2: Structure rules | Heading-related lint rules dependsOn: G1 | Three rules implemented with tests: first line is a top-level heading, heading levels increment by one, no duplicate sibling headings | cli-developer |
| G3: Whitespace rules | Whitespace and line-ending lint rules dependsOn: G1 | Four rules implemented with tests: no trailing spaces, no hard tabs, no consecutive blank lines, file ends with a single newline | cli-developer |
| G4: Link rules | Link integrity lint rules dependsOn: G1 | Three rules implemented with tests: relative link targets exist on disk, no empty link text, no bare URLs outside code spans | cli-developer |
| G5: Code fence rules | Fenced code block lint rules dependsOn: G1 | Three rules implemented with tests: every fence declares a language, every fence is closed, fence marker style is consistent within a file | cli-developer |
| G6: List and table rules | List and table lint rules dependsOn: G1 | Three rules implemented with tests: consistent unordered list markers, ordered list numbering is sequential, table rows have equal column counts | cli-developer |
| G7: CLI and config | Usability surface dependsOn: G1 | Four features implemented with tests: --fix applies safe autofixes, .mdlintrc config file selects enabled rules, --format supports text and json, --ignore accepts glob patterns | cli-developer |
| G8: Quality | Test coverage of the linter dependsOn: G1 | pytest line coverage of the mdlint package at 80 percent or above, measured by coverage.json and not estimated | qa-engineer |
| G9: Docs | User-facing documentation dependsOn: G1 | README documents install and usage, and a rule reference page documents every implemented rule with an example of passing and failing input | tech-writer |

---

## Rule ID convention

Rules are identified `MD<family><nn>`, e.g. `MDS01` (structure), `MDW01`
(whitespace), `MDL01` (link), `MDF01` (fence), `MDT01` (list/table). A rule
ships with: the check, a test for the passing case, a test for the failing
case, and a row in the rule reference.

## Non-goals

- Not a formatter. `--fix` applies only unambiguous, safe autofixes.
- No config-format bikeshedding. One `.mdlintrc`, INI-style, nothing more.
- No plugin system. Rules live in the repo.
- No performance work until correctness is complete.

## Organizational Structure

- **cli-developer** — implements the engine, the rules, and the CLI surface
- **qa-engineer** — owns test coverage and the test suite's honesty
- **tech-writer** — owns README and the rule reference
