# Can a scene performance pass hold this machine still?

`eval/SCENES.md` proposes scoring a scene as a **ramp**: raise a scene's complexity level until
median frame time crosses a budget, report the highest level sustained. That measures the stack
only if CPU, RAM and GPU are held underneath it. This page reports whether they can be, on the
machine every existing result came from, and what the alternative is.

**The answer is a null on the GPU and it closes the question.** Every mechanism tested here — and
they are the ones a search of the host's own tooling turns up — leaves GPU throughput untouched,
and one competing GPU process costs more than two ramp levels. So the honest design is an
**uncapped ramp on an exclusive machine, spaced rather than back-to-back, interleaved across arms,
with the machine recorded per trial** — and that design is buildable today, because the two
numbers that decide whether it can mean anything both came back small enough.

**What a null here is and is not.** These arms establish that the tested mechanisms do not cap or
bias GPU work; they cannot establish that no mechanism could. Each arm is one row of
`host_perf_probe.py --gpu`, and a candidate nobody has thought of is a new row rather than a
refutation — which is the shape of the re-open conditions in `DECISIONS.md`.

Every figure below names the arm that made it, and all of them were measured on 2026-08-24 on the
machine described next. The producer is one file, and the arms are fenced here so the doc sweep
checks them:

```bash
python3 eval/tools/host_perf_probe.py --caps      # can CPU or RAM be bounded?
python3 eval/tools/host_perf_probe.py --gpu       # a GPU lever, and how isolated GPU work is
python3 eval/tools/host_perf_probe.py --spread 12 # 12 launches, 25 s idle between
python3 eval/tools/host_perf_probe.py --drift 10  # the same workload back to back for 10 min
python3 eval/tools/host_perf_probe.py --selftest  # the analysis, offline, with its mutants
```

## The machine

    Apple M3 Max  16 cpu (12P+4E)  64 GB  Darwin 25.2.0  arm64

It is a laptop on AC power that other work runs on: the arms below recorded `load1` between 3.79
and 17.01, and ambient GPU utilisation with nothing of ours running was 0% median, non-zero in 10
of 30 samples, peaking at 18%. **This host is not exclusive**, which matters more than any cap
below.

## Capping, GPU first

### No tested mechanism bounds the GPU, and none biases it either

The CPU-side levers that demonstrably act on the CPU do not reach the GPU. `--gpu` runs the same
fixed workload under each candidate, interleaved over 4 rounds:

| arm | median frame time | vs control | per round |
|---|---|---|---|
| control | 9.052 ms | 1.00 | 8.359, 8.387, 9.716, 10.138 |
| `taskpolicy -b` | 9.106 ms | 1.01 | 8.358, 8.402, 9.811, 10.053 |
| `taskpolicy -c utility` | 9.221 ms | 1.02 | 8.362, 8.454, 9.987, 10.128 |
| **contended** — one more GPU process | 19.286 ms | **2.13** | 16.321, 18.470, 20.102, 22.748 |

`taskpolicy -b` cuts CPU throughput to 0.20x (below), so it is not an inert arm. On the GPU it
tracks the control to within **0.1 ms** in every round; `-c utility` tracks it to within
**0.28 ms**, its widest gap being 9.987 ms against a control of 9.716 ms. Both are far smaller
than the control row's own movement of 8.36 → 10.14 across the same four rounds, which is what
any ratio here has to be read against and why the arms are interleaved rather than run in blocks.

**Read the contended row as the isolation figure, not as a cap.** Adding one more GPU process
roughly doubles frame time — 1.95x, 2.20x, 2.07x, 2.24x against the control of its own round.
The GPU time-slices between clients and gives no client a floor.

### RAM: nothing on this host bounds it, and one flag lies about it

`setrlimit` was asked directly rather than through the shell builtin, so `EINVAL` separates "this
limit does not exist here" from "you may not raise it":

| rlimit | current / hard | `setrlimit` |
|---|---|---|
| `RLIMIT_AS` | infinity | **FAILED, `Invalid argument`** |
| `RLIMIT_DATA` | infinity | **FAILED, `Invalid argument`** |
| `RLIMIT_RSS` | infinity | **FAILED, `Invalid argument`** |
| `RLIMIT_STACK` | 8372224 / 67092480 | OK |
| `RLIMIT_CPU` | infinity | OK |

`RLIMIT_AS` and `RLIMIT_RSS` are **the same number on Darwin** (both `5`), so there is one
address-space limit and it is unsettable. `RLIMIT_STACK` is the control that makes the other rows
readable: it is set to its own hard limit and succeeds, so `EINVAL` on the three above is the
kernel refusing the limit rather than refusing the value.

**`taskpolicy -m` documents "memory limit (in MiB)" and does not enforce one.** A hog asked for
2048 MB and touched every page:

| arm | exit | got |
|---|---|---|
| control, no restriction | 0 | `ALLOCATED_MB 2048` |
| `taskpolicy -m 512` | 0 | `ALLOCATED_MB 2048` — **IGNORED** |
| `taskpolicy -m 64 -j 10 -a` | 0 | `ALLOCATED_MB 2048` — **IGNORED** |

A 64x overshoot, with a jetsam priority and application resource policies, at exit 0. This is
#61's shape exactly — an accepted-but-ignored flag, indistinguishable from a working guard by
anything a script can see — so it is named here rather than left for someone to discover by
building a cap on it.

### CPU: one enforceable rlimit, one large bias, and no way to ask for a core count

`RLIMIT_CPU` is real: set to 2 seconds against a hog wanting 8, the process died of `SIGXCPU` at
exit 152, where the unrestricted control ran to completion at exit 0. It bounds **cumulative CPU
seconds and kills on exceeding them**, which is a kill switch rather than a rate.

The rate levers, measured as CPU-seconds taken in a fixed 6 s wall window by 16 spinning threads,
interleaved over 3 rounds:

| arm | CPU-seconds | vs control | its own run-to-run range |
|---|---|---|---|
| control | 89.46 | 1.00 | 0.7% |
| `taskpolicy -b` | 18.20 | 0.20 | 17.0% |
| `taskpolicy -c background` | 17.60 | 0.20 | 17.7% |
| `taskpolicy -c utility` | 87.24 | 0.98 | 2.4% |
| `nice -n 20` | 89.40 | 1.00 | 0.3% |

**`nice` and `utility` do nothing**, at 1.00x and 0.98x against a control whose own rounds span
0.7%. Background QoS is a large effect and it is still not a cap, for a reason that does not
depend on how noisy the number is: **it takes no argument.** There is no way to say *this trial
gets 4 cores*. It is on or off, and what it grants is whatever the E-cluster had spare — 17% and
17.7% run-to-run here, and 57% in a separate 4-round sample that ranged 9.29 to 16.89
CPU-seconds on the unchanged workload.

## The Linux VM route: real caps, and no GPU at all

The one configuration where all three caps are real is a Linux guest with cgroups v2. A VM is
already installed here, so this was measured rather than assumed. Inside it:

- `/sys/fs/cgroup` is `cgroup2fs` — real cgroups v2.
- **`/dev/dri` does not exist**, `/sys/class/drm` holds only `version`, no DRM or virtio-gpu
  module is loaded, and there is no Vulkan loader. There is no GPU device of any kind.

The caps enforce, to the standard the host arms failed:

| cap | control | treatment |
|---|---|---|
| `--memory=512m` writing 2048 MB | exit 0, 2.0 GB written | **exit 137**, OOM-killed, nothing written |
| `--cpus=2`, 16 busy loops for 6 s | 72.06 CPU-seconds | **12.47 CPU-seconds = 2.08 cores against 2.00 asked**, a 3.9% error |

That is what a cap looks like: a number you ask for and get back. Compare `taskpolicy -b`, which
has no number to ask for.

**And it is still the wrong machine.** A GPU-bound scene rendered without a GPU is not the
experiment, so a container run would compare software rasterisation across four stacks — and it
would be a different machine from the one every existing result came from, which is a regime
boundary rather than a free upgrade.

> **`--shm-size=4g` is required on both arms of the RAM row.** `/dev/shm` is capped at 64 MB by
> default in a container, so without it the hog stops at the tmpfs limit in the control **and**
> under the cap, and both arms agree at 64 MB — one value across the population the row exists to
> discriminate, which is rule 12's tell rather than a result.

## How much the machine moves, with no cap in the picture

Two numbers decide whether a ramp can mean anything, and they answer differently.

### Spaced launches are stable to about 1%

`--spread` runs the same fixed workload in separate processes with a 25 s idle gap between them.
Three independent runs, one of them started hot straight after the 10-minute drift arm:

| run | n | median of per-launch medians | range as a share of the median |
|---|---|---|---|
| first, machine quiet | 12 | 8.3883 ms | 0.784% |
| second, started hot | 12 | 8.3821 ms | 2.485% |
| third, through the committed tool | 3 | 8.3839 ms | 0.766% |

The three medians agree to **0.074%**, across runs separated by fifteen minutes and a ten-minute
GPU burn. The second run's wider range is its **first** launch alone (8.567 ms); launches 1–11
span 8.358–8.407 ms, a 0.585% range. So a 25 s idle gap fully recovers a machine that had been
reading 11.5 ms back-to-back moments earlier — **the drift below is about sustained load, not
about accumulated heat.**

The host clock is looser than the GPU clock: per-launch `wall_ms` medians spread 2.200% where
`gpu_ms` spread 0.784% in the same run. Which clock a ramp reads is a design decision.

### Back-to-back, the same workload swings by a factor of two

`--drift` removes the gap. Over 10 minutes, bucketed per minute:

| t | median | | t | median |
|---|---|---|---|---|
| +0 s | 9.947 ms | | +300 s | 10.940 ms |
| +60 s | 12.751 ms | | +360 s | 10.391 ms |
| +120 s | **15.815 ms** | | +420 s | 10.178 ms |
| +180 s | 13.728 ms | | +480 s | 10.147 ms |
| +240 s | 12.300 ms | | +540 s | 11.502 ms |

Best single launch **8.362 ms**, worst **16.514 ms** — a **1.975x swing on a workload that never
changed**, and the first launch more than 10% above the opening value arrived at **t+16 s**.

**The shape is not a monotone throttle** — it climbs to a peak at t+120 s and recovers — so heat
is not the whole cause, and this arm cannot separate thermal throttling from the SoC's shared
CPU/GPU power budget or from a co-tenant process. It does not need to: whatever the cause, the
ramp reads it. What the spread arm adds is that a 25 s gap undoes it.

### What that costs a ramp, in levels

A ramp reports the highest level sustained, so a frame time inflated by `r` costs
`log(r) / log(step)` levels, where `step` is the work ratio between adjacent levels:

| condition | ratio | at step 1.25 | at step 1.5 | at step 2.0 |
|---|---|---|---|---|
| spaced launches, worst of 3 runs | 1.025 | 0.11 | 0.06 | 0.04 |
| back-to-back over 10 min | 1.975 | 3.05 | 1.68 | 0.98 |
| one competing GPU process | 2.130 | 3.39 | 1.86 | 1.09 |

**Spaced, the host costs about a tenth of a level and a ramp can separate stacks. Back-to-back or
shared, it costs one to three levels and no stack comparison survives.** That is the whole result,
and it is a design constraint rather than a blocker.

## Frame timing, per stack

A ramp has to read a clock, and the four stacks do not offer the same one. Every row was read
from the installed toolchain or the starter, not from documentation:

| stack | GPU-side frame timer here | what it offers | source |
|---|---|---|---|
| rust — Bevy 0.19 | **no** | `FrameTimeDiagnosticsPlugin` gives `fps` and `frame_time`; `RenderDiagnosticsPlugin` states *"Timestamp queries … supported only on Vulkan and DX12. On other platforms (Metal, WebGPU, WebGL2) only CPU time will be recorded"* | the crate's own doc comment |
| ts — three 0.185, `WebGLRenderer` | **no** | the capture path pins `--use-angle=swiftshader`, and the renderer string confirms `SwiftShader driver` — a CPU rasteriser | `starters/ts/src/view/harness.ts`, confirmed by reading `WEBGL_debug_renderer_info` |
| godot 4.7 | **yes** | `viewport_set_measure_render_time` and `viewport_get_measured_render_time_gpu`, plus `--print-fps` and `--gpu-profile` | `strings` on the installed binary, `godot --help` |
| unity 6000.0.45f1 | **yes** | `FrameTimingManager` with `CaptureFrameTimings`, `GetLatestTimings`, `cpuFrameTime`, `gpuFrameTime` | `strings` on `UnityEngine.CoreModule.dll` |

**So a cross-stack ramp must read a stack-neutral clock — wall time per presented frame, taken by
the harness outside the engine — or it compares a CPU frame time on one arm against a GPU frame
time on another.** The engines' own timers stay useful per stack and as a cross-check; they are
not the comparable quantity.

### The real-time path is not the capture path, and it differs per stack

The correctness pass is deterministic, headless and tick-indexed, with no wall clock anywhere. It
cannot be reused for timing. What each stack offers instead:

| stack | harness-drivable GPU path today | real-time path | opens a window? |
|---|---|---|---|
| rust | `just film` / `just test-render` — windowless wgpu on Metal, loop pumped by hand under `TimeUpdateStrategy` | `just run`, a windowed app | yes, and **refused under the harness**: Bevy on macOS cannot be stopped from taking keyboard focus |
| ts | `just film` — headless Chromium, **software rasteriser** | `just run` starts a dev *server*; a human opens the browser | no window, and no GPU either |
| godot | `just film` / `just test-render` — **needs a real display** and opens a 640x400 window; `--headless` returns a null image | `just run`, windowed | yes |
| unity | `just film` — `-batchmode` **without** `-nographics`, a real graphics device | `just run` builds a player and `open -g -j` launches it hidden | no visible window |

Two of these need work before a ramp can run at all:

- **ts has no hardware path in the harness.** Measured on this host, Playwright's headless
  Chromium gets `SwiftShader driver` **both** with the starter's pin and with no flags at all;
  only `--use-angle=metal` reaches `ANGLE Metal Renderer: Apple M3 Max`. `navigator.gpu` is
  undefined in every arm, so three's WebGPU renderer is unavailable. A ts ramp needs a second
  launch path — which is a perf-pass change, not a starter change, and the correctness pass keeps
  its software rasteriser for the determinism it was pinned for.
- **rust and godot want a window.** Bevy's real-time path is refused under the harness for focus
  stealing, and godot's rendering path needs a real display by measurement. `just film` is
  windowless on rust and unity and windowed on godot, so a perf harness that drives `film`-shaped
  invocations still puts a window on the operator's desk for one arm of four (rule 13).

## What a performance pass must do, given all of the above

1. **Do not build a cap.** None exists for the GPU, none exists for RAM, and the CPU has a kill
   switch and a bias with no argument. Report the machine instead: `host_perf_probe.py --spread`
   is a cheap before-and-after witness that the host was in its usual state.
2. **Space the trials.** A 25 s idle gap between measured runs recovered this machine completely;
   back-to-back costs one to three ramp levels. Spacing is the single highest-value design choice
   here and it is free.
3. **Require exclusivity.** One competing GPU process costs 2.13x. Nothing else may run — not the
   correctness pass, not a second trial, not a judge call. The GPU gives no client a floor.
4. **Interleave the arms and record when each trial ran**, as `eval/SCENES.md` already asks. The
   drift arm's shape is why: it is not monotone, so a block design cannot be corrected afterwards
   by assuming the machine only ever got slower.
5. **Read a harness-side wall clock**, not each engine's own timer, or the arms are not
   comparable. Keep the engine timers as a per-stack cross-check.
6. **Discard warm-up frames and state how many.** On a pure compute workload with no shaders,
   1–2 leading frames sat above steady state and a single frame reached 22.093 ms against an
   8.4 ms median. A real engine is far worse — the rust starter's own capture harness allows up
   to 240 settle frames because wgpu compiles pipelines lazily.
7. **Report the median over hundreds of frames, never a max and never twelve.** The 12-frame
   capture list the correctness pass uses is far too few: single frames at 2–3x the median occur
   in every run measured here.

## What this did not establish

- **The run-to-run spread of a real submission, which is what the ticket asked for.** No scene
  has been built, so there is nothing to repeat. Everything above is one fixed synthetic GPU
  workload, and it is a **floor**: a submission adds process start, shader compilation, asset
  loading and engine variance on top. The floor is the useful half of the answer — it says the
  *machine* is not what stops a ramp, provided trials are spaced and the host is exclusive — but
  the submission-level figure has to be measured on the first scene that exists, before any
  stack comparison is reported.
- **The cause of the drift.** Thermal throttling, the shared CPU/GPU power budget and co-tenancy
  are not separated by these arms. Only the size of the effect and its recovery time are.
- **Whether a render workload drifts like a compute workload.** The fixed workload is a pure ALU
  compute kernel. It is the strongest available thermal stressor, so it plausibly bounds the
  effect from above, but that is an argument and not a measurement.
- **Anything about a different machine.** Every number here is this host on this date.
