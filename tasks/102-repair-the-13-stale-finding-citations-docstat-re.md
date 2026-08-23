---
id: 102
title: Repair the 13 stale finding citations docstat --renumbered DECIDES, and triage the 28 it cannot
status: done
priority: 4
refs: eval/tools/docstat.py, AGENTS.md renumbering table, tasks/86
done_when: docstat.py --renumbered reports an empty DECIDED STALE list at HEAD unpiped, every replacement recorded beside the eval/findings/ heading text that establishes it rather than beside the count, and each of the 28 UNDECIDABLE rows carries either a repair or a one-line note saying which finding it meant and why history could not say
established_by: '31 stale citations repaired, not the 16 the ticket names: the decided half was 16 of 16 wrong by construction, and 15 of the 51 undecidable rows were wrong too. Every replacement graded by opening eval/findings/ and reading the heading, never by the count, which is zero whatever is written; the six destination headings are quoted in the ticket. THE RESULT: all 15 undecidable-half errors are in tasks/, every one a task citing the number it allocated itself, and 0 of the 36 rows in live documents were wrong - case C of _check_renumbered_citations, where the author''s numbering lived only in an uncommitted worktree. The agreement heuristic that buckets 36 as correct puts tasks/88:8 and tasks/97:8 in the wrong bucket, so it is a reading order and not a verdict. Five rows are range endpoints, not citations. New: eval/renumber_triage.json records the 36 verdicts keyed by citing text not by line number, --renumbered now prints UNTRIAGED first, --sweep gates on an entry whose sentence no longer exists, eval/tools/triage_control.py is 14 controls with every red demonstrated including the two variants - a line moved 40 lines still pairs, and a citation past column 96 still pairs, which was a real bug that put 4 adjudicated rows in the untriaged list. Gates unpiped after merging main: --renumbered DECIDED STALE 0 and UNTRIAGED 0 of 36, --sweep exit 0 over 169 docs, --selftest 0 pins wrong, --findings exit 0, --withdrawn exit 0, triage_control 14/14, withdrawn_control 0, findings_control 0, tasks.py check 106 well-formed, lint.py exit 0. Branch task-102-stale-finding-citations, not pushed. NEEDS A FINDING NUMBER - the claim is in the ticket.'
---

docstat --renumbered names 13 citations at HEAD whose number was reassigned by a merge: #126 meaning what is now #128 in DECISIONS.md x3, README.md, judge/RUBRIC.md x3, judge/AGENTS.md and .claude/skills/add-game/SKILL.md x2; #133 meaning #134 in DECISIONS.md and tasks/88; #132 meaning #133 in eval/RUNS.md. Every one still RESOLVES, which is why no other check sees them and why a reader following one lands on real work that is not the work the author meant, which is #118. Task 86 repaired only the three that collided with the number it was landing, deliberately leaving files other agents were editing that day. THE TRAP, measured under task 86 and stated in docstat's own docstring: the count cannot grade the repair. A line edited in the working tree blames to UNCOMMITTED and is skipped, and a line committed today has todays findings tree as its authoring tree and is never stale, so the number falls to zero whatever you write in place of it. Grade each replacement by reading the heading in eval/findings/.

## Updated at dispatch, 2026-08-23 — the count moved, and here is why it is not 13

`docstat.py --sweep` now reports **12**, not the 13 this ticket was filed with. The difference is
not progress: merges since filing re-authored some of the lines that carried stale citations, and
`--renumbered` decides what is stale by the **authoring tree of the line**, so a line committed
today is graded against today's numbers whatever it says.

**That is the trap this ticket must not fall into, and it is why the count cannot grade the
repair.** Once you fix a citation, the fixed line has today's authoring tree, so it drops out of
the check *whether or not you fixed it correctly*. **The count going to zero is not evidence the
repairs are right.** Grade each one by opening the finding it now cites and reading the heading.

**Findings have moved again since filing.** The log now runs to **#140**, and #137, #138, #139 and
#140 were all allocated today, two of them after a collision was resolved by renumbering. Re-run
`--sweep` yourself and work from what it prints, not from the numbers in this ticket's body.

**File conflict, live:** task 101 also edits `DECISIONS.md` and `eval/judge/RUBRIC.md` to add
`#139` citations. Merge `main` before you finish.
