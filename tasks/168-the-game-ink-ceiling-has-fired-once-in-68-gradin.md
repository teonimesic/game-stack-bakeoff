---
id: 168
title: the GAME ink ceiling has fired once in 68 gradings and it was a false negative too
status: in_testing
priority: 3
refs: eval/judge/static.py,eval/judge/ink_window_control.py,eval/judge/RUBRIC.md,eval/RUNS.md,tasks/163
done_when: the game half of INK_WINDOW is decided on the same standard tasks/163 applied to the scene half - either a ceiling with a derivation and a population, or no ceiling - and if it moves, wg-g4c g4_platformer__godot__t1 is re-graded, the regime move is recorded in eval/RUNS.md, and every live document quoting the 0.881 figure or the 7-of-68 tier-1 census breakdown is repaired
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/48
established_by: 5 review rounds; ink_window_control.py 51/51 offline and with --runs-root; the pre-change ceiling restored turns exactly 3 of 38 rows red at exit 1, all 3 rows the change is about; gates/controls/CodeRabbit all green at d389efe
---

tasks/163 made render.nonempty's ink window per task class and gave a scene the floor with no ceiling. It deliberately left the GAME ceiling at 0.85, because moving it flips a stored game gate verdict and the figure three live documents quote - a re-scoring event on the game population. But the measurement it left behind says the game ceiling is the same defect. python3 eval/judge/ink_window_control.py --runs-root <main>/eval/runs, over 85 gradings / 69 submissions: the ceiling has fired TWICE and neither firing was a defect. One is the scene, repaired. The other is wg-g4c g4_platformer__godot__t1 at mean ink 0.881 - a night platformer drawn over a gradient sky, whose only tier-1 failure is this one and which scored 1.000 on tier 2 (RUBRIC.md already records it as one of the five non-blocking failures). Read the frame: eval/runs/wg-g4c-2026-08-21T02-26-46/artifacts/g4_platformer__godot__t1/eval/frames/frame_0005.png. The mechanism is that ink_coverage counts pixels differing from the single most-common quantised colour, so a GRADIENT SKY has no modal region and reads as ~1.0 whatever is drawn on it - which is a property of the palette, not of the render. The floor, meanwhile, has fired twice and both times on trials with ZERO frames, where render.frames reports the same fact in the same record. So over the whole game corpus render.nonempty has never separated anything render.frames did not, and its only independent firing was wrong. Decide it on evidence, not by widening: state the ceiling's population and its derivation, or remove it and say what the floor is then carrying.

## note 2026-08-27

## note 2026-08-27 (orchestrator) — 163 has MERGED, and two of its results change what you inherit

Branch from a `main` that already contains `tasks/163`. Three things it left you:

1. **`static.TIER1_BOUND_POPULATION`** now maps every tier-1 criterion to the population its bound
   was calibrated on, over a closed 5-value list, gated by `static.assert_tier1_bounds_declared()`.
   `render.nonempty` is the single `task_class` entry. If you remove the game ceiling, that map is
   part of what you are changing, not a file to update afterwards.
2. **`ink_window_control.py` reports classification provenance now**, and the number is worth
   knowing before you quote any per-class census from it: `task_class` is **read** from the record
   on **1** of 69 stored submissions and **inferred** by `_class_of` from the id shape on **68**.
   Your whole game population is inferred. That does not make it wrong - the id shape is a real
   second channel - but a claim about 'the game corpus' rests on `_class_of` being right, so say so
   rather than letting the census imply the classes were read.
3. **163 declined to move this ceiling and said why**, in `DECISIONS.md`: moving it flips a stored
   gate verdict and the figure three live documents quote. That is a cost, not an objection - your
   ticket exists because the same measurement says the ceiling is the same defect. Decide it on the
   evidence.

**Contended files, as of now.** `eval/RUNS.md` and `DECISIONS.md` are both touched by two pull
requests waiting to merge (`tasks/161` and `tasks/164`). Expect to rebase, and expect the conflict
to be additive - keep both sides. `eval/runs/` is **read-only** for you: re-grade
`wg-g4c g4_platformer__godot__t1` and record the verdict in the ticket and `eval/RUNS.md`, but do
not store a new judge round there.

**The trap, stated plainly because 163 met it one criterion over:** the wrong repair is to widen the
ceiling until the platformer passes. Its own ticket says it - either a ceiling with a derivation and
a named population, or no ceiling. `tasks/164` is the worked example of doing this right: its new
constants are derived from whole-pixel rounding, and its source states they sit 60x below what the
failing subject would have needed, so the subject that exposed the defect still fails.

## note 2026-08-27

## What was decided, and the derivation that decided it

**No ceiling, for any task class.** `render.nonempty` is a **floor of 0.001** plus a refusal of
**a frame set in which every frame is a single colour**. Both halves are properties every starter
shares, so `TIER1_BOUND_POPULATION["render.nonempty"]` moved `task_class` -> `starter`,
`TASK_CLASS_BOUND_TABLES` is `{}`, and 0 tier-1 bounds are class-dependent.

**The ceiling was not decided on the corpus.** It was decided on what `mean_ink` measures.
`ink_coverage` counts pixels differing from **one** reference colour and `analyse_frames` takes
that colour from **frame 0's** mode - so the quantity is departure from the first frame's mode, a
property of the palette. A solid flood reads **0.0** and lands on the floor; what reads near 1.0
is a gradient.

**The measurement that settles it, and the review found it.** 12 frames each holding one colour
have drawn nothing, and `mean_ink` depends only on how the colours are ARRANGED:

| 12 uniform frames | mean_ink | floor-only | old 0.001-0.85 |
|---|---|---|---|
| all one colour | 0.0 | FAIL | FAIL |
| frame 0, then 11 of another | 0.91667 | PASS | FAIL |
| alternating 2 colours | 0.5 | PASS | **PASS** |
| 6 of one, then 6 of another | 0.5 | PASS | **PASS** |

`0.001-0.85` admitted **2 of the 3** non-zero arrangements. So the ceiling was never the guard
against a blank render - it closed 1 of 3 and looked like one. `png.Image.is_flat` reads each
frame against **its own** mode, `analyse_frames` counts them as `flat_frames`, and all 4 rows now
FAIL. **0 of the 67 stored frame sets contain a flat frame**, worst per-set cost 0.46 s.

## Numbers the next agent should not re-derive

- Corpus: 85 gradings / 69 submissions. 4 `render.nonempty` failures. The 2 **floor** firings are
  true positives (`wg-arena3d` rust cells, 0 frames). Among the 2 **ceiling** firings: **0 true
  positives, 2 false negatives**. `task_class` is READ on 1 of 69 and INFERRED on 68.
- Game `mean_ink`, 6 highest: 0.67885, 0.70252, 0.73621, 0.77226, 0.82777, 0.88137 - **all
  `g4_platformer`**. Largest gap among those 6 is **0.0555**. **0.85 fell in a gap of 0.0536**,
  between 2 trials of the same game. The 7th value down is `g3_arena__rust__t0` at **0.60285**,
  0.076 below the 6th.
- **The first draft of that sentence said 0.053 and "the 7 highest", and both were wrong.** Review
  round 2 caught the first; re-deriving it from the stored records rather than re-reading the
  prose found the second. Rule 5, and it fired against the author.
- Re-grade: `wg-g4c g4_platformer__godot__t1` gate `FAIL 1/14` -> **`PASS 14/14`**, tier 2 1.000
  unchanged. It is an **offline** re-grade; the stored record still holds the FAIL and nothing
  under `eval/runs/**` was rewritten.
- Tier-1 census today: **8 failing submissions in 69**, 2 blocking / 6 non-blocking.
  `weight_sensitivity --all`: **8 of 11** groups single-valued. The `7 of 68` / `7 failing trials`
  breakdown in `README.md` and root `AGENTS.md` was already stale before this ticket - the scene
  had joined the population - and is repaired against the producers.

## Traps met, so they are not met again

- **`flat_frames` absent is a third value.** Every stored record predates it, so a re-grade asks
  the floor alone and its evidence says so. Anything reading a missing count as 0 re-opens the
  hole for the stored corpus.
- **`mean_ink` was deliberately NOT changed to a per-frame background.** Doing so moves 8 of the
  67 stored sets - `g3_arena__rust__t0` 0.60285 -> 0.04481, `g3_arena__ts__t0` 0.51997 -> 0.03886,
  `g4_platformer__godot__t1` 0.88137 -> 0.67869, `g4_platformer__godot__t0` 0.67885 -> 0.78194,
  `s1_parallax__ts__t0` 0.96561 -> 0.85042. That is **`tasks/178`**, filed with all of it.
- **`blank` and `flood` can no longer test the floor**, because they fail on both halves. The
  floor's subject is the new `whisper` fixture at 0.00025. A mutant aimed at the floor and checked
  against `blank` would pass for the other reason (#37).
- **Two different wrong-class failures, two different catchers.** `static.assert_task_class`
  refuses an **unregistered** class before a toolchain is spent; a **registered but wrong** one -
  a scene routed as a game - is caught by `eval/tools/scene_runner_control.py`. An earlier draft
  called the first "the only place a wrong class can be caught", which is false.

## Handed over

- **A finding number is needed** and was not allocated. The claim: *the ink ceiling ran 68 game
  gradings, separated nothing `render.frames` did not, its only independent firing was a false
  negative, and it caught 1 of 3 arrangements of a render that drew nothing - so it was not the
  guard it looked like.*
- **The regime ordinal `TWENTY-FOURTH`** was hand-allocated while 2 pull requests were in flight
  against `eval/RUNS.md`. `docstat.py --sweep`'s regime-ordinal check goes red on a collision.
  Every cross-reference cites the heading *`render.nonempty` lost its ink ceiling*, not the number.
- **2 review comments declined**, each answered in its thread: the `scene_runner_control` mutant
  rows (they already assert the negation of the row they guard, written out independently), and
  the *"check the ordinal before citing it"* sentence (it stands verbatim on the twenty-third
  break, and ordinals here have collided).

## note 2026-08-27

## The review, and what it changed (5 rounds, 27 comments)

**25 acted on, 2 declined.** Both declines are answered in their threads with evidence.

**Round 1 changed the result, not just the prose.** It asked whether removing the ceiling opens a
fail-open path, because `analyse_frames` takes its reference colour from frame 0 and applies it to
every frame. It does — and measuring it showed the ceiling had **never closed that path**, which
is now the strongest part of the derivation and is `BLANK_RENDERS` in the control. The repair
(`png.Image.is_flat` + `flat_frames`) closes all 4 arrangements, where the ceiling closed 1 of 3.

**Round 2 found a published number wrong.** `0.053` where the data says `0.0555` — and
re-deriving that sentence from the stored records rather than re-reading the prose found a second
error beside it, *"the 7 highest are all `g4_platformer`"*, when it is the top **6**. **Rule 5
fired against the author here**: both figures were carried forward from a scratch reading rather
than re-read from the producer at the moment of writing.

**Rounds 3-5 were documentation**, all accepted: bound the historical claim at `tasks/163` rather
than running it to the present; keep the corpus history in `eval/RUNS.md` and out of
`eval/judge/AGENTS.md`; say *"a frame set in which every frame is a single colour"*; repository-
root paths for every producer command in a live document; and state the re-open condition in
`flat_frames`' own **whole-frame** unit rather than the region-level one the code does not measure.

**The 2 declines.**

1. `scene_runner_control.py`'s mutant rows. The row asserts `task_class == "game"`, which is the
   negation of the check it guards (`== "scene"`) written out as an independent literal — exactly
   what rule 12's corollary asks for, and deriving it from the check would reproduce `tasks/113`.
   The alternative suggested is not implementable: `"game"` is a **valid** class no guard rejects.
2. *"Check the ordinal before citing it."* It stands verbatim on the twenty-third break, regime
   ordinals are one of the 4 hand-allocated namespaces here and every one has collided, and
   `docstat.py --sweep` carries a regime-ordinal check for that reason.

**`Reviews paused` fired at the round-5 head**, which is CodeRabbit's response to a branch under
active development. It is a notice, not a failed round: round 5 landed as `LANDED_REVIEW` before
it appeared.
