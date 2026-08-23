---
id: 106
title: tasks_control.py never runs check end to end on an unreachable done_when
status: in_flight
priority: 4
refs: eval/tools/tasks_control.py, eval/tools/tasks_mutants.py, tasks/105
done_when: tasks_control.py gains a row that runs tasks.py check as a subprocess on a scratch queue holding an unreachable done_when and asserts the warning text is PRINTED, plus its negative control on a reachable one; tasks_mutants.py SELFTEST_MUTANT is then replaced with a mutation that is still inert and the reason it is inert is recorded, or --selftest is replaced by whatever else proves the runner can report SURVIVED
---

Measured 2026-08-23 while building tasks_mutants.py, and it is that file's positive control rather than a suspicion: replacing the line 'if warn:' in cmd_check with 'if False:' makes tasks.py compute every reachability warning and print none, and all 28 rows of tasks_control.py stay green - exit 0, 0 FAILED. Direction 4 calls reachability_warning IN PROCESS over 11 wordings, which pins the PREDICATE well and never asks whether check prints what the predicate returns. The same shape as the defect task 82 repaired one function away: a mechanism whose loss no row can see. It is priority 4 rather than 1 because the warning is advisory - it fails nothing and gates nothing - so its silent loss costs a smell, not a result. WHAT THE NEXT AGENT MUST NOT RE-DERIVE: closing this breaks tasks_mutants.py --selftest by design. That selftest needs an INERT mutation to prove the runner can print SURVIVED at all, and this is the one it uses; SELFTEST_MUTANT's comment says so and the selftest fails loudly with 'either a row now covers it - in which case pick a new inert mutation' rather than silently. Do not delete the selftest to make this green: a mutant runner that can only ever print CAUGHT is rule 1's total=0 passed=0.
