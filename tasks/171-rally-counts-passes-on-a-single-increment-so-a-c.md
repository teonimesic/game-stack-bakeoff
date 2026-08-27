---
id: 171
title: rally.counts passes on a single increment, so a counter that moves once and stops is scored as correct
status: todo
priority: 3
refs: eval/judge/bot_pong.py, eval/judge/bot_mutants.py, eval/judge/tier2_census.py, tasks/159, https://github.com/teonimesic/game-stack-bakeoff/pull/43
done_when: rally.counts either keeps rose_on_hit > 0 with the reason written into bot_pong._rally, or requires every observed hit with the sample floor argued rather than assumed. Either way tier2_census.py --runs-root <checkout>/eval/runs is run before and after and both figures are recorded, bot_mutants.py exits 0 with the RALLY_FROZEN mutant still red, and a correct game producing few hits is shown not to be newly failed.
---

bot_pong._rally returns rose_on_hit > 0. The criterion asks 'Does the rally counter increase on each paddle hit?' and the verdict answers 'on at least one of them'. Its sibling paddle.deflects is already all-or-nothing - deflect_ok is cleared by any hit without a velocity sign flip - so the two halves of the same loop hold the submission to different standards. Raised by CodeRabbit on PR 43 as a Major, and DECLINED THERE ON PURPOSE rather than because it is wrong: tightening a scored criterion moves stored verdicts, and eval/judge/AGENTS.md and DECISIONS.md both say a criterion change is a re-scoring event that needs its own ticket with a tier2_census.py before-and-after. tasks/159 deliberately left the verdict function byte-identical to what it replaced. The reviewer's proposed condition was hits >= 6 and rose_on_hit == hits; DO NOT ADOPT IT UNMEASURED - the hits >= 6 half is a new false-negative channel of the #46 family, failing a correct game that simply produces fewer than 6 hits in the 3000-tick drive, and the loop's own early break at hits >= 6 and rose_on_hit has to move with it or the two disagree.
