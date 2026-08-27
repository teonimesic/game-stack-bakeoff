---
id: 178
title: mean_ink measures every frame against frame 0 background and 8 of 67 stored sets move if it does not
status: done
priority: 3
refs: eval/judge/static.py,eval/judge/png.py,eval/judge/ink_window_control.py,tasks/168
done_when: either analyse_frames keeps frame 0 background with a stated derivation for why that is the right reference, or it moves to a per-frame background with the 8 moved stored values recorded in eval/RUNS.md as a regime move and the ink figures every live document quotes repaired; ink_window_control.py pins whichever is chosen in both directions, and the choice is recorded in DECISIONS.md
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/55
established_by: 'Merged as PR #55. Two measurements decided it, both taken on the pre-change code BEFORE it was changed. (1) The fail-open: 12 frames where frame 0 is uniform black and the other 11 are uniform white carrying one 2x2 speck - 4 pixels of 256000 drawn - read mean_ink 0.91665 and PASSED render.nonempty, and BOTH halves of the criterion admitted it, because a frame with a speck is not flat so flat_frames could not see it either. Under each frame''s own background it reads 0.00001 and FAILS. (2) 14 of 804 stored frames read exactly 1.00000 under frame 0''s mode, in 3 sets, while drawing the same 4 percent they had drawn all along - g3_arena__rust__t0 flashes its arena red at frame 5 - and 0 of 804 under a per-frame reference. THE TICKET''S OBJECTION DISSOLVED RATHER THAN BEING WORKED AROUND: I worried a per-frame mode moves when a subject grows past half the frame, and that is equally true of frame 0''s mode - same computation, one arbitrary frame - so the fixed reference does not avoid the error, it freezes one frame''s version and applies it to 11 frames it was never measured on. The ticket''s figures were also wrong and the agent re-derived them from the producer: 10 of 67 sets move, not 8, the two omitted being g3_arena__godot__t0 and g3_arena__unity__t0. 0 verdicts move; the lowest value under either reference is 0.00811, 8x the floor. Verified by the orchestrator on the branch: ink_window_control exits 0 at 56/56 (was 51), the colour-drift row states in advance that the case read 0.91665 and PASSED under frame 0, and the mutant restoring the frame-0 reference is caught. Two pieces of good practice worth copying: the now-redundant all-flat half was KEPT rather than deleted - it is fail-closed and still reports how many frames were blank - with its dead mutant replaced by an implication row rather than dropped quietly; and review caught a defect of the agent''s own making, reference_shift() reading an ABSENT mean_ink as agreement, fixed and controlled both ways. This is a regime break (eval/RUNS.md, twenty-fifth) rather than a withdrawal, because the stored mean_ink values remain true of their records. WR-ink-arrangement-0-91667 retires the 0.91667 figure, which was never a property of any render. Findings #196.'
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

## note 2026-08-27

## The decision: a per-frame background, and what decided it

**`static.analyse_frames` takes a background per frame**, so `mean_ink` is the fraction of a frame
that is not its own background. `eval/RUNS.md` carries the twenty-fifth comparability break;
`DECISIONS.md` carries the decision.

**2 measurements decided it, both taken on the pre-change code BEFORE it was changed.** Neither is
in the ticket, and neither should be re-derived:

| | against frame 0's mode | against each frame's own |
|---|---|---|
| 12 frames, frame 0 uniform black, the other 11 uniform white carrying one 2x2 speck - 4 pixels of 256000 drawn | `mean_ink` **0.91665**, `flat_frames` 1 of 12, `render.nonempty` **PASS** | **0.00001**, **FAIL** |
| stored frames reading *exactly* 1.00000 | **14 of 804**, in 3 sets; their own modes give 0.04336, 0.03777, 0.44721 | **0 of 804** |

The first is fail-open and **both halves of the criterion admitted it** - a frame with a speck is
not flat, so `flat_frames` cannot see it either. The second is rule 12's signature: a census
returning one saturated value across the population it exists to discriminate is reporting the
instrument. `g3_arena__rust__t0` flashes its arena red at frame 5 and its last 7 frames all read
1.00000 while drawing the same 0.043 of a frame they had drawn all along.

**The ticket's objection dissolves.** *"A per-frame mode makes the reference move when a subject
grows past half the frame"* is true of frame 0's mode too - it is the same computation on one
arbitrary frame. The fixed reference does not avoid the error; it freezes one frame's version of it
and applies it to 11 frames it was never measured on. What it buys is stability across a set, and
nothing consumes `per_frame_ink` as a time series: change between frames is `render.animates`, via
`differs_from`.

## Numbers the next agent should not re-derive

- **10 of 67 stored sets move, not the 8 the ticket carried.** The 2 the ticket did not list are
  `g3_arena__godot__t0` (+0.00345) and `g3_arena__unity__t0` (+0.00222). Full table in
  `eval/RUNS.md`.
- **0 verdicts move.** Lowest value under either reference is **0.00811**, 8x the floor. No stored
  record, verdict, gate verdict or tier-2 score changes; nothing under `eval/runs/**` was written.
- **Population:** 85 gradings / 69 submissions / **67** with readable frames on disk. The 2 without
  are `wg-arena3d`'s rust cells at 0 frames.
- **Corpus shape, per class, never pooled.** Game sets with frames: **66**. Under frame 0 the 6
  highest were `g4_platformer` and the 7th/8th were `g3_arena` at 0.60285 / 0.51997 - both the
  saturation above. Under the per-frame reference the **7 highest are all `g4_platformer`** and the
  8th is `g2_tetris3d__ts__t1` at 0.40621. The retired 0.85 would refuse 1 of the 67 rather than 2,
  and it is the scene at 0.85042.
- **`--reference-shift` is the producer** and it takes ~120 s: `python3
  eval/judge/ink_window_control.py --runs-root <main>/eval/runs --reference-shift`.

## Traps met, so they are not met again

- **The all-flat half is now REDUNDANT, not independent, and it is kept.** `png.Image.is_flat` is
  `ink_coverage(own mode) == 0.0`, which is the floor's own per-frame term, so all-flat implies
  `mean_ink` 0.0 implies below the floor. There is therefore **no input on which `flat_frames` can
  fire alone**, and the old mutant *'no frame is ever flat'* - which expected 3 of 4 blank renders
  to survive - no longer bites. It was replaced by an implication row, not deleted quietly. Do not
  read the redundancy as a reason to remove the half: it is the fail-closed direction, and
  `flat_frames` still reports HOW MANY frames were blank, which a mean cannot.
- **`frames.background` became `frames.backgrounds`**, a list, one per frame. A reference that
  moves cannot be recorded in a scalar. Nothing read the old field (one write, no reads).
- **A stored `mean_ink` is a frame-0 reading.** Re-grading a stored record is not a re-measurement
  of it. Both `corpus()` and the RUNS.md sections say so now.
- **`0.91667` is retired** as `WR-ink-arrangement-0-91667` - the one figure here that was never a
  property of any render, only of the reference. The stored `mean_ink` values are **not** withdrawn:
  they remain true of the records that hold them, which is why this is a regime break rather than a
  withdrawal. That distinction is worth keeping - the register's `--withdrawn` gate named exactly
  the 3 live blocks restating 0.91667 and all 3 were repaired from it.
- **`reference_shift()` shipped fail-open for one round.** `stored is not None and stored != f0`
  read *absent* as *agreement*, so a record with no `mean_ink` skipped the extraction proof and
  entered the shift table. Caught by review, fixed, and controlled in both directions on a
  synthetic runs tree. 0 of the 67 stored records are in that state, so no published figure moved.

## The control, both directions

`python3 eval/judge/ink_window_control.py` - **56 expectations**, up from 51. New: the
`COLOUR_DRIFT` variant; a mutant restoring the frame-0 reference inside `analyse_frames` (the real
body, not a stub returning a number), caught by that row; `BLANK_RENDERS`' advance values
re-derived - all 4 read 0.0, and the fourth column is now what each reads under the retired
reference, **measured** by `_frame0_inks` every run rather than copied; and a `the two halves`
phase asserting `is_flat` agrees with `mean_ink`'s per-frame term on every fixture and arrangement,
and that each half refuses all 4 blank renders alone.

**The other direction, from outside the file:** restoring the pre-change `analyse_frames` for the
whole run turns **7 of 56 rows red at exit 1** - the 3 non-zero blank arrangements, the
arrangement-identity row, the colour-drift row, the `is_flat` agreement row and the floor-suffices
row.

## Handed over

**A finding number is needed** and was not allocated. The claim: *`mean_ink` was measured against
frame 0's modal colour and applied to 11 frames it was never measured on. That made 14 of 804
stored frames read exactly 1.00000 while drawing 4% of a frame, and it passed a render that drew 4
pixels of 256000 at `mean_ink` 0.91665 with `flat_frames` unable to see it. Measuring each frame
against its own mode moves 10 of 67 stored sets and 0 verdicts.*

**The regime ordinal TWENTY-FIFTH** was hand-allocated; `docstat.py --sweep` goes red on a
collision and was green. Every cross-reference cites the heading *`mean_ink` moved to a per-frame
background*, not the number.

**3 review rounds, 4 comments, all acted on, 0 declined.** Round 3 came back `LANDED_COMMENT` -
nothing left to say. CI: `gates` pass, `controls` pass, CodeRabbit pass.
