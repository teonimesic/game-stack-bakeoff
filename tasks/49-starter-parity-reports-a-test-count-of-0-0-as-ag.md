---
id: 49
title: starter_parity reports a test count of 0/0 as agreement, and never reads the exit code it already collected
status: open
priority: 3
refs: eval/judge/starter_parity.py, eval/RUNS.md tenth comparability break, AGENTS.md rule 1
done_when: starter_parity.py goes red, or at minimum reports a loud problem, when a stack's just test does not run at all; pinned by a positive control (a tree with node_modules present reports its real count and stays green) and a negative control (the same tree with node_modules removed no longer reports 0/0 as if it were agreement)
---

test_counts() runs just test and returns exit, passed, total, but main() prints passed/total and never inspects exit, so a stack whose toolchain is not installed reports 0/0 and the tool still prints No drift detected on any measured axis. Measured 2026-08-23 in the task-47 worktree: ts printed 0/0 because node_modules is untracked and exists only in the main checkout, while rust 22/22, unity 32/32 and godot 23/23 were real. This is AGENTS.md rule 1 inside a live pre-campaign gate - total=0 passed=0 is indistinguishable from correctly failing - and eval/RUNS.md cites this exact field as evidence for the tenth comparability break (ts now 67/67 tests), so the field is read as a number by a durable document. The three other axes of the tool were unaffected and the parity run for task 47 is otherwise sound; the guide-size and hash-chain axes did their job.
