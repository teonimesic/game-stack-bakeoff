---
id: 137
title: 'Exploration: can CPU, RAM and GPU be bounded for a scene performance pass on this host, and what does frame timing cost to measure'
status: in_review
priority: 2
refs: 'eval/SCENES.md, tasks/134, #49, #61, AGENTS.md rule 10'
done_when: 'A report in eval/SCENES.md (or a file it links) stating, for CPU, RAM and GPU separately: whether a real cap is achievable on this host, by what mechanism, and verified by measuring that the process could NOT exceed it rather than that a flag was accepted. Plus three measurements regardless of the capping answer: how each stack reports real-time frame timing, how much a fixed workload drifts thermally over a run-length repetition, and the run-to-run ramp spread on a single unchanged submission. A null - no portable cap, here is the alternative - closes this.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/26
---

`eval/SCENES.md` proposes a performance pass scored as a **ramp**: raise a scene's complexity
level until median frame time exceeds a budget, report the highest level sustained. That measures
the stack only if the resources underneath are held; otherwise it measures the machine, and a
laptop's machine changes during the run.

This is an EXPLORATION ticket. Its output is a report on what is achievable and what it costs,
not a capping implementation. **A null is a complete answer** - "no portable cap exists, here is
what to do instead" closes this.

## Why it is not a setting

The host is macOS (darwin). There are no cgroups. The candidates and what is already suspected:

- `ulimit -v` / `RLIMIT_AS` - macOS largely ignores it for the address-space limit that matters,
  and a GPU-backed process's memory is not all in that space anyway.
- `taskpolicy`, QoS classes, CPU affinity - these bias SCHEDULING, they are not hard caps. A
  scheduling bias is reportable but it is not "this trial had 2 cores".
- Docker / a Linux VM - real cgroups, and on macOS **no GPU passthrough**, which removes the
  thing being measured. A CPU-capped software-rendered scene is not the experiment.
- A Linux box with a real GPU and cgroups v2 - the only configuration where all three caps are
  real. It is also a DIFFERENT MACHINE from the one every existing result came from, which is a
  regime boundary and a confound, not a free upgrade.

**The GPU is the crux and should be answered first.** If GPU work cannot be bounded, then CPU and
RAM caps buy little for a GPU-bound scene, and the honest design is an uncapped ramp with the
machine recorded - which is a legitimate outcome, not a failure.

## What must be established regardless of the capping answer

- **Frame-time measurement that is not the capture path.** The correctness pass is deterministic
  and headless and is expected to run slower than real time. Establish how each stack reports
  real-time frame timing, per stack, or the ramp has nothing to read.
- **Thermal drift.** Measure it before designing around it: run one fixed workload repeatedly for
  the length of a plausible run and report how much the number moves. If it drifts more than the
  gaps between stacks, interleaving is mandatory and any non-interleaved perf result is
  uninterpretable.
- **Run-to-run spread on ONE submission.** A ramp level that varies by two levels across repeats
  of the same build cannot separate stacks. Measure the spread before anyone reports a difference.

## What NOT to conclude

Do not report a capping mechanism as working because a command accepted its flag. Unity's
standalone player takes `-disable-audio`, does nothing with it, and exits 0 - an accepted-but-
ignored flag is worse than an unsupported one, because it is indistinguishable from a working
guard by anything a script can see (#61). Verify a cap by measuring that the process actually
could not exceed it, on the path that really holds the resource.

## note 2026-08-24

## note 2026-08-24 — the correctness half has landed, so this is the only thing between scenes and a run

`eval/suites/scene_prompts.py` (133), `eval/judge/scene_probe.py` (134) and the three tier-3
aspects (135) are all merged. Scenes are gradeable for **correctness**. This ticket is the
performance half, and `eval/SCENES.md` states plainly that a performance pass must not be built
until this reports.

## Read the correctness contract before designing around it

The capture path is deterministic and tick-indexed on purpose: 660 ticks, 12 frames at
`floor(i*660/11)`, no wall-clock anywhere. **A performance pass cannot reuse it** — it is expected
to run slower than real time, and adding timing to it would contaminate the thing that makes every
criterion computable. Two passes, two records.

## A measurement that just arrived, and it sharpens the third required number

Task 135's agent measured, incidentally: **two consecutive `gates.yml` runs one markdown edit
apart came back 65s and 102s** — a 57% spread on unchanged content. That is CI rather than a
scene, and it is not this ticket's population, but it is the same question — *how much does this
machine move under me?* — and it says the answer here is likely to be large.

So of this ticket's three required measurements, treat the **run-to-run spread on one unchanged
submission** as the one most likely to decide the outcome. If a ramp level varies by two levels
across repeats of the same build, no stack comparison is possible at any cap, and the honest
report says so and stops. That is a complete answer to this exploration, and a more useful one
than a capping mechanism nobody can trust.

## Order the work by what can kill it

1. **Run-to-run spread on one unchanged build.** Cheapest, and if it is large everything else is
   moot.
2. **Thermal drift** over a run-length repetition. Same character.
3. **Capping**, GPU first — if GPU work cannot be bounded, CPU and RAM caps buy little for a
   GPU-bound scene, and an uncapped ramp with the machine recorded is the honest design.

Do not build the ramp. This ticket decides whether a ramp can mean anything.
