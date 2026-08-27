---
id: 171
title: rally.counts passes on a single increment, so a counter that moves once and stops is scored as correct
status: done
priority: 3
refs: eval/judge/bot_pong.py, eval/judge/bot_mutants.py, eval/judge/tier2_census.py, tasks/159, https://github.com/teonimesic/game-stack-bakeoff/pull/43
done_when: rally.counts either keeps rose_on_hit > 0 with the reason written into bot_pong._rally, or requires every observed hit with the sample floor argued rather than assumed. Either way tier2_census.py --runs-root <checkout>/eval/runs is run before and after and both figures are recorded, bot_mutants.py exits 0 with the RALLY_FROZEN mutant still red, and a correct game producing few hits is shown not to be newly failed.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/59
established_by: 'Merged as PR #59. rally.counts could not fail a game whose counter skips hits: the verdict rose_on_hit > 0 answered ''on at least one of them'' to a criterion asking ''on each'', while paddle.deflects - computed in the SAME loop over the SAME hits - was already all-or-nothing. Measured on the reference before the verdict was touched: a ref_pong whose counter takes only the left paddle''s returns PASSED, with evidence ''rally rose on 3 of 6 paddle_hit ticks''. THE ONE-TICK QUESTION WAS DECIDED FROM THE CONTRACT, NOT FROM PRECEDENT, WHICH IS WHAT THE TICKET ASKED: its two siblings point opposite ways - tasks/159 declined a one-tick reading, tasks/170 repaired one - and g1 DEFINES rally as the number of consecutive paddle hits since the last point, so a skipped hit makes a line publish a rally its own event history contradicts. That is 159''s case. The verdict is now ''countable > 0 and rose_on_hit == countable''. Verified by the orchestrator on the branch: the verdict at bot_pong.py:552, bot_mutants --selftest exit 0 at 23 offline checks / 0 unmet, and I drove the defect back myself - reverting to the at-least-one reading gives exit 1 with ''expected FAIL rally rose on 3 of 6 paddle_hit ticks, got PASS rally rose on 3 of 6 paddle_hit ticks'', the SAME evidence string under both verdicts, which is the whole defect. I ran that mutant with python3 -B and a cleared __pycache__, applying #199''s lesson from the same afternoon. The reviewer''s ''hits >= 6'' floor was DECLINED as the ticket instructed, because it fails a correct game for a short rally (#46''s shape); the floor is one countable hit. The regime ordinal was hand-allocated and I checked it for a collision at merge as the agent asked - main held twenty-fourth and twenty-fifth, and of the three open pull requests only this one added a twenty-sixth. Not establishable and recorded as such: whether any stored grading would flip, because all 50 stored evidence strings predate the field and grep -rl ''rally rose on'' eval/runs/ returns 0 files, so rose_on_hit was never recorded. Findings #200.'
---

bot_pong._rally returns rose_on_hit > 0. The criterion asks 'Does the rally counter increase on each paddle hit?' and the verdict answers 'on at least one of them'. Its sibling paddle.deflects is already all-or-nothing - deflect_ok is cleared by any hit without a velocity sign flip - so the two halves of the same loop hold the submission to different standards. Raised by CodeRabbit on PR 43 as a Major, and DECLINED THERE ON PURPOSE rather than because it is wrong: tightening a scored criterion moves stored verdicts, and eval/judge/AGENTS.md and DECISIONS.md both say a criterion change is a re-scoring event that needs its own ticket with a tier2_census.py before-and-after. tasks/159 deliberately left the verdict function byte-identical to what it replaced. The reviewer's proposed condition was hits >= 6 and rose_on_hit == hits; DO NOT ADOPT IT UNMEASURED - the hits >= 6 half is a new false-negative channel of the #46 family, failing a correct game that simply produces fewer than 6 hits in the 3000-tick drive, and the loop's own early break at hits >= 6 and rose_on_hit has to move with it or the two disagree.

## note 2026-08-27

## note 2026-08-27 (orchestrator) — 170 settled the sibling question and it went the OTHER way

Your ticket descends from `tasks/159`, which DECLINED a one-tick reading for `rally.counts` because
the g1 contract defines rally as a count of the events a tick line carries. **`tasks/170` asked the
same question of `multiplier.falls` and REPAIRED it instead** (#195), on the reasoning that the g3
contract defines `multiplier` nowhere and that `multiplier.rises` reads its half over hundreds of
ticks by any mechanism, so a one-tick fall was an asymmetry nothing licensed.

**So there is no house answer to inherit. Decide yours from the g1 contract**, and say which of the
two precedents your case resembles and why.

What 170 found that bears on you directly: its criterion compared a peak against a value **459 ticks
later** and credited everything in between to the damage - a game with no damage link at all passed,
with an evidence string byte-identical to a correct submission's. **Your ticket is the mirror image:
`rally.counts` passes on a single increment, so a counter that moves once and stops scores as
correct.** Both are the same defect class - a criterion whose window is wider or narrower than the
property it names - and 170's rule generalises: *state what must still FAIL after the repair*.

**Baseline, re-run at the merged head:** `bot_mutants.py` exits 0 at **49 mutants pinned in both
directions over 45 criteria, 13 variants, 0 pending, 3 session-lock controls, 70 hazards, 0 unmet**.
State the new figures rather than assuming only your rows moved.

`tasks/166` remains deliberately LAST in the bot_mutants order; nothing else holds that file now.

## note 2026-08-27

## Outcome: REPAIRED — `rally.counts` requires every hit the drive can read

**The g1 contract decides it, and it is `tasks/159`'s case rather than `tasks/170`'s.** g1 defines
`rally` as *"the number of consecutive paddle hits since the last point was scored"*, so a hit the
counter skips makes a trace line publish a rally its own event history contradicts — the same
contradiction as a late counter, from the same sentence. 170 went the other way because g3 defines
`multiplier` nowhere. The verdict is now `countable > 0 and rose_on_hit == countable`, which is the
standard `paddle.deflects` already held in the same loop.

**The broken state was established before the repair, with a mutant.** `RALLY_HALF_COUNTED` — a
`ref_pong` whose counter takes only the left paddle's returns — **PASSED** `rally.counts` under
`rose_on_hit > 0`, reported by the suite as `UNMET`, with evidence `rally rose on 3 of 6
paddle_hit ticks`: the criterion printing the number that condemns the game beside a verdict that
clears it. It is now red.

**The sample floor is ONE countable hit, and the ticket's warning was right.** The reviewer's
`hits >= 6` half is not taken. A correct game producing a short rally would fail it, which is #46's
shape; the contract is per hit, so one hit measures it — and it is the floor `paddle.deflects`
uses. The drive's early break moved with the verdict: it now stops at 6 **countable** hits whatever
the counter did, holding one extra tick while a late increment is outstanding so `rose_late` can
still separate *a tick behind* from *never moved* on the final hit.

**A hit tick that also carries the point is counted in neither half** — the point zeroes `rally` on
that same line, so there is no reading under which the counter must rise there. The verdict
requires `countable > 0` rather than `hits > 0`, so a game that scored on every hit tick fails
rather than passing on an empty denominator (rule 7). Measured: that tape reads
`FAIL all 6 paddle_hit ticks also carried the point ...`, where the pre-repair code read
`FAIL rally rose on 0 of 6` — same verdict, and the denominator is now honest.

## What the next agent should not re-derive

**`bot_mutants.py --selftest` has a third arm: 10 written `(rally, events)` tapes driven straight
through `_rally`.** `ref_pong`'s physics cannot be steered into a rally of exactly one hit, into
hits on consecutive ticks, or into a hit tick carrying the point, so those games are written rather
than compiled. It starts no subprocess. It is also the producer for the numbers `_rally`'s
docstring had been quoting from `tasks/159`'s hand measurement — `TapeSession`, `rally_tapes()` and
`read_tape()` in `bot_mutants.py`.

**The arm's own negative control** (not committed; reproduce with `git show
<pre-merge base>:eval/judge/bot_pong.py` written beside `bot_mutants.py` and injected as
`sys.modules["bot_pong"]`): **3 unmet, exit 1**. The 3 that move are *misses every second hit*
(PASS → FAIL), *a hit tick that also carries the point* (`3 of 4` → `3 of 3` plus the exclusion
line) and *every hit tick carries the point* (same verdict, honest reason). The 4 correct-game rows
are green under both readings, which is the "few hits are not newly failed" evidence.

## The re-scoring figures, and why they cannot answer the question

`python3 eval/judge/tier2_census.py --runs-root <checkout>/eval/runs`, before and after, is
**identical**: `rally.counts` 25 gradings / 0 failures; 69 stored trials; 11 groups, 5 saturated;
10 selective failures; `VERDICT: SATURATED`.

**That agreement is not evidence that nothing moves.** A stored verdict is a record. All **50**
stored evidence strings read `rally counter incremented on paddle hits (6 hits seen)` — the format
predating `tasks/159` — and `grep -rl "rally rose on" eval/runs/` returns **0** files, so
`rose_on_hit` was never written down for any stored grading. Whether any of the 25 would fail the
new reading is answerable only by re-driving those submissions. Recorded as the **twenty-sixth**
comparability break in `eval/RUNS.md`; that ordinal is hand-allocated and has collided before.

## THE FINDING, and it needs a number from the orchestrator

**`rally.counts` could not fail a game whose counter skips hits, and its evidence said so in the
same sentence that cleared it.** The verdict `rose_on_hit > 0` answered *"on at least one of them"*
to a criterion asking *"on each"*, while its sibling `paddle.deflects`, computed in the same loop
over the same hits, was all-or-nothing. Measured on the reference: `PASS`, `rally rose on 3 of 6
paddle_hit ticks`.

Two things generalise past this criterion:

- **A mutant could not have found it and the suite had one.** `RALLY_FROZEN` removes the counter
  and the criterion goes red as designed; what was needed was a correct-shaped input that moves the
  counter *sometimes*, which is rule 15's variant half. The first patch tried — *the counter moves
  once and then stops*, the ticket's own words — read `0 of 33` and was red under **both** readings,
  because `_rally` shares its session with the wall-bounce drive and opens with the counter already
  past 0. **A mutant that degenerates into an existing mutant's shape pins nothing**, and only the
  evidence string showed it had.
- **The evidence carried the refuting number for as long as the defect existed.** `3 of 6` is
  printed beside `passed=True`. This is #183's shape in `fire.rate_limited` again — a criterion
  computing its verdict from a different quantity than the one it reports.

## Review, PR 59 — 3 rounds, ending clean

Round 1 (2 Minor): DECISIONS.md was narrating the prior verdict, the declined proposal and the
before-measurement — **taken**, that material is `eval/RUNS.md`'s; and the duplicated *"Check the
ordinal before citing it"* preface — **taken**, it is already stated in 8 sections of that file.
The heading's ordinal itself was **declined**: 25 sections head a break with its ordinal, the 4
immediately preceding are the same class of change, and the one section that omits one says in its
own body that it is *"deliberately not given an ordinal"* — so an ordinal-free heading in that file
is a claim, not a formatting choice.

Round 2 (1 Minor): `rose_on_hit` and `countable` are local names in `bot_pong.py` and DECISIONS.md
must read without opening the judge — **taken**.

Round 3 (1 Minor): delete the `tasks/159` re-open clause as conflicting with the new one —
**declined**, they are the triggers for two different rules in one section, and deleting the first
would leave `_rally` failing late counters with nothing saying what would change that. The
ambiguity was real and was in the labels: both now name their reading. Round 4 came back
`LANDED_COMMENT` — nothing further.
