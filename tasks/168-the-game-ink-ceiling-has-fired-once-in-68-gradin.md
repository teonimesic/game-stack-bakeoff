---
id: 168
title: the GAME ink ceiling has fired once in 68 gradings and it was a false negative too
status: todo
priority: 3
refs: eval/judge/static.py,eval/judge/ink_window_control.py,eval/judge/RUBRIC.md,eval/RUNS.md,tasks/163
done_when: the game half of INK_WINDOW is decided on the same standard tasks/163 applied to the scene half - either a ceiling with a derivation and a population, or no ceiling - and if it moves, wg-g4c g4_platformer__godot__t1 is re-graded, the regime move is recorded in eval/RUNS.md, and every live document quoting the 0.881 figure or the 7-of-68 tier-1 census breakdown is repaired
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
