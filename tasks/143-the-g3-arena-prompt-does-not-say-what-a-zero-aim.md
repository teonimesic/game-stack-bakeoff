---
id: 143
title: The g3_arena prompt does not say what a zero aim vector does, and the reference fixture silently retains the last one
status: todo
priority: 2
refs: eval/suites/wholegame_prompts.py _G3_INPUTS, eval/judge/fixtures/ref_arena/game.py _update_aim, eval/suites/rendered/g3_arena__godot.txt, eval/RUNS.md, PR 19
done_when: 'Either _G3_INPUTS states what a zero or absent aim vector does and the reference agrees with it, or the ticket records with evidence that no bot input can produce a zero aim so the case is unreachable. If the prompt changes: eval/RUNS.md records the comparability break, prompt_guard.py and prompt_guard_control.py exit 0, judge/bot_mutants.py exits 0, and eval/suites/rendered is re-recorded in the same commit. Either way, state how many stored arena traces contain a zero-aim tick and over what population.'
---

eval/judge/fixtures/ref_arena/game.py::_update_aim keeps the previous orientation when the aim vector has magnitude below 1e-6 - the comment says 'no aim held: keep facing where we last aimed' - and _fire then fires along it. The rendered g3_arena prompt says only 'The aim fields describe a direction; only its orientation matters, not its length'. A submission that reads a zero aim as 'do not fire' or as 'fire along +x' is consistent with everything the prompt says and inconsistent with the reference the play-bot was written against, so the same bot input produces different traces for two honest submissions and the difference is scored. Found by CodeRabbit on PR 19; it read the fixture and confirmed the reference behaviour. NOT fixed in task 133: _G3_INPUTS is a game prompt, 90 stored whole-game trials ran under this wording, and editing it is a regime boundary that ticket was not scoped for. Check first whether any stored arena trace actually contains a zero-aim tick - if the bot never sends one, this is latent rather than active, and that is a different priority.
