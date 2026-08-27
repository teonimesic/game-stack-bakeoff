---
id: 175
title: ci_minutes.py --selftest runs in no git-hook tier, so a workflow edit can go red only in CI
status: in_review
priority: 3
refs: .githooks/run-gates.sh,eval/tools/ci_minutes.py,.github/workflows/README.md,tasks/164
done_when: 'Either `ci_minutes.py --selftest` runs in a hook tier - pre-commit if it is cheap enough, pre-push otherwise, with the measured runtime stated and added to the register''s own cost column - or it is deliberately excluded and .github/workflows/README.md records the exclusion with the reason, which that file already requires for every gate left out. A control proves the chosen tier actually fires: edit a workflow file the way tasks/164 did, and the hook must go red where it previously stayed green.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/60
---

`eval/tools/ci_minutes.py --selftest` checks that the CI register in .github/workflows/README.md describes the workflows that actually exist, and it derives the hook list by RUNNING the hook rather than by restating it.

Measured during tasks/164: adding a step to .github/workflows/controls.yml turned `ci_minutes.py --selftest` red while `.githooks/run-gates.sh pre-push` stayed GREEN. So the check that guards the register is in neither hook tier, and the only thing that runs it is CI itself. CodeRabbit caught the resulting mismatch on that branch; the pins were fixed, but the gap that let it ship is untouched.

Why it matters: the register is the file AGENTS.md tells a session to read before adding a gate, before concluding one is missing, and before assuming a green run covered something. A register that can drift until CI complains is a register a local session cannot trust, and the failure is silent at exactly the moment someone is editing workflows - which is when they are least likely to be reading the register.

## note 2026-08-27

## note 2026-08-27 (orchestrator) — 177 has MERGED and it is the general form of your ticket

`tasks/177` landed as #192: `ci_minutes.py --controls` now answers *which controls does no gate run,
and does the register say why*, over 40 tracked controls, and it gates through `ci_minutes --selftest`
rather than a new step. **Your ticket is one instance of that shape, found independently, and it is
still open because 177 deliberately did not decide it** — its agent recorded that 175 would 'find the
hook table and coverage sentence where it expects them'.

What moved under you:

- `gates.yml` is at **56** now (177 added 2, `tasks/183` added 1, `tasks/176` added 1). Read it from
  `python3 eval/tools/ci_minutes.py --gates` rather than from any figure in this ticket.
- `ci_minutes.py` gained `--controls` and its selftest is at **94 mutants / 55 variants**.
- `.github/workflows/README.md` gained a `left out | why` table that a producer now checks.

**So the question your ticket asks has become answerable rather than arguable:** if
`ci_minutes --selftest` belongs in a hook tier, put it there with its measured runtime in the
register's cost column; if it is deliberately excluded, the exclusion table is the place, and the
new census will hold you to it either way.

Note `tasks/184` also wants a guard in `.githooks/run-gates.sh`. It is NOT dispatched, to avoid
colliding with you. If your work makes 184 easy to fold in, say so rather than doing it silently.

## note 2026-08-27

## What landed — 2026-08-27

PR #60, `task-175-ci-minutes-selftest-in-a-hook-tier`. `ci_minutes --selftest` runs in
**`pre-push`**. `.github/workflows/README.md` is the authority for the hook table, the
coverage sentence and the duty-cycle figure; `DECISIONS.md` for the decision.

### The gap, measured before anything changed

The plant is `tasks/164`'s: one step appended to `.github/workflows/controls.yml`.

| | before | after |
|---|---|---|
| `ci_minutes.py --selftest` | exit 1, `controls.yml gate count: got 12, want 11` | exit 1 |
| `run-gates.sh pre-commit` | exit 0 | exit 0, by design |
| `run-gates.sh pre-push` | **exit 0** | **exit 1**, naming the gate |

### Why `pre-push`, and why no timing went into the register

Local wall clock, one host, unpiped: the gate is **1.78s / 1.85s**; the `pre-commit` tier is
**3.26s / 2.95s** and its largest member (`tasks.py check`) is **1.70s**; `pre-push` went
**18.45s → 20.41s**. So by the register's own cost rule — `pre-push` holds "the one gate that
costs a multiple of the others" — the gate belongs in `pre-commit`.

**The tier was chosen on DUTY CYCLE instead, and that is the reusable part.** Its inputs are
the two workflows, `.githooks/run-gates.sh`, the register, the *set* of gate scripts under
`eval/`, and the tool itself — **79** of `main`'s **678** commits touch one of those
(2026-08-27), so 88% of commits cannot move its verdict while every one would pay. Catching
it at push instead of commit costs an amend. The `git log` pair that re-derives that fraction
is in the register; the extraction was proved on two rows whose answer was known in advance
(`43d1760`, the task-164 merge, is in the set; `cf31c0d` is not).

**The ticket asked for the runtime "added to the register's own cost column". There is no such
column and there must not be** — `.github/workflows/README.md` and `DECISIONS.md` both record
that no hook timing is published, because two readings of `pre-push` on one host minutes apart
have differed by more than the whole `pre-commit` tier costs. The register names
`time .githooks/run-gates.sh <tier>`; the figures live here and in the pull request.

### Making it a hook gate makes the pair mutually recursive

`ci_minutes --selftest` **runs the hook** as its own control — once under `GATES_LIST_ONLY`,
once for real with `python3` shadowed by a shim. The shim was the only thing between the pair
and unbounded recursion once the tool became a gate. Measured with the shim disabled: **8 hook
levels in 25s and still climbing**, killed rather than finished. `run-gates.sh` now reads
`GATES_DEPTH`, and the same mutant then **terminates in 39s at exit 1**.

**A check whose failure mode is a hang reports nothing at all**, so the ceiling is what turns
the pair back into something that can go red.

Three things about that guard that the next agent should not re-derive.

1. **The value is MATCHED against `unset`/`0`/`1`, never incremented.** Arithmetic on an
   unexpected value sets the ceiling aside rather than reaching it, and does it fail-open:
   under `/bin/sh`, `$((${GATES_DEPTH:-0} + 1))` reads `-1000` as `-999` (1002 levels allowed)
   and reads `abc` as `0`, which **restarts the count**. The accepted set is closed because
   this hook is the only writer.
2. **`""` is accepted, not refused.** `${GATES_DEPTH:-0}` substitutes on empty as well as
   unset, so an empty value *is* 0; refusing it would redden a hook whose caller merely
   exported the name.
3. **The ceiling is 2, not 1.** Depth 2 is what a hook-driven selftest legitimately reaches.
   A ceiling of 1 reddens `pre-push` on every push rather than only on a broken shim, and
   there is a variant pinning exactly that.

### Two failures worth carrying out of this ticket

**A control that PINS a counter also RESETS it.** The first ceiling control fixed
`GATES_DEPTH=1` and executed the tier, so every level restored the level beneath it and the
ceiling could never be reached — the control was the recursion engine, and it was found only
by running the broken-shim mutant, which hung. `abc` reading as 0 is the same failure through
a different door. The acceptance probes now list rather than execute; listing still passes
through the ceiling, which sits above `list_only`.

**Acceptance is not propagation, and only the second bounds anything.** Every depth row in
round 1 preset `GATES_DEPTH` and read the hook's *own* answer, so it asked whether the hook
accepts a value and never what the level *below* inherits. Two mutants a real nesting would
recurse under — `1) depth=1` (accepted, never advanced) and `export GATES_DEPTH` deleted —
**passed those pins at exit 0**, verified by checking out 57b28eb's `ci_minutes.py` and
planting each. The shim now records the `GATES_DEPTH` it was invoked with, one line per gate,
and `_depth_seen` executes the tier once per inbound value: `unset`/`""`/`0` reach `1`, `1`
reaches `2`, `2` reaches no gate at all. Those rows execute safely because the depth is pinned
**outside** the recursion rather than inside it — one hook, all its gates the shim, nothing
beneath able to re-enter.

### The pins, and the one that has to exist

`ci_minutes --selftest` closes at **101 mutants / 63 variants** (was 94/55). Eight planted
mutants, all DIED: `dropped`, `no_guard`, `ceiling_1`, `silent_refusal`, `arithmetic`,
`suffix_match`, `no_advance`, `no_export`.

**`dropped` is the one to understand before touching this.** The hook table and the hook check
each other, so removing the gate from both *and* correcting the coverage sentence leaves every
pre-existing row green — agreeing on an absence is agreement. `--controls` cannot see it
either: it censuses stems ending `_control`/`_mutants`/`_selftest`, and `ci_minutes.py` is
none of them. So there is one live row asserting `pre-push` names this tool, by **equality on
the normalised command** rather than a suffix. Removing the gate is now an edit somebody has
to make deliberately.

### Not done here, deliberately

`tasks/184` wants a `core.bare` guard in this same `.githooks/run-gates.sh`. It would fold in
cleanly — the file now has a place for cheap fail-closed assertions above the gate list, and
`GATES_DEPTH` is the pattern to copy (refuse by name, state the repair in the message). It was
left alone so this diff stayed one ticket.

No finding number is allocated. Whether the recursion measurement warrants one is the
orchestrator's call; the account above is complete either way, and its shape is
`AGENTS.md` rule 15 — a mutant asks whether a check can fail, and both defects here were
found by asking what the check could still *pass* on.

## note 2026-08-27

## The review, and one thing found on the way — 2026-08-27

PR #60. **3 rounds, 7 comments, all acted on, none declined.** Every round found something
real, and two of them found the same class of defect one level apart, which is the part worth
keeping.

| round | what it found |
|---|---|
| 1 | `GATES_DEPTH` was **incremented**, so `-1000` read as `-999` (1002 levels allowed) and `abc` read as `0` (count restarts). Also: a false sentence in the register, hook timings published in `DECISIONS.md` six lines above that file's own rule against publishing them, `endswith` where an equality belonged, and `eval/tools/ci_minutes.py` missing from its own duty-cycle census |
| 2 | the depth rows tested **acceptance**, never **propagation**. They preset `GATES_DEPTH` and read the hook's own answer, so `1) depth=1` and a deleted `export GATES_DEPTH` both passed at exit 0 while a real nesting would recurse |
| 3 | the propagation rows compared `sorted(set(...))` of the shim's records, so they had the **value** and not the **population**: a tier running 1 of its 6 gates reads identically |

**Rounds 2 and 3 are one lesson at two scales.** Round 2: what a check reads must be the thing
the mechanism protects, not the thing it is easiest to ask the mechanism about. Round 3: and it
must be read over the whole population, not collapsed. Both were false negatives — a mutant
asks whether a check *can* fail, and only asking what it can still *pass* on found either
(`AGENTS.md` rule 15). Each was verified against the previous head rather than taken on trust:
`no_advance`, `no_export` and `first_only` were each planted against the pins that were live
before their round and came back **exit 0**.

**Round 4 never arrived, and that is an allowance rather than a clean round.** Requested 3
times; CodeRabbit answered *"You've used all 10 included reviews currently available"* each
time, and the last notice stated no interval. `gh pr checks` reads `CodeRabbit pass — Review
rate limited`, which must **not** be read as a clean review.

### Found while sizing this branch's own step, and fixed here

`gates` came back **3m13s** against a register publishing **75–115s**. The step was read
per-step out of the jobs endpoint, as the register itself instructs: `ci_minutes --selftest` is
not in the slowest 12 there, and `judge/ink_window_control` at 69s and `cost_census_mutants` at
29s are what that run is made of. So the gate this ticket adds is not the cause — **the band
was**.

Re-read with the register's own command, last 12 successful runs of each workflow on `main`:

| | published 2026-08-25 | read 2026-08-27 |
|---|---|---|
| `gates` | 75–115s | **127–208s** |
| `controls` | 658–827s | **706–970s** |

**24 of 24 runs sit outside the band published for them**, so this is not the run-to-run noise
that row already warns about. Both replaced, with the span sentence (81s and 264s, from 40s and
169s). The row now also says the band is a **reading, not a property of the tier** — the same
lesson one level up from the one it already carried, and the reason to re-run the command
rather than trust the digits. `tasks/129` and `tasks/153` hold the retired figures; a live
document replaces superseded content rather than annotating it.

### State at handback

Branch merged up to `main` (6 commits) and re-verified at the merge head: the 9-mutant sweep is
9 of 9 DIED, and the ticket's own control still gives `pre-push` exit 1 and `pre-commit` exit 0
on a planted `controls.yml` step. `mergeable.py` refused the pre-merge head for being behind,
which is what prompted the merge.
