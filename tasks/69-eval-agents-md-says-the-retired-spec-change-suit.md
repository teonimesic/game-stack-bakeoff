---
id: 69
title: eval/AGENTS.md says the retired spec-change suite has 71 stored trials; the tree holds 47 trial JSONs
status: open
priority: 3
refs: ''
done_when: State what population gives 71 and what gives 47, with the command for each, or correct whichever is wrong in every live doc that states it. If 71 is unreproducible from the stored tree, say so and say what evidence would have been needed - a count that cannot be reproduced is the defect task 64 existed to remove, not a smaller version of it.
---

census.py partitions runs/*/trials/*.json into 90 whole-game records (a game field) and 47 without one. eval/AGENTS.md, DECISIONS.md and eval/RUNS.md all say 71 for that suite, in three places that describe it as the sole surviving record of what those trials were asked to do. Either 71 counts something other than trials/*.json - arms, tasks, a run that was pruned - or one of the two numbers is wrong. Nobody has established which, and 71 is quoted as a reason to keep files.
