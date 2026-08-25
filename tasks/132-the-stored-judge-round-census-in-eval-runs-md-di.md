---
id: 132
title: The stored-judge-round census in eval/RUNS.md disagrees with the producer printed above it, on three rows of four
status: in_testing
priority: 2
refs: 'eval/RUNS.md, eval/judge/blurb_selftest.py, #83, tasks/130'
done_when: Every row of that table is re-read from `python3 eval/judge/blurb_selftest.py --stored-rounds <checkout>/eval/runs` and states the population it counted; the two sentences that make claims about the 10 (single-directory, and 10-of-10 byte-identical) either still hold for the new population or are replaced by what does; and the paragraph beneath still supports its conclusion or says what changed. BLOCKED BEHIND 130 - both edit eval/RUNS.md.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/36
established_by: 'PR #36, all 3 checks green at 035b68b; producer re-read 97/40/14/26 with the 14 split 10 in wg-aspect-reliability (moved) and 4 in wg-g4c-2026-08-21T02-26-46/judge-blind-2026-08-23 (same); pre-repair brief rebuilt from bc9fb52~1 reproduces both stored hashes; blurb_selftest check 13 plus stored_rounds_mutants at 7 mutants caught and a variant control that survives without the variant and is caught with it'
---

`eval/RUNS.md` (~line 278) carries a four-row census of stored judge rounds, with its producer
printed directly above it. Running that producer disagrees with three of the four rows:

| row | stated | `blurb_selftest.py --stored-rounds` |
|---|---|---|
| stored judge rounds in `eval/runs/**` | 93 | **97** |
| of those, code-seeing | 36 | **40** |
| code rounds carrying `provenance.brief_sha256` | 10 | **14** |
| the other code-seeing rounds, unassessable | 26 | 26 (agrees) |

All three gaps are exactly 4, consistent with the blind judge-field sweep of 2026-08-23 adding
4 rounds of `architecture` and `idiomatic`.

**This is not a digit swap, which is why it is a ticket and not an edit.** Two adjacent sentences
make claims ABOUT the population:

- the 10-row says *"all in `wg-aspect-reliability`, all `knowingly_truncated: false`"*. With 14 that
  is no longer true - the 4 new rounds are in a different sweep directory, and whether they carry
  `knowingly_truncated: false` has to be read, not assumed.
- the next row says *"of those 10, whose stored hash rebuilt byte-identically: 10 of 10"*. The
  producer now reports `architecture` 2 same / 5 moved and `idiomatic` 2 same / 5 moved, so the
  comparable figure is 4 same of 14, and the "moved" rows are expected - the brief was
  deliberately changed on 2026-08-23 and the paragraph beneath already says the same producer
  reports `moved` after the change.

So the repair has to re-state what each row's population IS, not just re-run the numbers. Read
the paragraph under the table before touching it: the argument it supports - that 10 rounds are
proof rather than inference and 26 are permanently unassessable - is the thing that must still
be true afterwards, or be replaced by what is.

The 26-row agreeing is the tell that the table was correct when written and was overtaken, which
is the failure mode AGENTS.md names: the producer is printed right there and nobody re-ran it.

## note 2026-08-25

## note 2026-08-25 — figures re-measured, unchanged since filing, and the fourth row is the trap

Re-ran the producer the table itself names. Same numbers as when this was filed, so nothing has
drifted further and the ticket is exactly as scoped:

| row | stated | `blurb_selftest.py --stored-rounds` |
|---|---|---|
| stored judge rounds | 93 | **97** |
| code-seeing | 36 | **40** |
| carrying `provenance.brief_sha256` | 10 | **14** |
| unassessable | 26 | 26 |

**The unassessable row agreeing at 26 is the trap, not a comfort.** Three rows moved by exactly 4
and one did not, so a repair that simply adds 4 to every figure produces a table that is
internally consistent and wrong. Work out what each row counts before touching any digit.

## Two sentences make claims about the POPULATION and both are now false

These are the actual work; the digits are the easy part.

- *"**10** — all in `wg-aspect-reliability`, all `knowingly_truncated: false`"*. At 14 the
  single-directory claim cannot hold: the four added rounds are the blind judge-field sweep of
  2026-08-23, in a different directory. **Read `knowingly_truncated` on the new four rather than
  assuming it carries over.**
- *"of those 10, whose stored hash rebuilt **byte-identically**: 10 of 10"*. The producer now
  reports `architecture` at 2 same / 5 moved and `idiomatic` at 2 same / 5 moved, so the
  comparable figure is **4 of 14**. The `moved` rows are expected — the brief was deliberately
  changed on 2026-08-23 and the paragraph beneath already says the same producer reports `moved`
  after the change. **Do not read `moved` as a defect.**

## What must still be true when you are done

The paragraph under the table argues that 10 rounds are **proof rather than inference** and 26 are
**permanently unassessable**. That argument is the reason the table exists. Either it still holds
at the new population, or it is replaced by what does — and if the second, say so plainly rather
than editing numbers under an argument that no longer follows from them.

**This is #83's evidence.** The 26 are unassessable because they predate `provenance`, and that is
what made the judge-leak question boundable at all. Nothing here may make them look assessable.

## note 2026-08-25

## What was measured, and what the next agent must not re-derive

Producer, re-read 2026-08-25 from `python3 eval/judge/blurb_selftest.py --stored-rounds
<main>/eval/runs`: **97** stored rounds, **40** code-seeing, **14** hashed, **26** unassessable.
Unchanged from filing, so nothing drifted further while this was queued.

**The 14 partition cleanly, and the partition is the answer to both stale sentences.** All 14 are
`knowingly_truncated: false`:

| directory | aspect | n | stored chars -> rebuilt here | reads |
|---|---|---|---|---|
| `wg-aspect-reliability` | `architecture` | 5 | 3536 -> 3576 | `moved` |
| `wg-aspect-reliability` | `idiomatic` | 5 | 3928 -> 4000 | `moved` |
| `wg-g4c-2026-08-21T02-26-46/judge-blind-2026-08-23` | `architecture` | 2 | 3576 -> 3576 | `same` |
| `wg-g4c-2026-08-21T02-26-46/judge-blind-2026-08-23` | `idiomatic` | 2 | 4000 -> 4000 | `same` |

The 26 unassessable sit in 7 directories under 3 wrappers: `wg-funframes-crossgame` 14,
`wg-tetris-judge-2026-08-17` 8, `wg-g4c-capgate` 4.

**The section heading was a false universal and was replaced.** *EVERY STORED CODE ROUND WAS TOLD
ITS PACK MIGHT BE TRUNCATED* stopped being true the moment the 2026-08-23 blind sweep stored 4
rounds that read the repaired brief. It is now *THE CODE JUDGE WAS TOLD ITS PACK MIGHT BE
TRUNCATED WHEN IT WAS NOT*, and the one citation of the old wording (in `blurb_selftest.py`'s
docstring) moved with it.

**The "10 of 10 byte-identical" claim is now RE-DERIVABLE rather than historical**, which is
better than the row it replaces. Do not re-measure this by hand:

    git worktree add --detach <tmp> bc9fb52~1     # the commit before the brief repair
    # in <tmp>: field._brief(aspects.ASPECTS[aid], "g4_platformer", None)
    #   -- NOTE: pre-repair `_brief` takes no `knowingly_truncated` argument

returns `6a94883e3dbe0eb2` / 3536 chars for `architecture` and `6fd7554b71a03f5e` / 3928 for
`idiomatic`, which are exactly what those 10 rounds stored. So `moved` against the current
checkout is the expected reading and not a defect.

The per-aspect table lower in that section had drifted the same way and is re-read: **34** hashed
rounds, `architecture` and `idiomatic` at 7 each rather than "30, 5 per aspect".

## THE FINDING - claim, measurement and control. NO NUMBER ALLOCATED.

> **A POPULATION with no producer goes stale exactly as a QUANTITY with no producer does, and it
> is harder to notice, because the count beside it still looks right.**

`AGENTS.md` already requires a producer beside any quantity, and this table had one printed
directly above it. It still went stale for two days on 3 rows of 4 - and the part that could not
be checked at all was the prose: *"all in `wg-aspect-reliability`, all `knowingly_truncated:
false`"*. No command in the repository printed a directory or a pack state, so a reader who ran
the producer saw four numbers and no way to tell that the sentence beside them described a
population that had grown.

**Measurement.** The producer now prints the directory and recorded pack state of every code
round it counts. Run against the corpus it names two directories where the prose named one.

**Control, both directions.** The census reads a gitignored path, so nothing could see it:
`blurb_selftest.py` now builds a fixture tree whose answer is written out as literals and asserts
the census against it (check 13), and `eval/judge/stored_rounds_mutants.py` is the red half - **7
mutants, all caught, control green**, plus a `--variant-control` that measures the variant is
load-bearing rather than asserting it (mutant SURVIVED without it, caught with it). Written red
first: 3 red rows against the unextended census with the 4 counts already correct.

## Two things the review found that are worth carrying forward

1. **The repair reproduced the ticket's own defect one level in.** A hashed code round whose
   aspect `aspects.py` no longer defines was counted in the headline and skipped before the
   population key was built - a population omitting a record its own total included. Fixed with a
   third verdict column and the invariant `n = same + moved + unbuildable` per row, which is what
   makes it checkable rather than promised. If you add a branch to that loop, keep the invariant.
2. **The first version of that invariant check summed the literals written beside it and could
   not fail.** It now parses the census's own output and takes the expected total from the
   census's own headline line. Rule 12's corollary, met in the act of answering a review comment.

## Neighbouring counts repaired in passing, both with producers

- `.github/workflows/gates.yml` said the lint backlog "stands at 67 findings" against
  `python3 eval/tools/lint.py --counts` reading **97**.
- `ci_minutes.py`'s `hook_census` docstring carried a second hand-written copy of the gate count.
  Restated as a ratio so `gate_census` is the only copy. The pin and the register moved 47 -> 49
  for the two new steps.
