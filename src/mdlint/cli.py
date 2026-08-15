"""Command-line entry point for mdlint."""

import argparse
import fnmatch
import json
import sys
from pathlib import Path

from mdlint.config import ConfigError, load_enabled_rule_ids
from mdlint.engine import apply_fixes, lint_lines
from mdlint.rules import Rule, all_rules
from mdlint.violation import Violation

READ_ERRORS = (FileNotFoundError, IsADirectoryError, PermissionError, UnicodeDecodeError)

DEFAULT_CONFIG_NAME = ".mdlintrc"


def _resolve_rules(config_path: Path) -> list[Rule]:
    """Return the rules to run, filtered by the config file's "enabled" list."""
    enabled_ids = load_enabled_rule_ids(config_path)
    if enabled_ids is None:
        return all_rules()
    enabled = set(enabled_ids)
    return [rule for rule in all_rules() if rule.id in enabled]


def _is_ignored(file: str, patterns: list[str]) -> bool:
    """Return True if file matches any --ignore glob pattern."""
    name = Path(file).name
    return any(
        fnmatch.fnmatch(file, pattern) or fnmatch.fnmatch(name, pattern) for pattern in patterns
    )


def _print_text(violations: list[Violation]) -> None:
    for violation in violations:
        print(f"{violation.file}:{violation.line}: {violation.rule_id} {violation.message}")


def main(argv: list[str] | None = None) -> int:
    """Lint the given files and print violations, returning the process exit code."""
    parser = argparse.ArgumentParser(prog="mdlint")
    parser.add_argument("files", nargs="+")
    parser.add_argument("--fix", action="store_true", help="apply safe autofixes in place")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="output format")
    parser.add_argument(
        "--ignore", action="append", default=[], metavar="PATTERN", help="glob pattern to skip"
    )
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG_NAME,
        metavar="PATH",
        help=f"path to config file (default: {DEFAULT_CONFIG_NAME} in the current directory)",
    )
    args = parser.parse_args(argv)

    try:
        rules = _resolve_rules(Path(args.config))
    except ConfigError as err:
        print(f"mdlint: {err}", file=sys.stderr)
        return 2

    had_violations = False
    had_errors = False
    all_violations: list[Violation] = []
    errors: list[dict[str, str]] = []

    for file in args.files:
        if _is_ignored(file, args.ignore):
            continue

        try:
            # split("\n"), not splitlines(): MDW04 needs to tell "no trailing
            # newline" apart from "one trailing newline", which splitlines()
            # can't distinguish since it discards the newline entirely.
            lines = Path(file).read_text(encoding="utf-8").split("\n")
        except READ_ERRORS as err:
            print(f"mdlint: {file}: {err}", file=sys.stderr)
            had_errors = True
            errors.append({"file": file, "message": str(err)})
            continue

        if args.fix:
            fixed_lines = apply_fixes(lines, rules)
            if fixed_lines != lines:
                # lines came from split("\n"), so a trailing empty element
                # already represents the file's final newline; joining alone
                # reconstructs the exact text without adding another one.
                Path(file).write_text("\n".join(fixed_lines), encoding="utf-8")
            lines = fixed_lines

        violations = lint_lines(file, lines, rules)
        if violations:
            had_violations = True
        all_violations.extend(violations)

    if args.format == "json":
        payload = {
            "violations": [
                {
                    "file": v.file,
                    "line": v.line,
                    "rule_id": v.rule_id,
                    "message": v.message,
                }
                for v in all_violations
            ],
            "errors": errors,
        }
        print(json.dumps(payload, indent=2))
    else:
        _print_text(all_violations)

    if had_errors:
        return 2
    if had_violations:
        return 1
    return 0
