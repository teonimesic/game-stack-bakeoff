---
id: 86
title: 'Number and land the task 78 finding: an unobservable gate'
status: done
priority: 3
refs: tasks/78, tasks/84, eval/FINDINGS.md, eval/RUNS.md fifteenth break
done_when: the finding is numbered against the highest number on main at the time, added to eval/FINDINGS.md and its index, cited from eval/RUNS.md's fifteenth comparability break and from tasks/84 in place of their current prose, and docstat.py --sweep passes unpiped
established_by: 'The number was ALREADY ALLOCATED: the orchestrator numbered the task 78 finding #130 at the merge 53b9a63, so this task allocated nothing and verified instead - docstat.py --findings reads 117 findings #19-#135, 0 gaps, 117 index rows, 117 distinct, so #130 is unique and indexed and its heading is the ticket''s claim. What was missing was the citing, and one LIVE document still asserted what #130 overturned: eval/RUNS.md''s fifteenth comparability break said the hook was already live in all four arms, which is rule 2 in the ledger that decides which runs may be compared. It now says wired and cites #130. The break''s measurement subsection restated #130 in full and is replaced by the citation plus only what the ledger needs - 0 blocks in both arms over the 12 trials with a stored baseline that reached a stop, n=0 outcomes, therefore no before/after comparison across this break is settleable from stored trials in either direction - keeping one sentence that does not follow from #130 and is about the runs, that no per-stack warm guard can have short-circuited in wg-g4c. tasks/84''s brief carried the same restatement and now cites #130, keeping the fix and the graded-diff constraint that are 84''s own. #130 gained the half the ticket named and its body lacked: a silent success path forecloses the question retrospectively because the evidence was never written. THE TRAP: #130 names two findings across the corpus - eval/RUNS.md:851, :889 and eval/judge/AGENTS.md:164 cited #130 meaning the anonymiser finding, now #131, in the same file the new citation lands in. All three repaired and graded by reading #131''s heading at eval/findings/one-arm-bias.md:2499, NOT by the count, because docstat''s own docstring establishes that --renumbered cannot grade a repair - an uncommitted line blames to UNCOMMITTED and is skipped and a line committed today is never stale, so 16 to 13 would have happened had the replacement been #999. An adversarial #132 planted beside the new citation was correctly NOT reported, for the same documented reason. The check''s real positive control fires: --renumbered --at 1120695^ names eval/PROTOCOL.md:541 among 8 decided stale, absent at HEAD. #126''s archive sentence live in all four is marked as overturned rather than rewritten. Gates unpiped, before and after and again after committing: docstat --sweep exit 0 sweep clean over 162 docs, --selftest 0 pins wrong, --findings exit 0, tasks.py check 101 well-formed - and the sweep was green throughout, so it is not a control on any of this. 13 stale citations remain in files other agents were editing that day, untouched on purpose and filed as task 102. Branch task-86-number-the-unobservable-gate-finding, commits 3cbb63b and 90436f0.'
---

Task 78 produced a finding and DELIBERATELY DID NOT ALLOCATE A NUMBER for it. Eleven finding-number collisions happened on 2026-08-23 because every agent reads the highest number from its own branch, forked before the last merge, and eleven worktrees were live while task 78 ran. The work skill says to hand the number to the orchestrator in that situation rather than take one. The finding, ready to number: THE STOP GATE HAS NO OBSERVABLE OUTPUT ON ITS SUCCESS PATH, SO 'THE GATE IS LIVE' HAS NEVER BEEN MEASURED - ONLY THE FILES HAVE. Measured: a blocking Stop hook writes a transcript entry (user, isMeta true, content beginning 'Stop hook feedback:'); an exit-0 Stop hook writes nothing. 19 stored trial transcripts carry a block, all dated 2026-08-11 or 2026-08-12; none from wg-matrix onward. In the 12 trials where the exposure is provable from a stored starter baseline and a stop was reached, 0 of 4 rust and 0 of 8 ts/unity/godot blocked - a null with n=0 outcomes, so the stored trials cannot say whether the rust guide's Stop-hook sentence changed behaviour. The generalisable half is the one AGENTS.md already states and this instance sharpens: a mechanism whose success path is silent is indistinguishable from a mechanism that did not run, and the archive cannot be re-interrogated later because the evidence was never written.

---

## Note added 2026-08-23 by task 84

**The defect this finding describes is now REPAIRED**, so the finding's last sentence should say
so rather than leaving a reader to assume the archive is still accumulating unobservable gates.
All four `verify-gate.sh` hooks write an audit trail to `$STARTER_HOOK_LOG`; `eval/wholegame.py`
addresses it outside the trial tree and stores `stop_hook` in every trial record. See
`eval/RUNS.md`, "ALL FOUR STOP HOOKS GAINED AN AUDIT TRAIL ON 2026-08-23" (cite the heading, not
the ordinal), and `tasks/84`.

**What does not change:** every trial recorded before that date is permanently unassessable on
this axis, which is the half of the finding worth publishing. The generalisable statement gains a
concrete counterpart - the same shape as the judge's file-open log, where 26 rounds have no log
and are permanently unassessable while everything after the capture can be interrogated.

`tasks/84` deliberately took no finding number, so this ticket is still the sole allocator.
