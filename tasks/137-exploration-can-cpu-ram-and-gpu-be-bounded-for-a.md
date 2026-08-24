---
id: 137
title: 'Exploration: can CPU, RAM and GPU be bounded for a scene performance pass on this host, and what does frame timing cost to measure'
status: todo
priority: 2
refs: 'eval/SCENES.md, tasks/134, #49, #61, AGENTS.md rule 10'
done_when: 'A report in eval/SCENES.md (or a file it links) stating, for CPU, RAM and GPU separately: whether a real cap is achievable on this host, by what mechanism, and verified by measuring that the process could NOT exceed it rather than that a flag was accepted. Plus three measurements regardless of the capping answer: how each stack reports real-time frame timing, how much a fixed workload drifts thermally over a run-length repetition, and the run-to-run ramp spread on a single unchanged submission. A null - no portable cap, here is the alternative - closes this.'
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
