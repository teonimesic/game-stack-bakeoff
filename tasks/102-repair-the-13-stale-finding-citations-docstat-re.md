---
id: 102
title: Repair the 13 stale finding citations docstat --renumbered DECIDES, and triage the 28 it cannot
status: open
priority: 4
refs: eval/tools/docstat.py, AGENTS.md renumbering table, tasks/86
done_when: docstat.py --renumbered reports an empty DECIDED STALE list at HEAD unpiped, every replacement recorded beside the eval/findings/ heading text that establishes it rather than beside the count, and each of the 28 UNDECIDABLE rows carries either a repair or a one-line note saying which finding it meant and why history could not say
---

docstat --renumbered names 13 citations at HEAD whose number was reassigned by a merge: #126 meaning what is now #128 in DECISIONS.md x3, README.md, judge/RUBRIC.md x3, judge/AGENTS.md and .claude/skills/add-game/SKILL.md x2; #133 meaning #134 in DECISIONS.md and tasks/88; #132 meaning #133 in eval/RUNS.md. Every one still RESOLVES, which is why no other check sees them and why a reader following one lands on real work that is not the work the author meant, which is #118. Task 86 repaired only the three that collided with the number it was landing, deliberately leaving files other agents were editing that day. THE TRAP, measured under task 86 and stated in docstat's own docstring: the count cannot grade the repair. A line edited in the working tree blames to UNCOMMITTED and is skipped, and a line committed today has todays findings tree as its authoring tree and is never stale, so the number falls to zero whatever you write in place of it. Grade each replacement by reading the heading in eval/findings/.
