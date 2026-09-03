"""Acceptance gate: does mdlint agree with CommonMark?

Runs the SHIPPED mdlint CLI over a corpus and compares its violations against
structural ground truth from a reference parser (``oracle.py``). Every relation
here is mechanical — a set equality — so this layer contains no judgement and
cannot be argued with. That is deliberate: the layer that can block a PR has no
opinions, and the layers that have opinions (reviewers, judges, the deliverable
gate) cannot block on this.

## The ratchet

mdlint currently disagrees with CommonMark in many places. A gate demanding zero
disagreement would block every PR on day one and would simply be switched off.
So the known disagreements live in ``baseline.json`` and the gate fails on:

  * a NEW disagreement          -> a regression was introduced
  * a baseline entry that no longer reproduces -> it was fixed; remove it from the
    baseline so it can never come back

The second half is what makes this a ratchet rather than a permanent excuse list.
Fixes are locked in the moment they land.

Usage:
    python tools/acceptance/check.py                  # gate (exit 1 on failure)
    python tools/acceptance/check.py --update-baseline
    python tools/acceptance/check.py --mdlint-src PATH  # used by the canary
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import oracle  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIR = Path(__file__).resolve().parent / "corpus"
BASELINE = Path(__file__).resolve().parent / "baseline.json"
DEFAULT_SRC = ROOT / "src"


def run_mdlint(files: list[Path], src: Path) -> dict:
    """Run the mdlint CLI as a subprocess and return its parsed JSON report."""
    code = "import sys\nfrom mdlint.cli import main\nsys.exit(main())"
    proc = subprocess.run(
        [sys.executable, "-c", code, "--format", "json", *[str(f) for f in files]],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(src), "PATH": "/usr/bin:/bin"},
        cwd=str(ROOT),
        timeout=120,
    )
    if not proc.stdout.strip():
        raise RuntimeError(
            f"mdlint produced no output (exit {proc.returncode}): {proc.stderr[:400]}"
        )
    return json.loads(proc.stdout)


def _by_file(report: dict) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for violation in report.get("violations", []):
        grouped.setdefault(violation["file"], []).append(violation)
    return grouped


def _lines_for(violations: list[dict], rule: str) -> set[int]:
    return {v["line"] for v in violations if v["rule_id"] == rule}


def _mdl02_targets(violations: list[dict]) -> set[str]:
    """Pull the target out of "link to 'X' has empty link text"."""
    targets = set()
    for v in violations:
        if v["rule_id"] != "MDL02":
            continue
        message = v["message"]
        if "'" in message:
            targets.add(message.split("'")[1])
    return targets


def compare(path: Path, violations: list[dict]) -> list[str]:
    """Every way this document's report disagrees with CommonMark.

    Each disagreement is a stable string so it can live in the baseline.
    """
    text = path.read_text(encoding="utf-8")
    rel = path.relative_to(ROOT).as_posix()
    out = []

    def record(rule: str, kind: str, key: str) -> None:
        out.append(f"{rel} | {rule} | {kind} | {key}")

    # R1 - MDF01 must fire on exactly the fenced blocks that declare no language.
    expected = oracle.undeclared_fence_lines(text)
    actual = _lines_for(violations, "MDF01")
    for line in sorted(actual - expected):
        record("MDF01", "false_positive", f"line {line} is not an undeclared fence opening")
    for line in sorted(expected - actual):
        record("MDF01", "false_negative", f"line {line} opens a fence with no language")

    # R2 - MDS01 must never fire on a document that plainly opens with an H1.
    if oracle.starts_with_h1(text) and _lines_for(violations, "MDS01"):
        record("MDS01", "false_positive", "document's first heading is a level-1 heading")

    # R3 - MDS02 must fire on exactly the headings that skip a level.
    expected = oracle.heading_jump_lines(text)
    actual = _lines_for(violations, "MDS02")
    for line in sorted(actual - expected):
        record("MDS02", "false_positive", f"line {line} is not a level jump")
    for line in sorted(expected - actual):
        record("MDS02", "false_negative", f"line {line} skips a heading level")

    # R4 - MDL02 must fire on exactly the links whose visible text is empty.
    expected = oracle.empty_text_link_targets(text)
    actual = _mdl02_targets(violations)
    for target in sorted(actual - expected):
        record("MDL02", "false_positive", f"link to {target!r} has visible text")
    for target in sorted(expected - actual):
        record("MDL02", "false_negative", f"link to {target!r} has no visible text")

    # R5 - MDF02 must fire on exactly the fenced blocks with no matching closer.
    expected = oracle.unclosed_fence_lines(text)
    actual = _lines_for(violations, "MDF02")
    for line in sorted(actual - expected):
        record("MDF02", "false_positive", f"line {line} opens a fence that is closed")
    for line in sorted(expected - actual):
        record("MDF02", "false_negative", f"line {line} opens a fence with no closer")

    # R6 - MDS03 must fire on exactly the headings that repeat an earlier sibling.
    expected = oracle.duplicate_sibling_lines(text)
    actual = _lines_for(violations, "MDS03")
    for line in sorted(actual - expected):
        record("MDS03", "false_positive", f"line {line} is not a duplicate sibling heading")
    for line in sorted(expected - actual):
        record("MDS03", "false_negative", f"line {line} repeats an earlier sibling heading")

    return out


def collect(src: Path) -> list[str]:
    files = sorted(CORPUS_DIR.rglob("*.md"))
    if not files:
        raise SystemExit(f"no corpus documents under {CORPUS_DIR}")
    report = run_mdlint(files, src)
    grouped = _by_file(report)
    findings: list[str] = []
    for path in files:
        key = str(path)
        violations = grouped.get(key) or grouped.get(path.relative_to(ROOT).as_posix()) or []
        findings.extend(compare(path, violations))
    return sorted(findings)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--mdlint-src", default=str(DEFAULT_SRC))
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    findings = collect(Path(args.mdlint_src))

    if args.update_baseline:
        BASELINE.write_text(json.dumps(findings, indent=2) + "\n", encoding="utf-8")
        print(f"baseline updated: {len(findings)} known disagreement(s)")
        return 0

    known = set(json.loads(BASELINE.read_text(encoding="utf-8"))) if BASELINE.exists() else set()
    current = set(findings)
    new = sorted(current - known)
    fixed = sorted(known - current)

    if not args.quiet:
        print(f"corpus disagreements: {len(current)} (baseline {len(known)})")

    if new:
        print(f"\nREGRESSION - {len(new)} new disagreement(s) with CommonMark:")
        for item in new:
            print(f"  + {item}")
    if fixed:
        print(f"\nRATCHET - {len(fixed)} baseline entry/entries no longer reproduce.")
        print("These were fixed. Remove them from the baseline so they cannot return:")
        for item in fixed:
            print(f"  - {item}")
        print("\n  python tools/acceptance/check.py --update-baseline")

    if new or fixed:
        return 1
    if not args.quiet:
        print("OK - mdlint agrees with CommonMark everywhere outside the baseline.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
