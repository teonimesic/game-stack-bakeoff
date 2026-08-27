---
id: 166
title: The end of a game has two signals and the bots read one to find it and the other to score it
status: in_testing
priority: 3
refs: eval/judge/probe.py, eval/judge/bot_arena.py, eval/judge/bot_tetris3d.py, eval/suites/wholegame_prompts.py, tasks/157
done_when: 'One of the two signals is authoritative and every reader agrees: either `probe.end_condition_holds` takes the end signal as an argument so an event-detected end is not read as "game_over went False", or every caller detects the end from the state flag only and the event branches are deleted. Whichever way it goes, `eval/suites/wholegame_prompts.py` states it in the contract the submissions are held to, a mutant exists for the losing signal, `bot_mutants.py` exits 0, and `tier2_census.py --runs-root <main checkout>/eval/runs` is recorded before and after because the choice can move a stored verdict.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/66
established_by: 'PR #66, 3 review rounds then a clean one, gates+controls+CodeRabbit all pass. bot_mutants.py exit 0 at 52 mutants over 45 criteria, 15 variants, 0 pending, 3 session-lock controls, 70 hazards, 0 unmet, against a 50/45/13/0/3/70/0 baseline re-run at 24b9fb8. tier2_census.py --runs-root <main>/eval/runs byte-identical before and after. Both directions on both fixtures: a correct game announcing the end 6 ticks before entering it went FAIL to PASS; a broken game announcing and never entering stayed FAIL with evidence that now names the real defect. Guard pinned by 3 mutants that each turn --selftest red. Needs a FINDINGS number - see the note.'
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

## note 2026-08-27

## note 2026-08-27 (orchestrator) — the ordering is SETTLED: 166 goes LAST, after 158 and 160

This ticket asked for the order to be decided and written down, and to SHOW the independence
rather than assume it. Shown, from the artifacts:

| ticket | criterion | window it is computed over | truncated by end-detection? |
|---|---|---|---|
| 158 | first-piece timing, `bot_tetris3d` | `for _ in range(20)` at line 189 and `for _ in range(120)` at line 201 | **no** — fixed counts, and `_gameover_check` is a separate criterion built at line 250 from the method at line 607 |
| 160 | `fire.rate_limited`, `bot_arena` | `for _ in range(ticks)` in the block built at line 905 | **no** — no `game_over` break in that block |

The loops that DO break on the end signal are elsewhere in `bot_arena` — the wave/kills
collection at lines 465-472 breaks on `t.state.get('game_over') is True`, the flag alone. So
end-detection does truncate some scoring windows, which is why this ticket is real; it just does
not truncate the two that 158 and 160 repair.

**My first guess was the opposite and the artifacts corrected it.** I expected both to sit
downstream of end-detection by construction. They do not, and the check that settled it was
cheap — grep the loop bound, not the criterion's prose.

**Why last rather than first, given they are independent either way:** 158 and 160 will move
stored verdicts themselves. If this ticket runs first, its before/after census is immediately
overtaken by two more re-scorings and stops isolating anything. Running last, the census measures
the end-detection change alone against a baseline that has stopped moving. Take the before-census
AFTER 158 and 160 have merged, not from a number recorded earlier in this file.

**Not batched, and that is deliberate.** The standing instruction on this project is one agent per
task. 158 and 160 serialise on `bot_mutants.py` regardless, so this costs an extra round and buys
a reviewable branch per repair.

## note 2026-08-27

## note 2026-08-27 (orchestrator) — correction: the cluster is FIVE tickets, not three

The note above says `158`, `160` and `166` serialise on `eval/judge/bot_mutants.py`. That
population was wrong. `grep -l bot_mutants tasks/*.md` over the todo tickets returns **158, 160,
166, 170, 171** — and I wrote an ordering over three of them without running the grep that
enumerates the file's users. This is the failure `AGENTS.md` names in the rule audit: a trigger
written as the instances I happened to have in mind rather than as the property (*edits
`bot_mutants.py`*), and it was committed by someone who had just re-read that rule.

**What survives the correction:** 158 and 160 are independent of this ticket, shown from their
loop bounds, and that showing stands. **What does not:** "158, then 160, then 166" is not a
complete order, because two more tickets queue on the same file.

**The independence check has NOT been run for 170 and 171, and must not be assumed from the
other two.** 170 is `multiplier.falls` in `bot_arena`, the same module whose wave/kills loop at
lines 465-472 does break on `game_over` — so it is the one cluster member with a prior reason to
be entangled with end-detection, and it needs the loop-bound check run against it specifically
before it is ordered. 171 is `rally.counts` in `bot_pong`, which this ticket's own filing note
already called probably independent.

**Standing order until that check is run:** 158 first (in flight), then 160, then 170 and 171 in
either order, and this ticket **last** — the before/after census argument applies against all four,
not just two. Whoever runs 170's check should record the result here and fix the order if it comes
out the other way.

## note 2026-08-27

## note 2026-08-27 (tasks/170) — the loop-bound check for 170, run rather than inherited

`tasks/170`'s ticket asked for this specifically, because `bot_arena` is the module whose
wave/kills collection breaks on `t.state.get('game_over') is True`. Read from the artifacts at
`4258c135e`, before 170's repair:

| ticket | criterion | window it is computed over | truncated by end-detection? |
|---|---|---|---|
| 170 | `multiplier.falls`, `bot_arena` | `for _ in range(6000)` at line 1065 and `for _ in range(4000)` at line 1086 | **yes, both** — each carries `if t.state.get("game_over") is True: break` |

So the answer is the opposite of 158's and 160's: this window **is** truncated by end-detection.
**It does not re-open the order, and the reason is which SIGNAL it reads.** Both loops break on
the **state flag alone**, never on a `game_over` event — which is the signal this ticket says
every bot already *scores* from. The two readings the loops could take under either resolution:

- *flag only everywhere, event branches deleted* — these loops are already that. Unchanged.
- *`end_condition_holds` takes the end signal as an argument, callers keep flag-or-event* — the
  loops would gain an event branch, and it can only make them exit EARLIER on a game that raises
  the event and leaves the flag `False`. On such a game the criterion today runs the full 4000
  idle ticks in a dead simulation and returns *"the player was never hit"*; with the branch it
  returns the same failure sooner. **The verdict is a fail either way**, so no stored `g3_arena`
  verdict can move on that account.

170 has since landed and its two new loop bounds are the same shape: the 8-tick window it opens
after the damage tick also breaks on the flag alone. **This ticket stays last**, and 170's own
re-scoring is already recorded in its before/after census.

## note 2026-08-27

## note 2026-08-27 (orchestrator) — every ticket you were ordered behind has MERGED; you are last, as decided

The ordering recorded in this file has run its course: **158, 160, 170, 171 and 173 are all merged.**
Nothing holds `eval/judge/bot_mutants.py`. Branch from `main` and expect no rebase.

**The independence check this ticket asked for was run for each of them, and the answers differ** —
which is why they went first:

| ticket | window | truncated by end-detection? |
|---|---|---|
| 158 | `range(20)`, `range(120)` in `bot_tetris3d` | no - fixed counts |
| 160 | `range(ticks)` in `bot_arena` | no - fixed count |
| 170 | `multiplier.falls` | **YES**, both loops (lines 1065, 1086) |

170's answer was the one that could have re-opened the order and did not: **both of its loops break on
the state flag alone, never on a `game_over` event**, so adding the event branch could only make them
exit earlier on a game whose verdict is a fail either way. That is measured and recorded, not assumed
— and it is the single most useful input you have, because it tells you the event branch is currently
*unreachable* in the place it would most plausibly matter.

**Your baseline, re-run by the orchestrator at the merged head:** `bot_mutants.py` exit 0 at **50
mutants pinned in both directions over 45 criteria, 13 variants, 0 pending, 3 session-lock controls,
70 hazards, 0 unmet**. State the new figures rather than assuming only your own rows moved — three
tickets in a row found the summary line's populations had drifted.

**What the five merged tickets established that bears on your decision**, because you are deciding
what a criterion measures for every g2, g3 and g4 submission:

- **#190**: a criterion that fails on a HIGH count must take the MAXIMUM of its candidate signals;
  one that fails on a LOW count the minimum. Picking the 'better' signal is picking the one that
  excuses. You have two signals for one event — that rule is directly yours.
- **#195**: a criterion naming two events has a third thing it never states, the interval between
  them, and everything in it is attributed to the second event.
- **#200**: the same evidence string read PASS under one verdict and FAIL under the other, three times
  this week. **A stored evidence string is not a check on the verdict beside it.**

**Say what must still FAIL after your change**, and check it does. That clause is what the last three
tickets in this cluster were missing when they were written.

## note 2026-08-27

## The choice, and why the other branch of `done_when` was not taken

**The state flag wins; the `game_over` event branches are deleted.** Three reasons, in the
order they decided it:

1. The prompt already defined the field as the CONDITION and the event as a thing that
   happened on a tick, and `probe.end_condition_holds` — the one shared end-condition
   policy for all 4 bots since `tasks/157` — already scored the field.
2. **2 of the 4 bots already resolved it that way.** `bot_pong` and `bot_platformer`
   never read the event. Only `bot_arena._death` and `bot_tetris3d._gameover_check` did,
   the latter in **2** places (the post-drop history scan and the no-falling-piece
   branch), which the ticket counted as one.
3. **#190.** `flag OR event` is the union — the reading that locates an end soonest. The
   criterion fails on the ABSENCE of an end, so the union is the signal that excuses.

The other branch — passing the end signal into `end_condition_holds` — would have kept
two readings alive and made every future caller choose between them. What landed instead
makes the function REFUSE the wrong one.

## What was measured, before and after, on both fixtures

A scratch harness drove `bot_arena.BOT._death` and `bot_tetris3d.BOT._gameover_check`
against patched fixture copies. The before-column was read at `24b9fb8`, before any edit.

| subject | before | after |
|---|---|---|
| `ref_arena` untouched | PASS | PASS |
| `ref_arena`, announced then entered 6 ticks later — CORRECT | **FAIL** `BROKE at tick 537: game_over went False with nothing pressed` | **PASS** |
| `ref_arena`, announced and never entered — BROKEN | FAIL, same sentence | FAIL `the player never died in 9001 idle ticks (hp 0.0)` |
| `ref_tetris3d` untouched | PASS | PASS |
| `ref_tetris3d`, announced then entered 6 ticks later | **FAIL** `BROKE at tick 54: …` | **PASS** |
| `ref_tetris3d`, announced and never entered | FAIL, same sentence | FAIL `stacked into one corner for 169 ticks without the game ending; game_over=False` |

**The verdict on a BROKEN game never moved, and that is the part worth knowing.** An
event-only game failed before and fails now. What the defect cost was a **false negative
of the second kind** — rows 2 and 5, a correct game the criterion could not pass — and an
evidence string that described a different defect from the one present. Both fixtures now
carry a `VARIANT` (must pass) and a `MUTANT` (must fail).

**6 ticks, and the length is load-bearing.** At 1 tick both bots pass either way, because
`end_condition_holds` reads its first idle tick AFTER the one it was handed.

## The guard on `end_condition_holds`, and the control that could not fail

`end_condition_holds` now reads `s.last.state["game_over"]` first and returns a failed
`EndCondition` naming what it found, driving neither window. **The branch is unreachable
from any fixture** — all 4 callers locate on the flag — so it is pinned offline by
`EndTapeSession` in `--selftest`.

**The first version of that control was green against a deleted guard.** It compared the
verdict and the evidence string, and both are byte-identical either way: `detail()` reads
`flag_at_entry`, which is recorded on both paths. The row now carries **ticks driven** — 0
on the refusal, 8 when the windows run — and 3 mutants of the guard turn `--selftest` red:
the early return deleted, `held_while_idle` no longer reading `flag_at_entry`, and the
guard testing falsiness so `None` slips through. Pristine is exit 0.

**`idle_broke_at` is None on the refusal path on purpose.** Setting it to the entry tick
would have made `held_while_idle` False by that route instead, leaving
`flag_at_entry is True and …` unkillable by any mutant — dead weight that reads as a
defence.

## `Hazard.covered_by` is a tuple now

One criterion can have more than one constructed answer while the registry keeps one entry
per criterion. `gameover.triggers` is mis-scored by a closing card AND by a game that
announces the end before entering it, and the single-label field made the second subject
unclaimable — `hazard_gate` reports it as *claimed by no criterion*. 21 call sites moved
from `_V_X` to `(_V_X,)`, and 2 selftest rows cover the ways a second entry goes wrong.

## The FINDING this produced, for the orchestrator to number

**A criterion can locate a condition with one signal and score it with another, and every
verdict it returns is still right.** `gameover.triggers` on 2 of 4 bots read
`flag OR event` to find the end and the flag alone to judge it. On every game either
signal can produce, the two readings return the SAME verdict — the disagreement is
entirely in the evidence, and the evidence named a defect (`game_over went False`) that
was not the one present (`game_over was never True`). The cost is not a wrong score; it is
a **false negative on a game neither reading was designed for** — a correct game whose
flag lands a few ticks after its event, which FAILED on both fixtures and now passes.

> A split between how a check LOCATES its subject and how it SCORES it is invisible in
> every verdict and visible only in the evidence, so nothing that reads verdicts can find
> it. #200 said a stored evidence string is not a check on the verdict beside it. This is
> the converse and it is worse: **a verdict is not a check on the evidence beside it
> either, and a criterion can be right for a reason it did not measure.**

Measured: 6 subjects across 2 fixtures, 0 verdict changes on the 4 that are broken or
untouched, 2 verdict changes on the 2 correct games nothing had constructed before.

## What could NOT be established

**Whether any stored submission carries this shape.** Not answerable from
`eval/runs/**`: no probe trace is kept, so what a submission published on its end tick
cannot be read back. The 2 fixtures are the whole evidence and `eval/RUNS.md` says so
rather than implying a corpus measurement.

## Filed: `tasks/191`

`bot_pong._match_ends` locates the end from the **SCORE** (`max(score) >= 11`) and hands
the session to `end_condition_holds`, which scores the flag. Same defect shape, a third
signal. Out of scope here because the obvious repair is **fail-open**: breaking on the flag
lets a game that reaches 11 and keeps playing pass, provided no further point lands. The
guard added here already makes pong's evidence honest; the verdict is FAIL either way.

## What the review found that the measurements could not

3 rounds, 5 comments, 2 of them real defects in prose I had written:

- **The contract paragraph contradicted itself** — the event *"announces the tick the game
  ended on"*, the field is what *"the game has ended"* means, and the two *"need not be the
  same tick"*. It also bound the field to *"the tick the game stops accepting play"*, which
  made the new variants non-conforming under my own wording.
- **The replacement then over-reached** — *"nothing else establishes that"* is FALSE on g4,
  where `victory` beside `stage_clear` is a second terminal condition, and
  `_probe_section()` renders into all 4 game prompts. The shipped claim is about the
  field/event DISTINCTION, true of all 4 pairs in the suite and specifying none of their
  triggers.
- **`eval/RUNS.md` cited a command that could not run** — `<the commit before>` is not a
  revision and the pathspec swept in `index.json`. Replaced with a corpus measurement
  needing no revision, because the repository squash-merges and any SHA written there would
  resolve to the WRONG commit rather than to none.

**Declined, with the evidence:** reshaping the 2 new variants. One remedy offered makes the
fixture identical to the reference in the property under test; the other swaps one
incidental difference for another. A closing flourish that gates the simulation is the same
shape as the 4 opening-card variants this suite already declares correct.

**Declined after testing the reason and finding it wrong:** renaming the RUNS.md heading out
of the series format. I expected `docstat.py --sweep` to go red on the suggested heading and
planted it to check — **exit 0, `regime ordinals: 40 known` unchanged.** No gate objects. What
survived is that other documents cite these sections by heading and the suggested title drops
both the ordinal and the measured result. The *other* half of that comment was right and was
acted on: the `Check the ordinal before citing it` boilerplate is gone from this section.

## A hazard for whoever runs a control next

`eval/tools/skill_layout_control.py` plants broken skill layouts and restores them with
`git checkout -- .claude/skills`, which reads the **index**. A `git add -A` running in another
shell during that window makes the restore fail with *pathspec did not match any file(s) known
to git*, and it leaves `.claude/skills` deleted — the symlink `AGENTS.md` calls load-bearing.
Its own lock guards against a second copy of itself and cannot see a concurrent index write.
Recovered with `git checkout HEAD -- .claude/skills`; re-run clean at 5/5.
