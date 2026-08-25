---
id: 156
title: 'Scenes have all three tiers and cannot be run: wholegame.py has no knowledge of them'
status: done
priority: 1
refs: 'eval/wholegame.py, eval/suites/scene_prompts.py, eval/judge/scene_probe.py, eval/SCENES.md, tasks/133, tasks/136, #172'
done_when: One scene trial runs end to end under the existing harness and is graded by scene_probe.py, with its record stored under eval/runs/ and the per-criterion verdicts reported; aspects.applicability is called on every path the runner can reach a pack by, checked by naming them; whether the standing matrix command launches scenes is decided deliberately and written where the default is; the deterministic capture path gains no wall-clock timing; and the wall-clock cost of a full scene matrix is stated from that one cell. Launching a matrix is NOT in scope.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/37
established_by: 'PR #37 squash-merged. Scenes are runnable: wholegame.py had 0 occurrences of ''scene'' and the only thing between a scene and a play-bot was BOTS missing a key - a refusal by accident of a four-entry dict, arriving AFTER tier 1 had already run six recipes. Verified the stored trial myself: terminal_reason harness_kill_external with num_turns, cost_usd and input_tokens all None rather than 0, and the probe''s first contact with a real submission gives 5 pass, 1 FALSE NEGATIVE (layers.depth_ordered read a modular residue out of a field the contract wraps - all 7 layers below their own span while 37 wrap events fired) and 2 scored=False. A mutant could not have found that; only a submission that wraps could, which is rule 15. Wall clock is stated conditionally after review: >= 3599 s for the one measured cell, and the 16-cell figure named as 16 x one observation rather than a measurement of 16 cells.'
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

## note 2026-08-25

## What landed, and what the run found — 2026-08-25

PR #37, three commits. `eval/RUNS.md` holds the run entry and is the authority for every
figure below.

### The scene trial: killed at 60 minutes, salvaged, graded

`eval/runs/wg-scene-s1ts-2026-08-25`, one cell, `s1_parallax` x ts. **The build phase was
killed from outside at 3599s**, mid-agent-turn, by the session's background-task manager —
the transcript's last entry is `[Request interrupted by user]`. `build_trial` therefore
never reached the lines that capture the submission or write the trial record.

**What the next agent must not re-derive:** the work tree survives a kill like this, and
the submission is recoverable by re-running the capture by hand (`git add -A`,
`diff --cached --binary HEAD`, the tarball, `find`). The trial record was then written by
hand and says so in its own fields — `record_source`, `record_note`, and
`terminal_reason: "harness_kill_external"`, deliberately outside the harness's own
enumeration because nothing in the trial ended it.

**`num_turns` and the token totals are NOT reconstructable**, and this is worth knowing
before anyone tries: they come off the CLI's terminal result event, which never arrived,
and `modelUsage` appears nowhere else in the transcript. They are `null`, `cost_usd` is
`null` rather than `0`, and the transcript-derived counts (198 assistant messages, 137
tool-use blocks) live in a separate `transcript_reconstruction` field so nothing can
mistake them for the harness's counters.

**Do not relaunch this cell expecting to resume.** `prepare()` starts with `rmtree`, so a
relaunch destroys the salvaged tree; and the harness has no resume.

### The headline: `layers.depth_ordered` is a false negative

`tasks/162`. The criterion computes `abs(offset_last - offset_first)` per layer and asks
whether it decreases with declared depth. The scene contract asks submissions to **wrap**
`offset` — `loop.seamless` exists precisely because layers wrap — so the criterion read a
modular residue rather than a scroll rate.

The evidence is a property of the numbers rather than a reading of the source, which is
why it is worth trusting: **all 7 layers returned a value below their own declared span**,
and 37 `wrap` events fired in the same trace.

| layer | depth | span | measured |
|---|---|---|---|
| road | 0 | 240 | 120.1 |
| verge | 0.6 | 340 | 165.1 |
| grove | 1.5 | 440 | 304.0 |
| ridge | 4 | 400 | 232.0 |
| range | 9 | 480 | 36.0 |
| clouds | 20 | 900 | 245.7 |
| sky | 60 | 1800 | 84.6 |

The sign-convention hypothesis was checked and does not rescue it: the submission's own
`layerFactor(depth) = 1/(1+depth)` agrees with the criterion's direction.

**A mutant could not have found this** — only a submission that wraps could. Rule 15,
#46's shape, and it took the first real one.

### Two more, both filed

- `tasks/162` — the repair above, plus the open question the prompt never answers: does
  the contract mean `offset` cumulative or wrapped? Decide it in `eval/SCENES.md`.
- `tasks/163` — `render.nonempty` fails a scene at ink 0.966 against a 0.001–0.85 window
  calibrated on games. A scene that fills the frame is complying. The FLOOR still has work
  to do; the ceiling is what does not transfer.

`layers.image_parallax` and `loop.seamless` came back `scored=False`: the image estimator
read only 2 of 7 declared layers, against 8 missed pairs of 132 on the fixtures. The
probe's docstring predicted the direction. Not filed as a defect — it is the instrument
error `DECISIONS.md` already records, at the rate that docstring warned about.

### A finding is owed and I did not number it

The work skill forbids allocating one. The claim, the measurement and the control are in
the table above and in `eval/RUNS.md`; **the orchestrator should number it at merge.**

### What is wired, and where the decisions live

`--scenes` defaults to NONE and `--games` to every game; `wholegame.select_tasks()` holds
both and `DECISIONS.md` the reason. `aspects.INSTRUMENTS` declares the class of
`playbot`, `scene_probe` and `legacy_judge` so `applicability()` guards all six routes;
`eval/tools/scene_runner_control.py --paths` prints them. `census.py` has a third
population. The tier-2 slot keeps the name `playbot` deliberately — see `DECISIONS.md`.

### Not done, and deliberately

- **No matrix was launched.** The ticket puts that out of scope.
- `cost_census.py` was left alone. A group there is `(run, game)`, so a scene never shares
  one with a game, and a single 1-stack cell does not qualify as a group at all — it is
  rejected with a printed reason. Worth revisiting when a real scene matrix exists.
- The git hooks were not installed. `core.hooksPath` is shared git config and would arm
  the operator's main checkout; CI runs the same gates.

### Review

Two rounds, six comments, all six acted on. One half of one comment declined with its
evidence (the wall-clock figure stays in the CI register, which `AGENTS.md` defines as
recording what each gate costs). A third round was polled for and **did not arrive within
the bound** — `pr_review_state.py` returned `UNRESOLVED`, exit 13.
