---
id: 135
title: 'Tier 3 for scenes: fidelity, motion and framework_fluency, with the unblindable one marked as such'
status: in_testing
priority: 2
refs: 'eval/SCENES.md, eval/judge/RUBRIC.md, eval/judge/aspects.py, eval/judge/verify_blind.py, eval/judge/weight_sensitivity.py, tasks/134, #21, #92'
done_when: The three aspects exist and are asked only of scenes; verify_blind.py passes for fidelity and motion; framework_fluency is marked unblindable in RUBRIC.md and in every place its number is published, and is reported per stack rather than ranked across stacks; the scene tier 3 ships at weight 0.00 with weight_sensitivity.py run over the open interval and its result recorded. BLOCKED BEHIND 134.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/22
established_by: 'PR #22, 3 review rounds then 2 clean; gates+controls pass in CI at ba7ff68. aspects_selftest 6 checks / 6 mutants+variants / id-shape corroboration both ways; field_ranks --selftest check 14 with a mutant and a variant; blurb_selftest check 10 pins the run_field KeyError both ways. verify_blind green on out-of-repo starters, red on a planted canary + criterion id, 81 criterion ids before and after. weight_sensitivity --selftest PASSED, 10 groups all games, 0 scene gradings: NOT ASKED. Filed tasks 144, 145, 146.'
---

Games are judged on `architecture`, `idiomatic`, `fun`, `fun_frames`, `ux`, `audio`. A scene has
no player, so `fun` has no referent and `fun_frames` is judging a thing that does not exist.
`eval/SCENES.md` proposes three aspects: `fidelity` (frames), `motion` (frames),
`framework_fluency` (code).

## The blinding problem, which is the substance of this ticket and not a footnote

**`framework_fluency` cannot be blinded.** The question IS which engine's APIs appear in the
source, so naming the stack is the measurement rather than a leak of it. It must be reported per
stack and must never enter a cross-stack ranking or any blind comparison.

This is not a new wall. The blind judge field of 2026-08-23 found `architecture` opened ZERO
arm-naming files and the judge still wrote that it had identified every stack from code content
alone - the blinding is defeated by what the code IS, not by what the files are called, and
`idiomatic` is structurally unblindable for the same reason. Do not add a third aspect with that
property without saying so where the number is published.

`verify_blind.py` must still pass for the two frame-seeing aspects.

## The weight question this is the honest test of

Tier 3 sits at weight 0.00 because it could not reorder anything (#21, and DECISIONS.md task 29).
Scenes have an aesthetic component the probe cannot reach, so they are the first real chance to
ask whether that weight should ever be above zero.

**Ask it as a measurement, not as an argument.** `weight_sensitivity.py` sweeps the OPEN interval
and reports whether a weight can reorder anything. Run it on scene results before proposing any
weight. And read #92's lesson before acting on a null: an inert parameter is a question about the
QUANTITY, not about the parameter - if tier 3 cannot act, go and measure what it has ever
measured rather than tuning the weight.

## What NOT to do

Do not give the scene tier 3 a non-zero weight in the same change that introduces it. Ship it at
0.00, reported alongside, and let the sweep decide in a later ticket on real data.

## note 2026-08-24

## note 2026-08-24 — 134 has landed, so tier 2 exists and this is the layer above it

`eval/judge/scene_probe.py` is merged: 15 criteria, 20 mutants, 8 variants. Read it before
proposing aspects — the point of tier 3 here is what the probe **cannot** reach, and the probe now
reaches further than `eval/SCENES.md` assumed when this ticket was written.

## The measurement this ticket is actually for

Tier 3 sits at weight 0.00 because it could not reorder anything. Scenes are the first honest
chance to ask whether that should ever change, and the answer must come from
`weight_sensitivity.py` over the **open** interval, not from an argument that aesthetics matter.

**Read #92 before acting on a null.** If the sweep says the weight cannot act, the correct next
move is to ask what the tier has ever *measured* — not to tune the weight. Reweighting an inert
term is the move that looks like a fix and changes nothing, and that mistake has already been made
once here.

**There is no scene corpus yet**, so the sweep has nothing to run over. That is not a blocker for
shipping the aspects at 0.00; it IS a blocker for proposing any other weight, and the ticket should
close saying so rather than guessing.

## `framework_fluency` — say it is unblindable at the point of proposal

The whole question is which engine's APIs appear in the source, so naming the stack IS the
measurement rather than a leak of it. Mark it in `RUBRIC.md` and anywhere its number is published,
report it per stack, and never rank stacks with it.

This is not a new wall: the blind judge field of 2026-08-23 found `architecture` opened **zero**
arm-naming files and the judge still identified every stack from code content alone. `idiomatic`
is structurally unblindable for the same reason. `verify_blind.py` must still pass for the two
frame-seeing aspects.

## note 2026-08-24

## note — what landed, and what the next agent must not re-derive

PR #22. `aspects.py` gains 3 scene aspects and 2 fields on `Aspect`; `GAME_ASPECTS`,
`SCENE_ASPECTS` and `CROSS_STACK_BARRED` are DERIVED from them, never listed by hand.

### The guard, and where it lives

`aspects.applicability(aspect_id, task_id)` is the whole "asked only of scenes" mechanism.
It is called from **3** paths — `field.py pack`, `field.run_field`, `field_sweep.main` —
because the resource is *a judge field run against a task* and a guard beside one caller is
a guard the next caller does not have. It takes an optional `registry=` so
`aspects_selftest.py` can drive the real function with a mutated aspect set.

**Task ids resolve from the suites first, then from an id shape.** `wholegame_prompts.TASKS`
and `scene_prompts.SCENES` are the address; `^[gs]\d+_` is a fallback that exists only so
the judge fixtures' synthetic `g9_probe` field still packs — a guard that refuses every
fixture is a guard somebody removes. The fallback is **corroborated** against the suites on
all 6 real ids in `aspects_selftest`, and driven with a doctored map that must go red. An id
neither channel can classify is refused.

### The cross-stack bar, and the thing it deliberately does NOT do

`Aspect.cross_stack_bar` holds the REASON, not a flag. Set on `framework_fluency` (barred by
construction) and on `idiomatic` (barred on measurement, #53). `field_ranks.report` prints
the reason plus that aspect's per-stack means, **alphabetically by stack** — sorting them by
value would hand back the ranking the bar exists to withhold.

**It changes nothing about pooling, on purpose.** `classify()` still calls `idiomatic`
SCORED, so it is inside the pooled between-stack figure `JUDGING.md` quotes and states that
`field_ranks --per-aspect` reproduces. Removing it re-analyses published game results. That
is **`tasks/146`** — do not do it as a side effect of something else.

### The weight answer is NOT ASKED, and both halves matter

Measured with `judge/weight_sensitivity.py --selftest` (SELFTEST PASSED, 12 controls) and
`judge/weight_sensitivity.py runs/*` (groups: 10, FLIPS=0, STABLE=3, UNIDENTIFIABLE=7):

1. **0 scene gradings exist.** All 10 groups are games — 25 `g1_pong`, 19 `g2_tetris3d`,
   16 `g3_arena`, 24 `g4_platformer`. Extraction proved on a row whose answer was known in
   advance: `runs/wg-g4c-2026-08-21T02-26-46/artifacts` holds exactly 8 `g4_platformer__*`.
2. **The tool sweeps the wrong parameter.** `w1` over `(tier 1, tier 2)`; the scene question
   is `w3` over `(tier 2, tier 3)`. **`tasks/145`** needs a `w3` mode with its own
   constructed-crossover control, or a sibling tool — not a re-run of this one.

`--selftest` passing is what makes (1) a statement about the population rather than about the
instrument. Read #92 before acting on a null when one arrives.

### `fidelity` is weaker than its one-line summary and the number must say so

No pack carries a statement of the scene: the rendered prompt exists per stack, so handing a
judge one names the arm in its own evidence. The aspect therefore recovers the subject from
the field of 8. **It can find a submission that omits what 7 others drew; it cannot find one
where all 8 missed the same requirement.** **`tasks/144`** closes it.

### Blinding — 2 gates, and they are not the same question

- `verify_blind.py` is about the BUILDING agent and scans the trial tree. Green on the four
  starters copied outside the repository (81 criterion ids checked), red on a planted canary
  plus a planted `layer.clears`, green again on removal. **Run it against a copy outside the
  repo** — in place, `eval/starters/<stack>` has `eval/judge/RUBRIC.md` up its own path.
  This branch's `RUBRIC.md` edit added **0** criterion ids: 81 before, 81 after.
- `aspects_selftest.py` is about what the JUDGE is told, and it is the gate `fidelity` and
  `motion` actually have to pass. Both are frames-reading, so they fall under the existing
  checks automatically — no stack name, no arm count, `FRAMES_BLIND_SPOT` carried verbatim.

### Two things the review found that were mine, and one it was right about generally

- **`run_field` indexed `ASPECTS[aspect_id]` before its own guard.** `field.py run --aspect`
  has no `choices`, so an unknown id raised `KeyError` where every sibling refusal in that
  function is a stored `usable: False`. Fixed and pinned both ways in `blurb_selftest.py`
  check 10. **Both halves target the pack with no recorded completeness state**, so each
  stops at a guard; a positive half aimed at a healthy pack spawns the judge, which I found
  out by writing it that way first and burning a call.
- **`evaluate-run/SKILL.md` had become a second source of truth** for the aspect list. It
  points at `RUBRIC.md`/`JUDGING.md` now. Every skill here is required to; #38.
- Dates and migration history came out of `RUBRIC.md`, `JUDGING.md`, `judge/AGENTS.md` and
  `SCENES.md`. **The counts and their producer commands stayed** — `AGENTS.md` requires a
  producer beside a quantity, and the reviewer agreed on the second pass.

### CI

`field_ranks --selftest` and `weight_sensitivity --selftest` were in neither `gates.yml` nor
the excluded-gates register. Both are now steps; `ci_minutes --selftest`'s pinned count and
the register move 42 -> 44. The register's timings are re-read from this branch's runs —
gates 65s, controls 689s at `ba7ff68` — and `controls` loses its "a floor" qualifier.

### One thing to watch, and it cost a wrong `git add`

`skill_layout_control.py` plants and removes `SKILL.md` files under `.codex/` etc. while it
runs. A `git add -A` racing it **staged a plant that no longer exists on disk**. If a stray
`.codex/skills/**` row appears in `git status`, that is what it is: `git rm --cached -r` it.
Do not run it in the background beside a staging step.
