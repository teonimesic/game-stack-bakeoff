---
id: 93
title: Publish the finding that tasks.py check exited 0 on a ticket carrying another ticket's brief
status: done
priority: 3
refs: tasks/82, eval/tools/tasks.py misfiled_body, .claude/skills/tasks/SKILL.md, commit 436bf64
done_when: eval/FINDINGS.md carries a numbered finding for the queue lint reading exit 0 over commit 436bf64's two malformed task files, with the number allocated against main at the time of writing and the index row present so docstat.py --sweep stays green; or, if a peer has already published the same observation under another number, that number is recorded here instead and this closes
established_by: 'Published as #141 in eval/findings/certifies-nothing.md, index row present in eval/FINDINGS.md, and the range updated to 19-141 in AGENTS.md, README.md and eval/FINDINGS.md. Number allocated against main at 1f6fb65 highest 140, after main moved four times during the task - 1fc9133 at 135, 22ad6ea at 136, d69f606 at 139 with its index row MISSING and docstat --findings RED on main itself, then 1f6fb65 at 140 - with 137, 138 and 139 held by unmerged peer branches at various points. BROKEN STATE ESTABLISHED FIRST, not quoted from tasks/82: the queue rebuilt from git blobs at 436bf64, all 70 files, run under the tasks.py that shipped with that same commit, exits 0 printing 70 task(s), all well-formed; the current copy over the byte-identical 70 files exits 1 naming both halves. THE FINDING IS LARGER THAN THE TICKET DESCRIBED and the extra half is what makes it a finding. The same mistake was made TWICE on 2026-08-23, and check caught one and certified the other. At 709d51a 01:09:16 the guessed filename did not exist - the slug truncates to -to-doc, not -to-do - so the append created a second file with no frontmatter, and the era''s own check exits 1 naming both no frontmatter and id 37 used by 2 files, measured over its own 39-file queue; repaired 36 seconds later. At 436bf64 09:12:56 the guessed filename DID exist, so the append landed task 71''s 59-line brief inside a live ticket, and check exited 0. A wrong address that MISSES produces a malformed artifact the frontmatter lint can see; one that HITS produces a well-formed one it cannot. 709d51a appears nowhere in tasks/82 and was found by a FALSE POSITIVE OF THIS TASK''S OWN CENSUS EXTRACTION - a file with no frontmatter at all classified as empty-bodied - which is rule 12''s corollary paying for itself, since the extraction had been proved first against tasks/71 at 436bf64 whose value was read directly. COVERAGE MEASURED: the pre-fix cmd_check evaluated four frontmatter values, id title status done_when, plus did the frontmatter parse; body was parsed and stored on every record and read by exactly one code path in the whole tool, show, which prints it to the agent. Zero checks read it. Over the 70 files at 436bf64 that is 27,156 of 328,692 bytes, 8.3 percent. A FIGURE IN THE TICKET WAS WRONG AND IS CORRECTED, not annotated: for a day is really 25m48s on main''s first-parent chain, 436bf64 09:12:56 to 28f6598 09:38:44, and the same wrong figure was in eval/tools/tasks_control.py''s docstring; both fixed. Duration is the wrong measure anyway - the dispatched agent forked at 23be12c 09:14:41, AFTER the misfile, and delivered at c2bc8ce 09:38:42, so 100 percent of one task''s execution ran against an empty ticket, and the damage was bounded by a duplicate copy of the brief in the commit message rather than by any gate. EMPTY-BODY CENSUS RE-RUN over the grown corpus rather than quoted: 393 distinct tracked file-versions across 143 snapshots, 2 with frontmatter and a blank body, both tasks/71, at exactly the three commits of this defect; task 82''s figures were 275 and 81. GATES read unpiped: docstat --findings 0, --sweep 0, --withdrawn 0, --selftest 0, findings_control 0, tasks.py check 0, tasks_control 0 at 28 measurements 0 FAILED 0 NOT CHECKED, withdrawn_control 0. NOT ESTABLISHED and filed as tasks/105: task 82''s five mutants have NO RUNNER - eval/tools/ holds disclosure_mutants.py and no tasks_mutants.py, and tasks_control.py''s argparse takes only --skip-prefix - so they exist as prose in a closed ticket''s frontmatter and nothing in the repository can re-run them. NOT RE-RUN and attributed to task 82 rather than claimed here: the MISFILED_MARGIN sweep over 3175 file-versions, defect at 0.3615 against a worst non-defect of 0.1399. Also removed a dangling duplicated sentence fragment in eval/FINDINGS.md''s header. Branch task-93-publish-the-frontmatter-only-lint-finding, commit 7f01125.'
---

Task 82 repaired the defect and gated it, but did not publish the finding, and the reason is worth stating: main's highest finding number moved from #128 to #131 during the task, so allocating one from a forked branch is how eleven collisions happened on 2026-08-23 and docstat.py --sweep fails on a duplicate. WHAT THE FINDING IS. tasks.py check gated a task file's FRONTMATTER from the start and never read its BODY - the only part an agent is actually briefed from. Commit 436bf64 appended task 71's entire 59-line brief to tasks/70-set-a-size-....md, a filename guessed from a queue listing title, and created tasks/71-....md with no body at all. check exited 0 on both, for a day, while task 71's dispatched agent worked from an empty ticket and tasks.py show 70 rendered a brief about trial disclosures. This is the project's signature pattern - a mechanism that runs, reports success and measures nothing - landing on the queue lint itself, and it is AGENTS.md rule 12's first table row happening a second time. THE REPAIR IS ALREADY DONE and is not what needs publishing: eval/tools/tasks.py now fails on an empty body and on a body that restates another task's title and done_when, pinned both ways by eval/tools/tasks_control.py at 28 measurements, 0 FAILED, 0 NOT CHECKED, with five mutants each killed by the row naming its mechanism. WHAT NOT TO DO. Do not renumber anything to make a citation resolve, and do not reuse a gap below the maximum - read the highest number from main immediately before writing, per the work skill.

## Published as #141. What the next agent must not re-derive

**The number is #141, allocated against `main` at `1f6fb65` (highest #140), after four
re-reads.** Main moved under this task **four times** in one working session — 1fc9133 (#135)
→ 22ad6ea (#136) → d69f606 (#139 body, index row missing, `--findings` RED on main itself) →
1f6fb65 (#140, green, a duplicate `**137**` index row having been renumbered away in between).
Numbers 137, 138 and 139 were held by unmerged peer branches at the moment this task started.
**Do not read the highest number once and hold it across the work** — read it, then merge
`main` and read it again immediately before the write.

**The ticket's own account of the defect was wrong in one figure, and it is corrected here
rather than annotated.** *"check exited 0 on both, for a day"* — the real exposure on main's
first-parent chain is **25m48s**, `436bf64` 09:12:56 → `28f6598` 09:38:44. The same wrong
figure was in `eval/tools/tasks_control.py`'s docstring; both are fixed.

**The finding is bigger than the ticket described, and the extra half is what makes it a
finding rather than a bug report.** The same mistake was made **twice on 2026-08-23**, and
`tasks.py check` caught one and certified the other:

| | `709d51a` 01:09:16 | `436bf64` 09:12:56 |
|---|---|---|
| guessed filename | did NOT exist (`-to-do` vs the real `-to-doc`) | DID exist (`tasks/70`) |
| era's own `check` | exit **1** — `no frontmatter`, `id 37 used by 2 files` | exit **0** — `70 task(s), all well-formed` |

A wrong address that **misses** produces a malformed artifact the frontmatter lint can see; one
that **hits** produces a well-formed one it cannot. `709d51a` is not mentioned anywhere in
`tasks/82`, and it was found by a **false positive of this task's own census extraction** — a
file with no frontmatter at all classified as empty-bodied.

**Re-measured here, so it does not need re-running:**

- The queue rebuilt from git blobs at `436bf64` (70 files) under the `tasks.py` that shipped
  with that commit → exit 0, `70 task(s), all well-formed`. Under the current copy → exit 1
  naming both halves. Same for `709d51a` (39 files) → exit 1.
- The pre-fix `cmd_check` evaluated **four** frontmatter values plus "did the frontmatter
  parse". `body` was read by exactly one code path in the whole tool — `show`. ~~**27,156 of
  328,692 bytes, 8.3%.**~~ **Both terms wrong; corrected at merge to 29,591 of 329,185 bytes,
  9.0%.** The figure had no producer, so nothing could disagree with it — `eval/tools/`
  `lint_coverage.py 436bf64` is now that producer, and `--selftest` pins the denominator
  against `git ls-tree -l` and pins a second extraction method 47 bytes away. See #141.
- Empty-body census re-run over the grown corpus: **393 distinct tracked file-versions across
  143 snapshots, 2 empty-bodied, both `tasks/71`**. Task 82's figures were 275 and 81.
- `tasks_control.py` exit **0**, 28 measurements, 0 FAILED, 0 NOT CHECKED.

**Not established, and filed as `tasks/105`:** task 82's five mutants have **no runner**.
`eval/tools/` has `disclosure_mutants.py` and no `tasks_mutants.py`; `tasks_control.py`'s
argparse takes only `--skip-prefix`. They exist as prose in a closed ticket's frontmatter and
nothing can re-run them.

**Not re-run, and attributed rather than quoted as this task's own:** the `MISFILED_MARGIN`
sweep (3175 file-versions, 81 snapshots, 0.3615 vs 0.1399). That is task 82's measurement.
