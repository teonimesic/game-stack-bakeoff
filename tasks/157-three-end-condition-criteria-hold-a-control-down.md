---
id: 157
title: Three end-condition criteria hold a control down after the game ends; pong's presses nothing, and that repair was never carried across
status: in_review
priority: 2
refs: eval/judge/bot_mutants.py, eval/judge/bot_arena.py, eval/judge/bot_platformer.py, eval/judge/bot_tetris3d.py, eval/judge/bot_pong.py, tasks/155
done_when: The three criteria establish that PLAY stopped rather than that inputs were refused, the way match.ends does; the matching entries in PENDING_VARIANTS come back with an empty failing set and are promoted into VARIANTS; bot_mutants.py exits 0; and eval/judge/tier2_census.py is re-run against the main checkout's eval/runs with the before and after verdict counts recorded in the ticket.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/40
---

bot_pong._match_ends idles 600 ticks after the win, because a real Rust submission held a game-over card for GAME_OVER_LOCKOUT_TICKS = 96 and then let a control start a new match, and pressing inputs restarted it. The g3 and g4 prompts carry the identical sentence - the game stops accepting play until it is reset - yet bot_arena._death holds fire, aim and move for 300 ticks after death and bot_platformer._hurt holds move_right, jump and attack for 200, and bot_tetris3d._gameover_check holds hard_drop and move_pos_x for 200. Measured 2026-08-25 in eval/judge/bot_mutants.py PENDING_VARIANTS: a fixture that takes a control as a reset after a 96-tick card fails gameover.triggers on ref_arena and ref_platformer. On ref_tetris3d the same fixture PASSES, and the pass is not evidence - the game restarted and stacked out again inside the window, and the score reset to 0 made the frozen test true. Raise the card to 190 ticks on the same fixture and the verdict flips to False, so the verdict is a function of the card length rather than of the game. Blast radius measured: all 6 stored gameover.triggers failures in eval/runs are probe-unusable session failures, none of them this shape, so no stored FALSE turns TRUE - but a stored PASS could turn FALSE and that is a re-scoring event.
