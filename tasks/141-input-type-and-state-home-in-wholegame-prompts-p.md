---
id: 141
title: INPUT_TYPE and STATE_HOME in wholegame_prompts.py are defined and referenced by nothing
status: todo
priority: 3
refs: eval/suites/wholegame_prompts.py, eval/tools/prompt_guard.py --identity, tasks/133
done_when: Either both dicts are gone and prompt_guard.py --identity reports 6 in scope and 6 referenced for wholegame_prompts, or each is referenced by at least one task template and --identity reports no DEFINED AND UNUSED row. Either way prompt_guard.py exits 0, prompt_guard_control.py exits 0, and prompt_guard.py --diff eval/suites/rendered is re-recorded in the same commit if any rendered byte moved.
---

prompt_guard.py --identity reports 8 vocabulary dicts in scope for the games and 6 referenced by a template. INPUT_TYPE and STATE_HOME each appear exactly once in eval/suites/wholegame_prompts.py - their own definition - so no rendered prompt has ever contained them. They were left alone in task 133 because that ticket was scoped to the scene prompts and deleting them changes no rendered byte, which is exactly why nobody notices them. A dict that looks like part of the stack vocabulary and is not will be edited by someone who believes it reaches a prompt. Decide: delete them, or use them where the prose currently inlines the concept.
