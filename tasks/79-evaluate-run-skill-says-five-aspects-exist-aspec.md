---
id: 79
title: evaluate-run skill says five aspects exist; aspects.py defines six
status: open
priority: 3
refs: .claude/skills/evaluate-run/SKILL.md, eval/judge/aspects.py, eval/judge/RUBRIC.md, eval/judge/JUDGING.md
done_when: The skill, RUBRIC.md and JUDGING.md all state the same aspect count as aspects.py, verified by running docstat.py --sweep and by grepping the ASPECTS tuple and each doc's count sentence side by side. If fun_frames is deliberately not a scored aspect, that is stated where the count is, with the reason.
---

Re-read from source 2026-08-23 under task 39. .claude/skills/evaluate-run/SKILL.md:59 states 'The five aspects that exist are fun, ux, audio, idiomatic, architecture' and that anything else named in prose is a candidate rather than a judge. eval/judge/aspects.py:281 reads ASPECTS = {a.id: a for a in (IDIOMATIC, ARCHITECTURE, FUN, FUN_FRAMES, AUDIO, UX)} - six, including fun_frames, and field_sweep.py --aspects takes choices=sorted(ASPECTS) so --aspects fun_frames is accepted rather than rejected. The skill's two named authorities disagree with each other as well: eval/judge/RUBRIC.md:422 says five, eval/judge/JUDGING.md:1077 reports a result over all six. The skill copied the stale half. This is failure #38 - a doc naming judges that do not exist - with the sign reversed: a doc denying a judge that does exist, so a reader under-runs the subjective layer and never learns why.
