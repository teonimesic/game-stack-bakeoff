---
id: 137
title: 'Exploration: can CPU, RAM and GPU be bounded for a scene performance pass on this host, and what does frame timing cost to measure'
status: done
priority: 2
refs: 'eval/SCENES.md, tasks/134, #49, #61, AGENTS.md rule 10'
done_when: 'A report in eval/SCENES.md (or a file it links) stating, for CPU, RAM and GPU separately: whether a real cap is achievable on this host, by what mechanism, and verified by measuring that the process could NOT exceed it rather than that a flag was accepted. Plus three measurements regardless of the capping answer: how each stack reports real-time frame timing, how much a fixed workload drifts thermally over a run-length repetition, and the run-to-run ramp spread on a single unchanged submission. A null - no portable cap, here is the alternative - closes this.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/26
established_by: 'PR #26 squash-merged. Verified two load-bearing claims independently: taskpolicy -m 16 allowed 1024 MiB at exit 0, a 64x overshoot with no error - #61''s accepted-but-ignored shape reproduced; and the memory rlimits genuinely refuse, established with a control that discriminates (lowering the SOFT limit, always permitted, is REFUSED for RLIMIT_AS/DATA/RSS/STACK and ACCEPTED for RLIMIT_CPU and RLIMIT_NOFILE - my first probe refused everything including its own control and proved nothing). The null closes the ticket: no GPU lever exists, the CPU levers do not touch GPU frame time, and the container that has real cgroup caps has no GPU device. What replaces it is measured - spaced 25s the same workload holds to 0.766-2.485 percent against a 1.975x back-to-back swing. Allocated FINDINGS #172.'
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

## note 2026-08-25

## What this exploration settled, 2026-08-25

**The report is `eval/PERF-HOST.md`; the producer for its host figures is
`eval/tools/host_perf_probe.py`. Read those before re-measuring anything here.**

### The answer
No tested mechanism gives a usable GPU, RAM or CPU-rate cap on this host. What replaces a cap
is **spacing trials 25 s apart and requiring an exclusive machine**, and both are measured.
`DECISIONS.md`, *The scene performance pass is an uncapped ramp on a spaced, exclusive
machine*, carries the decision and its re-open conditions.

### Things not to re-derive
- **`taskpolicy -m` accepts a MiB memory limit and does not enforce it.** 64x overshoot at
  exit 0, with a jetsam priority and app resource policies. #61's shape. Do not build on it.
- **`RLIMIT_AS`/`RLIMIT_DATA`/`RLIMIT_RSS` cannot be set on Darwin at all** — `EINVAL` from
  `setrlimit`, and `RLIMIT_AS` and `RLIMIT_RSS` are the same number (5). `RLIMIT_STACK` set to
  its own hard limit is the control that proves the refusal is about the limit, not the value.
- **`RLIMIT_CPU` is the one enforceable rlimit** and it kills on cumulative CPU seconds.
- **No CPU-side QoS lever reaches the GPU.** `taskpolicy -b` cuts CPU throughput to 0.20x and
  moves GPU frame time under 0.1 ms in every interleaved round.
- **The GPU gives no client a floor**: 1 more GPU process costs 2.13x.
- **The colima VM has cgroup v2 caps that really enforce** (`--memory=512m` OOM-kills at exit
  137; `--cpus=2` gives 2.08 cores) **and no GPU device at all** — no `/dev/dri`, no DRM
  module, no Vulkan loader. It is a different experiment, not a stricter one. The VM was left
  stopped and the docker context restored to `desktop-linux`.
- **Frame timing is not the same quantity across stacks.** Bevy 0.19 on Metal records CPU time
  only (its own `RenderDiagnosticsPlugin` doc comment says so); the ts capture path is pinned
  to SwiftShader and has no GPU; godot 4.7 and unity 6 both expose a real GPU-side timer. A
  cross-stack ramp must read a harness-side wall clock.
- **Headless Chromium on this host gets SwiftShader with the starter's pin AND with no flags at
  all.** Only `--use-angle=metal` reaches `ANGLE Metal Renderer: Apple M3 Max`. `navigator.gpu`
  is undefined in every arm, so three's WebGPU renderer is unavailable. A ts perf pass needs a
  second launch path; that is a perf-pass change, not a starter change.

### The gap this ticket could not close
**The run-to-run spread of a real submission.** No scene has been built, so there is nothing to
repeat. Every figure is one fixed synthetic compute workload and is a **floor** — a submission
adds process start, shader compilation, asset loading and engine variance on top. Measure it on
the first scene that exists, before reporting any stack comparison. Both `eval/PERF-HOST.md`
and `eval/SCENES.md` say so.

Also unseparated: the cause of the drift. Thermal throttling, the SoC's shared CPU/GPU power
budget and co-tenancy are not distinguished by these arms — only the size (1.975x) and the
recovery time (a 25 s gap undoes it).

### Traps met while doing this, so the next agent does not meet them again
- **`/dev/shm` is 64 MB by default in a container**, so a `dd`-based memory-cap test stops
  there in BOTH arms and they agree — one value across the population the check exists to
  discriminate. `--shm-size=4g` on both arms is what makes the row work.
- **`docstat.py --sweep` only checks flags on FENCED command lines.** A phantom
  `--no-such-arm` in inline backticks reads exit 0; the same phantom in a ```bash block reads
  exit 1. Put commands you want gated in a fenced block. (Verified both ways on
  `eval/PERF-HOST.md`.)
- **`DECISIONS.md` carries no `[#NN]:` definition block** — only `README.md` does — so writing
  a finding citation there as `[#61]` takes `linkcheck.py` to exit 1. Bare `(#61)` is what its
  46 other citations use. Converting `DECISIONS.md` and `eval/` to reference-style would need a
  definition block per file plus those files added to `linkcheck.LIVE_DOCS`; that is real work
  and nobody has filed it.
- **CodeRabbit's "Reviews paused" is reported by the `CodeRabbit` check as `pass` / "Review
  completed".** The check is not evidence a review happened. It pauses after enough commits,
  edits its summary comment IN PLACE — so `pr_review_state.py` returns `UNRESOLVED` rather than
  seeing a new comment — and the way to tell is the summary comment's `updated_at` plus its
  body. Post `@coderabbitai review` and poll again with `--ignore-notice`.

### Where the numbers came from
The raw per-frame series behind the spread and drift tables were written to a session
scratchpad and are NOT in the repository. Re-derive with the producer rather than hunting for
them: `--spread 12` is ~5.5 min, `--drift 10` is ~10 min, `--gpu` ~4 min, `--caps` ~2.5 min.
Every arm refuses off darwin by name; `--selftest` is offline and runs anywhere.

## note 2026-08-25

## Review, 2026-08-25 — 7 rounds, past the ceiling

**This ticket used 7 review rounds against a ceiling of 5, and every round found something
real.** Recording it because `.agents/skills/work/SKILL.md` asks that the orchestrator be told
when a ticket turns out bigger than it was filed as.

| rounds | what they found |
|---|---|
| 1–2 | 2 fail-open classifications in `--caps` (a non-zero exit read as `ENFORCED`; the same for a failing *unrestricted* control) and a cache selftest that could not fail |
| 3–5 | 7 claims stated wider than their evidence, across all 3 documents |
| 6–7 | a percentile docstring justifying its convention with a reason that argues for both, then claiming numpy equivalence it does not have |

The shape of the misses is worth carrying forward: **not the measurements, which held up, but the
sentences written about them.** Every round 3-5 finding was a claim quantified more broadly than
the arms supported — "no mechanism" for "no tested mechanism", "all 3 caps" for a VM with no GPU,
"3 independent runs" for 3 runs one of which inherited the previous arm's machine state.

### Two things about CodeRabbit on this repository

- **Its `pass` / "Review completed" check is not evidence a review happened.** This branch sat in
  **Reviews paused** while the check read `pass`. The tell is the summary comment's `updated_at`
  and its body, not the check.
- **`pr_review_state.py` returning `UNRESOLVED` was correct** in that state, because the pause is
  written by editing the existing summary comment in place rather than by posting a new one, so
  neither the review arm nor the comment arm can fire. Both clean rounds here needed an explicit
  `@coderabbitai review` first, then a poll with `--ignore-notice`.

### Final state
`5cb9dee`, 0 commits behind `main`, 0 unresolved threads of 26, and `gates` / `controls` /
`CodeRabbit` all green. 2 comments were declined, each answered in its thread with the
measurement behind the decline; the reviewer accepted one explicitly and did not re-raise the
other.
