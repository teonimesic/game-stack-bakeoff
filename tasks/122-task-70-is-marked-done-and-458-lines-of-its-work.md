---
id: 122
title: Task 70 is marked done and 458 lines of its work never reached main
status: todo
priority: 1
refs: branch task-70-ranking-ban-threshold at bd2014c, eval/judge/paired_verdicts.py (absent from main), eval/judge/discrimination.py (on main, a DIFFERENT 194-line file), DECISIONS.md deterministic-tier ranking ban, tasks/70
done_when: either the branch's work is landed on main and the two discrimination.py versions are reconciled with a stated reason for whichever survives, or task 70 is reopened with what is actually missing written into its body; and a check exists that would have caught a task marked done whose branch is not an ancestor of main, with its false-positive count on the live queue measured and stated before it ships
---

Found 2026-08-23 while clearing stale worktrees. tasks/70 has status done with an established_by naming a scoped recount of 5 of 436 paired criteria, and its branch bd2014c is NOT an ancestor of main. The branch carries 678 insertions across 5 files, including eval/judge/paired_verdicts.py at 458 lines, which does not exist on main at all. eval/judge/discrimination.py DOES exist on main but is a different 331-line file against the branch's 194 - so the work is partially absent and partially divergent, which is worse than wholly absent because a reader checking one path finds something. A queue entry saying done for work that is not on main is the stale-queue failure the heartbeat warns about, and nothing detected it: no gate compares a closed ticket against the tree.

## note 2026-08-23

## What must not be re-derived, and the traps in this one

**Do NOT delete the branch.** It is the only copy of `paired_verdicts.py`. It has no worktree
now, so nothing is holding it; `git log task-70-ranking-ban-threshold` still reaches it.

**Do not merge it blind.** It forked before a large amount of work: `README.md` went 643 → ~370
lines and was restructured twice, `DECISIONS.md` gained many sections, the skills moved to
`.agents/skills/`, and the findings log went from #19-#132 to #19-#157. Its `README.md` and
`DECISIONS.md` edits will conflict, and taking either side wholesale is how a real result gets
discarded.

**The claim to adjudicate is whether the work is still CORRECT, not just whether it merges.**
Its subject — the within-cell verdict variance that would re-open the deterministic-tier ranking
ban — has moved since it was written. `WR-paired-verdict-tie` in `eval/withdrawn.json` carries
the per-scope replacement figures, and `README.md`'s result table now cites the register rather
than restating them. Re-run its numbers against today's `eval/runs` before landing any of them
(`AGENTS.md` rule 5, and #144: citing a producer is not running it).

**Two files named `discrimination.py` are not two versions of one file until you check.** Main's
is 331 lines and predates the branch's 194-line one; they may be unrelated work that collided on
a name. Diff them before assuming either supersedes the other.

**On the gate half of `done_when`:** the trigger is *a ticket whose status is `done` and whose
branch is not an ancestor of `main`*. That is a closed property, which this project's tally says
is the kind that comes in at zero false positives — but **measure it on the live queue and say
the number** before shipping, because five triggers have now been measured and three of the five
were unusable (#140, #142, #146 at 26, 8 and 49; #152 and #156 at 0). Note the obvious
complication: most closed tickets have had their branch **deleted**, so "not an ancestor" is
unanswerable for them and must read as NOT CHECKED rather than as a pass.
