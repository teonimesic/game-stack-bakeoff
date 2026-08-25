---
id: 132
title: The stored-judge-round census in eval/RUNS.md disagrees with the producer printed above it, on three rows of four
status: todo
priority: 2
refs: 'eval/RUNS.md, eval/judge/blurb_selftest.py, #83, tasks/130'
done_when: Every row of that table is re-read from `python3 eval/judge/blurb_selftest.py --stored-rounds <checkout>/eval/runs` and states the population it counted; the two sentences that make claims about the 10 (single-directory, and 10-of-10 byte-identical) either still hold for the new population or are replaced by what does; and the paragraph beneath still supports its conclusion or says what changed. BLOCKED BEHIND 130 - both edit eval/RUNS.md.
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
