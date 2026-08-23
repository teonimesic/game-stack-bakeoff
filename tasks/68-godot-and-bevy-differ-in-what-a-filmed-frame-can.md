---
id: 68
title: Godot and Bevy differ in what a filmed frame can contain, and no criterion knows it
status: in_flight
priority: 3
refs: 'eval/FINDINGS.md #107, eval/starters/godot/view/fx.gd, eval/starters/unity/Assets/View/Fx.cs'
done_when: either the two capture paths are made equivalent in what accumulated presentation state they can show, verified by a probe that renders state built over N ticks and is caught in both arms, or the asymmetry is recorded in eval/RUNS.md and every frames-reading aspect states that it cannot compare these two arms on accumulated state
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
