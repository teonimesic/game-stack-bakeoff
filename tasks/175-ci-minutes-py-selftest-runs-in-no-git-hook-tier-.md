---
id: 175
title: ci_minutes.py --selftest runs in no git-hook tier, so a workflow edit can go red only in CI
status: todo
priority: 3
refs: .githooks/run-gates.sh,eval/tools/ci_minutes.py,.github/workflows/README.md,tasks/164
done_when: 'Either `ci_minutes.py --selftest` runs in a hook tier - pre-commit if it is cheap enough, pre-push otherwise, with the measured runtime stated and added to the register''s own cost column - or it is deliberately excluded and .github/workflows/README.md records the exclusion with the reason, which that file already requires for every gate left out. A control proves the chosen tier actually fires: edit a workflow file the way tasks/164 did, and the hook must go red where it previously stayed green.'
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
