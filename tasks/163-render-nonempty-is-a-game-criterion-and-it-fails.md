---
id: 163
title: render.nonempty is a GAME criterion and it fails a scene for drawing what it was asked to draw
status: in_review
priority: 2
refs: eval/judge/static.py,eval/judge/evaluate.py,eval/SCENES.md,eval/RUNS.md,tasks/156
done_when: the tier-1 ink window is decided per task class rather than once - a scene's ceiling stated with the measurement behind it, not a number picked to admit the one submission that exists - and static.collect takes it from the caller the way audio_game and film_ticks already do; a control pins both directions per class, including that a BLANK scene frame still fails; eval/runs/wg-scene-s1ts-2026-08-25 is re-graded and its gate verdict recorded either way; and eval/judge/RUBRIC.md says what the window is per class
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/42
---

static.collect scores render.nonempty on mean ink coverage inside a 0.001-0.85 window calibrated on games, which draw a subject against a background. A scene fills the frame by design. The first scene ever graded failed it at 0.966 - sky, road and scenery covering the frame - so the criterion deducted for compliance, the same shape as the stale-cache defect and as the audio criteria that task 156 already stopped asking of a scene. The floor still has work to do (a blank frame must fail); the CEILING is what does not transfer.

## note 2026-08-26

## note 2026-08-26 (orchestrator) — tier 1 is a GATE, which is what makes this urgent

`render.nonempty` is tier 1, and tier 1 is not a weighted term — it is a **gate**. So a false
negative here does not cost a fraction of a score; it can stop a correct submission being scored at
all. That is a different severity from the tier-2 scene defects (`tasks/162`, `tasks/164`) and is
why this sits above them despite the same p2.

**The scene it failed drew what it was asked to draw**, at 0.966 mean ink against a window
calibrated on games. A gate tuned on one task class refusing a correct member of another is the
shape #123 already found once, when tier 1's 7 failures in 68 trials turned out to be 5 lint
findings on a game that played perfectly.

## Calibrate on the population, and say which population

The window exists to catch a submission that renders nothing. **A scene that fills the frame is not
that**, and the fix is not to widen the window until this one passes — that is the tolerance error
`tasks/162` was told to avoid, one criterion over.

State which population each bound was calibrated on, and where a scene bound differs from a game
bound, say so **in the criterion** rather than in a comment. `aspects.applicability()` is the
existing precedent for a check that knows the task class it is being asked about.

## What NOT to do

Do not assume the only affected criterion is this one. The scene run exercised **5 tier-1 audio
criteria that are already not asked of scenes** — someone decided that correctly. Ask the same
question of every tier-1 criterion: is its bound a property of the artifact, or of games? A census
answering that for all of them is worth more than one repaired window, and is a complete answer
even if it finds this is the only one.

## note 2026-08-26

## note 2026-08-26 — the agent was KILLED by an account limit, not by the work

Terminated mid-task: *"You've hit your weekly limit · resets 6pm (America/Sao_Paulo)"*. Its last
line was **"Now verify the three new guards in both directions"**, so the guards exist and are
**unverified**. Nothing about the work had failed.

State left behind, read from the artifacts:

- **PR #42 is open**, branch `task-163-ink-window-per-task-class`.
- `controls` **SUCCESS**, `gates` **FAILURE** on one named step:
  `tokenvalue --selftest (no producer prints a money sigil)`.

That failure is diagnosable without re-running anything: a `$` next to a digit has entered a file
in `PRODUCERS`. It is the same gate that reddened `main` at the start of 2026-08-24 (#162's
origin), and the repair is the unit rather than the number — `tokval`, not `$` (`#159`).

**Do not treat the three guards as verified because CI later goes green.** Green would only mean
the sigil is gone. The guards still need both directions, and the ticket's own instruction stands:
do not widen the window until the stored scene passes.
