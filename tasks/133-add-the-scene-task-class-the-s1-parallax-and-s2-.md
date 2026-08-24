---
id: 133
title: 'Add the scene task class: the s1_parallax and s2_glass prompts, rendered per stack from one template each'
status: done
priority: 1
refs: 'eval/SCENES.md, eval/suites/wholegame_prompts.py, eval/tools/prompt_guard.py, .agents/skills/add-game/SKILL.md, #41'
done_when: Both scenes render for all four stacks through one template each; `prompt_guard.py` exits 0 with no engine name in a scene body and the per-stack rule sets identical; a rendered-prompt snapshot is stored; the byte-identical share across stacks is MEASURED and written down rather than asserted; and no criterion, threshold or tolerance from eval/SCENES.md appears in any prompt - checked by grepping the rendered prompts for the criterion vocabulary, not by reading them.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/19
established_by: 'PR #19 squash-merged. Verified independently: both scenes render for all four stacks; the #41 isolation holds in BOTH directions under my own perturbation (scene preamble moves 8/8 scenes and 0/16 games; game preamble moves 16/16 games and 0/8 scenes); prompt_guard_control is 25 rows as declared, 14 mutants red and 5 variants green; and 9 criterion phrases from SCENES.md appear in 0 of 24 rendered prompts, with the grep proved on tick/seed/capture hitting all 24 first.'
---

The suite has one task class: whole games, driven by a held-out play-bot. A **scene** is a timed
audiovisual sequence with no player, added to ask what games cannot — how well a stack's rendering
and animation facilities can be driven, and how well an agent drives them. `eval/SCENES.md` holds
the design, the criteria and the research questions; read it first, it is the authority and this
ticket is the bug if they disagree.

This ticket is **the prompts and the contract only**. The probe that grades them is task 134.

## What already exists, and is why this is affordable

Every starter's capture harness makes a frame a pure function of `(seed, ticks, inputs)`
(`eval/starters/*/AGENTS.md`). A scene is that contract with `inputs` dropped: render at a fixed
list of TICK indices, never wall-clock; emit one telemetry record per captured tick; identical
frames for a given seed across runs. Nothing new is needed in the starters for this — verify that
claim per stack before relying on it, because it is the whole basis of the estimate.

## The two scenes

`s1_parallax` (2D) and `s2_glass` (3D), specified in `eval/SCENES.md`. Write them the way
`wholegame_prompts.py` writes games: ONE template per scene rendered per stack through the
vocabulary dicts, not four hand-written copies. 97-98% of every existing prompt is byte-identical
across stacks and the identity is structural — keep it that way.

## The three prompt rules, all of which cost a run when broken

1. Semantically identical across stacks, natively worded. Byte-identical prompts are not
   neutral; they end up in one stack's vocabulary.
2. No type widths.
3. **The prompt is not the rubric.** State what to render and what "done" means. Do NOT name a
   criterion, a threshold or a tolerance. `eval/SCENES.md` lists what each criterion catches —
   that file is for us, and none of it may appear in a prompt. Writing "make sure the water stays
   level" because the probe checks it is teaching to the test and invalidates the comparison.

The probe CONTRACT is legitimately in the prompt: the telemetry field names, the tick list, the
seed handling. Field names are functional spec; thresholds are not.

## The trap that is specific to this ticket

`_preamble()` is shared by every task. An edit aimed at scenes reaches all four games, correctly
where aimed and invisibly everywhere else — that is #41, which contaminated the one experiment
designed around a single variable. If scenes need preamble text that games do not, it goes in a
scene-specific block, and `prompt_guard.py` must still pass.

## note 2026-08-24

## note 2026-08-24 — ambition, and the rule it must not break

The scenes should push each stack as far as it goes: ray-traced or path-traced lighting, real
refraction and caustics, GPU particle systems in the thousands, post-processing.

**Ask for the visible RESULT, never the technique.** "Use ray tracing" prescribes the
implementation and destroys the measurement that makes scenes worth having - which facility the
agent reached for. "The caustics the glass casts on the table move as it tilts" asks for something
hard to fake, leaves the method open, and turns the method into a finding that
`framework_fluency` reads.

Same for quantities. "Many small irregular pieces, each moving independently" - never a number. A
number in a prompt is a threshold, and thresholds are rubric.

`eval/SCENES.md` now has this as its own section; read it before writing either prompt.

## The performance pass is NOT yours

Frame rate is a second, real-time pass and it is deliberately out of scope here (tasks/134 for
correctness, tasks/137 for whether resources can be bounded at all). Do not add wall-clock timing
to the capture contract - the correctness pass is deterministic and tick-indexed precisely so no
wall-clock enters it.

## note 2026-08-24

## What the next agent should not re-derive

**The two prompts are in `eval/suites/scene_prompts.py`, NOT in `wholegame_prompts.py`, and
that is load-bearing twice over.** `wholegame.py` defaults `--games` to every key of
`TASKS`, so a scene registered there is launched by the standing matrix command against a
probe that does not exist. And a preamble shared across task classes is #41 with a
different subject. Both are recorded in `DECISIONS.md`; the isolation is measured, not
argued — editing the scene preamble moves 8 rendered prompts and no game, editing the game
preamble moves 16 and no scene (`prompt_guard_control.py`).

**The vocabulary dicts are IMPORTED from `wholegame_prompts`, not copied.** `SIM_HOME`,
`VIEW_HOME` and `THREE_D_NOTE` are shared; `SCENE_RENDER_NOTE`, `CAPTURE_NOTE`, `TIME_NOTE`
and `TWO_D_NOTE` are scene-local. `SCENE_RENDER_NOTE` exists because `RENDER_NOTE` says
"Draw the *game*" — editing a shared dict to suit one task class would have been the same
mistake in miniature.

## For task 134, the probe

**Everything the probe needs is already in the starters and none of it needed changing.**
Verified per stack, not assumed: `just film SEED TICKS SCRIPT OUTDIR` captures at most 12
frames at ticks `floor(i * TICKS / 11)` for `i` in `0..11`, identically in
`crates/game/src/bin/film.rs:59`, `scripts/film.ts:35`, `tools/film.gd:33` and
`Assets/Editor/Probe.cs:171`, and each starter has a `rendering is reproducible across
runs` test. So the "fixed list of tick indices" the design asks for is a pure function of
the tick count. Both scenes are **660 ticks**, which puts the 12 captured frames on
multiples of 60.

**The scene ignores input.** The prompt says every input object is empty and exists only to
advance the clock, so `probe-file` still drives it.

**Two image addresses are in the telemetry contract on purpose**, because a criterion needs
somewhere in the frame to look and rule 12 says the address is an input to the check:
`s1` reports `layers[].top`/`bottom` as fractions of frame height, and `s2` reports
`glass.screen` as fractions of frame width and height. Neither is a threshold.

**The phase schedule is reported, not fixed by the prompt.** `s2` reports `phase` as one of
`draining/tilting/falling/broken/rewinding/whole`, and `s1` emits `light_begin`/`light_end`
and `wrap`. A criterion should locate its window from telemetry and then check the image —
that is how it ESTABLISHES its condition rather than waiting to observe one. The degenerate
case a scene could reach for is a one-tick phase; the prompts describe relative pacing
("the long, slow part", "this part is quick") and state no number, so if 134 wants to rule
it out that is a criterion, not a prompt edit.

**What the prompts deliberately do NOT say, because they are the criteria:** `s1` never
says the layers scroll at rates ordered by depth; `s2` never says the water surface stays
level while the glass tilts. Do not "fix" these. `scene_prompts.py`'s docstring says so at
the top.

## The rubric gate, and the trap in extending it

`prompt_guard.py` has a third assertion now: no criterion, threshold or tolerance from
`eval/SCENES.md` in a **rendered** scene prompt. Two things to know before touching the
lists:

1. **Every `RUBRIC_TERM` must appear in `eval/SCENES.md`**, asserted at run time against a
   copy with markdown emphasis and wrapping removed. Adding a term the authority never used
   turns the guard red.
2. **Adding a criterion to `SCENES.md` does NOT automatically extend the gate.** The list is
   curated, not derived. The derived version was built first and measured: 85 content words,
   31 hits over the 24 rendered prompts, **0 real leaks**. `DECISIONS.md` carries the
   derivation. So when 134 adds criteria, add their measurement vocabulary to `RUBRIC_TERMS`
   by hand and re-run `prompt_guard_control.py`.

**A term that fires on the functional contract comes off the list.** `probe` was on it and
hit all 8 scene prompts with no true positive — `just probe SEED` is a recipe every prompt
must name.

## The snapshot is a gate now

`eval/suites/rendered/` holds all 24 rendered prompts and `gates.yml` runs
`prompt_guard.py --diff eval/suites/rendered` on every push. **Any deliberate prompt edit
must re-record it in the same commit**:
`python3 eval/tools/prompt_guard.py --snapshot eval/suites/rendered`. This is the only
mechanical defence against #41 outside a live run — the three assertions cannot see a
shared-preamble edit, because it leaves every rule identical across stacks and names no
engine.

`--diff` also refuses a snapshot directory holding a `.txt` the index does not name, which
is what re-recording over an older snapshot leaves behind when a task is removed. It names
the file and deletes nothing.

## Filed, not fixed here

- **task 141** — `INPUT_TYPE` and `STATE_HOME` in `wholegame_prompts.py` are defined and
  referenced by nothing. Surfaced by `prompt_guard.py --identity`.
- **task 142** — the game preamble demands a distinct sound per event while the audio
  section 40 lines later allows two events to share one. In all 16 rendered game prompts,
  for the life of the project.
- **task 143** — `_G3_INPUTS` says nothing about a zero aim vector while
  `ref_arena/game.py::_update_aim` silently retains the last non-zero one and fires along
  it.

142 and 143 are both edits to templates shared by all four games that 90 stored trials ran
under, so each is a comparability break needing an `eval/RUNS.md` entry. Both were found by
CodeRabbit reading the **checked-in rendered prompts**, which had never been reviewable
before.

## No finding number allocated

Nothing here ran and measured nothing, so no finding is owed. The one thing worth a number
if the orchestrator disagrees: `.agents/skills/add-game/SKILL.md` published "97-98%
byte-identical" with **no producer and no unit** for the life of the project. It reproduces
as the LINE share; the character share is 90.9%, six percentage points lower. Both now come
from `prompt_guard.py --identity`.
