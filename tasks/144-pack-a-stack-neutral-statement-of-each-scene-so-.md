---
id: 144
title: Pack a stack-neutral statement of each scene, so fidelity can ask the question it is named for
status: todo
priority: 3
refs: eval/SCENES.md, eval/judge/RUBRIC.md, eval/judge/aspects.py, eval/judge/field.py, eval/judge/verify_blind.py, tasks/135
done_when: 'A stack-neutral statement of each scene exists, is written into the pack by field.build_pack for scene fields only, and carries no arm-naming token: verify_blind.py --packs over a built scene pack is green, and a planted stack token in the statement turns it red. blurb_selftest.judge_facing_texts() covers it, because it is judge-facing text making a claim. fidelity''s notes stop telling the judge to recover the subject from the field. The ''cannot find what all eight missed'' caveat is removed from SCENES.md and RUBRIC.md in the same change.'
---

fidelity asks 'does this read as the scene it was asked for'. The pack carries no statement of the scene: the rendered prompt exists per stack (eval/suites/rendered/s1_parallax__ts.txt and its three siblings), so handing a judge one names the arm in its own evidence - the leak blind_extensions and neutralise exist to close. Until a neutral statement is packed, the aspect recovers the subject from the field of eight and can find a submission that omits what seven others drew, but CANNOT find one where all eight missed the same requirement. That narrowing is recorded in eval/SCENES.md, eval/judge/RUBRIC.md and the aspect's own comment; this ticket removes it.
