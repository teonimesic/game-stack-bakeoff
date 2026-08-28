---
id: 191
title: bot_pong locates the end of a match from the SCORE, and end_condition_holds scores the flag
status: in_progress
priority: 3
refs: eval/judge/bot_pong.py, eval/judge/probe.py, eval/judge/bot_mutants.py, tasks/166
done_when: 'bot_pong._match_ends either locates the end of a match from `state.game_over` or states in a HAZARDS entry why the score is the right locator for this game and the flag is not. Whichever way it goes: a VARIANT on ref_pong where the flag lands some ticks after the eleventh point must PASS, a MUTANT where the match reaches 11 and the flag never rises must FAIL, and the widening the ticket describes - a game that reaches 11, plays on, and sets the flag later - must be stated with a measured bound on how long it can play. `bot_mutants.py` exits 0 and the summary line is quoted with all its populations.'
---

tasks/166 made the state flag the authoritative end signal and deleted the game_over EVENT branches from bot_arena._death and bot_tetris3d._gameover_check. bot_pong is the caller it did not change, because it reads neither of those two signals: _match_ends breaks its 12,000-tick drive on max(score) >= 11 and then hands the session straight to probe.end_condition_holds, which scores state.game_over. That is the same defect shape one signal further out - a THIRD signal locates the end and the flag scores it - and 166 left it alone on purpose, because the fix has a fail-open direction its scope did not license.

What is already true after 166: end_condition_holds now REFUSES a session whose flag is not True at the hand-over and says so, so a pong game that reaches 11 without setting game_over reads `the end was located at tick N with game_over=False` instead of the old `BROKE at tick N: game_over went False`. The verdict is FAIL either way. So this is an evidence-quality defect today, not a wrong verdict - and a latent false negative for any correct game whose flag lands a tick or more after the eleventh point. ref_pong sets both on the same tick, so nothing in the suite currently exercises it.

The fail-open direction, which is why it needs its own adjudication rather than a copy of 166s patch: making the loop break on the flag instead of the score lets a game that reaches 11 and KEEPS PLAYING pass, provided it eventually sets the flag and no further point lands. Today `stayed = end.passed and max(end_l, end_r) == 11` catches the case where another point lands and not the case where none does. AGENTS.md rule 7: every reason not to count a failure is a channel a bug can widen, so the repair has to say what it costs.

## note 2026-08-27

## note 2026-08-28 (orchestrator) — 166 has MERGED as #205, and the rule that decided it is yours to apply

`tasks/166` is in and its finding is **#205**: *a criterion located the end of a game with one
signal and scored it with another*. Yours is the same defect one signal further out, and 166's
agent filed it rather than widening its own scope, which was right.

**The rule 166 used to decide, and it is the one your ticket's fail-open warning is about.** #190
says a criterion failing on a HIGH count takes the maximum of its candidate signals and one failing
on a LOW count the minimum, because picking the 'better' signal is picking the one that excuses. 166
generalised it: the criterion fails on the **absence** of an end, so `flag OR event` is the union -
the widest reading, hence the excusing one - and the flag won. **Ask the same question of the score.**
A locator that fires EARLIER than the flag widens the window in which a game may leave the flag unset,
which is the direction that excuses; a locator that fires LATER cannot.

**Two things 166 established that you inherit:**

- `end_condition_holds` now REFUSES a session whose flag is not True at the hand-over, so today this
  is an evidence-quality defect rather than a wrong verdict. Your ticket says so; do not let a repair
  quietly turn it into a verdict change without saying which stored verdicts move.
- **166's own first control for that guard was GREEN against a deleted guard**, because the verdict
  and evidence were byte-identical on both paths. It was caught by asking what the row would look
  like with the mechanism gone. Your `done_when` requires a VARIANT and a MUTANT; check each can
  actually distinguish, rather than that each is present.

**Baseline, at the merged head:** `bot_mutants.py` exit 0 at **52 mutants over 45 criteria, 15
variants, 0 pending, 3 session-lock controls, 70 hazards, 0 unmet**; `--selftest` 28 offline checks.
Nothing holds `eval/judge/bot_mutants.py` — branch from `main`, expect no rebase.

`ref_pong` sets both on the same tick, so the suite exercises none of this today. **The bound your
ticket asks for is the deliverable**, not the repair.
