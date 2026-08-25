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

## note 2026-08-24

## note 2026-08-24 — THE CAUSE IN THIS TICKET'S BODY IS WRONG. Read this before the body.

The body says the flag census reads `project_docs()` and that skills are outside it. **That is not
the mechanism.** Corrected by the agent working `tasks/147`, and re-measured here decisively:

| identical plant, `` `--zzqwerty-nonexistent` `` | `--sweep` |
|---|---|
| `.agents/skills/evaluate-run/SKILL.md` — **names a harness** | **exit 1** |
| `.agents/skills/prune/SKILL.md` — names none | exit 0 |

Skills **are** in the corpus. The backticked-flag half is gated **file-wide** at
`docstat.py:3664`, `re.search(r"(wholegame|runner|judge/|evaluate|regrade)\.py", text)`, and only
runs when the document names one of those four. **4 of the 10 skills do; 6 do not**, and those 6
have their backticked flags unchecked.

The bare-fenced half is deliberately outside that gate, and its own docstring says why: the
document-wide form *"hid a false positive for three weeks until an unrelated edit added a harness
name"*.

## What this changes about the ticket

The `done_when` still stands — a planted flag in a skill must turn `--sweep` red, proved alongside
a plant in a document already covered. **What must not happen is the repair the wrong cause
implies:** widening `project_docs()` would not fix this and would move the exact-count ratchet in
the passing direction for nothing.

**The obvious repair here is also measured and also bad.** Task 147's agent widened the harness
trigger to `_our_script_names()`: 43 documents to 165, **25 new rows, 0 true positives** — `gh`,
`git`, Godot and Chrome flags. So the file-wide trigger cannot simply be opened up, and this is the
census-trigger lesson again: choose on the live false-positive count, not on which sounds more
general.

That makes **recording the exclusion the likely right answer**, and closing this ticket that way is
success, not a shortfall. Task 147 already records it in three places for the register; this ticket
is the same question for the 6 skills that name no harness.

## What NOT to conclude from this note

That the class is understood. **Two mechanisms have now been proposed for one symptom and the first
was wrong** (#170 carries the correction). Before changing anything, reproduce both plants above
and confirm the split is the harness name and not something else that happens to correlate with it.
