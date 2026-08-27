---
name: add-game
description: "Add a game or scene task, or a play-bot criterion, to the eval suite: prompt rules that keep the comparison fair, criteria written as experiments rather than observations, and the mandatory mutant per criterion."
when_to_use: "Writing or editing a task prompt, game or scene; designing probe state and events; writing or changing a bot criterion; a criterion is producing false negatives. Trigger phrases: add a game, add a scene, new task, write a criterion, the bot is failing good submissions, add a mutant."
argument-hint: [game-id]
---

# Adding a task or a criterion

Authoritative files: `eval/suites/wholegame_prompts.py` (its module docstring holds the
prompt rules), `eval/suites/scene_prompts.py`, `eval/SCENES.md`, `eval/judge/RUBRIC.md`,
`eval/G4-PLATFORMER.md` (a worked design). **If any of them disagrees with this skill, it
wins and this skill is the bug.**

**2 task classes, 2 modules.** Games are in `eval/suites/wholegame_prompts.py`; scenes —
timed sequences with no player — are in `eval/suites/scene_prompts.py`. Each class has its
own preamble, so an edit for one cannot reach the other. Everything below applies to both.

## The prompt

Three rules, each of which cost a run when broken:

1. **Semantically identical across stacks, natively worded.** Byte-identical prompts are
   not neutral — they end up written in one stack's vocabulary. Same behaviour, same
   acceptance criteria, each in its own stack's nouns.
2. **No type widths.** `u32` has no C# equivalent; say "a whole number count".
3. **The prompt is not the rubric.** It says what to build and what "done" means
   functionally. It must not name criteria, thresholds, or weights. Writing "make sure
   line clears work well" because the rubric checks line clears is teaching to the test.
   For scenes this is **gated**, not merely stated — see the guard below.

Legitimately in the prompt: the probe *contract*. Field and event names are functional
spec; thresholds are not.

**A preamble is shared by every task in its class.** Editing it for one task changes all
of them — correctly where aimed, invisibly everywhere else. Before any comparison, **diff
the rendered prompts, not the source that renders them**; the stored `artifacts/<tid>/
prompt.txt` is what the agent actually saw.

## Assert the prompt structure — run the tool, do not eyeball it

```
cd eval
python3 tools/prompt_guard.py                       # all three assertions; exit 1 on violation
python3 tools/prompt_guard.py --identity            # the byte-identical share, per task
python3 tools/prompt_guard.py --snapshot DIR        # record what a run's agents received
python3 tools/prompt_guard.py --diff DIR            # what renders NOW vs that snapshot
python3 tools/prompt_guard_control.py               # can the guard fail? can it still pass?
```

The prompts are **one template per task rendered per stack** — `gN_*(stack)` and
`sN_*(stack)` functions over vocabulary dicts, no per-stack copies. Most of every prompt is
byte-identical across the stacks and the differences are only "where things go" and "how to
make sound"; the identity is structural, not maintained by hand. **Never quote a share from
memory or from here — run `--identity` and quote its number with its unit.** It prints
lines and characters separately because they differ by 6 points, and `eval/SCENES.md`
carries the current table.

3 ways that structure breaks silently. All 3 are asserted:

**Stack axis — an engine name in a task body.** `Bevy` or `AudioStreamPlayer` in the task's
own text instead of a vocabulary dict hands one stack its own vocabulary. Protects the
comparison itself: a prompt written in one stack's words is not the same task for the other
3.

**Task axis — a preamble is shared by every task in its class.** An edit aimed at one task
reaches all of them, correctly where aimed and invisibly everywhere else. Protects
single-variable experiments (#41).

**Rubric axis — a scene prompt stating a scene criterion.** `eval/SCENES.md` is for us; a
prompt repeating one of its criteria, thresholds or tolerances is teaching to the test.
Protects the discriminating power of every scene criterion. The guard greps the **rendered**
scene prompts, because a leak arriving through a vocabulary dict leaves the body looking
clean.

> **Snapshot the rendered prompts at the start of every run, and diff before any
> comparison.** Diff the rendered inputs, not the source that renders them — a shared
> preamble leaves the source looking untouched while every task's prompt has changed.
> `eval/suites/rendered/` is the checked-in snapshot and `gates.yml` diffs against it, so
> **a deliberate prompt edit must re-record it in the same commit**:
> `python3 eval/tools/prompt_guard.py --snapshot eval/suites/rendered`.

All 3 are pinned in both directions by `tools/prompt_guard_control.py`, which applies one
edit per row to a temp copy of the guard and its inputs and compares against what the row
declared in advance. Run it after any change to the guard; a red row there is the guard
losing an ability, not a prompt problem.

A guard that only ever prints "ok" has not been shown to be capable of anything else — and
a guard that reddens on correct input is one somebody switches off. A term that fires on
the functional contract comes off the rubric list; `DECISIONS.md` records how that choice
is made.

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
promote on reasoning alone — and check what promoting it would DO before doing the work:
`judge/tier2_census.py --runs-root <main checkout>/eval/runs` prints each diagnostic's
stored values per group, and one that is single-valued moves every score in its group by
the same amount and separates nothing. All three current diagnostics are in that state
(#128).

## Ask what the criterion could ever separate, before writing it

`judge/tier2_census.py` is also the check on a NEW scored criterion, and it is free.
Tier 2 currently returns one value across every measurable trial in 5 of 11 (run, game) groups -
run it rather than quoting that, since the corpus moves - and four criteria built from real
requirements the g4 prompt states passed 8 of 8 (#128) — so the default outcome of adding
one is a longer rubric that ranks exactly as much as before. **A criterion that everything
passes raises the denominator and lowers nothing.** Say, in advance, which stored
submission you expect it to fail and why; if you cannot name one, you are adding
denominator.

## Before it ships

- `python3 judge/bot_mutants.py` — exit 0
- `python3 judge/verify_blind.py` — exit 0, unpiped; criterion ids must not leak into any
  prompt
- The reference fixture's own `just verify` — exit 0
- Register in `evaluate.py` and `RUBRIC.md`
- Calibrate cost with **two trials in different cells**, and quote the range, not a point
  estimate — within-cell spread has been measured at 1.6×
