# Interventions log

Every human touch during the mdlint experiment. Budget: **2** by-design
approvals (`.planning/EXPERIMENT.md`). Anything beyond that is a finding.

A touch counts if the daemon could not have proceeded without it. Reading
logs, running metrics, and observing do not count.

---

## Run window

- **Launched:** 2026-08-03 12:12 UTC (daemon `com.forgelabs.daemon.mdlint-sandbox-d1bfdc`, PID 61138)
- **14-day bar ends:** 2026-08-17
- **Repo:** https://github.com/andersenqvistdev/mdlint-sandbox

## Interventions

| # | When (UTC) | What | Why | Counts? |
|---|-----------|------|-----|---------|
| 1 | 2026-08-03 12:37 | `forge-queue approve --all` — approved 6 ideation ideas | The documented by-design touch from ProjectK's runbook. Without it the queue stays empty and no work starts. | **Yes (1/2)** |

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

## Observations (no action taken)

- **Greenfield minting works as predicted.** Tasks minted from the goal
  success_metric, producing concrete titles like *"[QUEUE-FILL] G2: Three
  rules implemented with tests: first line is a top-level heading…"* — in
  direct contrast to forge-framework's *"[QUEUE-FILL] G7: Improve success rate
  from 86% to 90%+"*. This is the empirical contrast the experiment was
  designed to capture.
- G1 was correctly scheduled first; the `dependsOn` gating held G2–G9 back.
