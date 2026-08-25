---
id: 142
title: The game preamble demands a distinct sound per event and the audio section allows two events to share one
status: in_testing
priority: 2
refs: eval/suites/wholegame_prompts.py _preamble and _probe_section, eval/suites/rendered/g1_pong__unity.txt, eval/judge/RUBRIC.md audio criteria, eval/RUNS.md, PR 19
done_when: One of the two clauses is gone or reworded so no rendered game prompt states both, decided against what judge/ actually scores. eval/RUNS.md records the comparability break with the date, since every future game trial is then cross-regime with the 90 stored ones. prompt_guard.py exits 0, prompt_guard_control.py exits 0, and the snapshot at eval/suites/rendered is re-recorded in the same commit. If the answer is that the two clauses are NOT in conflict, say why in the ticket with the criterion that adjudicates it, and close as a negative result.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/27
established_by: PR 27, 5 review rounds, round 5 clean. judge/ adjudicates for the manifest clause in 4 places; audio.distinct floors at half the declared events BECAUSE the task permits sharing. prompt_guard --diff exit 1 on 16 of 24 rendered prompts before re-snapshot, exit 0 after; prompt_guard_control 25/25 rows as declared. RUNS.md TWENTY-FIRST break vs 91 records from census.py. docstat ordinal gate repaired (it reddened on the correct document) and pinned 12 ways where it had none. CI gates+controls+CodeRabbit all pass.
---

Every rendered game prompt states both. The definition of done in _preamble(): 'a distinct sound effect for each of the events listed below'. The audio-manifest section of _probe_section(), 40 lines later: 'Whether two events share a sound, and what the sounds are, is yours to design.' A submission that maps three events to one file satisfies the manifest contract and fails the stated definition of done, and the audio criteria in judge/ decide which of the two the grader believes. Found by CodeRabbit on PR 19 against eval/suites/rendered/g1_pong__unity.txt lines 27-28 and 115-118, which only became reviewable because task 133 checked the rendered prompts in. NOT fixed there: _preamble() and _probe_section() are shared by all four games, 90 stored whole-game trials ran under this wording, and editing either is a regime boundary that task 133 was not scoped for.

## note 2026-08-25

## note 2026-08-25 — the blast radius is smaller than when this was filed, and it is measured

This ticket was written before task 133 landed, when `_preamble()` was shared by everything. It is
not any more: scenes have their own `_scene_preamble()` in `eval/suites/scene_prompts.py`, and the
isolation was verified in both directions at merge by perturbing each preamble in turn —

| edit | moves |
|---|---|
| the **game** preamble | **16 of 16** game prompts, **0 of 8** scene prompts |
| the **scene** preamble | 8 of 8 scene prompts, 0 of 16 game prompts |

So this edit reaches 16 rendered prompts and no scene. It is still a regime boundary against the
**90 stored game trials** and still needs its `eval/RUNS.md` entry — but it does not put scenes on
the far side of one, and the scene suite has no stored trials to be cross-regime with anyway.

## Let `judge/` adjudicate, not taste

The `done_when` says decide *"against what judge/ actually scores"*, and that is the whole ticket.
Read `eval/judge/audio.py` and the audio criteria in `RUBRIC.md` **first**, and let the wording
follow the criterion. Do not pick the clause that reads better.

**Both outcomes close this**, including *"they are not in conflict, and here is the criterion that
adjudicates it"*. A negative result here is worth as much as an edit and costs a regime boundary
less.

## What NOT to do

Do not edit `_preamble()` and re-snapshot in separate commits — `eval/suites/rendered/` is diffed
by CI, and a snapshot that lags its source is a red gate on the next unrelated pull request.

Do not treat the 90 stored trials as re-gradeable afterwards. If the wording changes, trials before
and after are **different populations**, and the `RUNS.md` entry is what stops someone pooling them
a month from now.

## note 2026-08-25

## note 2026-08-25 — DONE. The answer, and what it cost to establish

**`judge/` adjudicates for the manifest clause. The preamble was the clause that was wrong**, and
one word left it: `_preamble()` now reads *"a sound effect for each of the events listed below"*.
PR 27, 5 review rounds, all gates green.

### The adjudication, so nobody re-derives it

Four independent places in `judge/`, and **not one has ever asked for a distinct sound per event**:

| where | what it asks |
|---|---|
| `audio.distinct` | floor `max(2, ceil(n / 2))` — HALF the declared events, with a comment saying why: *"Sharing one sound between two events is explicitly allowed by the task"* |
| `audio.manifest` | an ENTRY per declared event with a `file`. Never a distinct file |
| `audio.triggered` | each event the run FIRED has a cue that exists, decodes, is audible |
| `aspects.py` `AUDIO` (tier 3) | *"five technically distinct clips that are all the same bright square-wave blip is worse than three well-chosen ones"* — it prefers FEWER cues |

`SAME_SOUND_COSINE = 0.9995` carries the same reasoning in a constant. The prompt was the outlier.

### Numbers to reuse rather than re-measure

- **16 rendered game prompts moved, 0 scene prompts.** `prompt_guard.py --diff` exit 1 naming 16
  of 24. Corroborates the earlier note's perturbation test from the other direction.
- **91** stored whole-game trial records — `python3 eval/tools/census.py`, population *stored trial
  records carrying a `game` field*, read 2026-08-25. **The ticket said 90; the producer says 91.**
- `eval/RUNS.md` carries the **TWENTY-FIRST** comparability break. Task-text boundary, not
  grader-side: no stored trial or score changes, re-grading returns what it returned before.

### The gate this tripped, and the general lesson

`docstat.py --sweep` went RED on a CORRECT `eval/RUNS.md`: *"skips second, third, fourth between
first and twentieth"*. `_check_regime_ordinals` alternated `ORDINALS` into its pattern and the
tuple ended at `twentieth`, so `\b`-anchored `FIRST` matched INSIDE `TWENTY-FIRST` and the new
break was filed under `first`.

> **A hand-maintained ordinal list is an enumeration used as a trigger, and it ran out — but the
> damage was not "unknown word", it was WRONG WORD.** The repair is to read the ordinal
> generically and REPORT an unrecognised one, so exhausting the list is loud instead of wrong.
> Extending the list alone would have bought about ten breaks and the same failure.

The check had **no pins at all** before this. It now has 12 and is a function of its input.

### What the review found, and it is worth reading before writing another check here

**5 rounds, 6 findings. Every substantive one was a check answering the WRONG QUESTION, not a
check that could not answer — none reachable by mutating the code under test (rule 15).** Three of
them were in code written during this very ticket:

1. **`startswith("#")` is stricter than the markdown renderer.** CommonMark allows an ATX heading
   3 leading spaces, so an indented duplicate ordinal evaded the collision check while rendering
   as a heading everywhere. `old test sees 2 headings -> duplicate visible: False`; new sees 3 ->
   True. Bound is 3 because a 4th space is an indented code block — pinned in both directions.
2. **Red pins asserting `bool(got)` passed for the wrong reason.** The function has 4 diagnostics,
   one firing whenever the scan finds nothing at all. With the parser mutated to match nothing:
   **4 of 4 red pins PASS**; with per-case fragment assertions, **4 of 4 FAIL**. A red pin must
   name the diagnostic it is about whenever its subject has a catch-all message.
3. **The control imported its expectation from its subject** (rule 12's corollary, task 113
   again). The compound-ordinal variant built its input as `ORDINALS[:22]`. With `ORDINALS`
   regressed to `twentieth`: *20 headings, compound ordinals actually present: **0**, verdict
   GREEN.* **Green for the absence of the thing it existed to test.** The 22 words are now
   written out, with a guard that fails the pin set if the fixture stops reaching
   `twenty-second`.
4. **"unfailable" was false** — my own overstatement in a paragraph written to correct a rubric
   overstatement. `shape_problems` has 3 conditions and only one reads `expected`; `music is
   None`, `sfx is None` and an unparseable manifest still fail `audio.manifest` on g4.

### Two fail-opens found in `audio.py`, filed not fixed

**`tasks/152` — `audio.distinct`'s numerator and denominator range over different sets.** Groups
are counted over EVERY `sfx` entry; the floor comes from the DECLARED events; undeclared entries
do not fail `audio.manifest`. Measured on `g1_pong` (5 events, floor 3):

    5 events over 3 distinct sounds, no extras:        PASS
    5 events ALL sharing 1 clip + 2 unique extras:     PASS
    5 events ALL sharing 1 clip, no extras:            FAIL

**Two junk entries convert a fail into a pass**, on precisely the failure `audio.py`'s docstring
says the criterion exists to catch.

**`tasks/151` — `GAME_EVENTS` has no `g4_platformer` key** while `_G4_EVENTS` declares eight
events. On g4 `expected` is empty, so `audio.manifest` loses its per-event question entirely and
`audio.distinct` floors on `len(sfx_clips)` — the submission's own manifest.

Both are grader changes that can move stored tier-1 gate outcomes, which is why neither was done
here. **`RUBRIC.md` now states both with the reproduction and the ticket ids** rather than
describing behaviour the code does not have.

### Declined, with the evidence, in the PR thread

Synchronising the `README.md` grading table, and re-grading the stored trials offline. No
criterion, threshold, weight or tier moved; README line 204 already says "genuinely distinct **by
decoded content**", which is unchanged and true; adding the floor there would put a threshold on
the front door. Re-grading is forbidden by this ticket and by `eval/judge/AGENTS.md`, and would
return identical scores anyway.

### Needs a finding number

The `docstat.py` ordinal defect: **a gate that ran, reported a defect, and the defect was the
gate's own.** A false positive on a correct document is how a gate gets switched off. Not
allocated here — the orchestrator allocates against `main` at merge.
