---
id: 143
title: The g3_arena prompt does not say what a zero aim vector does, and the reference fixture silently retains the last one
status: in_review
priority: 2
refs: eval/suites/wholegame_prompts.py _G3_INPUTS, eval/judge/fixtures/ref_arena/game.py _update_aim, eval/suites/rendered/g3_arena__godot.txt, eval/RUNS.md, PR 19
done_when: 'Either _G3_INPUTS states what a zero or absent aim vector does and the reference agrees with it, or the ticket records with evidence that no bot input can produce a zero aim so the case is unreachable. If the prompt changes: eval/RUNS.md records the comparability break, prompt_guard.py and prompt_guard_control.py exit 0, judge/bot_mutants.py exits 0, and eval/suites/rendered is re-recorded in the same commit. Either way, state how many stored arena traces contain a zero-aim tick and over what population.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/31
---

eval/judge/fixtures/ref_arena/game.py::_update_aim keeps the previous orientation when the aim vector has magnitude below 1e-6 - the comment says 'no aim held: keep facing where we last aimed' - and _fire then fires along it. The rendered g3_arena prompt says only 'The aim fields describe a direction; only its orientation matters, not its length'. A submission that reads a zero aim as 'do not fire' or as 'fire along +x' is consistent with everything the prompt says and inconsistent with the reference the play-bot was written against, so the same bot input produces different traces for two honest submissions and the difference is scored. Found by CodeRabbit on PR 19; it read the fixture and confirmed the reference behaviour. NOT fixed in task 133: _G3_INPUTS is a game prompt, 90 stored whole-game trials ran under this wording, and editing it is a regime boundary that ticket was not scoped for. Check first whether any stored arena trace actually contains a zero-aim tick - if the bot never sends one, this is latent rather than active, and that is a different priority.

## note 2026-08-25

## note 2026-08-25 — the census comes FIRST, and it decides whether this is a prompt change at all

The `done_when` already says to check whether any stored arena trace contains a zero-aim tick.
**Do that before touching the prompt**, because it decides which of two very different tickets
this is:

- **No stored trace has one** → the defect is latent. Record the count and the population, state
  what an honest submission could do differently, and the cheapest correct fix may be to make the
  prompt say what the reference does — **with no regime boundary**, because no stored trial's
  behaviour could have depended on it. Say so explicitly rather than leaving it inferred.
- **Some trace has one** → two honest submissions diverged on scored behaviour, and that is a
  finding in its own right before it is a prompt fix.

**Prove the extraction before believing a zero.** A census that returns 0 because it looked in the
wrong field is indistinguishable from one that returns 0 because the case never happened, and this
project has published that mistake more than once (#170, #171). Find a tick whose aim you can state
in advance and show the extractor reports it correctly, then trust the count.

## Two things that landed today and change the ground

**Task 142 is the model for the boundary, and 152 wrote the twenty-second.** If the prompt changes,
copy that shape. Note the ordinal gate now reads compound ordinals correctly — `twenty-first` used
to be filed under `first` — so it will not misfile a twenty-third.

**`audio.py` no longer transcribes the arena's events by hand**: task 152 found `g3_arena` declares
**9** and the grader held 6, and fixed it. That is the same class as this ticket — the prompt and
something downstream disagreeing about the task — so if you find a second copy of the aim
semantics anywhere in `judge/`, it is a defect of the same shape and worth its own ticket.

## What NOT to do

Do not change `ref_arena/game.py` to match a new prompt sentence without checking `bot_mutants.py`
still exits 0. The reference is what the play-bot's criteria were written against; moving it moves
the criteria's meaning, and the mutant suite is what would notice.

## note 2026-08-25

## note 2026-08-25 — the case IS driven, the defect was latent, and the prompt now states it

**The census decided the branch, and it is the first branch of the two the ticket names.**
The play-bot drives the unspecified case, so this was a prompt change and a regime boundary,
recorded as `eval/RUNS.md`'s **twenty-third comparability break**.

### The numbers, and where they come from

`python3 eval/judge/aim_contract_control.py` — new in this ticket, and the producer for every
figure below. Population: *every tick the arena play-bot sends against the reference.*

| | |
|---|---|
| ticks sent | 7,540 |
| carrying a zero or absent aim | 4,636 |
| of those, holding `fire` | 33 |

All 33 come from `_multiplier_falls`, whose first loop builds `inputs = {"fire": True}` and adds
an aim only when `_nearest()` finds a live enemy — so it fires through the gaps between waves
with no direction attached. **Nothing else in `bot_arena.py` fires without an explicit aim**:
`_play_inputs` and `_combat` both fall back to `_aim((1,0,0))`, and `_materialises`, `_death` and
the `idle_tape` determinism replay send zero-aim ticks that never hold `fire`.

**There are no stored per-tick traces, and that is a fact about the corpus rather than a gap in
the search.** A stored arena trial holds `prompt.txt`, `diff.patch`, `tree.txt`, frames, a
`judge_pack`, and a `playbot.json` of verdicts and evidence strings. No input tape is written
anywhere under `eval/runs/**`. So the tick census above is the only population that exists for
this question, and re-running the bot is the only way to take it.

### The population of stored trials is 8, not 24

`python3 eval/tools/census.py` reports **24** stored `g3_arena` trials. Only the **8** in
`wg-arena3d-2026-08-15T12-46-30` ran under a prompt that declares `aim_x` at all — the other
16 (`wg-matrix-2026-08-13`, `archive-arena2d-wg-audio48`) predate the 2026-08-15 3D rewrite and
have no aim fields in their stored `prompt.txt`. Split with `grep -l aim_x` over those files.

### The defect was LATENT, and that is a measurement

Driving the whole play-bot against a reference patched to *return the gun to +x*, and again
against one patched to *withhold the shot*, returns **the same verdict on all 22 criteria** —
byte-identical evidence strings. No stored score could have depended on which reading a
submission chose. The exposure was to a future submission, not a past one.

**That identity is exactly the shape AGENTS.md rule 9 warns about**, so it is not believed on its
own: `aim_contract_control`'s direct rows show each arm producing a different bullet velocity on
a zero-aim firing tick, which is what separates *"the patches never applied"* from *"the readings
genuinely do not diverge"*.

### What the 8 stored submissions do, read from their source

- **8 of 8 hold the previous orientation** on a zero aim — `AIM_DEADZONE` 0.15, `AIM_EPSILON`
  0.0004, `length_squared() > 0.001`, `aim != Vec3::ZERO`, `lengthSquared3(...) > 0`, `> 1e-6`,
  `LengthSquared > 0f`, `> 1e-6f`. **0 of 8** reset the gun and **0 of 8** withhold the shot.
- **8 of 8 start the gun somewhere other than the reference's +x** — `-z` in six,
  `Vec3.Forward` and `Vec3.UnitZ` in the two Unity trials. That is why the new prompt sentence
  leaves the starting orientation to the submission, and why the control's `startz` arm exists:
  every criterion must return what it returned when only that free choice moves.

### Two things the next agent should not re-derive

**A zero aim arrives in two separable shapes.** The fields omitted, and the fields present and
zero. They are one sentence in the task and two branches in a submission (`"aim_x" in inputs`),
and a control that tests only one is green against a reference that mishandles the other — a
reference patched exactly that way passes every row of the single-shape version and turns 2 of
the 6 two-shape rows red. Both shapes are checked, for every arm.

**There is no second copy of the aim semantics in `judge/`.** The ticket's note asked, by
analogy with the hand-transcribed `GAME_EVENTS` task 152 found in `audio.py`. `grep -rn aim
eval/judge/*.py` outside `bot_arena.py` and `bot_mutants.py` returns only the substring inside
"claim". The contract lives in `_G3_INPUTS` and in `ref_arena/game.py::_update_aim`, and the
latter now carries a docstring naming the former.

### Deliberately NOT done

- **No criterion was changed.** `resetx` and `nofire` are now readings the prompt forbids, so a
  criterion *could* be written to fail them. The control records that none currently does, and
  goes red if that changes — at which point the question is whether the new criterion is
  legitimate, not whether the control is.
- **The starting orientation was not pinned.** Pinning it to +x would retroactively make 8 of 8
  stored submissions wrong for a choice the task never constrained.
- **No finding number was allocated.** The null above may be worth one; that is the
  orchestrator's to allocate against `main`.

## note 2026-08-25

## note 2026-08-25 — the controls timings were re-read, and the register's own point held

`.github/workflows/README.md` asks that a CI timing be re-read from a run rather than carried
forward or estimated by adding step times. Adding a gate is exactly the moment that matters, so
it was re-read from this branch's own `controls` run (32841910162, every step success):

| | was | now |
|---|---|---|
| `controls`, whole job | 685s | **791s** |
| `bot_mutants` | 226s | 286s |
| `tasks_mutants` | 320s | 305s |
| `skill_layout_control` | 125s | 75s |
| `aim_contract_control` | — | **11s** (5.2s locally) |

**The whole-job figure moved by 106s and this ticket's step is 11s of it.** That is the
register's own claim about run-to-run spread being larger than the cost of a step, measured on
the occasion it was written for. `gates` is left at 102s: nothing in `gates.yml`'s step list
changed here.
