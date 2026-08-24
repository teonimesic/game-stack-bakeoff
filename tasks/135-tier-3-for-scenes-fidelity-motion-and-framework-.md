---
id: 135
title: 'Tier 3 for scenes: fidelity, motion and framework_fluency, with the unblindable one marked as such'
status: in_review
priority: 2
refs: 'eval/SCENES.md, eval/judge/RUBRIC.md, eval/judge/aspects.py, eval/judge/verify_blind.py, eval/judge/weight_sensitivity.py, tasks/134, #21, #92'
done_when: The three aspects exist and are asked only of scenes; verify_blind.py passes for fidelity and motion; framework_fluency is marked unblindable in RUBRIC.md and in every place its number is published, and is reported per stack rather than ranked across stacks; the scene tier 3 ships at weight 0.00 with weight_sensitivity.py run over the open interval and its result recorded. BLOCKED BEHIND 134.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/22
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
