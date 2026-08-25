---
id: 163
title: render.nonempty is a GAME criterion and it fails a scene for drawing what it was asked to draw
status: todo
priority: 2
refs: eval/judge/static.py,eval/judge/evaluate.py,eval/SCENES.md,eval/RUNS.md,tasks/156
done_when: the tier-1 ink window is decided per task class rather than once - a scene's ceiling stated with the measurement behind it, not a number picked to admit the one submission that exists - and static.collect takes it from the caller the way audio_game and film_ticks already do; a control pins both directions per class, including that a BLANK scene frame still fails; eval/runs/wg-scene-s1ts-2026-08-25 is re-graded and its gate verdict recorded either way; and eval/judge/RUBRIC.md says what the window is per class
---

static.collect scores render.nonempty on mean ink coverage inside a 0.001-0.85 window calibrated on games, which draw a subject against a background. A scene fills the frame by design. The first scene ever graded failed it at 0.966 - sky, road and scenery covering the frame - so the criterion deducted for compliance, the same shape as the stale-cache defect and as the audio criteria that task 156 already stopped asking of a scene. The floor still has work to do (a blank frame must fail); the CEILING is what does not transfer.
