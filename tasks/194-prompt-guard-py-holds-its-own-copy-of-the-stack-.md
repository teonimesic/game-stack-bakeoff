---
id: 194
title: prompt_guard.py holds its own copy of the stack tuple instead of reading wholegame_prompts, which owns it
status: todo
priority: 3
refs: eval/tools/prompt_guard.py,eval/suites/wholegame_prompts.py
done_when: 'prompt_guard.py no longer holds a second literal: read STACKS from wholegame_prompts (W.STACKS) or assert equality at import, fail-closed. Add the check that would catch a reintroduced copy: a selftest case or assertion that the module attribute is the imported object, so a future literal edit fails rather than drifts. python3 eval/tools/prompt_guard.py --snapshot --diff (or the invocation the module documents) and its selftest exit 0 unpiped afterward.'
---

eval/tools/prompt_guard.py line 44 defines STACKS = ("rust", "ts", "unity", "godot") two lines below "import wholegame_prompts as W", and never reads W.STACKS. Every other consumer takes the tuple from wholegame_prompts: wholegame.py reads P.STACKS for starters, iteration and CLI choices, and scene_prompts.py imports STACKS from it and re-exports. So prompt_guard carries the only unpinned copy of a value the module beside it owns. prompt_guard is the tool that asserts prompt identity across stacks; if a fifth stack is added in wholegame_prompts, prompt_guard would go on rendering and identity-checking the old four and report a clean population of the wrong size — the drift is invisible in its own output because the count it prints is derived from the copy. This is the rule-12 corollary spelled in AGENTS.md for paths, applied to a value: spelled in two files with nothing asserting them equal. Found in the 2026-08-28 cleanup pass over eval/suites/wholegame_prompts.py and its readers.
