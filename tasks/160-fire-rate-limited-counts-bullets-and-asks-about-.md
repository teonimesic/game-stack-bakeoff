---
id: 160
title: fire.rate_limited counts BULLETS and asks about SHOTS, and prints the right number beside the wrong verdict
status: todo
priority: 2
refs: eval/judge/bot_arena.py, eval/judge/bot_mutants.py, tasks/155
done_when: The criterion counts fire events rather than bullet ids, or states in bot_arena.py why a bullet count is the right proxy and what a spread weapon should score; the ref_arena spread entry in PENDING_VARIANTS comes back with an empty failing set and is promoted into VARIANTS; bot_mutants.py exits 0; and the stored g3_arena verdicts are re-derived with eval/judge/tier2_census.py against the main checkout's eval/runs with before and after counts recorded here.
---

The criterion's own question is: is there a minimum interval between shots rather than one bullet per tick. bot_arena._firing_in scores it as 0 less than n_x and n_x at most 80, where n_x is the number of distinct BULLET ids created over 120 ticks of held fire. A weapon that fires a spread puts several bullets in the world per shot, which is an ordinary design for a game the g3 prompt asks to make loud, fast and readable at a glance. Measured 2026-08-25 in eval/judge/bot_mutants.py PENDING_VARIANTS: a ref_arena fixture firing a three-round spread on a 4-tick cooldown fails with 90 bullets from 120 ticks of held fire (30 fire events). 30 shots in 120 ticks IS a rate limit, and the criterion prints that number in its own evidence string beside a verdict computed from the other one.

## note 2026-08-27

## note 2026-08-27 (orchestrator) — third in line; 158 lands before you, 166 after

`158`, `160` and `166` serialise on `eval/judge/bot_mutants.py`. Order settled as **158, then 160,
then 166**; the derivation is in `tasks/166`. Rebase on `main` after 158 merges — your conflict
with it will be in the mutant registry, where both tickets add entries and both should be kept.

**166 does not reach you.** It says end-detection is read inconsistently (flag-or-event to locate
the end, flag alone to score it). `fire.rate_limited` is built in the block at `bot_arena.py` line
905 and counts over `for _ in range(ticks)` — a fixed window with no `game_over` break — so which
end signal wins cannot move your count. The loops that DO break on the flag are the wave/kills
collection at lines 465-472, which is not yours.

## note 2026-08-27

## note 2026-08-27 (orchestrator) — 158 has MERGED; branch from main and there is no rebase to do

The note above told you to rebase on `main` after 158 lands and expect a conflict in the mutant
registry. 158 merged as of now, so you branch from a `main` that already contains it and the
conflict does not arise. Ignore that paragraph.

**What 158 established that bears on your work**, because it is the same file and the same suite:

- `eval/judge/bot_mutants.py` is at **43 criteria pinned in both directions, 10 variants, 1
  pending, 3 session-lock controls, 70 criteria with a recorded hazard, 0 unmet**, exit 0. That is
  the baseline your change moves; re-run it and state the new figures rather than assuming only
  your own rows moved.
- 158's ticket said two opening budgets and there were **four** — `_play_for_a_clear` and
  `_gameover_check` each open a *fresh* `ProbeSession`, so a title card gates them from their own
  tick 0. **`bot_arena` opens 9 fresh sessions and nobody has measured whether they have the same
  defect**; that is `tasks/173`, filed rather than assumed, and it is NOT yours. If you trip over
  it while working `fire.rate_limited`, record what you saw in `tasks/173` and carry on.
- 158 added mutants for two criteria that had none, on the reasoning that **widening a limit can
  only make a criterion easier to pass**, so a criterion that had become incapable of failing would
  read as a clean run. If your repair changes what `fire.rate_limited` accepts, check it still has
  a mutant that can drive it red — `bot_mutants.py --hazards` is the producer.

Your own ticket's trap is stated in its body: the criterion counts BULLETS and asks about SHOTS,
and prints the right number beside the wrong verdict. A repair that changes the printed number
without changing what is counted leaves the verdict wrong and the evidence newly convincing.
