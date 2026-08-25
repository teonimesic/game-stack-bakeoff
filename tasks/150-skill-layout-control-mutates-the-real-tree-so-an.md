---
id: 150
title: skill_layout_control mutates the real tree, so an interrupted run leaves the repository broken and blames the skills
status: in_review
priority: 3
refs: eval/tools/skill_layout_control.py, eval/tools/docstat.py cmd_selftest, tasks/147
done_when: 'An interrupted skill_layout_control.py leaves the tree either unplanted or self-identifying: either the plant/restore is made crash-safe (restore from the index, or a marker file the tool itself detects and repairs on next run), or the baseline red path prints the exact repair command and the fact that a previous interrupted run is the likely cause. Established by KILLING the process mid-plant - SIGTERM during the run, not a simulated failure - and showing docstat.py --sweep is green afterwards, or red with the repair named. The 5/5 plants must still be caught.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/28
---

It plants each way the skill layout can break INTO THE WORKING TREE and restores afterwards. Killed mid-plant - a timeout, a Ctrl-C, a crash - it leaves .claude/skills as a real directory of copies, and every later docstat.py --sweep is exit 1 with 11 rows saying a real skill file exists outside .agents/skills. Measured on task 147: a 2-minute Bash timeout killed it at exit 143, and the next four gate runs were red for a reason that had nothing to do with the change under test. The rows point at the skills, so the reader looks there; the repair is rm -rf .claude/skills followed by git checkout -- .claude/skills, which nothing tells them. docstat.py --selftest solved the same problem the other way and says so in its docstring: it mutates copies in memory and asserts eval/FINDINGS.md's size and mtime are unchanged, precisely so that a crash between plant and restore cannot leave the archive edited. A symlink plant cannot be done in memory, so the fix here is not the same - but the tree can be restored from the index rather than from a variable, and the failure can name itself.
