---
id: 153
title: The register says pre-push runs the full gates.yml set; it runs 5 of 46
status: done
priority: 2
refs: .githooks/run-gates.sh, .github/workflows/README.md, eval/tools/ci_minutes.py, tasks/129
done_when: The register's description of what each hook runs is true of .githooks/run-gates.sh, checked by naming the five (or whatever the set becomes) rather than by an adjective; any surviving timing carries its producer command; and if the hook's list is derived from gates.yml instead, a control proves the two cannot drift - red when a gate is added to one and not the other. Closing this by correcting the description alone, with the coverage gap stated explicitly, is a complete answer.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/33
established_by: 'PR #33 squash-merged. Verified independently: ci_minutes.py --hooks reports pre-commit at 4 of gates.yml''s 47 checks and pre-push at 5, all docstat/tasks documentation and queue checks - so ''the full gates.yml set'' had never been true of anything. The list is derived by RUNNING the hook under GATES_LIST_ONLY=1, so it comes out of the hook''s own control flow rather than a second copy. I reproduced the negative control myself with a marker-writing python3 shim: flag on prints 5 lines with the marker ABSENT, flag off fires the same shim 5 times - so ''executed nothing'' is a measurement rather than an inert probe. One review thread declined with evidence: DECISIONS.md is where reasoning lives, 41 of its entries carry dated attribution, and its reasoning is on the never-prune list.'
---

`.github/workflows/README.md` says the `pre-push` hook runs **"the full `gates.yml` set"**. It does
not. `.githooks/run-gates.sh` invokes a **hardcoded list of five** commands:

    docstat.py --selftest
    docstat.py --findings
    docstat.py --withdrawn
    tasks.py check
    docstat.py --sweep      (pre-push only)

`gates.yml` has **46** gates (`ci_minutes.py --gates`). So pre-push runs **5 of 46**, and the
register tells a reader it runs all of them.

**This is the dangerous direction.** Someone who pushes on a green pre-push believes they have run
what CI will run. They have run about a ninth of it, and the four they ran are all documentation
checks — no mutant suite, no selftest of any tool, no control.

Measured 2026-08-25: `pre-push` took **24.8s**, against the register's **~13s** in the same table.
Both numbers are stale in the same row.

## The tension this ticket has to resolve, rather than assume

The hooks are **not installed by default** and that is deliberate. Making pre-push run all 46 gates
would make it slower still, and `.github/workflows/README.md` already records the reasoning that a
gate people skip is worse than one nobody added — a 46-gate pre-push is a `--no-verify` habit
waiting to form.

So the fix is not obviously "run more". The candidates:

1. **Correct the description** to say what the five are and why those five — cheapest, honest, and
   leaves the coverage gap explicit rather than implied.
2. **Derive the hook's list from `gates.yml`** filtered by a cheapness marker, so the two cannot
   drift and the register's claim becomes true by construction.
3. **Two tiers**, with pre-push running everything and a documented bypass for the impatient.

**Option 1 is a complete answer** and closing this ticket that way is success. What is not
acceptable is the current state, where the document overstates what the hook did.

## What NOT to do

Do not re-time the hook and paste a new number without a producer beside it — that is the defect
`tasks/129` covers, in the same table. If a timing survives, it needs the command that reproduces
it, and `time .githooks/run-gates.sh <tier>` is already named there.

Do not assume the five are the right five. Ask what each is protecting: they are all
`docstat`/`tasks` checks, and the thing that most often reddens `main` in practice is exactly
those — but that is a claim to check against the last month of red gate runs, not to assert.

## note 2026-08-25

## note 2026-08-25 (orchestrator) — take `tasks/129` as well; it is the same table

**You are authorised to close `tasks/129` in this branch.** Both tickets are about the same table
in `.github/workflows/README.md` being untrue: 129 says its tier timings have no producer and have
moved, this one says its hook descriptions are false. Two agents editing that table collide, and
whoever fixes one will read the other while deciding what a timing is for.

129 already carries the evidence that decides it: the last 10 successful `gates` runs on `main`
span **54–78s**, two consecutive runs one markdown edit apart came back **65s and 102s** — a 57%
spread on unchanged content — and my own measurement of `pre-push` was **24.8s** against the
table's **~13s**. **Runner variance dwarfs the thing a per-run timing would be read for**, which is
why 129's second permitted outcome — delete the figures and say what the register does instead —
now looks like the right one.

## One more source of truth to check while you are there

Task 148 found the tier timings had been copied into `gates.yml`, `controls.yml` and the dispatch
skill, **every copy disagreeing with the register**, and pointed them all at the register. So the
register is now the single statement — which raises the stakes on it being true, and means a
timing that survives here is one three other files defer to.

## What NOT to do

Do not re-time and paste a new number. That is 129's original defect repeating one value later. A
figure that survives carries the command that reproduces it and the population it covers, and
`gh pr checks <n>` is already named there for the tiers.

Do not describe the hooks with an adjective. *"The cheap gates"* and *"the full `gates.yml` set"*
are both adjectives, and one of them is false: `run-gates.sh` invokes a hardcoded list of five.
Name them, or derive them and prove the two cannot drift.

## note 2026-08-25

## Closed in PR #33, with `tasks/129` in the same branch

### What the hook actually runs, and how it is now checked

`.githooks/run-gates.sh` takes **`GATES_LIST_ONLY=1`**: `run()` and `run_advisory()` print
their argv instead of executing it, and the script exits 0. So the list is obtained by
**running** the hook, not by re-parsing it — it comes out of the same control flow, including
the `pre-push`-only branch and the worktree/main-checkout branch.

    GATES_LIST_ONLY=1 .githooks/run-gates.sh pre-push
    python3 eval/tools/ci_minutes.py --hooks

`hook_census()` in `eval/tools/ci_minutes.py` compares that against a table in
`.github/workflows/README.md` (`| command | `pre-commit` | `pre-push` |`, one row per command)
and a coverage sentence in a fixed form that `COVERAGE_RE` reads. `ci_minutes --selftest`
asserts they are equal, so **adding a gate to the hook takes 3 edits and is red until all 3
are done**: the script, the table row, the coverage counts.

**The queue lint moved into `run_advisory`.** It used to be a bare `python3` call in the `else`
branch, which meant the tier's command list depended on which checkout you stood in — and a
list-only run from a worktree would have executed it. Both spellings now share `list_only`, so
the published list is checkout-independent. That is worth knowing before touching that branch.

### Do not re-derive: what was measured

| | |
|---|---|
| `pre-commit` | 4 of `gates.yml`'s 47 checks |
| `pre-push` | 5 of 47 |
| the register's old claim | "the full `gates.yml` set" — true of nothing, ever |
| `gates` wall clock, last 12 successful runs on `main`, 2026-08-25 | 75–115s (published: 102s) |
| `controls`, same population | 658–827s (published: 791s) |
| `pre-push` locally, same host, minutes apart | 16.8s and 17.2s, against 24.8s at triage and ~13s published |

Both published workflow figures were *inside* their range — unlike the 51.9s/685s that 129 was
filed against — so the defect was no longer that they were wrong, it was that a point value
there cannot support the inference a reader draws from it. The `takes` row is now the spread,
with its population and the `gh run list` one-liner beside it. **No hook timing is published
anywhere**, including in `run-gates.sh`'s own comments and both wrapper hooks, which each
carried a stale one.

### The decision, and why option 2 was not taken

`DECISIONS.md`, *The gates run in CI and in git hooks, in three tiers*, now records it with a
reversal condition. The ticket offered three options; this is **option 1 plus a gate**.

Deriving the hook's list from `gates.yml` behind a cheapness marker (option 2) adds a second
selector to maintain for the same handful of commands, and it answers a question nobody had —
the tier was not missing coverage, it was missing a *checkable* description. Running all 47
(option 3) makes `pre-push` minutes long and turns `--no-verify` into a habit.

**The reversal condition is 2 pushes to `main` reddened by the same gate outside the subset.**

### What could not be established

Whether the 5 are the **right** 5, checked against the last month of red gate runs on `main`.
The ticket asks for that as a claim to check rather than assert; the Actions API does not
report which step failed for runs already garbage-collected, and there is no stored record of
per-step failures. The reversal condition is the forward-looking version of that question.

### For the orchestrator: 2 finding candidates, unnumbered

Per `.agents/skills/work/SKILL.md` I have not allocated numbers.

1. **A description by ADJECTIVE is the shape no check can read, and it survives indefinitely.**
   The register described 3 of its own mechanisms with adjectives — *"the cheap gates"*,
   *"the full `gates.yml` set"*, *"~13s"* — and the middle one had never been true of anything.
   Nothing could disagree with it because there was nothing to disagree with. This is the
   documentation twin of the enumeration-trigger lesson in `AGENTS.md`: an adjective is a
   trigger with no extension.
2. **A point timing in a table gets read as a difference.** `gates` spans 75–115s across 12
   consecutive successful runs of unchanged-ish content — a band far wider than any step this
   repository adds — so the quantity a reader wants (*did my step make CI slower?*) is not
   recoverable from the number published for it. The useful statement is the spread or nothing.

### Review

3 rounds, PR #33. Round 1: 4 findings, all real, all applied — 2 of them behavioural (the
register/script comparison was order-sensitive where the register claims no order; an
unreadable `gates.yml` came back red with every word of the diagnosis wrong). Round 2: 1
finding, 2 mutable thresholds written as words; applied, and the `Adding one` half declined on
the reviewer's own learning about indefinite pronouns. Round 3: clean.

`ci_minutes --selftest` goes from 19 mutants / 5 variants to **37 / 14**.
