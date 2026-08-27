---
id: 178
title: mean_ink measures every frame against frame 0 background and 8 of 67 stored sets move if it does not
status: in_review
priority: 3
refs: eval/judge/static.py,eval/judge/png.py,eval/judge/ink_window_control.py,tasks/168
done_when: either analyse_frames keeps frame 0 background with a stated derivation for why that is the right reference, or it moves to a per-frame background with the 8 moved stored values recorded in eval/RUNS.md as a regime move and the ink figures every live document quotes repaired; ink_window_control.py pins whichever is chosen in both directions, and the choice is recorded in DECISIONS.md
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/55
---

static.analyse_frames takes bg = imgs[0].dominant_background() and applies it to all 12 frames, so mean_ink is departure from the FIRST frame mode rather than from each frame own. Raised by review on tasks/168. Consequences measured there: a frame that is uniform in any colour other than frame 0 reads 1.0 rather than 0.0, which is why 12 blank frames read 0.0, 0.5 or 0.91667 depending only on how the colours are arranged. tasks/168 closed the grading hole with a separate per-frame flat_frames count and deliberately did NOT touch mean_ink, because recomputing it against each frame own background moves 8 of the 67 stored frame sets - g3_arena__rust__t0 0.60285 to 0.04481, g3_arena__ts__t0 0.51997 to 0.03886, g4_platformer__godot__t1 0.88137 to 0.67869, g4_platformer__godot__t0 0.67885 to 0.78194, s1_parallax__ts__t0 0.96561 to 0.85042 - which is a re-measurement of the corpus. The open question is which background is the right one, and it is a real question in both directions: a per-frame mode makes a uniform frame read 0.0 whatever its colour, and also makes the reference move when a subject grows past half the frame. Neither reading is derived anywhere today.

## note 2026-08-27

## note 2026-08-27 (orchestrator) — 168 has MERGED and it changed the criterion around your question

`tasks/168` landed as #191: the ink CEILING is gone for every task class, because `mean_ink` is
departure from **frame 0's modal colour** and so cannot bound 'was anything drawn' at all.
`render.nonempty` is now a floor of 0.001 plus a refusal of a frame set in which every frame is a
single colour, via `png.Image.is_flat` and a `flat_frames` count.

**That makes your question sharper, not moot.** 168 established what `mean_ink` is; you are asking
whether its REFERENCE - frame 0 rather than each frame's own mode - is the right one, and your
ticket already measured that recomputing per frame moves **8 of 67** stored sets, with
`g3_arena__rust__t0` going 0.60285 -> 0.04481. Both facts now live in the same criterion.

Three things to carry:

- **`flat_frames` absent is a THIRD value**, not zero, for records written before 2026-08-27. Do not
  let a repair collapse that.
- **The retired 0.85 ceiling is kept as a per-row comparison** in `ink_window_control.py`, each
  fixture stating in advance whether it would have caught or admitted that row. If your change moves
  any fixture's `mean_ink`, those advance statements move too and must be re-derived rather than
  re-recorded.
- **`eval/runs/` is read-only.** Re-grade offline; store nothing there.

A null closes this: if frame 0 turns out to be the right reference, say what makes it right and what
the 8 moved values mean under that answer.
