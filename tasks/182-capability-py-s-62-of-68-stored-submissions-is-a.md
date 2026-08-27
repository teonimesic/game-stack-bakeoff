---
id: 182
title: capability.py's '62 of 68 stored submissions' is a hardcoded string, printed beside a computed header reading 69
status: done
priority: 3
refs: eval/judge/capability.py,DECISIONS.md
done_when: the figure is computed by capability.py from the records it just read, with the population it counted stated beside it and the 2 submissions whose capture failed accounted for explicitly rather than silently - a mutant that freezes the count is red - or the sentence says it is a hand reading of a named date's corpus and DECISIONS.md's row stops saying 'currently'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/57
established_by: 'Merged as PR #57. The broken state was measured first: capability.py --runs eval/runs/wg-audio-2026-08-14T12-29-42 printed ''11 stored submissions'' in its header and ''62 of 68 stored submissions captured at exactly the starter default'' in the same output - the literal did not move with the population, and against the full tree it sat under a header reading 69. resolution_census() now partitions the records the invocation actually swept and names every trial not at the default. Verified by the orchestrator on the branch: over the whole tree it reads ''64 of the 69 records swept captured at exactly the starter default 640x400; 3 varied (420x640, 720x540, 768x576); 2 have no geometry to compare (2 submission_failed)'', which sums to 69, and capability_selftest.py exits 0 at ''all controls hold''. THE RETIRED NUMBER WAS WRONG WHEN IT WAS WRITTEN, NOT ONLY STALE, and the arithmetic is checkable without rerunning anything: 69 records less the 1 scene is 68 games, of which 63 are at the default, not 62 - and the archived paragraph''s own parts, 62 + 3 + 2, never reached 68. Registered as WR-capture-default-62-of-68. The extraction was proved before the census was believed, on a row whose answer was known in advance and with an instrument sharing no code with the subject: sips reads 720x540 on g2_tetris3d__ts__t1''s first frame and 640x400 on __t0, agreeing with png_geometry''s IHDR read. A TRAP WORTH CARRYING: restoring a mutant to a file of the same byte length inside the same mtime second leaves CPython importing the mutant''s .pyc - it cost a false red here and can equally produce a false SURVIVED, so mutation harnesses want python3 -B and a cleared __pycache__. Filed rather than fixed: tasks/185, capability.TRIAL_RE does not match a scene trial id, so the stored scene reports as stack ''?'' and is excluded from every per-stack partition including the four-arm gate, which therefore answers over 68 of 69 records without saying so - nothing is wrong today, it is a silent-exclusion channel. The other 68s in the docstring and around DECISIONS.md''s task-25 rationale were deliberately left: they are decision-time evidence, one explicitly dated, and tasks/169 recorded that repairing those blind erases the population a decision was made on. Findings #199.'
---

capability.py prints '62 of 68 stored submissions captured at exactly the starter default' as the 'why' text of capture.resolution_as_a_variable. It is a literal in the WHY dict at capability.py:181, not a count of anything the run just read - and the same invocation prints '69 stored submissions' in its own header two screens above it. DECISIONS.md's re-open table quotes it in the present tense: 'Currently 62 of 68 sit on the starter default'. AGENTS.md's rule is that a quantity with no producer goes stale forever, and this one is worse than that: it LOOKS produced, because a producer prints it. It is a capture-geometry figure rather than a tier census, so tasks/169 left it alone deliberately.

## note 2026-08-27

## note 2026-08-27 (orchestrator) — 169 has MERGED and it gives you the rule to apply

`tasks/169` landed and recorded the decision in `DECISIONS.md`: **a corpus figure in a live document
is CURRENT or DATED, and which one is a choice made per figure.** A CURRENT figure must match its
producer re-run in the same session and carry the date it was last read; a DATED one names the
population and date it describes. *The date is provenance, not permission.*

`capability.py`'s hardcoded '62 of 68' is the case that rule does not yet reach, and your ticket
already names why it is worse than an unproduced number: it is printed **beside a computed header**,
so it looks produced. A reader has no way to see that one number came from the tree and the other
from a string literal.

Two things from 169 worth carrying: neither classification was applied as a blanket - '61 of 68'
became '61 of 69' with its numerator right **by coincidence**, and '35 of 68' had its numerator
re-derived from the group table - so decide per figure and show the derivation. And #194 records the
structural reason these drift at all: **a census reads stored gradings, so a criterion repair never
reaches it**, which is why a figure can be correct and stale at once.

`eval/runs/` is read-only for you.

## note 2026-08-27

Done via PR #57, branch `task-182-capability-resolution-census`. The first route in
`done_when` was taken: the figure is COUNTED, not dated.

## The number, and the part that is a finding

`resolution_census()` in `eval/judge/capability.py` partitions the records the invocation
swept into three buckets — at the starter default, varied, and no geometry at all — and
`report()` prints it under the `capture.resolution_as_a_variable` entry, naming every
trial that is not at the default. Over `<main>/eval/runs` on 2026-08-27:

    64 of the 69 records swept captured at exactly the starter default 640x400;
    3 varied (420x640 x1, 720x540 x1, 768x576 x1);
    2 have no geometry to compare (2 submission_failed)

The same binary against the 11-record `wg-audio-2026-08-14T12-29-42` subset reads
`10 of the 11`, which the literal could not do — before the change that same invocation
printed `11 stored submissions` in its header and `62 of 68` two screens below it.

**NEEDS A FINDING NUMBER — do not let this go by as a stale-figure repair.** The retired
literal was **wrong when it was written**, not only overtaken. Restricted to the 68 game
submissions it named (the corpus before `wg-scene-s1ts-2026-08-25` added the 69th record)
the census is **63** at the default, 3 varied, 2 with no geometry. `62 + 3 + 2 = 67`, so
the partition never closed, and the same output block in
`eval/findings/certifies-nothing.md` states "62 of 68 … Three deviated … and two produced
no frames" — the three parts contradict each other in one paragraph and nothing noticed
for four days. The shape worth writing down is: **an unclosed partition is a detectable
defect and a bare ratio is not.** `62 of 68` on its own agrees with itself; `62 + 3 + 2`
does not reach 68. That is why `ResolutionCensus` is three buckets rather than a
numerator and a denominator, and why the selftest asserts they sum to the population.

The withdrawal is declared as `WR-capture-default-62-of-68` in `eval/withdrawn.json`,
anchored in `eval/findings/certifies-nothing.md`. `DECISIONS.md`'s re-open row for
*Performance fields are captured, not scored* now names the producer and the date it was
last read.

## What the next agent must not re-derive

- **The three trials that varied**, once and for all:
  `wg-matrix-2026-08-13T14-02-50/g2_tetris3d__unity__t1` 420x640,
  `wg-audio-2026-08-14T12-29-42/g2_tetris3d__ts__t1` 720x540,
  `wg-audio48-2026-08-14T19-55-47/g2_tetris3d__rust__t0` 768x576. The two with no
  geometry are both `wg-arena3d-2026-08-15T12-46-30/g3_arena__rust__t{0,1}`, `just film`
  exit 101 — that is #49's run.
- **The extraction was proved against an independent reader before the census was
  believed**: `sips -g pixelWidth -g pixelHeight` on
  `.../g2_tetris3d__ts__t1/eval/frames/frame_0000.png` reads 720x540 and on `__t0` reads
  640x400, agreeing with `png_geometry`'s IHDR read. Any future sweep of these frames can
  use `sips` as the second opinion; it shares no code with the module.
- **`STARTER_DEFAULT_GEOMETRY = (640, 400)` is not an assumption.**
  `capability_selftest.test_starter_default_is_what_the_starters_say` reads
  `VIEW_WIDTH`/`VIEW_HEIGHT` out of all four starter sources
  (`rust/crates/game/src/lib.rs`, `ts/src/view/index.ts`,
  `unity/Assets/View/GameView.cs`, `godot/view/view.gd`) and compares. If a starter's
  view geometry ever changes, that gate goes red before the census can mislabel anything.
  It reads the starters and edits nothing, so it is not a regime boundary.

## A trap that cost real time here, and would cost it again

**A source-level mutant restored to a file of the SAME BYTE LENGTH inside the SAME mtime
second leaves CPython running the mutant's `.pyc`.** After a mutant run that restored
`capability.py` byte for byte and reported `RESTORED exit=0`, a later invocation of the
selftest failed with `constant says (800, 600)` while `grep` on the file showed
`(640, 400)` — the module was being imported from `eval/judge/__pycache__`. The source
cache is keyed on (mtime seconds, size), and `(640, 400)` and `(800, 600)` are the same
size. It fails in both directions: a mutant can also SURVIVE by importing a clean cached
module, which reads as a control that could not fail.

**Run any source-mutation harness with `python3 -B` and delete `__pycache__` before the
baseline.** The four mutants below were all re-run that way before being believed.

## The controls, and what each mutant returns

`python3 eval/judge/capability_selftest.py` — all controls hold; it is already wired into
CI as `judge/capability_selftest` in `.github/workflows/gates.yml`. Four new sections:
a positive control whose expected census is stated in the test as literals and separately
re-derived from the records (never by calling the subject — task 113's failure), a mutant
census that ignores its records, three variants (all-default, empty, majority-varied), and
a register check that no `DECLINED` entry carries an `N of M` figure of its own, with its
own mutant and variant.

Source-level mutants of the real module, `-B`, each restored byte for byte, baseline and
restored green:

| mutant | selftest |
|---|---|
| the literal `62 of 68` back in the `DECLINED` prose | exit 1, 1 FAIL row |
| `resolution_census` returns a frozen census | exit 1, 16 FAIL rows |
| `STARTER_DEFAULT_GEOMETRY` set to `(800, 600)` | exit 1, 10 FAIL rows, all four starter rows among them |
| records with no geometry dropped from the denominator | exit 1, 7 FAIL rows |

The register check's mutant is a synthetic entry rather than a mutation of the real
`DECLINED` dict, so it pins the PREDICATE and not the address. The source-level M1 above
is what pins the address, and it is a one-off rather than a standing gate — worth knowing
if that check ever needs trusting on its own.

## Filed, not fixed

`tasks/185` — `capability.TRIAL_RE` does not match a scene trial id, so
`wg-scene-s1ts-2026-08-25/s1_parallax__ts__t0` parses as game `?` stack `?` and is
excluded from every per-stack partition, including `no_stack_correlated_gap`. The gate
therefore answers over 68 of the 69 records without saying so. Nothing is wrong today —
the scene's fields are all populated — but a scene submission with a genuine per-arm
absence would be silently uncounted.

## Left alone on purpose

The other `68`s in `capability.py`'s module docstring and in `DECISIONS.md` around the
task-25 rationale. They are decision-time evidence, one of them explicitly dated
`2026-08-23`, and `tasks/169` recorded that repairing those blind erases the population a
decision was made on.
