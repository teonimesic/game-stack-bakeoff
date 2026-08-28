---
id: 199
title: aspects.py's applicability docstring says scene_runner_control --paths prints the runner's 3 routes; the tool prints 6
status: in_review
priority: 5
refs: eval/judge/aspects.py,eval/tools/scene_runner_control.py
done_when: the pointer in the applicability docstring names what the tool actually prints - the 6 routes, distinguishing the applicability-guarded ones from those guarded by select_tasks or argparse choices - OR scene_runner_control gains a mode printing exactly the applicability-guarded subset and the pointer names that mode; either way docstat.py --sweep and aspects_selftest.py exit 0 unpiped after, and the count claim in the edited text was re-run against the tool before committing.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/78
---

MEASURED 2026-08-28: python3 eval/tools/scene_runner_control.py --paths prints '6 guarded routes' P1-P6 (P1 wholegame build/select_tasks, P5 evaluate.py --game via argparse choices, P6 wholegame concurrency-check via argparse choices), while eval/judge/aspects.py:719 (applicability docstring) says the tool 'prints the runner's 3 with their guards'. A reader who follows the pointer expecting 3 lines gets 6, three of which are guarded by mechanisms that never call applicability (select_tasks, argparse choices). Note the adjacent sound finding, recorded so nobody re-derives it: the docstring's own '6 paths applicability is called from' (field pack, field run_field, field_sweep.main, plus evaluate's up-front resolution, tier-2 dispatch, legacy call) is TRUE - evaluate.py:275 calls resolve_instrument whose :215 applicability call covers the tier-2 dispatch transitively, documented at evaluate.py:345, and the 5 grep-level call sites cover those 6 routes. The stale text is only the pointer's count.

## note 2026-08-28

DONE 2026-08-28, PR #78 (branch task-199-aspects-docstring-route-count). Took the first
done_when option: the pointer was rewritten, no tool mode added.

- eval/judge/aspects.py:718 now reads: "--paths prints 6 routes, not just these 3: P2-P4 are
  the runner paths above, each reaching this function; P1 is guarded by
  `wholegame.select_tasks` and P5/P6 by argparse `choices` at the CLI surface -- guards on
  those routes that never call this function."
- SCOPE EXTENSION, declared: eval/AGENTS.md scene paragraph said the 6 routes are "each
  guarded by judge/aspects.applicability" - the same defect at a second address, directly
  falsified by this ticket's own measurement (the tool's guard column names select_tasks for
  P1 and argparse choices for P5/P6). It now names the split P2-P4 / P1 / P5-P6 and says "an
  operator's command" where it said "the runner" (P5 is evaluate.py's own CLI). Nothing else
  in that paragraph moved.

Verified before committing: the MEASURED note's claims re-read in code (evaluate.py:275
resolve_instrument -> applicability at :215, covering the tier-2 dispatch transitively per the
comment at :345; assert_legacy_judge_allowed at :187; 5 grep-level call sites covering the 6
docstring paths) - the adjacent finding is sound and was left alone. The stale text was only
the pointer's count.

Controls: broken state read from a fresh --paths run first (6 routes vs the docstring's 3);
the edited count claim re-run against --paths after the edit and matched line for line
(6 guarded routes; P2-P4 applicability; P1 select_tasks; P5/P6 argparse choices); both
done_when gates unpiped against the staged tree - docstat.py --sweep exit 0 over 266 docs,
aspects_selftest.py PASS exit 0 - with git status clean before and after, so the gates
rewrote nothing. Note for a future reader: P5/P6's argparse choices refuse only ids no suite
defines; a scene id passes them and then hits applicability inside evaluate(). The docstring
text and the tool's guard column describe the route's own surface guard, which is the claim
that was wrong; no text here says applicability is absent downstream.

## note 2026-08-28

REVIEW ROUND 1 (2026-08-28): CodeRabbit landed one thread, Minor/quick-win, on
eval/judge/aspects.py:718-721 - readability only, asking for the 6-route mapping as separate
sentences rather than a semicolon chain, in both files. Acted on it (the review was right that
the chain was hard to read; nothing it proposed was declined). Restructured in
eval/judge/aspects.py and eval/AGENTS.md, keeping the two facts its flat wording dropped:
P2-P4 are the runner paths named in the docstring's own enumeration, and the reason the split
matters is that select_tasks and argparse choices never call applicability. Committed 995bf9b,
pushed, replied in-thread (reply verified byte-identical against the API's stored body), and
the thread reports isResolved.

Re-verified with runs after the restructure: --paths prints the 6 routes with the guards the
new sentences state, line for line; docstat.py --sweep exit 0 and aspects_selftest.py PASS
exit 0, unpiped, against the staged tree, git status clean before and after.

CodeRabbit began a further informational pass on the new head; the merge gate does not require
it (mergeable.py marks that check not-required and review state reported-not-gated), and no
second round was requested - spending another pooled review on a sentence restructure is what
the work skill says to avoid. Handing back once the required CI checks finish on 995bf9b.
