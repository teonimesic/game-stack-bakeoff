---
id: 199
title: aspects.py's applicability docstring says scene_runner_control --paths prints the runner's 3 routes; the tool prints 6
status: todo
priority: 5
refs: eval/judge/aspects.py,eval/tools/scene_runner_control.py
done_when: the pointer in the applicability docstring names what the tool actually prints - the 6 routes, distinguishing the applicability-guarded ones from those guarded by select_tasks or argparse choices - OR scene_runner_control gains a mode printing exactly the applicability-guarded subset and the pointer names that mode; either way docstat.py --sweep and aspects_selftest.py exit 0 unpiped after, and the count claim in the edited text was re-run against the tool before committing.
---

MEASURED 2026-08-28: python3 eval/tools/scene_runner_control.py --paths prints '6 guarded routes' P1-P6 (P1 wholegame build/select_tasks, P5 evaluate.py --game via argparse choices, P6 wholegame concurrency-check via argparse choices), while eval/judge/aspects.py:719 (applicability docstring) says the tool 'prints the runner's 3 with their guards'. A reader who follows the pointer expecting 3 lines gets 6, three of which are guarded by mechanisms that never call applicability (select_tasks, argparse choices). Note the adjacent sound finding, recorded so nobody re-derives it: the docstring's own '6 paths applicability is called from' (field pack, field run_field, field_sweep.main, plus evaluate's up-front resolution, tier-2 dispatch, legacy call) is TRUE - evaluate.py:275 calls resolve_instrument whose :215 applicability call covers the tier-2 dispatch transitively, documented at evaluate.py:345, and the 5 grep-level call sites cover those 6 routes. The stale text is only the pointer's count.
