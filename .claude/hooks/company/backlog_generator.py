#!/usr/bin/env python3
"""Signal-driven backlog generation — a work source that does not run dry.

Goal-derived autofill (strategic_planner.autofill_queue_from_goals) is a FINITE
source: it mints only while a goal is unmet. On 2026-08-13 forge-framework had
exhausted every declared source at once —

  - goals: G3/G16 met, G1 blocked on a broken nightly, G13 [OWNER-ONLY],
    G15 cross-repo, G7 a meta-goal about its own autonomy rate;
  - roadmap/scout intake: 17 of 17 tasks handled, 0 schedulable;

so the queue sat empty with a healthy daemon idling. That is not a bug in any
gate: the repo had genuinely finished its declared work. This module adds a
source derived from MEASURABLE REPO SIGNALS rather than declared goals, so the
queue keeps depth after the roadmap is done.

Two constraints shape every design decision here, both learned by measurement:

1. **Admission relevance is the binding constraint, not brief quality.**
   Tasks minted with a gated source (``"planning"``) pass through
   task_admission, whose semantic-relevance judge rejects work that does not
   concretely advance an ACTIVE goal from vision.md. A survey on 2026-08-13
   found 448 functions over 80 lines and 22 modules over 1500 lines — real
   signal, mapping to NO active goal, and therefore rejected as
   process-navel-gazing every cycle. So each Signal declares the goal it
   advances, and a generator with no live goal behind it stays OFF by default.
   Adding a generator is not enough; the goal has to exist.

2. **Every brief must clear the brief-quality standard by construction.**
   A brief needs a pointer to something real plus a measured value. Every
   Signal here names an existing file and carries a number read from a
   measurement, never an estimate.

Usage:
    python backlog_generator.py scan              # dry run, print signals
    python backlog_generator.py scan --limit 5
    python backlog_generator.py mint --limit 5    # actually queue them
"""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Source marker: deliberately a GATED source (see task_admission.GATED_SOURCES)
# so generated work is vetted like any other machine mint. Using an ungated
# source would sneak past the relevance judge, which is the opposite of what
# this module is for.
TASK_SOURCE = "planning"

# Coverage-gap generator thresholds. A file is worth a task when it is both
# meaningfully uncovered AND big enough that closing the gap is real work --
# a 12-statement helper at 40% is noise, not a backlog item.
COVERAGE_MAX_PERCENT = 70.0
COVERAGE_MIN_MISSING_LINES = 25

# Test requirement lines appended to every generated brief. Mirrors the
# standard strategic_planner appends so worker expectations stay identical
# regardless of which source minted the task.
TEST_REQUIREMENT_LINES = (
    "**Test Requirements:**",
    "- New or changed code ships with tests in the same PR",
    "- Lint passes: ruff check and ruff format --check",
    "- One atomic commit; branch + PR, never a direct push to main",
)


@dataclass
class Signal:
    """One unit of generated work, already shaped to clear the gates."""

    generator: str
    goal_id: str
    title: str
    evidence: str
    acceptance: str
    pointers: list[str] = field(default_factory=list)
    complexity: str = "standard"

    def description(self) -> str:
        parts = [
            f"[Signal: {self.generator}] Generated from a measured repository "
            "signal, not from a goal gap.",
            "",
            f"**Goal:** {self.goal_id}",
            "",
            "**Evidence:**",
            self.evidence,
            "",
            "**Acceptance:**",
            self.acceptance,
        ]
        if self.pointers:
            parts += [
                "",
                "**Verified Pointers** (existence checked at generation time): "
                + ", ".join(self.pointers),
            ]
        parts += ["", *TEST_REQUIREMENT_LINES]
        return "\n".join(parts)

    def to_task_kwargs(self) -> dict[str, Any]:
        return {
            "title": self.title[:120],
            "description": self.description(),
            # P3-Normal: signal-derived work must not outrank declared goal work.
            "priority": 3,
            "source": TASK_SOURCE,
            "estimated_complexity": self.complexity,
        }


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------


def _coverage_is_stale(coverage_file: Path, project_root: Path) -> bool:
    """True when the measurement predates the newest Python change.

    Mirrors goal_tracker._read_trusted_coverage's freshness rule: a measurement
    older than the last *.py commit describes code that no longer exists.

    Without this the lane churns. Observed 2026-08-13: PRs #365/#367/#368 landed
    ~770 tests against forge_daemon.py, employee_activator.py and
    dashboard_server.py, but coverage.json still showed the pre-merge gaps, so
    the generator re-proposed those exact three modules, every mint was refused
    as a duplicate of just-completed work, and it would have repeated until the
    next nightly. Yielding nothing on stale input is the honest behaviour --
    same rule as never estimating a number.

    Fails OPEN (treats as fresh) outside git or on any error: a missing git
    binary must not silently disable the only non-goal work source.
    """
    try:
        mtime = coverage_file.stat().st_mtime
    except OSError:
        return True
    try:
        proc = subprocess.run(
            ["git", "log", "-1", "--format=%ct", "--", "*.py"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=15,
        )
        stamp = (proc.stdout or "").strip()
        if proc.returncode != 0 or not stamp:
            return False
        return float(stamp) > mtime
    except Exception:
        return False


def generate_coverage_gaps(
    project_root: Path,
    *,
    goal_id: str = "G1",
    limit: int = 5,
    max_percent: float = COVERAGE_MAX_PERCENT,
    min_missing: int = COVERAGE_MIN_MISSING_LINES,
) -> list[Signal]:
    """Per-file coverage gaps read from a real coverage.json.

    This is the richest goal-aligned signal available: G1 targets coverage, and
    the gap spans the whole hooks package. It reads the SAME trusted file
    goal_tracker._read_trusted_coverage uses, so a stale or missing measurement
    yields NO signals rather than an estimate — the W1-P2 rule (never report a
    number you did not measure) applies to generated work too.
    """
    coverage_file = project_root / "coverage.json"
    if not coverage_file.exists():
        return []
    if _coverage_is_stale(coverage_file, project_root):
        return []
    try:
        data = json.loads(coverage_file.read_text())
    except (OSError, json.JSONDecodeError):
        return []

    files = data.get("files")
    if not isinstance(files, dict):
        return []

    candidates: list[tuple[int, str, float, int]] = []
    for rel_path, entry in files.items():
        if not isinstance(entry, dict):
            continue
        summary = entry.get("summary") or {}
        percent = summary.get("percent_covered")
        missing = summary.get("missing_lines")
        statements = summary.get("num_statements")
        if not isinstance(percent, (int, float)) or not isinstance(missing, int):
            continue
        if percent >= max_percent or missing < min_missing:
            continue
        # Only propose work for files that still exist on disk: coverage.json
        # can outlive a deletion, and a task pointing at a removed file is a
        # hallucinated pointer the admission gate would reject anyway.
        if not (project_root / rel_path).exists():
            continue
        candidates.append(
            (missing, rel_path, float(percent), int(statements or 0)),
        )

    # Biggest absolute gap first: closing 300 uncovered lines moves G1 more
    # than closing 30, regardless of percentage.
    candidates.sort(reverse=True)

    signals: list[Signal] = []
    for missing, rel_path, percent, statements in candidates[:limit]:
        name = Path(rel_path).name
        signals.append(
            Signal(
                generator="coverage_gap",
                goal_id=goal_id,
                # Title shape matters mechanically, not just stylistically.
                # work_allocator.find_duplicate_task rejects a task whose TOKEN
                # overlap with a queued one reaches DUPLICATE_SIMILARITY_THRESHOLD
                # (0.70). A templated family shares most of its tokens, so the
                # first draft ("Add unit tests covering X (N% covered, M lines
                # uncovered)") measured EXACTLY 0.700 against its own siblings
                # and only 1 of 5 signals could ever queue. Front-loading the
                # module name and trimming boilerplate drops the worst pair to
                # 0.625. test_coverage_titles_are_not_mutually_duplicate pins it.
                title=f"{name} at {percent:.0f}% coverage: write tests for {missing} uncovered lines",
                evidence=(
                    f"Measured from coverage.json at the project root (the same "
                    f"trusted file goal_tracker._read_trusted_coverage reads, so "
                    f"this is a measurement and not an estimate): `{rel_path}` is "
                    f"at {percent:.1f}% line coverage with {missing} of "
                    f"{statements} statements uncovered. G1 targets raising "
                    f"coverage toward 50 percent, and this file is one of the "
                    f"largest single gaps in the package."
                ),
                acceptance=(
                    f"New tests in tests/ exercise the uncovered branches of "
                    f"`{rel_path}`, raising its line coverage measurably above "
                    f"{percent:.0f}%. Tests assert real behaviour — not import "
                    f"success — and the existing suite still passes."
                ),
                pointers=[rel_path],
            )
        )
    return signals


# Unconditional skip detection is done over the AST, not the file text.
#
# Text scanning for "@pytest.mark.skip(" matched the marker ANYWHERE, including
# inside STRING LITERALS. This module's own tests embed sample test source as
# strings to exercise this detector, so once those tests existed the generator
# matched its OWN fixtures (tests/test_backlog_generator.py) and proposed
# re-enabling a "skipped test" that is not a test at all. That signal can never
# be satisfied, so it regenerated every cycle: two merged no-op PRs (#373, #377)
# and a third task that burned 5 worker builds into the ceiling before the
# repetition was noticed on the queue dashboard.
#
# A decorator is a syntax node. Parsing for one makes string literals, comments
# and docstrings structurally incapable of matching, which kills the whole class
# rather than the one instance.
#
# `skipif` remains deliberately excluded: it is a legitimate platform/env guard
# (darwin-only launchd tests, network-dependent installs) and proposing those
# would generate work that should never be done.


def _attribute_path(node: ast.AST) -> str:
    """Dotted name for an attribute/name chain, e.g. 'pytest.mark.skip'."""
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def _unconditional_skip_reason(decorator: ast.AST) -> tuple[bool, str]:
    """(is_unconditional_skip, reason) for one decorator node."""
    target = decorator.func if isinstance(decorator, ast.Call) else decorator
    path = _attribute_path(target)
    # Bare "skip" (from pytest import mark) and the fully qualified form both
    # count; "skipif" must not.
    if not (path == "pytest.mark.skip" or path.endswith("mark.skip")):
        return False, ""
    reason = ""
    if isinstance(decorator, ast.Call):
        for keyword in decorator.keywords:
            if keyword.arg == "reason" and isinstance(keyword.value, ast.Constant):
                if isinstance(keyword.value.value, str):
                    reason = keyword.value.value
    return True, reason


def _skipped_tests(source: str) -> list[tuple[str, int, str]]:
    """(test_name, lineno, reason) for every unconditionally-skipped test."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        # An unparseable test file is not this module's problem to report.
        return []
    found: list[tuple[str, int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith("test_"):
            continue
        for decorator in node.decorator_list:
            is_skip, reason = _unconditional_skip_reason(decorator)
            if is_skip:
                found.append((node.name, decorator.lineno, reason))
                break
    return found


def generate_unconditional_skips(
    project_root: Path,
    *,
    goal_id: str = "G1",
    limit: int = 5,
) -> list[Signal]:
    """Tests disabled outright — coverage the suite claims but does not exercise."""
    tests_dir = project_root / "tests"
    if not tests_dir.is_dir():
        return []

    signals: list[Signal] = []
    for path in sorted(tests_dir.glob("test_*.py")):
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        rel = path.relative_to(project_root).as_posix()
        for test_name, line_no, reason in _skipped_tests(text):
            signals.append(
                Signal(
                    generator="unconditional_skip",
                    goal_id=goal_id,
                    title=f"Re-enable or delete skipped test {test_name} in {path.name}",
                    evidence=(
                        f"`{rel}` line {line_no} disables `{test_name}` with an "
                        f"unconditional @pytest.mark.skip"
                        + (f' (reason: "{reason[:120]}")' if reason else "")
                        + ". Unlike skipif, this is not a platform guard: the "
                        "assertion never runs on any machine, so the suite "
                        "reports coverage it does not actually exercise."
                    ),
                    acceptance=(
                        f"`{test_name}` either runs and passes (skip removed, or "
                        f"narrowed to a skipif with a stated condition), or is "
                        f"deleted with a one-line note saying why it is not worth "
                        f"keeping. No test is left unconditionally skipped."
                    ),
                    pointers=[rel],
                    complexity="trivial",
                )
            )
            if len(signals) >= limit:
                return signals
    return signals


# Registry. `enabled` is the goal-alignment switch described in the module
# docstring: a generator whose signal advances no ACTIVE goal must stay off, or
# it manufactures admission rejections every cycle. Flip one on only when
# vision.md carries a goal it serves.
SIGNAL_GENERATORS: dict[str, dict[str, Any]] = {
    "coverage_gap": {
        "fn": generate_coverage_gaps,
        "enabled": True,
        "goal": "G1",
        "note": "Needs a fresh coverage.json; yields nothing without one.",
    },
    "unconditional_skip": {
        "fn": generate_unconditional_skips,
        "enabled": True,
        "goal": "G1",
        "note": "Small but always available; no external dependency.",
    },
}


def generate(
    project_root: Path,
    *,
    generators: list[str] | None = None,
    limit: int = 5,
) -> list[Signal]:
    """Run enabled generators and return their signals, capped at `limit` total."""
    names = generators or [
        name for name, spec in SIGNAL_GENERATORS.items() if spec["enabled"]
    ]
    out: list[Signal] = []
    for name in names:
        spec = SIGNAL_GENERATORS.get(name)
        if not spec:
            continue
        remaining = limit - len(out)
        if remaining <= 0:
            break
        try:
            out.extend(spec["fn"](project_root, limit=remaining))
        except Exception:
            # A broken generator must never take the whole scan down; a missing
            # signal source is a quiet no-op, same as an absent coverage.json.
            continue
    return out[:limit]


def mint(signals: list[Signal], *, dry_run: bool = True) -> dict[str, Any]:
    """Queue the signals as tasks. Returns counts and per-signal outcomes."""
    result: dict[str, Any] = {
        "dry_run": dry_run,
        "generated": len(signals),
        "minted": 0,
        "failed": 0,
        "titles": [s.title for s in signals],
    }
    if dry_run or not signals:
        return result

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import work_allocator  # noqa: PLC0415

    for signal in signals:
        try:
            outcome = work_allocator.add_task(**signal.to_task_kwargs())
            if outcome.get("success"):
                result["minted"] += 1
            else:
                result["failed"] += 1
        except Exception:
            result["failed"] += 1
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("command", choices=["scan", "mint"])
    parser.add_argument("--project-root", default=".", type=Path)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument(
        "--generator",
        action="append",
        help="Run only this generator (repeatable).",
    )
    args = parser.parse_args(argv)

    root = args.project_root.resolve()
    signals = generate(root, generators=args.generator, limit=args.limit)

    if not signals:
        print("No signals found.")
        for name, spec in SIGNAL_GENERATORS.items():
            state = "on" if spec["enabled"] else "OFF"
            print(f"  {name:22} [{state}] goal={spec['goal']}  {spec['note']}")
        return 0

    for signal in signals:
        print(f"\n--- {signal.generator} -> {signal.goal_id} ---")
        print(f"  {signal.title}")
        for pointer in signal.pointers:
            print(f"  pointer: {pointer}")

    outcome = mint(signals, dry_run=args.command == "scan")
    print(
        f"\ngenerated={outcome['generated']} minted={outcome['minted']} "
        f"failed={outcome['failed']} dry_run={outcome['dry_run']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
