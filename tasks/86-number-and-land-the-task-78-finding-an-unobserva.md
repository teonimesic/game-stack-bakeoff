---
id: 86
title: 'Number and land the task 78 finding: an unobservable gate'
status: open
priority: 3
refs: tasks/78, tasks/84, eval/FINDINGS.md, eval/RUNS.md fifteenth break
done_when: the finding is numbered against the highest number on main at the time, added to eval/FINDINGS.md and its index, cited from eval/RUNS.md's fifteenth comparability break and from tasks/84 in place of their current prose, and docstat.py --sweep passes unpiped
---

Task 78 produced a finding and DELIBERATELY DID NOT ALLOCATE A NUMBER for it. Eleven finding-number collisions happened on 2026-08-23 because every agent reads the highest number from its own branch, forked before the last merge, and eleven worktrees were live while task 78 ran. The work skill says to hand the number to the orchestrator in that situation rather than take one. The finding, ready to number: THE STOP GATE HAS NO OBSERVABLE OUTPUT ON ITS SUCCESS PATH, SO 'THE GATE IS LIVE' HAS NEVER BEEN MEASURED - ONLY THE FILES HAVE. Measured: a blocking Stop hook writes a transcript entry (user, isMeta true, content beginning 'Stop hook feedback:'); an exit-0 Stop hook writes nothing. 19 stored trial transcripts carry a block, all dated 2026-08-11 or 2026-08-12; none from wg-matrix onward. In the 12 trials where the exposure is provable from a stored starter baseline and a stop was reached, 0 of 4 rust and 0 of 8 ts/unity/godot blocked - a null with n=0 outcomes, so the stored trials cannot say whether the rust guide's Stop-hook sentence changed behaviour. The generalisable half is the one AGENTS.md already states and this instance sharpens: a mechanism whose success path is silent is indistinguishable from a mechanism that did not run, and the archive cannot be re-interrogated later because the evidence was never written.
