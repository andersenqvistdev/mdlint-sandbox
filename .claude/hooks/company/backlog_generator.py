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
from datetime import datetime, timezone
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
#
# Raised 70 -> 90 on 2026-08-20 alongside G1's retarget. The ceiling has to
# track the goal it feeds: with G1 at 50% and this at 70, the lane hunted files
# under 70% for a goal already measuring 86.62%, and only 2 of 185 files still
# qualified -- the queue sat empty for 17.7h with the generator reporting
# nothing to do. A ceiling below the goal's own bar starves the lane long
# before the goal is met.
COVERAGE_MAX_PERCENT = 90.0
COVERAGE_MIN_MISSING_LINES = 25

# Largest per-file gap worth minting as ONE task, the upper bound to
# COVERAGE_MIN_MISSING_LINES' lower one. A worker closes a 30-line gap in a
# single pass; it does not close a 1,900-line one, and each attempt costs a
# worktree, a worker, a PR and its tokens.
#
# Evidence: forge_daemon.py (1,869-1,940 uncovered depending on the scan) was
# minted repeatedly from this path and failed five times, ending at
# "Build ceiling: 5 builds >= 5. Human review required". A blocked twin then
# incidentally suppressed further attempts — until #451 correctly stopped
# blocked tasks from vetoing re-mints, at which point the file was immediately
# minted again. The ceiling is the honest way to stop that work; relying on a
# zombie task to do it was an accident.
#
# Measured 2026-08-23 across 66 candidates below 90%: median gap 48 lines, 64
# at or under this bound. It excludes the two files no single PR can close
# (448 and 1,869) and nothing else. Those need a planned decomposition, not
# another autonomous attempt.
#
# strategic_planner's sibling path sources this at call time so both lanes
# agree on what counts as closeable work.
COVERAGE_MAX_MISSING_LINES = 400

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
            # Templated titles share most of their tokens (two coverage titles
            # with the same missing-line count score 0.857): the fuzzy matcher
            # would refuse a sibling as a duplicate. Exact titles only.
            "exact_duplicate_only": True,
        }


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------


def _python_paths_changed_since(timestamp: float, project_root: Path) -> set[str]:
    """Repo-relative *.py paths committed after `timestamp`.

    Returns an EMPTY set when the answer cannot be determined (no git binary,
    non-zero exit, timeout). Empty means "nothing is known to be stale", i.e.
    fail OPEN -- a missing git binary must not silently disable the richest
    work source. That matches the behaviour of the global rule this replaces.
    """
    try:
        proc = subprocess.run(
            [
                "git",
                "log",
                f"--since=@{int(timestamp)}",
                "--name-only",
                "--format=",
                "--",
                "*.py",
            ],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=15,
        )
        if proc.returncode != 0:
            return set()
        return {line.strip() for line in proc.stdout.splitlines() if line.strip()}
    except Exception:
        return set()


def _coverage_entry_is_stale(rel_path: str, changed: set[str]) -> bool:
    """True when this file's measurement can no longer be trusted.

    Staleness is a PER-FILE property, not a property of the whole measurement.

    The first version of this rule was global: if any *.py commit was newer
    than coverage.json, every generator yielded nothing. That looked right and
    was catastrophic in practice -- the nightly writes coverage.json around
    07:00, the daemon merges Python PRs all day, so the FIRST merge of the day
    invalidated all 184 files until the next night. Measured 2026-08-15: one
    merge (#382, touching only backlog_generator.py) suppressed 6 genuine
    candidates totalling ~2,635 uncovered lines. The lane the QoS fix had just
    unblocked was dead again within an hour, and silently -- "No signals found"
    reads identically whether the repo is clean or the rule ate everything.

    Two things make an entry untrustworthy, and both are what the original
    churn incident (PRs #365/#367/#368) actually consisted of:

      1. The measured file itself changed -- its statements moved, so the
         line numbers and totals describe code that no longer exists.
      2. Its test file changed -- the module is untouched but newly exercised,
         which is exactly how those three PRs made coverage.json describe a
         gap that had already been closed.

    Everything else keeps its measurement, which is the honest reading: a file
    nobody touched still has the coverage that was measured for it.
    """
    if rel_path in changed:
        return True
    stem = Path(rel_path).stem
    if not stem:
        return False
    # tests/test_backlog_generator.py <-> backlog_generator.py is the repo's
    # convention; match on containment so test_foo_extra.py counts too.
    return any(
        stem in Path(c).stem
        for c in changed
        if Path(c).name.startswith("test_") or "tests/" in c
    )


def generate_coverage_gaps(
    project_root: Path,
    *,
    goal_id: str = "G1",
    limit: int = 5,
    max_percent: float = COVERAGE_MAX_PERCENT,
    min_missing: int = COVERAGE_MIN_MISSING_LINES,
    max_missing: int = COVERAGE_MAX_MISSING_LINES,
) -> list[Signal]:
    """Per-file coverage gaps read from a real coverage.json.

    This is the richest goal-aligned signal available: G1 targets coverage, and
    the gap spans the whole hooks package. It reads the SAME trusted file
    goal_tracker._read_trusted_coverage uses, so a missing measurement — or a
    per-file entry invalidated since it was taken — yields NO signal for that
    file rather than an estimate. The W1-P2 rule (never report a number you did
    not measure) applies to generated work too.
    """
    coverage_file = project_root / "coverage.json"
    if not coverage_file.exists():
        return []
    try:
        measured_at = coverage_file.stat().st_mtime
    except OSError:
        return []
    try:
        data = json.loads(coverage_file.read_text())
    except (OSError, json.JSONDecodeError):
        return []

    files = data.get("files")
    if not isinstance(files, dict):
        return []

    # One git call for the whole scan, not one per file: 184 subprocesses per
    # daemon cycle would cost more than the signal is worth.
    changed = _python_paths_changed_since(measured_at, project_root)

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
        if percent >= max_percent or missing < min_missing or missing > max_missing:
            continue
        # Only propose work for files that still exist on disk: coverage.json
        # can outlive a deletion, and a task pointing at a removed file is a
        # hallucinated pointer the admission gate would reject anyway.
        if not (project_root / rel_path).exists():
            continue
        # Per-file freshness: a module whose source or tests moved since the
        # measurement is described by numbers that no longer hold.
        if _coverage_entry_is_stale(rel_path, changed):
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


# How far back to look for an already-completed twin before minting.
#
# work_allocator's own default is 4h, which is right for hand-filed work but
# far too short here: these signals are derived from coverage.json, which the
# nightly rewrites roughly once a day. Until that rewrite the generator keeps
# reading the SAME pre-merge numbers, so a file worked at 11:42 is still
# described as uncovered all afternoon. Measured 2026-08-20/21, both escapes
# landed just outside the 4h window:
#
#   learned_antipatterns.py  merged 11:42 -> re-minted 16:26  (4h44m) -> BLOCKED
#   pr_output_manager.py     merged 20:49 -> re-minted 04:02  (7h13m) -> 625 more
#                                                                       test lines,
#                                                                       coverage +0
#
# The dedup horizon has to cover the SNAPSHOT's staleness horizon, not the
# operator's attention span.
#
# This is deliberately a second line of defence. _coverage_entry_is_stale
# already skips a file whose source or tests moved since the measurement, but
# it answers that question with a `git log` call that returns an empty set --
# fails OPEN -- on timeout, a missing binary, or any non-zero exit. Under load
# (a full pytest run pins this repo for ~32 min) that guard can silently stop
# guarding. This check reads the queue and needs neither git nor mtime.
COVERAGE_SNAPSHOT_DEDUP_HOURS = 26.0


def _normalize_title(title: str) -> str:
    """Casefolded, whitespace-collapsed title for exact comparison."""
    return " ".join(str(title or "").split()).casefold()


def _coverage_module(title: str) -> str:
    """'consultant_lifecycle.py' from 'consultant_lifecycle.py at 82% coverage: ...'."""
    head = _normalize_title(title).split(" at ", 1)[0].strip()
    return head if head.endswith(".py") else ""


def _recently_completed_duplicate(work_allocator, queue: dict, signal: Signal):
    """A same-work task finished inside the snapshot horizon: the signal is stale.

    Exact normalized title, or the same coverage MODULE (a re-measured title
    carries new numbers: "at 84% ... 70 uncovered" after "at 82% ... 83
    uncovered" is the same work just merged, and the nightly has not
    re-measured it yet). Deliberately NOT token similarity: #450 made the
    QUEUE-FILL lane exact but left this one fuzzy, and with numeric tokens
    dominating the score a completion of one file vetoed siblings that merely
    shared a percentage — "3 generated, 1 minted" every run, the free slot
    going to the same file hourly. Completed-only: blocked and in-flight work
    is add_task's business (find_duplicate_task / find_held_twin).

    Never raises: a dedup failure must cost one wasted task, not the source.
    """
    wanted = _normalize_title(signal.title)
    wanted_module = _coverage_module(signal.title)
    if not wanted:
        return None
    try:
        now = datetime.now(timezone.utc)
        for task in queue.get("completed") or []:
            if not isinstance(task, dict):
                continue
            existing = task.get("title", "")
            same_title = _normalize_title(existing) == wanted
            same_module = (
                bool(wanted_module) and _coverage_module(existing) == wanted_module
            )
            if not (same_title or same_module):
                continue
            completed_at = task.get("completed_at")
            if not completed_at:
                continue
            try:
                done = datetime.fromisoformat(str(completed_at).replace("Z", "+00:00"))
            except (TypeError, ValueError):
                continue
            if done.tzinfo is None:
                done = done.replace(tzinfo=timezone.utc)
            if (now - done).total_seconds() <= COVERAGE_SNAPSHOT_DEDUP_HOURS * 3600:
                return {
                    "task_id": task.get("task_id"),
                    "title": existing,
                    "match_type": "exact" if same_title else "same_module",
                }
    except Exception:
        # Never let dedup failure block minting -- a missing twin is a wasted
        # task, a crashed generator is a dead work source.
        return None
    return None


def _record_mint_skip(
    work_allocator, goal_id: str, reasons: list[str], title: str
) -> bool:
    """Append a skip record to state/autofill_brief_skips.jsonl (best-effort).

    Same file and shape as strategic_planner._record_brief_quality_skip, so
    the operator reads one log for every lane. Until 2026-08-29 this lane left
    no trace of its decisions at all: four hourly re-mints of one file were
    visible only as four PRs.
    """
    try:
        path = (
            Path(work_allocator.get_company_dir())
            / "state"
            / "autofill_brief_skips.jsonl"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "goal_id": goal_id,
                        "missing": reasons,
                        "action": title[:200],
                        "lane": "backlog_generator",
                    }
                )
                + "\n"
            )
        return True
    except Exception:
        return False


def mint(signals: list[Signal], *, dry_run: bool = True) -> dict[str, Any]:
    """Queue the signals as tasks. Returns counts and per-signal outcomes."""
    result: dict[str, Any] = {
        "dry_run": dry_run,
        "generated": len(signals),
        "minted": 0,
        "failed": 0,
        "skipped_duplicate": 0,
        "skipped_held": 0,
        "titles": [s.title for s in signals],
    }
    if dry_run or not signals:
        return result

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import work_allocator  # noqa: PLC0415

    queue = work_allocator.load_queue()

    for signal in signals:
        try:
            duplicate = _recently_completed_duplicate(work_allocator, queue, signal)
            if duplicate:
                result["skipped_duplicate"] += 1
                _record_mint_skip(
                    work_allocator,
                    signal.goal_id,
                    [f"recent_duplicate:{duplicate.get('task_id', 'unknown')}"],
                    signal.title,
                )
                continue
            outcome = work_allocator.add_task(**signal.to_task_kwargs())
            if outcome.get("success"):
                result["minted"] += 1
            elif outcome.get("match_type") == "held_for_review":
                # The work exists as a PR a human has not reviewed yet.
                result["skipped_held"] += 1
                _record_mint_skip(
                    work_allocator,
                    signal.goal_id,
                    [f"held_pr:{outcome.get('existing_task_id', 'unknown')}"],
                    signal.title,
                )
            else:
                result["failed"] += 1
                _record_mint_skip(
                    work_allocator,
                    signal.goal_id,
                    [f"add_task_refused:{outcome.get('error', 'unknown')}"],
                    signal.title,
                )
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
