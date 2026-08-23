---
id: 80
title: 'godot just verify is red on a pristine starter: test-render fails, and the gate control has been reporting it'
status: done
priority: 2
refs: eval/tools/starter_gate_control.py, eval/starters/godot/justfile line 120, tasks/67
done_when: the cause of test-render exiting 1 on an untouched godot starter copy is identified and either repaired so starter_gate_control is 29 of 29 green, or recorded as an environment property with the condition that reproduces it and a control showing the other three arms are not subject to it
established_by: 'Cause: eval/starters/godot/tools/no_raise.gd is an [autoload], so it ran in EVERY godot process, not only just run; its last-resort MINIMISE of the window makes macOS stop producing frames and keep returning the last image drawn, so capture_frame handed the same stale picture to every render test. Proof from the artifact: the golden test''s frame.actual.png carries the HUD text tick 1 marker -3, 0 - the tick-1 probe capture taken before any test runs - while the test asked for seed 5 at tick 90. Six of nine tests failed blaming the arena transform, the particle system and the HUD; the two that PASSED were the two reproducibility tests, because a frozen frame is perfectly reproducible. NOT DETERMINISTIC, which is why one gate-control run was never a measurement of this row: pristine just test-render failed 5 of 12 on an idle machine, every failure printing flag INSUFFICIENT - minimised and every pass printing flag sufficient. BOTH DIRECTIONS, SINGLE VARIABLE: minimise removed with the NO_FOCUS flag kept, 0 of 12 failed; forced onto the minimise branch, 8 of 8 FAILED with 3 passed 6 failed every time. The minimise is not dead weight and was measured before touching it - lsappinfo front polled at 10 Hz returns the frontmost app from godot to the operator''s after about 0.35 s with the escalation live, against godot staying frontmost to process exit without it. REPAIR: tests/render_test.gd capture_frame now asserts its own precondition via _ensure_drawing_window - a capture needs a window that is DRAWING - written as the precondition and not as a fix for no_raise, and consuming no SETTLE_ATTEMPTS because exhausting them returns a null frame that run_all reports as nine SKIPs and exit 0, a green that measures nothing. SECOND DEFECT IN THE SAME FILE: under --headless there is no window but the dummy DisplayServer answers window_is_focused() with true, so check, test-sim, probe and probe-file each printed a claim to have minimised a window they never had - the LAST line those recipes emit, hence what the gate control recorded as their evidence, and a non-JSON line on just probe''s stdout which AGENTS.md documents as JSON only; eval/judge/probe.py files it under stdout pollution. Pinned by parsing every stdout line of just probe: before 4 lines 1 not JSON, after 3 lines 0. AFTER, on the committed bytes: just test-render 16 of 16 green with 9 on the minimise branch, 6 of 6 forced onto it, 16 fresh-copy warm-check-verify cycles green, and the RED direction still fires - view/_draw returning immediately gives 3 of 3 FAILED at 4 passed 5 failed. INSTRUMENT: eval/tools/starter_gate_control.py gains --log-dir and _run writes every invocation''s full output there with the streams kept apart, because a row''s last line is just''s own error: recipe X failed and names the recipe, never the reason - this ticket asked for that capture first and it was skipped, costing an hour. GATES, all unpiped: starter_gate_control 4 starters 29 measurements 0 FAILED 0 NOT CHECKED exit 0, plus 10 further godot-only runs all exit 0; judge/verify_blind.py BLIND 81 criterion ids over 4 out-of-repo trees exit 0; judge/parity_selftest.py 44 expectations 0 failed exit 0; judge/starter_parity.py No drift detected on any measured axis exit 0 with godot 26/26 tests really run; tools/docstat.py --sweep clean exit 0; tasks.py check 93 well-formed. DOCS: FINDINGS #132 in eval/findings/one-arm-bias.md with an index row, eval/RUNS.md records the FIFTEENTH comparability break with what it does and does not invalidate - only godot opens a render window and rust, ts and unity were green on 21 of 21 measurements in the same pre-repair run - and the range sentence in AGENTS.md, README.md and eval/FINDINGS.md moved to #19-#132. Branch task-80-godot-render-window-minimised, commit f48b49c, not pushed. NOTE FOR THE MERGE: this branch forked before main gained findings #128-#131, so the FINDINGS.md index table and the three range sentences will conflict; keep both sets of rows and the range at the higher number.'
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

## The cause, measured 2026-08-23 — do not re-derive any of this

**The row is not deterministic, which is why one run of the gate control is not a measurement of
it.** On an idle machine `just test-render` on a pristine copy failed **5 of 12** times. A single
green run of `starter_gate_control --stack godot` proves nothing about this row; count over
repetitions, and read the tool's exit code — never a `grep -c FAILED`, because the summary line
contains that word whatever the result.

**The cause is `eval/starters/godot/tools/no_raise.gd`, and it fires through the window.** It is
declared under `[autoload]` in `project.godot`, so it runs in EVERY godot process and not only
`just run`. When the `WINDOW_FLAG_NO_FOCUS` flag fails to stop the window taking focus, its last
resort is to MINIMISE the window to hand the keyboard back. **macOS stops producing frames for a
minimised window and keeps returning the last image it drew**, so
`get_viewport().get_texture().get_image()` returns a STALE image rather than null — and null is
the only thing `capture_frame` ever checked for.

The signature is unmistakable once seen: the golden test's `frame.actual.png` carries the HUD text
**`tick 1  marker -3, 0`** — the tick-1 probe capture taken at the top of `run_all` — while the
test asked for seed 5 at tick 90. Six of nine tests fail, each blaming something real and
innocent (the arena transform, the particle system, a HUD that "is not showing the state"), and
**the two that PASS are the two reproducibility tests**, because a frozen frame is perfectly
reproducible. That is rule 9 inside one process.

The one-line tell in any transcript: a failing run prints `[no_raise] flag INSUFFICIENT - window
raised anyway; minimised to return focus`; a passing run prints `flag sufficient`.

Pinned in both directions, single variable, on the pristine tree:

| `tools/no_raise.gd` | `just test-render` |
|---|---|
| as shipped | 5 of 12 FAILED |
| minimise removed, `NO_FOCUS` flag kept | 0 of 12 failed |
| forced to always minimise | 8 of 8 FAILED, 3 passed / 6 failed every time |

**The minimise is not dead weight — measure before removing it.** `lsappinfo front` polled at
10 Hz through a run: with the escalation live the frontmost application returns from `godot` to
the operator's after ~0.35 s; with it removed `godot` stays frontmost to process exit.

## What was changed

- `eval/starters/godot/tests/render_test.gd` — `capture_frame` now asserts its own precondition
  via `_ensure_drawing_window()`: a capture needs a window that is DRAWING, so a minimised one is
  restored and re-framed. Written as the precondition and **not** as a fix for `no_raise`, so a
  window minimised by anything else is covered. It deliberately consumes no `SETTLE_ATTEMPTS`:
  exhausting them returns a null frame, which `run_all` reports as nine SKIPs and **exit 0** — a
  green that measured nothing. Measured: restoring does not hand focus back to godot.
- `eval/starters/godot/tools/no_raise.gd` — returns early under the headless display driver.
  There is no window under `--headless`, but the dummy `DisplayServer` still answers
  `window_is_focused()` with **true**, so `check`, `test-sim`, `probe` and `probe-file` each
  printed a claim to have minimised a window they never had. That is the LAST line those recipes
  emit, so it is what the gate control recorded as their evidence, and it lands on `just probe`'s
  STDOUT, which this template's guide documents as carrying nothing but JSON trace lines
  (`eval/judge/probe.py` files it under "stdout pollution"). Pinned both ways with `json.loads`
  over every stdout line: pre-repair 4 lines, 1 not JSON; post-repair 3 lines, 0.
- `eval/tools/starter_gate_control.py` — `--log-dir`, and `_run` writes the full output of every
  invocation there, streams kept apart. **This ticket asked for that first and it was skipped**,
  which cost an hour rebuilding the same capture outside the tool. A row's last line is `just`'s
  own `error: recipe X failed on line N`, which names the recipe and never the reason.
