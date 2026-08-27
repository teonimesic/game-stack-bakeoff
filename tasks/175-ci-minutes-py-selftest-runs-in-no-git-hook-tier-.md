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
