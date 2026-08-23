---
id: 68
title: Godot and Bevy differ in what a filmed frame can contain, and no criterion knows it
status: done
priority: 3
refs: 'eval/FINDINGS.md #107, eval/starters/godot/view/fx.gd, eval/starters/unity/Assets/View/Fx.cs'
done_when: either the two capture paths are made equivalent in what accumulated presentation state they can show, verified by a probe that renders state built over N ticks and is caught in both arms, or the asymmetry is recorded in eval/RUNS.md and every frames-reading aspect states that it cannot compare these two arms on accumulated state
established_by: 'Probe added to each arm''s own view (one cell per simulation tick the renderer was shown) and run through each arm''s own capture path in scratch clones; starters untouched. observed_run at ticks 8/60/240: godot 1/1/1, ts 1/1/1, unity 1/1/1, rust 9/32/32 - so the partition is 1 vs 3, not godot vs bevy, and #107''s published two-arm framing is corrected in eval/findings/one-arm-bias.md. Positive control, view handed ticks 0..60 by hand, reaches 32 in godot, ts and unity, which is what makes the three 1s a measurement rather than a dead probe; rust''s control is uninformative by construction and is reported as such. Second axis measured: godot pumps 3 render frames per capture carrying 24.7/27.7/28.5 ms of wall clock across three identical captures, ts and unity pump 1, and rust exhausted all 240 settle frames and returned its fallback because a moving effect can never satisfy two byte-identical readbacks. Recorded rather than equalised: eval/RUNS.md carries both tables and the reasoning, and FRAMES_BLIND_SPOT in eval/judge/aspects.py is carried by ux, fun and fun_frames, naming no arm and counting no arms so the judge stays blind, byte-identical across fun and its fun_frames control. eval/judge/aspects_selftest.py pins all three properties with a mutant each plus a variant that counts the arms without naming one, 7 expectations, exit 0. Gates unpiped: docstat.py --sweep exit 0, tasks.py check exit 0, pack_selftest exit 0, gate_selftest exit 0, parity_selftest exit 0 with 44 expectations in the checkout that has node_modules. No starter or template file changed, nothing re-scored, no new finding number taken.'
---

## What this is

`just film` captures the 12 PNG frames that every frames-reading aspect (`ux`, `fun_frames`,
`fun`) judges. Each arm implements it in its own harness.

## What is wrong, and how we know

Finding **#107**, measured 2026-08-23: Godot's `capture_frame` **steps the simulation to tick N
with no view attached and syncs once**, so any presentation state that accumulates across ticks —
a trail, a particle burst, a shake, a decay — is structurally invisible to every filmed frame.
Bevy's runs the whole App per tick, so the same state is both visible **and** deterministic.
Task 52 found Unity's `RenderHarness.CaptureFrame` has the same shape as Godot's.

> Two harnesses agreeing on every recorded field can still differ in **what an artifact is able
> to contain.**

## Why it matters

Every frames-reading aspect compares arms on what the frames show. If two arms cannot show the
same class of thing, a difference in those aspects is partly a property of the capture path
rather than of the submission — and nothing anywhere records that.

This is the one-arm-bias shape (#62, #72, #77) in the evidence channel rather than in a grader,
which is why no criterion catches it: each arm's frames are internally valid.

It became live rather than theoretical when tasks 26 and 52 added particle scaffolding to Godot
and Unity. Both were **designed around** this — `fx.gd` and `Fx.cs` drive the emitter as a pure
function of sim state precisely because an emitter driven by elapsed time would render nothing.
That is a correct workaround for scaffolding the template ships, and it does nothing for an agent
who writes accumulated presentation state of their own.

## What should be done

First **establish the radius**, because it may be smaller than it looks: write a probe that
builds state over N ticks and renders it, run it in all four arms, and report which arms show it.
Task 52's `ABurstAges` render test is the nearest existing thing.

Then either make the capture paths equivalent, or record the asymmetry. **Recording is a
legitimate and possibly better outcome** — changing a capture path is a regime boundary that
invalidates frame comparisons across it, and the project has eight stored runs of frames.

If you record it, every frames-reading aspect must state that it cannot compare these arms on
accumulated presentation state. An aspect that cannot know its own blind spot will keep scoring
across it.

## What not to conclude

Do not read this as "Godot's frames are worse". They are internally valid and deterministic —
that determinism is *why* the harness syncs once. The defect is that two arms differ in what a
frame can contain, and that no document says so.

## What the work established, 2026-08-23 — do not re-derive

**The radius is 1 versus 3, not godot versus rust, and the title of this ticket is wrong.**
Godot, TypeScript **and Unity** all show the renderer exactly one simulation tick per filmed
frame. Rust/Bevy is the single arm that behaves differently. The majority behaviour was the one
being treated as the exception.

`observed_run` = consecutive ticks ending at the captured tick that the *renderer* was shown,
cap 32. Each arm's own capture path, run in a scratch clone (the starters were not touched):

| capture at tick | godot | rust | ts | unity |
|---|---|---|---|---|
| 0 | 1 | 1 | 1 | 1 |
| 8 | 1 | **9** | 1 | 1 |
| 60 | 1 | **32** (cap) | 1 | 1 |
| 240 | 1 | **32** (cap) | 1 | 1 |
| positive control — view handed ticks 0..60 | **32** | n/a | **32** | **32** |

Four things that cost time and should not be paid for twice:

1. **The probe must be a CONSECUTIVE-RUN counter, not a call counter.** Godot's `RenderTests`
   builds the view once in `setup()` and reuses it across every capture, so a naive "times
   `sync` was called" counter accumulates across *captures* and grows to look like success.
   Counting the longest run of consecutive ticks ending at the captured tick is immune. The one
   anomaly in the table — godot reading 2 at ticks=1 — is exactly this leaking through at the
   only tick count where the window can reach a neighbouring capture's tick.
2. **The positive control is what makes three 1s a measurement.** Hand the view the tick history
   the capture path withheld and every arm paints 32. Without it, "1" is indistinguishable from a
   probe that never worked. Rust's control is uninformative *by construction* — it already sees
   every tick — and that is reported, not omitted.
3. **A cap is a ceiling, not a measurement (AGENTS.md rule 8).** The render-frame axis was first
   measured with the same cap of 32 and returned 32 for *every* input including tick 0. Raising it
   to one screen pixel per frame turned the same reading into 238–239, which is `MAX_SETTLE_FRAMES`
   exhausted. The first number was not wrong so much as uninterpretable, and it looked fine.
4. **Two axes, partitioning differently.** Ticks (above) splits rust from the rest. *Render
   frames* splits again: godot pumps **3** per capture carrying **24.7 / 27.7 / 28.5 ms of wall
   clock** across three identical captures — so a `_process(delta)` tween there is partly visible
   and non-reproducible — while ts and unity pump exactly one and rust's settle loop pumps until
   two readbacks match, which an effect still in motion never satisfies. Bevy can show
   accumulating state; it cannot show it *and* settle.

**Decided: recorded, not equalised**, on the ticket's own grounds. `eval/RUNS.md` carries the
tables and the reasoning; `eval/findings/one-arm-bias.md` #107 carries a `RADIUS MEASURED`
section correcting its published two-arm framing; `eval/judge/JUDGING.md` states it beside the
evidence table.

**The graders are told, and the wording is constrained.** `FRAMES_BLIND_SPOT` in
`eval/judge/aspects.py` is carried by all three frames-reading aspects. It must **not name or
count the arms** — "three of the four" leaks the partition to a judge that is blinded to which
submission is which (#32) — and it must be **byte-identical in `fun` and `fun_frames`**, because
`fun_frames` is `fun`'s control and a control briefed differently from its treatment is not a
control. `eval/judge/aspects_selftest.py` pins all three properties with a mutant each plus a
variant that counts the arms without naming one.

**Not done, and deliberately:** no capture path was changed, nothing was re-scored (the judge
tier weighs 0.00), and no new finding number was taken — this is a correction to #107's radius,
and eight peer tasks were in flight against a shared numbering.
