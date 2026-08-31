# Acceptance gate — does mdlint agree with CommonMark?

mdlint's unit tests cannot answer that question. They were written by the same
process that wrote the linter, so where the linter misreads Markdown the tests
encode the misreading as expected behaviour. On 2026-08-31 the suite was green —
205 tests, ~99.83% line coverage — while the linter reported
``[`docs/rules.md`](docs/rules.md)`` as a link with *empty link text*, on its own
README. Not one test used that link form. Coverage measures which **lines run**,
never which **inputs were tried**.

So this gate asks something with no stake in the answer: a reference CommonMark
implementation (`markdown-it-py`).

## The three properties that make it worth having

**The oracle is outside the artifact.** `oracle.py` imports nothing from mdlint and
knows nothing about its rules. It answers only "what does CommonMark say this
document contains?" — fenced blocks, headings, links.

**The gate has no judgement.** Every relation in `check.py` is a set equality. There
is nothing to argue with and nothing to persuade, which is exactly why it is allowed
to block a PR. Judgement — review, deliverable gates — stays in layers that cannot
block on this.

**The gate is judged too.** `canary.py` injects known bugs into a throwaway copy of
mdlint and requires the gate to catch every one. A gate that always passes looks
identical to a gate that works, and coverage cannot tell them apart either — the
checker's own lines execute perfectly while it verifies nothing. If a mutant
survives, the run reports **unsound** instead of passing. This is not theoretical:
the first canary run failed. It proved the corpus had no document where fence
run-length mattered, so the gate was blind to fence pairing until a fixture was added.

## The ratchet

mdlint disagrees with CommonMark in several places today. A gate demanding zero
disagreement would block every PR immediately and would simply be turned off. So
known disagreements live in `baseline.json`, and the gate fails on two things:

- a **new** disagreement — a regression was introduced;
- a baseline entry that **no longer reproduces** — it was fixed, so it must be
  removed from the baseline and can never silently come back.

The second half is what makes this a ratchet rather than a permanent excuse list.

## Running it

```bash
pip install -e ".[acceptance]"

python tools/acceptance/canary.py           # is the gate sound?
python tools/acceptance/check.py            # does mdlint agree with CommonMark?
python tools/acceptance/check.py --update-baseline   # after fixing a defect
```

`markdown-it-py` is an **acceptance-only** dependency. mdlint's own
`dependencies` list stays empty; the reference parser never ships with the linter.

## In CI

The `acceptance` job takes `tools/acceptance/` from `origin/main`, not from the
branch under test — a change must not be able to edit the gate that judges it. Only
`baseline.json` is read from the branch, because a PR that genuinely fixes a defect
has to be able to retire its entry. Growing the baseline is still possible, but only
as an explicit line in the diff, where a human sees it.

## Adding a relation

A relation belongs here only if it is mechanical. If deciding whether mdlint is
right requires reading `docs/rules.md` and forming a view, it is a review comment,
not a gate. Add the ground truth to `oracle.py`, the set comparison to
`compare()` in `check.py`, and — this part is not optional — a mutant to
`canary.py` that the new relation must catch.
