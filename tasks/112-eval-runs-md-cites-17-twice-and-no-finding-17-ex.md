---
id: 112
title: 'eval/RUNS.md cites #17 twice and no finding #17 exists'
status: done
priority: 3
refs: eval/RUNS.md lines 1140 and 1153, eval/findings/limits-and-cost.md lines 345 and 368, eval/FINDINGS.md header, tasks/17
done_when: 'eval/RUNS.md lines 1140 and 1153 either name a target that resolves - a finding in eval/findings/, a task id spelled as such, or a named regime - or drop the reference and state the open question in words. The claim beside it must be re-read against whatever it ends up naming, not just renumbered: AGENTS.md says never renumber a finding to satisfy a citation. Archive copies in eval/findings/limits-and-cost.md are NOT to be edited. docstat.py --sweep and tasks.py check exit 0 unpiped.'
established_by: 'Both eval/RUNS.md #17 citations now name targets that resolve, neither by renumbering. Line 1140 names the SEVENTH comparability break (2026-08-17, STARTER_NO_RAISE=1) at eval/RUNS.md:1051 - a gated namespace, unlike #NN: renaming that heading gives docstat --sweep exit 1 ''skips seventh between fifth and eighteenth - a gap means a citation resolves to nothing'', exit 0 after restore. Line 1155 names FINDINGS #64, whose body IS the correction block it heads, matching the FINDINGS #63 citation 23 lines above. Claims re-read against the new targets, not repointed: 2.15x = 77.60/36.16 = 2.1460 from the wg-g4c table at line 819; wg-g4c is stated at line 814 to be the same regime as wg-g4b, i.e. post-seventh-break, so gated-in-this-regime holds; n=2 per cell holds; #64 body agrees on 48 vs 86/101/140 and on the 8-invocation 36.16 trial scoring 1.000. Archive copies at eval/findings/limits-and-cost.md 345 and 368 untouched. Out-of-range #NN census over 54 live md files, pinned in both directions before it was believed: 51 matches clean, 52 with a planted #999, 51 after restore; 49 after this repair with 0 rows in eval/RUNS.md; 50 again with #64 fabricated to #999, 49 after restore. NEGATIVE CONTROL, re-measured rather than taken from the ticket: --sweep and --findings both read exit 0 with a fabricated #999 in a live document, before and after the repair, so no shipped gate can see this class of defect and none would catch the new #64 if it were wrong - that is #146 re-confirmed, not a new finding. History established independently with git log -S: both lines were written in the initial squashed commit a3d0fd1, so intent is unrecoverable and only the sentence, not the citation, could be repaired. Gates unpiped: docstat.py --sweep exit 0, --findings exit 0 at 133 findings #19-#151, --renumbered exit 0 with 0 untriaged, tasks.py check exit 0 at 117 tasks. No finding number allocated. Filed tasks/118: the #146 census - 20 rows over 53 live files - has no producer and does not reproduce, giving 51 matches on 43 distinct lines at HEAD, and its unrepairable wording needs narrowing to the citation rather than the claim. Branch task-112-runs-17-citations, commit decba7d.'
---

The findings log is #19-#145 (python3 eval/tools/docstat.py --findings, read 2026-08-23). Two LIVE lines of eval/RUNS.md cite #17: line 1140 'whether 2.15x is a property of rust or of our gate is open (#17)' and line 1153 'What #17 measures, corrected'. #17 is below the published range, so it resolves to no finding. It is not task 17 either - task 17 is backing up eval/runs and keeping the git mirror current, unrelated to the rust just-run gate. The same two sentences appear in eval/findings/limits-and-cost.md at 345 and 368, which is archive and stays. Nothing catches this: docstat.py --sweep, --findings and --renumbered all exit 0 over it, because --renumbered is derived from git renumber events and #17 was never renumbered, and the citation was written in the initial squashed commit a3d0fd1 so blame cannot say what it meant. Established by planting a fabricated (#999) citation in a live document: --sweep exit 0, --findings exit 0, both indistinguishable from the clean tree. A census of out-of-range #NN over the 53 live md files returns 20 rows of which these 2 are the only true positives - the other 18 are rule numbers, task numbers, table-row references, GitHub issue numbers and 'the #1 risk', so the obvious widening is 18 false positives to 2 true and is the open-class trap of #140. Do not build that check without measuring it. Extraction pinned both directions: 20 rows clean, 21 with a planted #999, 20 again after restore.

## what was done, 2026-08-23

Done on branch `task-112-runs-17-citations` (commit `decba7d`). Neither citation was
renumbered; each now names the thing its own sentence is about.

**Line 1140** — the rust `just run` gate is the **seventh comparability break** (2026-08-17,
`STARTER_NO_RAISE=1`), a heading at `eval/RUNS.md:1051` in the same file. That is a better
target than any `#NN` would have been: the comparability-break ordinal is a **gated** namespace.
`docstat.py --sweep` parses those headings and fails on a duplicate or a gap. Pinned red:
renaming the seventh heading gives `--sweep` **exit 1**, "skips seventh between fifth and
eighteenth - a gap means a citation resolves to nothing". Restored, exit 0.

**Line 1153/1155** — the ⚠️ correction block it heads *is the body of* **#64** ("The count that
proved the gate was costly counted the documentation", `eval/findings/limits-and-cost.md:349`).
#64 exists in both the bodies and the `FINDINGS.md` index. It is now cited as `FINDINGS #64`,
matching the `FINDINGS #63` citation 23 lines above it.

**The claims were re-read against the new targets, not just repointed:**
- 2.15x = 77.60 / 36.16 = 2.1460, from the `wg-g4c` table at `eval/RUNS.md:819`.
- `wg-g4c-2026-08-21` is stated (line 814) to be the **same regime as `wg-g4b`**, which is the
  post-seventh-break regime, so "gated in this regime" holds for this field.
- The seventh break's own rust row says `just run` is REFUSED under the harness and that
  "whether that costs turns or changes what it builds is unmeasured" — the same open question
  the sentence states.
- n=2 per cell holds (2 trials per stack in that table). #64's body agrees with the live
  restatement on 48 vs 86/101/140 and on the 8-invocation $36.16 trial scoring 1.000.

**What the existing gates can and cannot see, measured here rather than taken from the ticket.**
A fabricated `(#999)` planted in `eval/RUNS.md` reads `--sweep` **exit 0** and `--findings`
**exit 0** — indistinguishable from the clean tree, before and after this repair. So nothing in
the repository would have caught either `#17`, and nothing would catch the `#64` either if it
were wrong. That is #146's finding, re-confirmed, not a new one.

**#146 says these two are "unrepairable", and that needs one word narrowed.** The *citation* was
unrepairable — the author's intent is unrecoverable, both lines being from the initial squashed
commit `a3d0fd1` (verified here with `git log -S`). The *sentence* was repairable, by stating the
mechanism and naming the regime instead of pointing at a number. #146 is archive and was not
edited. A future pass may want to add that qualifier to its "The two true positives are
unrepairable, which is the cost" subsection.

**Do not re-derive: #146's census does not reproduce, and its population is unrecoverable.**
#146 publishes "20 rows, 2 true positives" over "the 53 live markdown files". Re-run at HEAD over
git-tracked `*.md` minus `docstat.ARCHIVE_PATHS` — 54 live files — the same rule gives **51
matches on 43 distinct lines** before this repair, **49 on 41** after, broken down
research/ 26, DECISIONS.md 8, .agents/ 7, eval/ 5, AGENTS.md 3. Excluding `research/` and
`.agents/` gives 15, not 20. The gap is population, not range: the range only widened (#145 to
#151), which can only *reduce* rows. **#146 wrote the number without the command that produced
it**, which is exactly what AGENTS.md's "a count with a producer goes stale for an hour; a count
with none goes stale forever" row is about. The conclusion #146 draws is unaffected — the ratio
of false to true positives is still lopsided and the check still should not be built naively —
but its specific figures cannot be reproduced.

**A trap worth one line.** The first version of the census extractor matched only `## #NN`
finding headings and reported the published range as **#19-#25** against a true #19-#151, because
`eval/findings/` uses **two** heading styles and `limits-and-cost.md` uses `## 64.`. Do not
re-implement the body census — import `docstat._body_findings`, which handles both.
