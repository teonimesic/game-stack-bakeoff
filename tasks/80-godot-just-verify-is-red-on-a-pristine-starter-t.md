---
id: 80
title: 'godot just verify is red on a pristine starter: test-render fails, and the gate control has been reporting it'
status: in_flight
priority: 2
refs: eval/tools/starter_gate_control.py, eval/starters/godot/justfile line 120, tasks/67
done_when: the cause of test-render exiting 1 on an untouched godot starter copy is identified and either repaired so starter_gate_control is 29 of 29 green, or recorded as an environment property with the condition that reproduces it and a control showing the other three arms are not subject to it
---

Measured 2026-08-23 under task 67, running eval/tools/starter_gate_control.py unpiped to completion: 4 starters, 29 measurements, 1 FAILED, exit 1.

  FAIL godot: GREEN on pristine (the same just verify must also exit 0) (exit 1): error: recipe test-render failed on line 120 with exit code 1

rust, ts and unity are green in every direction. godot is green on warm, on check, and on both red-direction plants; it is the pristine-verify row alone that fails, in 4.1 seconds - so verify RAN and a check inside it returned 1, this is not a timeout. eval/starters/godot/AGENTS.md states warm verify is ~3 seconds, which matches.

Not caused by the task-67 change: git diff main -- eval/starters/ is empty, and the only files that branch touches are eval/judge/starter_parity.py and eval/judge/parity_selftest.py, neither of which starter_gate_control.py imports. The godot starter is byte-identical to main.

Why it matters: godot verify is what a building agent is told is the only evidence that its work is done, and what the Stop hook re-runs. If it is red on an untouched tree then every godot trial either saw a red gate it could not make green, or ran in a condition this control does not reproduce - and which of those it is changes how a godot arm's results read. Task 67 also recorded that the ticket claiming this gate green on 2026-08-23 was not checked.

One thing to be careful of: godot verify opens a real 640x400 window (its AGENTS.md says so, and there is no flag to avoid it), and the same run logged '[no_raise] flag INSUFFICIENT - window raised anyway; minimised to return focus' on the check row. Anything that reproduces this touches the operator's screen - see root AGENTS.md rule 13 and #61. Do not run it repeatedly on their desk without saying so.

Start by capturing test-render's own output rather than the recipe line: the gate control keeps only the last line.

## Authorised by the operator, 2026-08-23

**The operator has authorised running this even though reproducing it may open a window on their
machine.** That authorisation is recorded here rather than left in a chat message, because the
next agent to read this ticket needs it and the message will not survive.

It authorises the *window*, not the *noise*. Two things this project has already paid for:

- `eval/starters/_shared/launch.just` defines `STARTER_NO_RAISE` and `STARTER_SILENT_LAUNCH`, set
  to `"1"` by `wholegame.py` in trial environments. **Use the guarded path first** and only fall
  back to an unguarded run if the guarded one cannot reproduce the failure — say so if it does.
- `#61` is the record of a guard that tested the already-silent path and reported the defect
  unreproducible, and `#13`'s companion: Unity's player accepts `-disable-audio` and ignores it,
  so `exit 0` meant "the command ran", not "audio is off". **An accepted-but-ignored flag is
  worse than an unsupported one.** Do not conclude a guard works because a flag was accepted.

If a run does raise a window or make a sound, that is a finding about the guards, not an
acceptable cost — record it.

## What is established, so you do not re-derive it

`eval/tools/starter_gate_control.py` run to completion on 2026-08-23: **4 starters, 29
measurements, 1 FAILED, exit 1.** The failing row is godot's *"GREEN on pristine (the same
`just verify` must also exit 0)"* — `test-render` exit 1 in 4.1 s.

It is **not** caused by the starter changes made that day: `git diff main -- eval/starters/` was
empty at the time of measurement, and `starter_gate_control` imports neither file task 67
touched.

Note the shape this sits in. `just check` is green on the pristine godot tree — #98 repaired
that — and `just verify` is not. Those are different recipes, and the gate control gained the
verify direction only under task 51. **So this row has been red since it was first measured, and
was reported as green in a summary I wrote before running it to completion.** Establish how long
it has actually been failing before assuming it is new.
