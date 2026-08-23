---
id: 86
title: 'Number and land the task 78 finding: an unobservable gate'
status: open
priority: 3
refs: tasks/78, tasks/84, eval/FINDINGS.md, eval/RUNS.md fifteenth break
done_when: the finding is numbered against the highest number on main at the time, added to eval/FINDINGS.md and its index, cited from eval/RUNS.md's fifteenth comparability break and from tasks/84 in place of their current prose, and docstat.py --sweep passes unpiped
---

Task 78 produced a finding and DELIBERATELY DID NOT ALLOCATE A NUMBER for it. Eleven finding-number collisions happened on 2026-08-23 because every agent reads the highest number from its own branch, forked before the last merge, and eleven worktrees were live while task 78 ran. The work skill says to hand the number to the orchestrator in that situation rather than take one. The finding, ready to number: THE STOP GATE HAS NO OBSERVABLE OUTPUT ON ITS SUCCESS PATH, SO 'THE GATE IS LIVE' HAS NEVER BEEN MEASURED - ONLY THE FILES HAVE. Measured: a blocking Stop hook writes a transcript entry (user, isMeta true, content beginning 'Stop hook feedback:'); an exit-0 Stop hook writes nothing. 19 stored trial transcripts carry a block, all dated 2026-08-11 or 2026-08-12; none from wg-matrix onward. In the 12 trials where the exposure is provable from a stored starter baseline and a stop was reached, 0 of 4 rust and 0 of 8 ts/unity/godot blocked - a null with n=0 outcomes, so the stored trials cannot say whether the rust guide's Stop-hook sentence changed behaviour. The generalisable half is the one AGENTS.md already states and this instance sharpens: a mechanism whose success path is silent is indistinguishable from a mechanism that did not run, and the archive cannot be re-interrogated later because the evidence was never written.

---

## What was done, 2026-08-23 — branch `task-86-number-the-unobservable-gate-finding`

**THE NUMBER WAS ALREADY ALLOCATED, AND THAT IS THE FIRST THING TO CHECK, NOT THE LAST.** The
orchestrator numbered this finding **#130** when it merged task 78 (`53b9a63`), which the ticket
could not know because it was written on task 78's branch. Handing a number to the orchestrator
works; it just leaves the ticket that was filed to request it looking undone.

> **Before allocating a number a previous task deferred, look for it under the merge that closed
> that task, not only in the ticket.** `git log -S'<the heading text>' -- eval/findings/` answers
> it in one command.

Verified rather than assumed, from the producer: `docstat.py --findings` reads **117 findings,
#19-#135, 0 gaps, 117 index rows, 117 distinct**. #130 is unique, indexed, and its heading is the
ticket's claim. So nothing needed numbering and nothing needed renumbering.

### What actually was missing

**The citing — and one LIVE document still asserted the thing #130 overturned.**
`eval/RUNS.md`'s fifteenth comparability break said the hook *"was already live in all four
arms"*. That is rule 2, in the ledger that decides which runs may be compared. It now says
**wired**, and cites #130 for why "live" is not established.

The break's `What the stored trials can and cannot say about it` subsection restated #130 in full
— the transcript signature, the probe arms, the 19 dated blocks. Replaced by the citation plus
only what the ledger needs: 0 blocks in both arms over the 12 trials with a stored baseline that
reached a stop, n=0 outcomes, therefore **no before/after comparison across this break is
settleable from stored trials in either direction.** One sentence was KEPT deliberately because
it does not follow from #130 and is about the runs: none of the per-stack warm guards can have
short-circuited in `wg-g4c`.

`tasks/84`'s brief carried the same restatement and now cites #130, keeping what is 84's own —
the fix, and the constraint that the trial tree becomes the graded diff.

#130 itself gained the half this ticket named and its body lacked: **a silent success path
forecloses the question retrospectively**, because the evidence that would answer it was never
written.

### The trap under this task, which cost the most time

**`#130` names two findings across the corpus.** Before this task `eval/RUNS.md:851`, `:889` and
`eval/judge/AGENTS.md:164` cited `#130` meaning the **anonymiser** finding, which renumbering made
**#131** — so the new citation would have landed in the same file as two wrong ones. All three
repaired.

**`--renumbered`'s count cannot grade a repair, and its own docstring says so.** A line edited in
the working tree blames to UNCOMMITTED and is skipped; a line committed today has today's findings
tree as its authoring tree and is never stale. So **16 -> 13 would have happened had the
replacement been `#999`.** The three were graded by reading #131's heading in
`eval/findings/one-arm-bias.md:2499`. For the same reason **a plant at HEAD cannot restore the
alarm** — an adversarial `#132` inserted beside the new citation was correctly NOT reported.

The check's own positive control is the one that works: `--renumbered --at 1120695^` names
`eval/PROTOCOL.md:541` among 8 decided stale, and none of the 8 appear at HEAD.

### Left open, filed

**13 stale citations remain** (`#126`->`#128` x8, `#133`->`#134` x2, `#132`->`#133` x1, and the
undecidable half). They are in `DECISIONS.md`, `README.md`, `judge/RUBRIC.md`,
`.claude/skills/add-game/` — files other agents were editing the same day — and none of them
collide with a number this task landed. Not touched here on purpose.

### Gates, unpiped

`docstat.py --sweep` exit 0, sweep clean over 162 docs, before and after the change and again
after committing. `--selftest` 0 pins wrong. `--findings` exit 0. `tasks.py check` 99 well-formed.

> **The sweep was green throughout and is not a control on any of this.** It was green while
> `RUNS.md` asserted a claim #130 overturned and while the same file carried two `#130` citations
> meaning #131. The only checks that saw anything were `--renumbered` and reading the heading.
