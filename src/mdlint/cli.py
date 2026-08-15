"""Command-line entry point for mdlint."""

import argparse
import sys
from pathlib import Path

from mdlint.engine import lint_lines

READ_ERRORS = (FileNotFoundError, IsADirectoryError, PermissionError, UnicodeDecodeError)


def main(argv: list[str] | None = None) -> int:
    """Lint the given files and print violations, returning the process exit code."""
    parser = argparse.ArgumentParser(prog="mdlint")
    parser.add_argument("files", nargs="+")
    args = parser.parse_args(argv)

    had_violations = False
    had_errors = False

    for file in args.files:
        try:
            # split("\n"), not splitlines(): MDW04 needs to tell "no trailing
            # newline" apart from "one trailing newline", which splitlines()
            # can't distinguish since it discards the newline entirely.
            lines = Path(file).read_text(encoding="utf-8").split("\n")
        except READ_ERRORS as err:
            print(f"mdlint: {file}: {err}", file=sys.stderr)
            had_errors = True
            continue

        for violation in lint_lines(file, lines):
            had_violations = True
            print(f"{violation.file}:{violation.line}: {violation.rule_id} {violation.message}")

    if had_errors:
        return 2
    if had_violations:
        return 1
    return 0
