"""Mutant canary: prove the acceptance gate can actually fail.

A gate that always passes is indistinguishable from a gate that works, and it is
the more likely of the two — a checker with a typo, an empty corpus, or a
swallowed exception reports success forever. Coverage cannot tell the difference
either: the checker's own lines all execute perfectly while it verifies nothing.

So the checker is itself put under test. Each mutant below is a deliberate,
realistic bug injected into a throwaway copy of mdlint's source. Every one of them
MUST produce at least one disagreement that is not already in the baseline. A
mutant that survives means the gate is blind in that region, and the run is
reported as **unsound** rather than passing.

Usage:
    python tools/acceptance/canary.py
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check  # noqa: E402

SRC = check.ROOT / "src"

# Each mutant targets a relation the gate claims to enforce. Keep them realistic:
# these are the shapes of bug a careless edit actually produces.
MUTANTS = [
    {
        "name": "MDF01 emptiness test inverted",
        "file": "mdlint/rules/md_f01_fence_language_required.py",
        "find": "if block.info:",
        "replace": "if not block.info:",
        "guards": "R1 - MDF01 must fire on exactly the undeclared fences",
    },
    {
        "name": "MDS02 jump threshold loosened by one level",
        "file": "mdlint/rules/md_s02_heading_increment.py",
        "find": "heading.level > previous_level + 1",
        "replace": "heading.level > previous_level + 2",
        "guards": "R3 - MDS02 must fire on exactly the level jumps",
    },
    {
        "name": "MDL02 emptiness test inverted",
        "file": "mdlint/rules/md_l02_no_empty_link_text.py",
        "find": 'if link.text.strip() == "":',
        "replace": 'if link.text.strip() != "":',
        "guards": "R4 - MDL02 must fire on exactly the links with no visible text",
    },
    {
        "name": "fence closer accepts any marker run length",
        "file": "mdlint/fences.py",
        "find": "if marker == open_marker and length >= open_length:",
        "replace": "if marker == open_marker:",
        "guards": "R1 - fence pairing must match CommonMark",
    },
    {
        "name": "MDF02 closed test inverted",
        "file": "mdlint/rules/md_f02_fence_closed.py",
        "find": "if block.close_line is not None:",
        "replace": "if block.close_line is None:",
        "guards": "R5 - MDF02 must fire on exactly the fences with no matching closer",
    },
    {
        "name": "MDS03 duplicate test inverted",
        "file": "mdlint/rules/md_s03_no_duplicate_siblings.py",
        "find": "if heading.text in siblings:",
        "replace": "if heading.text not in siblings:",
        "guards": "R6 - MDS03 must fire on exactly the duplicate sibling headings",
    },
]


def apply_mutant(src_root: Path, mutant: dict) -> None:
    target = src_root / mutant["file"]
    text = target.read_text(encoding="utf-8")
    if mutant["find"] not in text:
        raise SystemExit(
            f"canary is stale: cannot find the mutation site for {mutant['name']!r}\n"
            f"  file:   {mutant['file']}\n"
            f"  needle: {mutant['find']!r}\n"
            "The source moved. Update the mutant so the canary keeps testing the gate."
        )
    target.write_text(text.replace(mutant["find"], mutant["replace"], 1), encoding="utf-8")


def main() -> int:
    baseline = set(check.collect(SRC))
    print(f"baseline for canary: {len(baseline)} disagreement(s) with unmutated source\n")

    survivors = []
    for mutant in MUTANTS:
        with tempfile.TemporaryDirectory() as tmp:
            mutated = Path(tmp) / "src"
            shutil.copytree(SRC, mutated)
            apply_mutant(mutated, mutant)
            try:
                found = set(check.collect(mutated))
            except Exception as exc:  # a mutant that crashes mdlint is still caught
                print(f"  CAUGHT   {mutant['name']} (mdlint failed to run: {type(exc).__name__})")
                continue

        new = found - baseline
        if new:
            print(f"  CAUGHT   {mutant['name']}  (+{len(new)} disagreement(s))")
        else:
            survivors.append(mutant)
            print(f"  SURVIVED {mutant['name']}")
            print(f"           gate is blind to: {mutant['guards']}")

    print()
    if survivors:
        print(f"UNSOUND - {len(survivors)} of {len(MUTANTS)} mutants survived.")
        print("The gate cannot detect these bugs, so a green run proves nothing about them.")
        return 1
    print(f"SOUND - all {len(MUTANTS)} mutants were caught.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
