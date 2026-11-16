# G2 (Structure rules) status — 2026-11-16

Task `task-20261116015939-11a59b` (Queue Auto-Fill) assigned G2 again with
0% progress reported. Re-verified from scratch before touching any code.

## Verification performed

- `MDS01`/`MDS02`/`MDS03` are implemented in `src/mdlint/rules/` and backed
  by dedicated suites in `tests/rules/` (22, 14, and 15 cases respectively)
  plus 32 shared heading-extraction cases in `tests/test_headings.py`
  covering ATX/setext forms, front matter, BOM, fences, blockquotes,
  indented code, and CommonMark's H6 cap.
- `docs/rules.md` documents all three rules with passing/failing examples,
  matching the goal's success metric in `.company/vision.md` (G2 row).
- Full suite: `pytest` → 469 passed, `--cov=mdlint` → 100% line coverage
  (`src/mdlint/rules/md_s01_first_line_heading.py`,
  `md_s02_heading_increment.py`, `md_s03_no_duplicate_siblings.py`, and
  `headings.py` all at 100%, 0 missing).
- `ruff check .` and `ruff format --check .` both clean.

No code gap was found. Writing additional tests here would be padding, not
coverage of a real gap — see `CLAUDE.md` guidance against unnecessary churn.

## Why this keeps getting re-assigned

This is not new: G7 (CLI/config), G6 (list/table), G8 (coverage) hit the
same pattern of already-complete goals being re-queued by auto-fill.
`.planning/EXPERIMENT.md` Run 3 prediction (b) names the root cause: the
goal scheduler never credits a completed goal in a product repo, so
`goal_priorities` for G2–G9 stay non-zero on every scan regardless of
actual status. That fix belongs in forge-framework's goal
scheduler/tracker, not in this product repo — per the experiment protocol
("Framework findings → queued as briefs to forge-framework"), and these
files aren't visible for editing from a product worktree anyway (goal
state lives in `.company/state.nosync`, not synced here).

## Recommendation

Route this as a brief to forge-framework for the goal-crediting bug.
No further action needed on G2 itself.
