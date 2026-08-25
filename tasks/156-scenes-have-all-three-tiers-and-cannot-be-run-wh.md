---
id: 156
title: 'Scenes have all three tiers and cannot be run: wholegame.py has no knowledge of them'
status: todo
priority: 1
refs: 'eval/wholegame.py, eval/suites/scene_prompts.py, eval/judge/scene_probe.py, eval/SCENES.md, tasks/133, tasks/136, #172'
done_when: One scene trial runs end to end under the existing harness and is graded by scene_probe.py, with its record stored under eval/runs/ and the per-criterion verdicts reported; aspects.applicability is called on every path the runner can reach a pack by, checked by naming them; whether the standing matrix command launches scenes is decided deliberately and written where the default is; the deterministic capture path gains no wall-clock timing; and the wall-clock cost of a full scene matrix is stated from that one cell. Launching a matrix is NOT in scope.
---

Scenes are complete through all three tiers and **cannot be run**. `eval/wholegame.py` has no
knowledge of them: `TASKS` holds `g1_pong`, `g2_tetris3d`, `g3_arena`, `g4_platformer` and nothing
else, and no reference to `scene_prompts`, `SCENES` or any scene id appears in the harness.

What exists, all merged:

| | |
|---|---|
| prompts | `eval/suites/scene_prompts.py` — `s1_parallax`, `s2_glass`, rendered for 4 stacks (task 133) |
| tier 2 | `eval/judge/scene_probe.py` — 15 criteria, 20 mutants, 8 variants (task 134) |
| tier 3 | `fidelity`, `motion`, `framework_fluency`, asked only of scenes (task 135) |
| the judge's subject | `field.SCENE_STATEMENTS` → `SCENE.md` in scene packs (task 144) |

**This gap is deliberate and its reason has expired.** Task 133 kept scenes out of `TASKS` because
`wholegame.py` defaults `--games` to every key of it, so a registered scene would have been
launched by the standing matrix command against a probe that did not exist. The probe exists.

## What the wiring has to get right

1. **A scene is not a game and the runner must not treat it as one.** Tier 2 for a scene is
   `scene_probe.py`, not a play-bot; `aspects.applicability()` already refuses a game aspect on a
   scene and vice versa, and it is called from three paths — the runner is the place to check it is
   called from a fourth if a new one is added.
2. **Defaulting `--games` to every key remains a trap.** Whatever registry scenes land in, decide
   deliberately whether the standing matrix command should launch them, and say so where the
   default is written. A scene trial is not a cheap addition to a game run.
3. **The capture contract is already specified** — 660 ticks, 12 frames at `floor(i*660/11)`,
   deterministic, no wall-clock. The runner must not add timing to that path.

## Sequencing, and it is not optional

`eval/SCENES.md` and `tasks/136` both record it: **scenes are one new variable and the second
agent harness is another.** A run whose cells differ in two ways is the failure this project has
paid for twice. Establish scenes under the `claude` harness first, or cross them deliberately as a
factorial design — but do not stumble into the middle case.

**And #172 constrains the schedule, not just the design:** the same fixed workload spaced 25 s
apart holds to 0.766–2.485% and swings **1.975x** back-to-back. That is about the performance pass
rather than the correctness pass, but a matrix that packs scene trials back-to-back forecloses the
performance question before it is asked.

## What this ticket is NOT

**It does not launch a matrix.** Wiring is code and controls; launching is spend and the operator's
call. Finish with a scene trial that runs end to end and is graded — one cell, not a matrix — and
say what a full run would cost in wall clock.
