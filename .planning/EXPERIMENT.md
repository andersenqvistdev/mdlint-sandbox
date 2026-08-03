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

## After the run

1. Publish both numbers separately — self-maintenance and product-build.
2. Framework findings → queued as briefs to forge-framework.
3. Fieldnote → forge-academy `fieldnotes/mdlint/`.
4. Update `.planning/AUTONOMY-ASSESSMENT-2026-08-03.md` Phase 2 with the result,
   including whether the greenfield-boundary prediction held.
