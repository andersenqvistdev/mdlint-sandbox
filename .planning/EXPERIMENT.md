# mdlint — Platform Experiment Protocol

**Pre-registered 2026-08-03, before the daemon was launched.** Recording the
bar in advance so neither the operator nor the assistant can rationalize the
result afterwards.

Origin: `.planning/AUTONOMY-ASSESSMENT-2026-08-03.md` in forge-framework,
Phase 2. Predecessor: ProjectK (csv2md, 2026-07-15).

---

## The question

Forge measures 86.3% autonomy on forge-framework. That number means *"good at
maintaining itself"* — of the last 40 merged PRs there, 38 touched daemon
internals, 35 touched tests, 30 touched docs, and **zero shipped product**.

**This experiment measures a different and previously-unmeasured number:
product-build autonomy — can the daemon build software for a user?**

The two numbers must be reported separately. They are not the same claim.

---

## Pass bar

Agreed with the operator before launch:

1. **14 consecutive days** of unattended operation.
2. **≥10 merged product PRs** — PRs implementing goals G1–G9. PRs that only
   fix the daemon, the harness, or CI do not count toward the 10.
3. **Product hand-verified working at the end** — `mdlint` run by a human
   against real Markdown, correct violations reported, exit codes correct.

## Intervention budget

ProjectK allowed 2 by-design interventions (idea approvals). Same here.
**Every human touch is logged in `INTERVENTIONS.md` with a timestamp, what was
done, and why.** Interventions beyond the budget are a finding, not a
footnote — they are the result.

A touch counts as an intervention if the daemon could not have proceeded
without it. Reading logs, running the metrics, and observing do not count.

---

## What gets measured

**Funnel, per hop:** goals → tasks minted → admitted → built → PR opened →
CI passed → judged → merged → *actually runs*. Phantom rate at each hop.

**Headline metrics:**
- Product-build autonomy rate (merged product PRs / distinct product tasks)
- Merged product PRs per day
- Interventions (count + reason)
- Verdict retention (deliverable judge verdicts that survive re-judging)
- Gateless merges (target: 0)
- Completed-while-unmerged (target: 0)

**The instrument this run adds — the greenfield boundary.** Forge's
brief-quality gate is skipped while a repo is greenfield
(`strategic_planner.py`, `if not is_greenfield:`). Once top-level `.py` files
exist, the gate switches on — and on forge-framework that same gate currently
passes a metric-restatement while blocking real product work.

**Record the exact commit where greenfield detection flips off, and watch the
following 48 hours closely.** This is predicted to be the highest-value data
the run produces, and the prediction is registered here in advance:

> **Prediction (2026-08-03):** after the greenfield flip, task minting will
> degrade — either the mint rate drops, or minted tasks start failing the
> admission gate for lack of verified pointers. If this does *not* happen, the
> forge-framework diagnosis is incomplete and needs revisiting.

---

## Known confounders

- **Worker contention.** forge-framework's daemon runs on the same machine and
  the two do not coordinate. It is idle (361+ cycles) at launch, so contention
  is near zero — but if forge-framework's gate is fixed mid-run and it wakes
  up, throttle *it*, not this experiment, and log the date.
- **Scope exhaustion.** ProjectK died at 9 tasks because 5 goals ran out of
  surface. This vision carries ~25 discrete items across 9 goals specifically
  to avoid that. If it still exhausts, that is a real finding about
  decomposition, not a scoping accident.
- **Prior art.** markdownlint and remark-lint exist. This is a test vehicle
  first and a usable tool second; novelty is not being measured.

---

## Failure modes that would invalidate the run

Declared in advance. If any occurs, the run is void and gets restarted rather
than reported:

- Someone edits mdlint source by hand (as opposed to fixing the framework).
- The daemon is restarted with a materially different config mid-run without
  logging it.
- CI is bypassed or a merge is forced.
- The repo is not actually isolated from forge-framework's worktree namespace.

---

---

# Run 3 — registered 2026-08-30, before the daemon was restarted

Run 2 answered the original question: **yes, the daemon can build software for
a user** — 20 merged product PRs, a working CLI, 173 tests, in 14 unattended
days. It also produced a defect list that the product's own tests could not
see. Run 3 asks the question that answer exposes.

## The question

**Can the loop repair itself against reality?** Building from a goal and
repairing against an external oracle are different skills. Run 2 showed the
first. The second is what a user actually depends on, because a tool that
ships confident false positives is worse than no tool.

Second question, cheaper but load-bearing: **do the four framework fixes this
run's own findings produced actually work in the field?** Run 2 diagnosed them
in the mothership; nothing has yet proved them here.

## What changed before the clock starts (intervention #3, logged)

`.claude/hooks/` and `bin/` re-synced from forge-framework, carrying:

- **#450 / #451 / #452** — exact-title dedup for the QUEUE-FILL lane, blocked
  tasks no longer veto their own re-mint, tractability ceiling on the generator.
- **#487** — `exact_duplicate_only` for every machine-minted lane, and a
  held-for-review task no longer re-mints hourly.
- **#465 / #471 / #481** — stale PID after reboot, stale `.git/index.lock`
  self-heal, worktrees branch from `origin/main`, git-update failures paged.
- **#484 / #485 / #486 / #488** — prompt_guard never blocks a machine prompt,
  judge errors carry the CLI output, the hourly goal refresh stops running the
  full suite, tests can no longer write real `.company/state`.

`.company/` (queue, goals, history), `forge-config.json` and all product source
are untouched, exactly as in intervention #2.

## Pass bar

1. **14 consecutive unattended days**, intervention budget 0 (both by-design
   approvals were spent in Runs 1 and 2).
2. **G5 ships its three code-fence rules.** Run 2 never minted a single G5
   task; this is the field test of the dedup fix.
3. **≥6 of the 9 Tier A defects stop reproducing**, each verified by running
   its documented command from `.planning/DEFECTS-2026-08-30.md`.
4. **No regression:** the parity table in that file still holds — the
   whitespace, structure and table families stay exact against the oracle, exit
   codes unchanged, `--fix` still idempotent.
5. **Thin-PR rate below 25 %** (Run 2: 9 of 20 = 45 %).

## Predictions, registered in advance

> **(a) G5 mints within 24 hours of the first autofill cycle.** Its title
> scores 0.750 against G2, G4 and G6 on the old matcher — above the 0.70
> threshold — which is why it received zero tasks in fourteen days. The synced
> framework compares normalized titles exactly for machine lanes. If G5 still
> does not mint, `exact_duplicate_only` is not reaching this path.
>
> **(b) Thin PRs continue.** The dedup fix is not the whole cause: throughout
> Run 2 `goal_scheduler.log` recorded `goal_priorities` G2–G9 = 0.0 on every
> scan, because the goal assessor never credits a completed goal in a product
> repo. That defect is NOT fixed in the synced framework. Predicting the
> failure in advance so the next fix is aimed at the assessor, not at dedup.
>
> **(c) At least one defect fix will pass its own tests and still fail the
> oracle.** Better briefs do not cure self-consistent wrongness: the worker
> that writes the fix will write the test. If this prediction fails — if every
> fix survives the oracle — then a sufficiently concrete brief IS the cure, and
> that is the more valuable result.

## What Run 3 adds to the instrument

Run 2's aggregate mint rate looked healthy (78 tasks) while one goal of nine
was starved. **Run 3 measures tasks-per-goal, not tasks.** A distribution that
sums correctly can still be broken, and only the per-goal count shows it.


## After the run

1. Publish both numbers separately — self-maintenance and product-build.
2. Framework findings → queued as briefs to forge-framework.
3. Fieldnote → forge-academy `fieldnotes/mdlint/`.
4. Update `.planning/AUTONOMY-ASSESSMENT-2026-08-03.md` Phase 2 with the result,
   including whether the greenfield-boundary prediction held.
