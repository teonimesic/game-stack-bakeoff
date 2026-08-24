---
id: 130
title: The g1_pong round-1 mean is stated as both 4.39 and 4.38, on a figure with no artifact behind it
status: in_review
priority: 3
refs: eval/judge/JUDGING.md, eval/RUNS.md, tasks/04, eval/judge/judge_ledger.py, eval/withdrawn.json
done_when: every live statement of the three-call figure agrees to the digit, the rounding rule is stated once where the figure is defined, and the fact that these rounds have no artifact is said beside it - or the figure is withdrawn into eval/withdrawn.json and the live documents repaired as docstat.py --withdrawn names them
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/15
established_by: 'PR #15, gates+controls green at 8adba4a. Live statements of the three-call figure now all read $13.16 / $4.39; WR-g1pong-round1-13-15 registered, docstat.py --withdrawn exit 1 before the citations and exit 0 after, variant planted in README.md red then green. CodeRabbit: 29 polls over 15 min, no review at the head, no deadlock heading.'
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

## note 2026-08-24

## What was decided, and why the ticket's premise was wrong

**The disagreement is about the SUM, not about rounding, and that is what makes it decidable.**
The ticket says *"13.16/3 = 4.38667 rounded up in one document and truncated in the other"* and
concludes no measurement can break the tie. Round the other candidate too:

    13.16 / 3 = 4.386667  ->  4.39   (half-up)
    13.15 / 3 = 4.383333  ->  4.38   (half-up)

Neither document truncated anything. Each was internally consistent, and they disagreed about
the sum. A rounding convention is a preference; a sum is a claim with evidence behind it.

**$13.16 closes the arithmetic of the ledger table that prints it.** `eval/RUNS.md`'s
specialist-judge table has `g2_tetris3d` rows summing to $33.63 - which
`python3 eval/judge/judge_ledger.py --tree eval/runs/` still re-derives to the cent from
`wg-tetris-judge-2026-08-17/pre/` - and a published day total of $46.79:

    46.79 - 33.63 = 13.16   exactly
    33.63 + 13.15 = 46.78   which is not the total printed above it

**State the limit with the result:** this is coherence with a published total, not a re-reading.
$46.79 has no artifact either, so if $46.79 is ever shown wrong the decision reopens - which is
what `DECISIONS.md`'s reversal clause says. But only $13.15 contradicts the table it was printed
beside, and `eval/judge/JUDGING.md` already stated $13.16 fifty lines below the paragraph saying
$13.15. The recorded per-call range $2.82-$5.29 discriminates neither: the third call is $5.05
under one reading and $5.04 under the other.

**Do not re-derive the artifact question.** `judge_ledger.py --tree eval/runs/` reads **97 rounds
over 12 directories** (2026-08-24) and none of them is this field. There is no producer for the
figure and there never will be; task 04 closed by re-running the calls into
`wg-funframes-crossgame/pong/`, which is a different field.

## What shipped

- `eval/RUNS.md` - the ledger row is the definition site: the figure, the rounding rule (**cents
  round half-up, never truncate**), the no-surviving-artifact fact beside it, and the instruction
  to project from the unrounded 13.16 / 3 (96 calls = $421.12, not 96 x 4.39 = $421.44).
- `eval/judge/JUDGING.md` - `$13.15` -> `$13.16`, `$4.38` -> `$4.39` in three places, the 96-call
  arithmetic derived from the sum, and a pointer to the definition site.
- `eval/withdrawn.json` - `WR-g1pong-round1-13-15` retires the losing pair.
- `DECISIONS.md` - the derivation and the reversal clause.

`eval/AGENTS.md` and `eval/judge/judge_ledger.py` already said $4.39 / 13.16 and were not touched.
Archive documents keep what they said.

## Why a register entry rather than only a correction

A stale figure agrees with every copy of itself, so no consistency check can see it (#113, #119).
Registering the losing pair converts "every live statement agrees to the digit" from a one-time
census into a standing gate: `docstat.py --withdrawn` now goes red if `13.15` and `4.38`
co-occur in a live block that does not cite the id. `match` requires BOTH, following
`WR-tier3-pair`, because a single loose decimal fires on unrelated prose.

Controls, both directions:

| | result |
|---|---|
| entry added, before any block cited the id | `docstat.py --withdrawn` **exit 1**, `eval/RUNS.md:1282-1293` |
| after citing the id in the three historical blocks | **exit 0** |
| variant: retired pair planted in `README.md`, then removed | **exit 1** at `README.md:362`, then exit 0 |
| false positive: the *replacement* text planted, including `4.386667` | **exit 0** |
| the two regexes over 5 strings whose answer was stated in advance | **0 failures** |

`run-gates.sh pre-push`, `withdrawn_control.py` (54/54), `linkcheck.py`, `tasks.py check`: all
exit 0. CI `gates` and `controls` both pass on the PR.

## Left for someone else

- **Task 132's table is untouched.** It edits the stored-judge-round census near
  `eval/RUNS.md:278`; this diff is entirely in the specialist-judge ledger section ~1000 lines
  lower. No re-scoping needed. My 97-rounds/12-directories reading agrees with 132's measured 97.
- **`eval/RUNS.md`'s section heading *"Specialist-judge calls - a separate ledger, because they
  spend money too"*** calls tokval spend, which #159 and task 128 say it is not. Three lines above
  this diff and deliberately not changed: it is a heading, so changing it moves an anchor, and it
  belongs to the #159 clean-up rather than to this ticket. Worth a ticket.
- **A finding number was NOT allocated** (work skill section 2). If the orchestrator wants one, the
  generalisable claim is: *two figures that look like a rounding disagreement may be a
  disagreement about the input. Round the other candidate too before concluding the tie is
  undecidable, then ask which candidate closes the arithmetic of the table it is printed in.*
