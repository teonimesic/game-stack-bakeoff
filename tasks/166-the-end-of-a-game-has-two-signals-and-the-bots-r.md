---
id: 166
title: The end of a game has two signals and the bots read one to find it and the other to score it
status: todo
priority: 3
refs: eval/judge/probe.py, eval/judge/bot_arena.py, eval/judge/bot_tetris3d.py, eval/suites/wholegame_prompts.py, tasks/157
done_when: 'One of the two signals is authoritative and every reader agrees: either `probe.end_condition_holds` takes the end signal as an argument so an event-detected end is not read as "game_over went False", or every caller detects the end from the state flag only and the event branches are deleted. Whichever way it goes, `eval/suites/wholegame_prompts.py` states it in the contract the submissions are held to, a mutant exists for the losing signal, `bot_mutants.py` exits 0, and `tier2_census.py --runs-root <main checkout>/eval/runs` is recorded before and after because the choice can move a stored verdict.'
---

Two bots detect the end by EITHER the state flag or a game_over EVENT - bot_arena._death and bot_tetris3d._gameover_check both break on `t.state.get("game_over") is True or "game_over" in t.events` - and then every verdict that follows is computed from the state flag alone. A submission that raises the event and leaves the flag False is therefore located as ended and then scored as not ended, on both the pre-repair criterion (`still_over = s.last.state.get("game_over") is True`) and the two-phase one that replaced it in tasks/157, which reports `BROKE at tick N: game_over went False with nothing pressed`. It is pre-existing and neither version introduced it. The event branch was itself paid for: bot_tetris3d carries a comment saying the no-falling-piece path failed two correct submissions until it started reading the event. So the two signals disagree about which one means "over", and the answer decides what the criterion measures for every g2, g3 and g4 submission. Raised by CodeRabbit on PR #40, declined there because settling it is a re-scoring event and belongs with its own tier2_census.py before-and-after rather than inside a repair to a different defect.

## note 2026-08-25

## note 2026-08-25 (orchestrator) — read this BEFORE 158, 159 and 160 are worked

This ticket says the bots **locate** the end of a game from the state flag *or* a `game_over` event
and **score** it from the flag alone. Three sibling tickets repair criteria that sit on top of that:

| ticket | criterion | bot |
|---|---|---|
| 158 | first-piece timing | `bot_tetris3d` |
| 159 | `rally.counts` | `bot_pong` |
| 160 | `fire.rate_limited` | `bot_arena` |

**If the two-signal defect is real, it may change what 158 and 160 should do**, because both touch
games whose end-detection this ticket says is inconsistent. 159 is pong and probably independent.

So this ticket is either **first or last, and which is a judgement to make and write down** — not
something to discover by working them in filing order. Settling it re-scores every g2/g3/g4
submission, which is the more expensive direction, so *last* is defensible if 158 and 160 can be
shown not to depend on it. **Show that rather than assuming it.**

## The queue serialises on one file, which is why the order matters

`158`, `159`, `160` and `166` all edit `eval/judge/bot_mutants.py`. They cannot run concurrently,
so this is four sequential rounds however they are ordered — and the ordering decision is free now
and expensive later.

**Batching is on the table.** Tasks 151 and 152 were merged into one branch for exactly this
reason and it worked; the argument there was that the second fix depended on the first's defect.
If two of these four share that property, say so and take both.
