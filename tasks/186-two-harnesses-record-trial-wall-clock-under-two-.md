---
id: 186
title: Two harnesses record trial wall-clock under two names, and the one nothing reads holds 4.4 hours of it
status: in_progress
priority: 3
refs: eval/runner.py,eval/wholegame.py,eval/RUNS.md,eval/judge/capability.py
done_when: 'The two names are reconciled - one quantity, one name, or an explicit statement in `eval/RUNS.md` that they are the same measurement recorded by two harnesses with the conversion written down. If `duration_ms` is kept, something must read it or the register must say why it is captured and not read; if it is dropped, the 47 stored records that carry it are evidence and the entry must say where that reading now lives. State which of the two the whole-game and spec-change suites each use after the change, and whether any published wall-clock figure moves - the expected answer is none, because nothing reads the one being changed, and that expectation should be checked rather than assumed. A null result closes this: if the two quantities turn out NOT to be the same measurement - different start points, different inclusions - say so with the two definitions side by side, because that is a sharper answer than renaming them.'
---

Found by the cleanup pass of 2026-08-27, the first to open `eval/runner.py`.

Both harnesses time a trial, under different field names, and only one of the two is ever read:

| written by | field | stored in | consumers outside its own module |
|---|---|---|---|
| `wholegame.py:450` | `wall_s` | whole-game trials | **6+** - `eval/judge/RUBRIC.md`, `capability.py`, `bot_mutants.py`, `BAKEOFF.md`, two findings files |
| `runner.py:726` | `duration_ms` | spec-change trials | **0, anywhere in the repository** |

Measured over the stored tree: `agent.duration_ms` is present and positive in **47 of 55** non-whole-game trial records and **0 of 84** whole-game ones. Its distribution is min 36s, median 332s, max 659s, totalling **4.4 hours of recorded agent wall-clock that nothing has ever read**. (`ci_minutes.py` mentions `run_duration_ms`, which is GitHub Actions' field for a workflow run and unrelated - checked.)

**Why this is more than a tidiness item.** `eval/RUNS.md` treats wall clock as a COMPARISON METRIC, and `wholegame.py` says so in a comment at line 459. A comparison that spans the two harnesses has to know the two names are the same quantity, and nothing says so - not the field names, not the docs, and not a producer. That is the shape #83 records: **an audit trail of what a mechanism did is worth more than the confidence you had when you built it, because the question it will be asked is not the one it was built for.** The judge's file-open log was captured for one reason and bounded a serious defect two weeks later; this capture has been sitting unread since 2026-08-12.

It is also live rather than historical: a second harness was added on 2026-08-25 as a recorded arm dimension, and any wall-clock comparison across harnesses or across the two suites meets this immediately.
