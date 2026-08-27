---
id: 171
title: rally.counts passes on a single increment, so a counter that moves once and stops is scored as correct
status: in_review
priority: 3
refs: eval/judge/bot_pong.py, eval/judge/bot_mutants.py, eval/judge/tier2_census.py, tasks/159, https://github.com/teonimesic/game-stack-bakeoff/pull/43
done_when: rally.counts either keeps rose_on_hit > 0 with the reason written into bot_pong._rally, or requires every observed hit with the sample floor argued rather than assumed. Either way tier2_census.py --runs-root <checkout>/eval/runs is run before and after and both figures are recorded, bot_mutants.py exits 0 with the RALLY_FROZEN mutant still red, and a correct game producing few hits is shown not to be newly failed.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/59
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
