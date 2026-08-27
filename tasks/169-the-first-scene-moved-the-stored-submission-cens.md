---
id: 169
title: the first scene moved the stored-submission census from 68 to 69 and four live documents still say 68
status: in_testing
priority: 3
refs: README.md,DECISIONS.md,eval/AGENTS.md,eval/judge/RUBRIC.md,eval/judge/tier1_census.py,eval/judge/tier2_census.py,tasks/163
done_when: every live document stating a tier-1 or tier-2 census figure either matches its producer's output today, or says in the same block which population and date it is reporting - and the distinction between the two is deliberate rather than whichever the author happened to leave. Both producers re-run unpiped with --runs-root <main>/eval/runs and their output pasted into the ticket.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/51
established_by: 'PR #51 at 10bf4e6. Both producers re-run unpiped against <main>/eval/runs before and after merging origin/main at 0d270fb, with their output in the ticket note: tier1_census 69 submissions / 8 failing / 11 groups / FLOOR-ONLY, tier2_census 69 trials / 5 of 11 saturated / SATURATED, unchanged by the merge. All 3 producers pass --selftest. gates.yml green; docstat --sweep, --findings, --withdrawn, linkcheck, tasks.py check all exit 0 against the staged index. 5 review rounds, 10 of 11 findings acted on, 1 declined and then withdrawn by the reviewer.'
---

wg-scene-s1ts-2026-08-25 added the 69th stored submission, and every census figure derived from the corpus moved by one. python3 eval/judge/tier1_census.py --runs-root <main>/eval/runs today prints 69 stored submissions, 85 gradings, 16 superseded, 8 failing trials, 11 groups, 0 both-vary, FLOOR-ONLY, and 0 reversed / 3 coarsened / 8 identical. tasks/163 repaired the two figures in eval/judge/RUBRIC.md that are explicitly headed 'what it reports today' plus its 5-of-5 corroboration row, because they sat directly above the section it was rewriting and leaving a knowingly-false 'today' figure is worse than a stale one elsewhere. It did NOT chase the rest, because most of them are decision-time evidence and repairing them blind would erase the population a decision was made on. Known restatements, read 2026-08-26: README.md:222 ('68 stored submissions ... 7 of 10 groups'); DECISIONS.md:160 (the tier-1 gate evidence bullet), :174 ('14 of 68 would move'), :203/:206/:228 (tier-2 census, 35 of 68), :982/:988 (the Open section's rubric-ceiling paragraph, 61 of 68 and 35 of 68), :1233, :2947 ('62 of 68'); eval/AGENTS.md:30 ('68 submissions before and after, over 84 gradings'); eval/RUNS.md:390; eval/judge/RUBRIC.md:144/:213/:215. Note that 84 is also now 85. The rule this is under is AGENTS.md's: a count with a producer goes stale for an hour, a count with none goes stale forever - these all have producers, so the work is deciding per figure whether it is a live count or a dated one, and saying which.

## note 2026-08-27

## note 2026-08-27 (orchestrator) — the numbers you must reconcile MOVED today; re-run before reading anything

This ticket was filed when the census was 68 games + 1 scene. Three tickets have merged since and
two of them change what the producers say. **Do not start from any figure in this ticket body or in
any document — run both producers first and work from that.**

What landed:

- **`tasks/163`** made `render.nonempty`'s bound per task class, and added
  `static.TIER1_BOUND_POPULATION`, a closed map from every tier-1 criterion to the population its
  bound was calibrated on.
- **`tasks/168`** then removed the ink CEILING for every class, because `mean_ink` is departure
  from frame 0's modal colour and so cannot bound 'was anything drawn' at all (#191).
  **`wg-g4c g4_platformer__godot__t1` re-grades from `gate: FAIL 1/14` to `PASS 14/14`.** Any
  document stating the tier-1 failure count, or the '7 failures in 68 trials' breakdown, or the
  five non-blocking failures, is now stating a figure from a retired rule.
- **`tasks/164`** moved `layers.image_parallax` on the stored scene to `scored=False`, taking that
  trial's tier 2 from `6 of 7 = 0.857` to `6 of 6 = 1.000`.

**So this ticket is larger than 'four documents say 68'** — the population count moved by one and
several of the VERDICTS inside it moved too. Its `done_when` already asks the right question, and
it is the important half: for each figure, is it a live count that must match its producer today, or
a historical reading that must name its population and date? **Decide that per figure and say so,
rather than making them all current or all dated.**

**`eval/runs/` is read-only for you.** Re-grade offline and record; store nothing there.

One thing worth knowing before you quote a per-class figure: `ink_window_control.py` reports that
`task_class` is **read** from the record on 1 of 69 stored submissions and **inferred** by
`_class_of` from the id shape on the other 68. The classes are almost entirely inferred. That is
not wrong - the id shape is a real second channel - but a sentence about 'the game corpus' rests on
`_class_of`, and should say so rather than implying the classes were read.

## note 2026-08-27

## What landed — 2026-08-27

PR #51, branch `task-169-census-figures-current-or-dated`, merged `origin/main` at `0d270fb`.
`DECISIONS.md` is the authority for the rule; the per-document figures are in the documents.

### Both producers, re-run unpiped against the main checkout's `eval/runs`

`python3 eval/judge/tier1_census.py --runs-root <main>/eval/runs`

    69 stored submissions carry tier-1 criteria (85 gradings on disk, 16 superseded and held out,
    0 report paths skipped as agent-authored)
    per criterion failures: verify.green 7, lint.clean 5, tests.green 5, render.nonempty 4,
      audio.{distinct,files_exist,manifest,music_loops,not_silent} 2 each on 43,
      build.compiles 2, probe.responds 2, render.animates 2, render.frames 2, tests.exist 2
    0 of 14 criteria have never failed
    every failing trial (n=8):
      wg-arena3d  g3_arena__rust__t0        t1=0.0    t2=0.0  [BLOCKING]
      wg-arena3d  g3_arena__rust__t1        t1=0.0    t2=0.0  [BLOCKING]
      wg-arena3d  g3_arena__ts__t0          t1=0.857  t2=1.0
      wg-arena3d  g3_arena__ts__t1          t1=0.857  t2=1.0
      wg-audio    g1_pong__godot__t1        t1=0.857  t2=1.0
      wg-g4c      g4_platformer__godot__t1  t1=0.929  t2=1.0
      wg-g4c      g4_platformer__unity__t1  t1=0.857  t2=1.0
      wg-scene-s1ts s1_parallax__ts__t0     t1=0.556  t2=0.833
    blocked: t2=0.00 on 2, t2>0 on 0.  failed-unblocked: t2=0.00 on 0, t2>0 on 6
    dropping tier 1: reversed 0, coarsened 3, identical 8
    groups: 11   both tiers vary among measurable trials: 0
    VERDICT: FLOOR-ONLY      (pooled instead: DISCRIMINATES)

`python3 eval/judge/tier2_census.py --runs-root <main>/eval/runs`

    69 stored trials carry tier-2 criteria
    trials with any tier-2 failure: 12   whole-trial: 2   selective: 10
    per (run, game): 11 groups, 5 saturated  (wg-audio g1 n=8, wg-audio g2 n=3,
      wg-audio48 g1 n=8, wg-audio48 g2 n=8, wg-g4c g4 n=8  =  35 trials)
    g4_platformer: never failed 20 of 20 scored criteria
    s1_parallax: 6 scored, layers.depth_ordered FAILED; layers.image_parallax and
      loop.seamless unscored
    diagnostics: 7 group-criterion pairs, every one single-valued False
    VERDICT: SATURATED

Two more producers carry figures the same live documents state, so they are recorded here too:
`weight_sensitivity.py --all` gives `groups: 11 FLIPS=0 STABLE=3 UNIDENTIFIABLE=8`, and
`ink_window_control.py` gives `game: n=68  scene: n=1` with 4 `render.nonempty` failures, 2 floor
and 2 ceiling.

**All four were re-run after merging `origin/main` at `0d270fb` (task 174, which rewrites
`scene_probe.py`). Every figure is unchanged**, and 174's own read-only re-grade returns the same
6 of 6, so nothing here rests on the pre-174 probe.

### The distinction that was decided

`DECISIONS.md`, *A corpus figure in a live document is CURRENT or DATED, and which one is a
choice*. **Classify each figure one at a time.** Present tense, a *what it reports today* heading,
or a producer's output must match the producer re-run in the same session **and carry the date it
was last read**; the evidence a decision was taken on names its date and population and is not
updated. **The date is provenance, not permission** — a live count still has to match. A decision
entry may carry both: the heading dates the decision, the evidence bullets are re-run and marked
current, and the entry says whether the verdict moved.

### The half that is not arithmetic, and the next agent should not re-derive it

**Nothing under `eval/runs/` was rewritten by `tasks/162`, `163`, `164`, `168` or `174`.** The
stored scene report is dated 2026-08-25 and holds the ORIGINAL grading. So the censuses report:

| stored, and counted by the census | after the repair, recorded in `eval/RUNS.md` only |
|---|---|
| `wg-g4c g4_platformer__godot__t1` `render.nonempty` FAIL, `gate: FAIL 1/14` | PASS, `gate: PASS 14/14` |
| `wg-scene s1_parallax__ts__t0` `render.nonempty` FAIL, `gate: FAIL 4/9` | PASS, `gate: FAIL 3/9` |
| `wg-scene s1_parallax__ts__t0` `layers.depth_ordered` FAIL, t2 = 5 of 6 = 0.833 | PASS, t2 = 6 of 6 = 1.000 |

That third row is why `eval/AGENTS.md`'s *"the re-grade stands at 6 of 6"* and `tier2_census.py`'s
0.833 are both correct; the file now says which is which.

**Consequences worth carrying:** re-graded, the tier-1 failing count is 7 rather than 8 (the
platformer leaves the set; the scene keeps 3 failures from an interrupted build), and the tier-2
selective count is 9 rather than 10, which restores *"every selective failure is
`wg-matrix-2026-08-13`"* — the sentence `DECISIONS.md` prices a harder task against.

### The class boundary, and the fact that makes the totals safe

**A `(run, game)` group is single-class by construction.** The 11 groups are 10 game and 1 scene;
no score crosses the boundary, and every denominator now reads back to its class: the 5 saturated
groups are game groups holding **35 of the 68 games**, and tier 1's ceiling is **61 of the 68
games, 0 of the 1 scene**. The game/scene split is **inferred**: `ink_window_control.py` reads
`task_class` from the record on 1 of 69 and infers it from the id shape on the other 68.

### Numbers that did NOT move, and one that moved without looking like it

- `61 of 68` became **`61 of 69`**: 69 − 8 = 61, the same numerator by coincidence. Do not read an
  unchanged numerator as an unchanged sentence.
- `35 of 68` became **`35 of the 68 games`**, numerator re-derived from the group table
  (8+3+8+8+8), not carried over.
- the game ink values are still **68**, because the 69th is the scene.

### Filed rather than fixed here

- **`tasks/181`** — `AGENTS.md` and `DECISIONS.md` cite findings as bare `(#NN)`, against
  `DECISIONS.md`'s own reference-style decision, which says *live document* and was implemented in
  `README.md` alone. Measured: converting one citation gives `AGENTS.md:650: shortcut reference #92
  has no definition in this file`, `linkcheck.py` exit 1 (restored). Migrate the file whole or
  narrow the decision.
- **`tasks/182`** — `capability.py`'s *"62 of 68 stored submissions"* is a hardcoded string in the
  `WHY` dict, printed by the same invocation whose header reads 69. It looks produced, which is
  worse than a figure with no producer.

### Not chased, deliberately

`eval/PROTOCOL.md`'s *"of 68 stored judge packs"* is a judge-pack count with a different producer,
cited to #104. `AGENTS.md`'s *"the first version reported flips on 3 of 10 groups"* is about a
superseded version of the tool, not a corpus count.

### The review

**5 rounds, 11 findings, 10 acted on and 1 declined with the measurement in its thread — the
reviewer withdrew that one.** Round 2 caught *"every count of the stored corpus moves when a trial
lands"*, which this ticket is itself a counterexample to. Round 4 caught *"today"* in a document
meant to be read later, and round 5 caught round 4's own new rule not being applied to
`README.md`. **The branch is handed back at the 5-round ceiling**, and `origin/main` was merged
after round 5, so the merge commit has had no review.

### A finding is owed and I did not number it

The work skill forbids allocating one. The claim: **a census reads stored gradings, so a criterion
repair never reaches it, and 3 stored verdicts in the corpus are currently against rules that no
longer exist.** The measurement and the control are above and in `eval/RUNS.md`. The orchestrator
should number it at merge if it wants one.
