---
id: 142
title: The game preamble demands a distinct sound per event and the audio section allows two events to share one
status: todo
priority: 2
refs: eval/suites/wholegame_prompts.py _preamble and _probe_section, eval/suites/rendered/g1_pong__unity.txt, eval/judge/RUBRIC.md audio criteria, eval/RUNS.md, PR 19
done_when: One of the two clauses is gone or reworded so no rendered game prompt states both, decided against what judge/ actually scores. eval/RUNS.md records the comparability break with the date, since every future game trial is then cross-regime with the 90 stored ones. prompt_guard.py exits 0, prompt_guard_control.py exits 0, and the snapshot at eval/suites/rendered is re-recorded in the same commit. If the answer is that the two clauses are NOT in conflict, say why in the ticket with the criterion that adjudicates it, and close as a negative result.
---

Every rendered game prompt states both. The definition of done in _preamble(): 'a distinct sound effect for each of the events listed below'. The audio-manifest section of _probe_section(), 40 lines later: 'Whether two events share a sound, and what the sounds are, is yours to design.' A submission that maps three events to one file satisfies the manifest contract and fails the stated definition of done, and the audio criteria in judge/ decide which of the two the grader believes. Found by CodeRabbit on PR 19 against eval/suites/rendered/g1_pong__unity.txt lines 27-28 and 115-118, which only became reviewable because task 133 checked the rendered prompts in. NOT fixed there: _preamble() and _probe_section() are shared by all four games, 90 stored whole-game trials ran under this wording, and editing either is a regime boundary that task 133 was not scoped for.
