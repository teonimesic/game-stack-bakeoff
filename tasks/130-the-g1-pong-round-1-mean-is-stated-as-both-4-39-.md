---
id: 130
title: The g1_pong round-1 mean is stated as both 4.39 and 4.38, on a figure with no artifact behind it
status: todo
priority: 3
refs: eval/judge/JUDGING.md, eval/RUNS.md, tasks/04, eval/judge/judge_ledger.py, eval/withdrawn.json
done_when: every live statement of the three-call figure agrees to the digit, the rounding rule is stated once where the figure is defined, and the fact that these rounds have no artifact is said beside it - or the figure is withdrawn into eval/withdrawn.json and the live documents repaired as docstat.py --withdrawn names them
---

eval/judge/JUDGING.md and eval/RUNS.md state the same three-call mean as 4.39 in one place and 4.38 in another, and the same sum as 13.16 and 13.15. It is 13.16/3 = 4.38667 rounded up in one document and truncated in the other. The three g1_pong calls of 2026-08-16 are the only judge rounds in this project with no surviving artifact (task 04), so neither figure can be re-read from source and judge_ledger.py --tree runs/ does not see them at all - it reads 97 rounds over 12 directories and none is that field. Raised by the CodeRabbit review of PR #13 and deliberately not fixed there: quietly adjusting one to match the other is the move eval/RUNS.md already refuses for the 118.62/118.63 pair, so which way it goes is a decision rather than an edit.

## note 2026-08-24

## Neighbouring figure, deliberately NOT yours — task 132

`eval/RUNS.md` also carries a stored-judge-round census that disagrees with its own producer on
three rows of four (93/36/10 against a measured 97/40/14). That is **task 132**, it edits the same
file, and it is queued behind you for that reason. Do not fix it here; if your work touches that
table, say so in the pull request so 132 can be re-scoped rather than conflicting.

## What makes this a decision rather than an edit

Both spellings come from `13.16 / 3 = 4.38667` — one document rounded, the other truncated. The
three `g1_pong` calls have no surviving artifact, so **neither figure can be re-read from source**
and no measurement can break the tie. `judge_ledger.py --tree runs/` reads 97 rounds over 12
directories and none of them is that field.

So the outcomes are: pick a rounding rule and state it once where the figure is defined, or
withdraw the figure into `eval/withdrawn.json` and repair what `docstat.py --withdrawn` names.
**Both are complete answers.** What is not an answer is quietly editing one digit to match the
other — `eval/RUNS.md` already refuses exactly that for the 118.62/118.63 pair, and doing it here
would contradict a live document.
