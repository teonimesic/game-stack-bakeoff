---
id: 77
title: AGENTS.md says the sweep checks file paths; docstat.py says NO PATH CHECK
status: open
priority: 3
refs: AGENTS.md, eval/tools/docstat.py, .claude/skills/audit-docs/SKILL.md
done_when: AGENTS.md no longer claims a path check that docstat.py does not implement - either the sentence is corrected to name what the sweep actually covers, or the path check is reinstated with the positive control the earlier measurement lacked. Verify by grepping both files and quoting the two lines side by side.
---

AGENTS.md:215 states the mechanical sweep covers 'aspect ids, criterion ids, --flags and file paths across every doc'. eval/tools/docstat.py:1597 reads '# NO PATH CHECK.' and records why it was removed: 0 true positives, 2 false. Both re-read from source 2026-08-23 under task 39. This is failure #38 running backwards: the always-loaded file names a gate that does not exist, so a reader believes the phantom-path class is covered when nothing checks it. It is also one of only two certain contradictions found in a full read of the four always-loaded docs plus all nine skills, which matters because arXiv:2510.14842 identifies conflict between instructions, not their number, as the mechanism behind compliance decay.
