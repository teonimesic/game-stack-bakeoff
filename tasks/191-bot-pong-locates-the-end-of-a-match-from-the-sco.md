---
id: 191
title: bot_pong locates the end of a match from the SCORE, and end_condition_holds scores the flag
status: todo
priority: 3
refs: eval/judge/bot_pong.py, eval/judge/probe.py, eval/judge/bot_mutants.py, tasks/166
done_when: 'bot_pong._match_ends either locates the end of a match from `state.game_over` or states in a HAZARDS entry why the score is the right locator for this game and the flag is not. Whichever way it goes: a VARIANT on ref_pong where the flag lands some ticks after the eleventh point must PASS, a MUTANT where the match reaches 11 and the flag never rises must FAIL, and the widening the ticket describes - a game that reaches 11, plays on, and sets the flag later - must be stated with a measured bound on how long it can play. `bot_mutants.py` exits 0 and the summary line is quoted with all its populations.'
---

tasks/166 made the state flag the authoritative end signal and deleted the game_over EVENT branches from bot_arena._death and bot_tetris3d._gameover_check. bot_pong is the caller it did not change, because it reads neither of those two signals: _match_ends breaks its 12,000-tick drive on max(score) >= 11 and then hands the session straight to probe.end_condition_holds, which scores state.game_over. That is the same defect shape one signal further out - a THIRD signal locates the end and the flag scores it - and 166 left it alone on purpose, because the fix has a fail-open direction its scope did not license.

What is already true after 166: end_condition_holds now REFUSES a session whose flag is not True at the hand-over and says so, so a pong game that reaches 11 without setting game_over reads `the end was located at tick N with game_over=False` instead of the old `BROKE at tick N: game_over went False`. The verdict is FAIL either way. So this is an evidence-quality defect today, not a wrong verdict - and a latent false negative for any correct game whose flag lands a tick or more after the eleventh point. ref_pong sets both on the same tick, so nothing in the suite currently exercises it.

The fail-open direction, which is why it needs its own adjudication rather than a copy of 166s patch: making the loop break on the flag instead of the score lets a game that reaches 11 and KEEPS PLAYING pass, provided it eventually sets the flag and no further point lands. Today `stayed = end.passed and max(end_l, end_r) == 11` catches the case where another point lands and not the case where none does. AGENTS.md rule 7: every reason not to count a failure is a channel a bug can widen, so the repair has to say what it costs.
