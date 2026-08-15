# Interventions log

Every human touch during the mdlint experiment. Budget: **2** by-design
approvals (`.planning/EXPERIMENT.md`). Anything beyond that is a finding.

A touch counts if the daemon could not have proceeded without it. Reading
logs, running metrics, and observing do not count.

---

## Run window

### Run 1 — 2026-08-03 → 2026-08-15. **FAILED the pass bar. Result recorded.**

- **First launch:** 2026-08-03 12:12 UTC — **shakedown only, does not count.**
  Finding #9 (`uv.lock` humanProtected) made shipping structurally impossible,
  so zero product PRs were reachable regardless of worker quality.
- **Clock start:** 2026-08-03 ~13:20 UTC, after findings #9 and #10 were fixed
  and the ceiling-blocked tasks were returned to pending.
- **Stalled:** 2026-08-04, after PR #5. Never resumed.
- **Closed:** 2026-08-15 06:30 UTC, two days short of the 14-day bar, because
  the outcome was no longer in doubt (see below).

**Measured outcome against the pre-registered bar:**

| Bar | Required | Actual |
|---|---|---|
| Consecutive unattended days | 14 | 12 (of which 11 were a total stall) |
| Merged product PRs | ≥10 | **2** (#4, #5 — and #4 is titled *RECOVERY ATTEMPT — Wrong Approach*) |
| Product hand-verified working | yes | not reached |

At close: queue 0 pending / 0 active / 0 blocked / 10 done, **1,296 consecutive
idle cycles**, and **315 brief-quality skips** in
`.company/state/autofill_brief_skips.jsonl`. The silence sentinel was firing
`['scout_silent', 'queue_empty', 'brief_skips']` on every cycle for 11 days.
It was working correctly; nobody was reading it.

**The registered prediction held.** `.planning/EXPERIMENT.md` predicted in
advance that after the greenfield boundary "task minting will degrade — either
the mint rate drops, or minted tasks start failing the admission gate for lack
of verified pointers." The mint rate went to **zero**, and the skip log gives
the reason per goal: `missing: ["verified_pointer", "measured_evidence"]` for
G5, G6, G7, G9 and `["verified_pointer"]` for G8, repeating every cycle.

**Confounder, stated plainly:** this sandbox ran a *frozen* copy of the
framework taken at 2026-08-03 11:33. It never received the brief-quality gate
fix (forge-framework PR #361, merged the same day) or anything after it. So
Run 1 tested the **diagnosed** system, not the fixed one. That makes it a clean
confirmation of the diagnosis and not a verdict on the current framework.

Verified 2026-08-15 by replaying the five stalled goal strings through the
**current** gate (`_is_fix_intent` / `_concrete_targets` /
`_existing_file_pointers`): **all five now PASS.** G7 is the sharpest case —
its `--fix` flag was matching `\bfix\b` and misclassifying the whole goal as
repair work demanding a verified pointer; the current regex reads it as a CLI
flag, one of five concrete targets it now recognises.

### Run 2 — from 2026-08-15

- **Clock start:** 2026-08-15 (see intervention #2)
- **14-day bar ends:** 2026-08-29
- **Framework:** synced from forge-framework at 2026-08-15, replacing the
  2026-08-03 freeze. Adds the brief-quality gate fix (#361), the signal-driven
  `backlog_generator.py`, the queue ping-pong fix (#370) and the QoS fix (#371).
- **Daemon:** `com.forgelabs.daemon.mdlint-sandbox-d1bfdc`
- **Repo:** https://github.com/andersenqvistdev/mdlint-sandbox

## Interventions

| # | When (UTC) | What | Why | Counts? |
|---|-----------|------|-----|---------|
| 1 | 2026-08-03 12:37 | `forge-queue approve --all` — approved 6 ideation ideas | The documented by-design touch from ProjectK's runbook. Without it the queue stays empty and no work starts. | **Yes (1/2)** |
| 2 | 2026-08-15 06:30 | Stopped the daemon, rsynced `.claude/hooks/` from forge-framework over the 2026-08-03 freeze, restarted. `.company/`, `forge-config.json` and all product source left untouched; previous tree kept at `.claude/hooks.bak-20260815`. | Framework defect repair, not a nudge to the daemon's work: the sandbox was running a build whose brief-quality gate rejected 5 of 9 goals unconditionally, 315 times. Run 1's result is recorded above rather than discarded. | **No — ends Run 1, starts Run 2** |

---

## Setup-phase findings (pre-launch, not interventions)

Recorded because they are framework bugs found while standing the project up.
All predate the run window and none required changing product code.

1. **LaunchAgent install leaves an unsubstituted placeholder.**
   `forge_daemon.py install` wrote `__APPLICATION_SUPPORT_DIR__/Forge/daemon_prestart_wrapper.sh`
   into ProgramArguments verbatim. The agent loaded but exited 127 (command
   not found) on every attempt. Fixed by patching the plist by hand.

2. **The plist template is not shipped by `install.sh`.**
   `install` failed with "plist template not found" — `.claude/hooks/company/launchd/`
   was absent entirely. Copied `com.forgelabs.daemon.plist` and
   `forge-daemon.sh` from forge-framework by hand.

3. **`ruff check .` fails on a fresh install.**
   Forge ships `.company/templates/projects/python-cli/pyproject.toml`
   containing `{{project_name}}` placeholders, which is not valid TOML. Any
   project whose CI runs `ruff check .` fails on its first PR. Worked around
   with `extend-exclude`. Note `pyproject.toml` is humanProtected, so **the
   daemon could not have fixed this itself.**

4. **`humanProtected.requireApprovalFor` ships as `["docs/*", "README.md"]`.**
   For any project with a documentation goal this guarantees approval requests —
   here it would have made goal G9 unachievable within the intervention budget.
   Cleared before launch.

5. **`branchProtection.expectedChecks` ships with the framework's own CI job
   names** (`Lint`, `Security`, `Hooks Validate`). Any project with different
   CI jobs gets a permanent "Branch protection degraded" warning. Set to
   `["test"]`.

6. **The silence sentinel's `scout_enabled` has no config plumbing.**
   `SentinelConfig(base_dir=...)` is constructed with defaults
   (`forge_daemon.py:5893`) and `scout_enabled` defaults to `True`, so a
   project with no opportunity scout pages `scout_silent` forever. Left
   in place deliberately — patching platform code mid-experiment would
   contaminate the measurement. Expect recurring false pages in the logs.

7. **Ideation tiers ideas as `executive`, needing `forge-ceo` and `forge-cto`.**
   This org has three employees and neither executive exists. `approve --all`
   overrode it, but the governance path assumes an executive tier that a small
   org does not have.

8. **Ideation routing ignores goal ownership.** vision.md assigns G3
   (whitespace rules) and G4 (link rules) to `cli-developer`; ideation handed
   them to `qa-engineer` and `tech-writer`. Whether the allocator re-routes by
   capability at execution time is worth watching.

9. **`uv.lock` in humanProtected makes the daemon structurally unable to ship
   on any uv-based project.** THE BIG ONE — it broke the run within 40 minutes
   of launch.

   Workers run via `uv run`, which regenerates `uv.lock` inside the worktree.
   The PR gate then refused every single result:
   `Refusing to create PR: touches human-protected path(s): uv.lock`.

   The failure mode is the worst kind: workers **succeeded** (exit 0, real
   tests written — one correctly identified that G8 was premature and flagged
   a genuine broken-entry-point bug), and the work was then discarded at the
   shipping step. The daemon logged *"Work done but not shipped — 8 file(s)
   modified but capture/PR failed"*, retried, and hit the 5-build ceiling on
   G1, G2 and G4 within the hour.

   This is a **W1 silent-wrongness instance in the shipping path**: no crash,
   no bad work — good work confidently thrown away. Any Forge project using
   `uv` (which is what the daemon's own LaunchAgent uses) hits this on its
   very first task.

   Fixed by removing `uv.lock` from `humanProtected.paths` and gitignoring it.
   Ceiling-blocked tasks returned to pending, build counters cleared.
   **Not counted as an intervention** — framework defect repair during the
   shakedown window; the run clock restarts (see Run window).

10. **Workspace trust silently drops 144 permission entries.** Worker logs
    showed `Ignoring 144 permissions.allow entries from .claude/settings.json:
    this workspace has not been trusted`. forge-doctor reports this as a benign
    WARN and ProjectK's runbook says to expect it — but it means every worker
    ran with its permission allowlist discarded. Set
    `projects[...].hasTrustDialogAccepted: true` in `~/.claude.json`
    (backup: `~/.claude.json.bak-before-mdlint-trust`).

## Observations (no action taken)

- **Greenfield minting works as predicted.** Tasks minted from the goal
  success_metric, producing concrete titles like *"[QUEUE-FILL] G2: Three
  rules implemented with tests: first line is a top-level heading…"* — in
  direct contrast to forge-framework's *"[QUEUE-FILL] G7: Improve success rate
  from 86% to 90%+"*. This is the empirical contrast the experiment was
  designed to capture.
- G1 was correctly scheduled first; the `dependsOn` gating held G2–G9 back.
