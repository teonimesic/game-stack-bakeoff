---
id: 60
title: prune_scan --only fat reports the archive it says it excludes
status: open
priority: 4
refs: eval/tools/prune_scan.py cat_fat, .claude/skills/prune/SKILL.md, CLEANUP-LOG.md 2026-08-23 task 53
done_when: cat_fat filters on _is_archive unless --include-archive is passed, matching cat_history and cat_dup; a control proves it both ways - default run does not list eval/FINDINGS.md and --include-archive does; and the fat total is re-recorded in CLEANUP-LOG.md next to the 28,852 measured under the old behaviour so the two are not compared as if one instrument produced them
---

cat_fat takes include_archive and never uses it, so eval/FINDINGS.md and eval/RUNS.md are scanned for long sections on every run while the banner printed directly above the results says they are excluded by default. The effect is not cosmetic: the largest single entry in the fat list is FINDINGS.md Every finding at ~3,994 tokens, 14 percent of the reported total, and it is the one section the prune skill names as must-never-prune. A cleanup pass reads a ranked list headed by the thing it is forbidden to touch. Task 53 measured the fat total with the tool left unchanged, deliberately, so the before and after numbers were taken with one instrument - the fix belongs in its own change.
