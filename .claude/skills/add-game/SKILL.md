---
name: add-game
description: "Add a game task or a play-bot criterion to the eval suite: prompt rules that keep the comparison fair, criteria written as experiments rather than observations, and the mandatory mutant per criterion."
when_to_use: "Writing or editing a task prompt; designing probe state and events; writing or changing a bot criterion; a criterion is producing false negatives. Trigger phrases: add a game, new task, write a criterion, the bot is failing good submissions, add a mutant."
argument-hint: [game-id]
---

# Adding a game or a criterion

Authoritative references: `eval/suites/wholegame_prompts.py` (its module docstring holds
the prompt rules), `eval/judge/RUBRIC.md`, `eval/G4-PLATFORMER.md` (a worked design).

## The prompt

Three rules, each of which cost a run when broken:

1. **Semantically identical across stacks, natively worded.** Byte-identical prompts are
   not neutral — they end up written in one stack's vocabulary. Same behaviour, same
   acceptance criteria, each in its own stack's nouns.
2. **No type widths.** `u32` has no C# equivalent; say "a whole number count".
3. **The prompt is not the rubric.** It says what to build and what "done" means
   functionally. It must not name criteria, thresholds, or weights. Writing "make sure
   line clears work well" because the rubric checks line clears is teaching to the test.

Legitimately in the prompt: the probe *contract*. Field and event names are functional
spec; thresholds are not.

**`_preamble()` is shared by every game.** Editing it for one task changes all of them —
correctly where aimed, invisibly everywhere else. Before any comparison, **diff the
rendered prompts, not the source that renders them**; the stored `artifacts/<tid>/
prompt.txt` is what the agent actually saw.

## Assert the prompt structure — run the tool, do not eyeball it

```
cd eval
python3 tools/prompt_guard.py                  # both assertions; exit 1 on violation
python3 tools/prompt_guard.py --snapshot DIR   # record what a run's agents received
python3 tools/prompt_guard.py --diff DIR       # what renders NOW vs that snapshot
```

The prompts are **one template per game rendered per stack** — four `gN_*(stack)` functions,
seven vocabulary dicts, no per-stack copies. Measured: 97–98% of every prompt is
byte-identical across all four stacks, and the differences are only "where things go" and
"how to make sound". The identity is structural, not maintained by hand.

Two ways that structure breaks silently, one per axis. Both are asserted:

**Stack axis — an engine name in a game body.** Writing `Bevy` or `AudioStreamPlayer` into
the game's own text instead of a vocabulary dict hands one stack its own vocabulary. The
first bake-off did this with byte-identical prompts and cost a full run; turn counts
reversed after the fix (rust 32→49, ts 50→43).

**Game axis — `_preamble()` is shared by every game.** An edit aimed at one game reaches
all of them, correctly where aimed and invisibly everywhere else. A mouse-aiming clause
written for the 3D arena landed in Pong, Tetris and the platformer, and would have
contaminated the one experiment whose entire design was a single variable (#41).

> **Snapshot the rendered prompts at the start of every run, and diff before any
> comparison.** Diff the rendered inputs, not the source that renders them — a shared
> preamble leaves the source looking untouched while every game's prompt has changed.

Both are pinned in both directions. If you change the tool, re-run the controls:

```
# A: plant an engine name in a game body  -> exit 1, names the game and the word
# B: snapshot, edit _preamble(), --diff   -> exit 1, reports all 16 rendered prompts
```

A guard that only ever prints "ok" has not been shown to be capable of anything else.

## Criteria are experiments, not observations

This is the single design error that cost fifteen criteria across three matrices.

> A criterion must **establish** the condition it tests, never wait to observe one.

Each of these named one thing and measured another:

| criterion | named | actually measured |
|---|---|---|
| `ball.wall_bounce` | does the ball bounce off walls | whether the serve angle happened to reach a wall |
| `move.translates` | does a piece slide | whether the piece happened to have room |
| `enemies.chase` | do enemies approach | which enemy happened to be nearest at two instants |
| `determinism.*` | is the run reproducible | whether a second process could open the project |

Drive a paddle to *create* the bounce. Choose the direction with room. Follow one enemy
by id and treat its destruction as proof it arrived. Serialise the sessions.

Assert the property in the criterion's own name — and note that this rule is a slogan you
can satisfy in your head while breaking it in the code. `player.falls` accepted
"`grounded` became false", which a zero-gravity character hanging in mid-air satisfies.
The reference, 19 fixture tests and a 19/19 run were all green with that in place.

## Every criterion needs a mutant

**Non-negotiable.** Add it to `judge/bot_mutants.py`: remove the behaviour the criterion
names, and confirm that specific criterion goes red.

- Rewriting an observation into an experiment makes it **easier to pass by construction**.
  Without a mutant you have replaced a false negative with a criterion that cannot fail,
  which looks like success.
- A mutant proves a criterion *can* fail. It cannot prove the criterion passes for the
  right reason — for that, read the evidence string of a **passing** run.

Run `python3 judge/bot_mutants.py` unpiped and read its own exit code.

## A criterion the bot cannot pass on correct work

Make it **diagnostic-only**, reported and unscored — as `layer.clears` and
`stage.completes` are. Scoring a criterion the instrument cannot satisfy manufactures a
false negative for every honest submission, and once averaged that is indistinguishable
from a real failure.

To promote it back, strengthen the bot until it passes against the reference. Never
promote on reasoning alone.

## Before it ships

- `python3 judge/bot_mutants.py` — exit 0
- `python3 judge/verify_blind.py` — exit 0, unpiped; criterion ids must not leak into any
  prompt
- The reference fixture's own `just verify` — exit 0
- Register in `evaluate.py` and `RUBRIC.md`
- Calibrate cost with **two trials in different cells**, and quote the range, not a point
  estimate — within-cell spread has been measured at 1.6×
