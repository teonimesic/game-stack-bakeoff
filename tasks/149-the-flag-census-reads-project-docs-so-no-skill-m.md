---
id: 149
title: The flag census reads project_docs(), so no SKILL.md is checked for phantom flags
status: todo
priority: 2
refs: 'eval/tools/docstat.py, .agents/skills/audit-docs/SKILL.md, tasks/147, #170, #38'
done_when: Either a planted phantom flag in a SKILL.md turns `--sweep` red - with the plant also proved in a document already covered, so a broken plant cannot masquerade as success - and whatever ratchet the corpus change touches is re-baselined deliberately with the new number stated; or the exclusion is written down in docstat.py AND in the audit-docs skill's list of what --sweep does not cover, naming which checks read skills and which do not. Either way `--sweep`, `--selftest` and the corpus pins stay green.
---

`docstat.py --sweep`'s flag census — *"flag `--x` matches no argparse in eval/"* — reads
`project_docs()`. **All 10 `SKILL.md` files are outside that corpus**, so none of them is
flag-checked. Skills are where commands and their flags are most densely written, which makes this
the worst place for the check to be absent.

Measured on `main`, one plant and a positive control, because an all-green result and a broken
probe look identical:

| identical plant, `` `--zzqwerty-nonexistent` `` | `--sweep` |
|---|---|
| `.agents/skills/prune/SKILL.md` | **exit 0** |
| `DECISIONS.md` | exit 1, naming the flag |

Skills **are** inside `reference_docs()`, so the reference and structure checks do read them. It is
specifically the flag census that does not, and the split is not an oversight in one place — it is
`cmd_sweep()` holding two corpora and different checks reading different ones.

## This is #170's territory, and 147 is adjacent — read both before starting

`tasks/147` found the same class for `.github/workflows/README.md` and closed it for
`reference_docs()` only. That ticket's note carries the measurement and the reason
`project_docs()` was deliberately NOT widened: it feeds an **exact-count ratchet**, and a larger
corpus moves that ratchet in the **passing** direction. So the naive fix — widen `project_docs()` —
loosens a different gate, and that is the whole difficulty here.

## What would satisfy this

Either the flag census reads a corpus that includes skills, with the ratchet it feeds decoupled or
re-baselined deliberately and the new baseline stated; **or** the exclusion is recorded in
`docstat.py` and in `.agents/skills/audit-docs/SKILL.md` — which already lists what `--sweep`
deliberately does not cover — saying which checks read skills and which do not.

**A recorded exclusion is an acceptable outcome and closing this that way is not a failure.** What
is not acceptable is the current state, where a reader of the audit-docs skill would reasonably
believe skill flags are checked.

## What NOT to do

Do not widen `project_docs()` without measuring what the ratchet does. And do not verify a fix by
planting a flag only in a skill: plant in a skill AND in a document already covered, so a
green-everywhere result cannot come from a broken plant.
