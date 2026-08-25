---
id: 143
title: The g3_arena prompt does not say what a zero aim vector does, and the reference fixture silently retains the last one
status: todo
priority: 2
refs: eval/suites/wholegame_prompts.py _G3_INPUTS, eval/judge/fixtures/ref_arena/game.py _update_aim, eval/suites/rendered/g3_arena__godot.txt, eval/RUNS.md, PR 19
done_when: 'Either _G3_INPUTS states what a zero or absent aim vector does and the reference agrees with it, or the ticket records with evidence that no bot input can produce a zero aim so the case is unreachable. If the prompt changes: eval/RUNS.md records the comparability break, prompt_guard.py and prompt_guard_control.py exit 0, judge/bot_mutants.py exits 0, and eval/suites/rendered is re-recorded in the same commit. Either way, state how many stored arena traces contain a zero-aim tick and over what population.'
---

eval/judge/fixtures/ref_arena/game.py::_update_aim keeps the previous orientation when the aim vector has magnitude below 1e-6 - the comment says 'no aim held: keep facing where we last aimed' - and _fire then fires along it. The rendered g3_arena prompt says only 'The aim fields describe a direction; only its orientation matters, not its length'. A submission that reads a zero aim as 'do not fire' or as 'fire along +x' is consistent with everything the prompt says and inconsistent with the reference the play-bot was written against, so the same bot input produces different traces for two honest submissions and the difference is scored. Found by CodeRabbit on PR 19; it read the fixture and confirmed the reference behaviour. NOT fixed in task 133: _G3_INPUTS is a game prompt, 90 stored whole-game trials ran under this wording, and editing it is a regime boundary that ticket was not scoped for. Check first whether any stored arena trace actually contains a zero-aim tick - if the bot never sends one, this is latent rather than active, and that is a different priority.

## note 2026-08-25

## note 2026-08-25 — the census comes FIRST, and it decides whether this is a prompt change at all

The `done_when` already says to check whether any stored arena trace contains a zero-aim tick.
**Do that before touching the prompt**, because it decides which of two very different tickets
this is:

- **No stored trace has one** → the defect is latent. Record the count and the population, state
  what an honest submission could do differently, and the cheapest correct fix may be to make the
  prompt say what the reference does — **with no regime boundary**, because no stored trial's
  behaviour could have depended on it. Say so explicitly rather than leaving it inferred.
- **Some trace has one** → two honest submissions diverged on scored behaviour, and that is a
  finding in its own right before it is a prompt fix.

**Prove the extraction before believing a zero.** A census that returns 0 because it looked in the
wrong field is indistinguishable from one that returns 0 because the case never happened, and this
project has published that mistake more than once (#170, #171). Find a tick whose aim you can state
in advance and show the extractor reports it correctly, then trust the count.

## Two things that landed today and change the ground

**Task 142 is the model for the boundary, and 152 wrote the twenty-second.** If the prompt changes,
copy that shape. Note the ordinal gate now reads compound ordinals correctly — `twenty-first` used
to be filed under `first` — so it will not misfile a twenty-third.

**`audio.py` no longer transcribes the arena's events by hand**: task 152 found `g3_arena` declares
**9** and the grader held 6, and fixed it. That is the same class as this ticket — the prompt and
something downstream disagreeing about the task — so if you find a second copy of the aim
semantics anywhere in `judge/`, it is a defect of the same shape and worth its own ticket.

## What NOT to do

Do not change `ref_arena/game.py` to match a new prompt sentence without checking `bot_mutants.py`
still exits 0. The reference is what the play-bot's criteria were written against; moving it moves
the criteria's meaning, and the mutant suite is what would notice.
