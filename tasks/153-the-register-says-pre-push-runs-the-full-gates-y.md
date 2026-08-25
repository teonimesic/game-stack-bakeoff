---
id: 153
title: The register says pre-push runs the full gates.yml set; it runs 5 of 46
status: todo
priority: 2
refs: .githooks/run-gates.sh, .github/workflows/README.md, eval/tools/ci_minutes.py, tasks/129
done_when: The register's description of what each hook runs is true of .githooks/run-gates.sh, checked by naming the five (or whatever the set becomes) rather than by an adjective; any surviving timing carries its producer command; and if the hook's list is derived from gates.yml instead, a control proves the two cannot drift - red when a gate is added to one and not the other. Closing this by correcting the description alone, with the coverage gap stated explicitly, is a complete answer.
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
