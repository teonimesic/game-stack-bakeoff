---
id: 144
title: Pack a stack-neutral statement of each scene, so fidelity can ask the question it is named for
status: in_review
priority: 3
refs: eval/SCENES.md, eval/judge/RUBRIC.md, eval/judge/aspects.py, eval/judge/field.py, eval/judge/verify_blind.py, tasks/135
done_when: 'A stack-neutral statement of each scene exists, is written into the pack by field.build_pack for scene fields only, and carries no arm-naming token: verify_blind.py --packs over a built scene pack is green, and a planted stack token in the statement turns it red. blurb_selftest.judge_facing_texts() covers it, because it is judge-facing text making a claim. fidelity''s notes stop telling the judge to recover the subject from the field. The ''cannot find what all eight missed'' caveat is removed from SCENES.md and RUBRIC.md in the same change.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/34
---

fidelity asks 'does this read as the scene it was asked for'. The pack carries no statement of the scene: the rendered prompt exists per stack (eval/suites/rendered/s1_parallax__ts.txt and its three siblings), so handing a judge one names the arm in its own evidence - the leak blind_extensions and neutralise exist to close. Until a neutral statement is packed, the aspect recovers the subject from the field of eight and can find a submission that omits what seven others drew, but CANNOT find one where all eight missed the same requirement. That narrowing is recorded in eval/SCENES.md, eval/judge/RUBRIC.md and the aspect's own comment; this ticket removes it.

## note 2026-08-25

## note 2026-08-25 — the tier-3 layer is merged, so this is the gap it shipped with

Tasks 133, 134 and 135 are all on `main`: scene prompts, the 15-criterion probe, and the three
tier-3 aspects. `fidelity` exists and is asked only of scenes. **This ticket is the thing it cannot
do yet**, stated in three places at merge: no pack carries a statement of the scene, and the
rendered prompt is **per stack**, so handing a judge one names the arm.

The consequence is precise and worth keeping precise: `fidelity` can currently find a submission
that omitted what 7 others drew. It **cannot** find one where all 8 missed the same requirement —
which is exactly the case a fidelity judge exists for.

## The constraint that makes this hard

A stack-neutral statement is not the prompt with the engine nouns removed. The prompts differ by
2.7% of lines across stacks, and the differences are *"where things go"* and *"how to make sound"*
— so a naive strip leaves a text that still reads as one stack's. **`verify_blind.py` is the gate**
and it must still pass; `eval/judge/anonymise.py` is the existing machinery for this class.

**Write the statement from `eval/SCENES.md`, not from a rendered prompt.** The design document
describes both scenes in stack-free terms already, and it is the source the prompts were written
from — going back to it is cheaper than laundering an output of it, and it cannot leak a vocabulary
dict by construction.

## What NOT to do

Do not put anything from the criteria into the pack. `SCENES.md` states what each criterion catches
and none of that may reach a judge — the same rule that governs prompts. Task 133 checked this by
grepping the rendered prompts for criterion vocabulary; do the same for the pack, and say what you
grepped for.
