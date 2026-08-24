---
id: 130
title: The g1_pong round-1 mean is stated as both 4.39 and 4.38, on a figure with no artifact behind it
status: in_testing
priority: 3
refs: eval/judge/JUDGING.md, eval/RUNS.md, tasks/04, eval/judge/judge_ledger.py, eval/withdrawn.json
done_when: every live statement of the three-call figure agrees to the digit, the rounding rule is stated once where the figure is defined, and the fact that these rounds have no artifact is said beside it - or the figure is withdrawn into eval/withdrawn.json and the live documents repaired as docstat.py --withdrawn names them
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/15
established_by: 'PR #15 at fcc8c64: gates, controls and CodeRabbit all pass, mergeState=CLEAN, 0 behind main. Review loop closed at 4 rounds, all 5 threads resolved - 5 findings acted on, 1 declined with evidence (register diff vs origin/main removes 0 lines; squash-only merge). Figure settled at 13.16/4.39 by the ledger table''s own arithmetic; WR-g1pong-round1-13-15 pinned red-then-green. Filed task 139: .coderabbit.yaml has failed validation since 2026-08-23, so every review ran on defaults.'
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

## note 2026-08-24

## Review round 1 (2026-08-24) — 4 threads, all acted on, none declined

The review landed **19m26s** after the push, past the skill's 15-minute bound; the hand-back that
said "no review" was correct at the time and wrong by 4m26s. That measurement is written up in
`tasks/127`, which also says the fix is to wait on the in-progress SIGNAL rather than on a clock.
Round 2 was polled that way — see `scratchpad/task130-poll-pr15.sh`, which asserts `headRefName`
before believing any answer and reports whether a round is still in flight when its cap expires.

### The Major finding was right, and the diff refuted itself

The block I added to `eval/RUNS.md` said *"the mean spans two aspects, which is why
`judge_ledger.py` prints no per-call mean at all"* and then, 3 lines above, priced 96 per-aspect
rounds from that same mean. **AGENTS.md rule 4 with the violation and its own refutation two
sentences apart.** `eval/judge/JUDGING.md` carried the same error at 2 sites.

The repair is not a relabel. The 96-round estimate is now priced **per (game, aspect)** off the
`g2_tetris3d` rows of the very ledger table the disputed figure sits in — each row is 1 aspect on
1 game, so each rate is over a homogeneous population:

| aspect | per call | x 96 rounds |
|---|---|---|
| `audio` | $0.60 | **$57.60** |
| `ux` | $1.37 | $131.04 |
| `fun` | $1.51 | $144.48 |
| `idiomatic` | $6.54 | $627.84 |
| `architecture` | $6.81 | **$653.28** |

**$58 to $653 for 1 game — an 11x spread, and the retired ~$420 lands inside it while matching no
aspect.** Each rate is 2 calls, so it is a lower bound, and that is stated beside it. The argument
the paragraph exists to make — a statistical tie is unaffordable — is unchanged and holds at both
ends; the binding constraint is still 96 sequential calls against 1 account's rate limit.

Removed rather than restated: *"That is the number to plan with"* and the
`3 games x 5 aspects x 2 orders ~ $130` projection, both of which came off the same mixed mean.

### Task 04 does not recover these calls, and the ledger said it did

*"task 04, closed by re-running them into `wg-funframes-crossgame/pong/` for $17.66"* was wrong on
3 counts, checked against `tasks/04-g1-pong-s-judge-outputs-are-missing.md`:

- it re-ran **`idiomatic` alone**, not `architecture` — so not "them";
- **4 ordered rounds**, not these 3 calls (`judge_ledger.py --tree runs/` shows
  `wg-funframes-crossgame/pong  4  17.66`);
- its own result is that #53's pong row **reproduces as a RANKING and not as SCORES** — ordering
  repeats exactly, every value ~0.6 lower.

This strengthens the ticket's claim rather than weakening it: $13.16 stays unreadable, and the
document now says why the obvious candidate for recovering it does not.

### The other 2

- *"cannot be re-read and never will be"* contradicted this section's own reversal clause 44 lines
  below. Now *"cannot be re-read from any currently surviving artifact"*.
- **Counts in digits.** `.coderabbit.yaml` 204-205 and `AGENTS.md` 344, unqualified. Converted
  every cardinal in the changed prose. Left alone deliberately: `one`/`the other` as pronouns and
  the ordinal *"the third call"* — not cardinal counts, and digitising them makes the sentence
  worse without making anything checkable.

## note 2026-08-24

## Round 2 clean, and a defect found in the reviewer itself

Round 2 landed by the **summary-comment arm** — CodeRabbit finished with **0 new threads**, all 4
round-1 threads resolved, and its check reads *pass / Review completed*. Loop closed at 2 rounds
against a ceiling of 5.

**The round-2 poll waited on the in-progress SIGNAL, not on a clock**, which is what `tasks/127`
asks for after the 15-minute bound missed by 4m26s here. `scratchpad/task130-poll-pr15.sh` prints
`inflight=N` on every line from the summary comment's in-progress marker, and distinguishes
*not finished* from *never coming* at its cap. It also asserts `headRefName` before believing any
answer — pinned both directions: aimed at PR #13 it exits 1 with
`WRONG PR: #13 is 'task-128-token-valuations-not-money'`.

### `.coderabbit.yaml` has been INERT since 2026-08-23 — filed as task 139

CodeRabbit's summary comment on this PR carries, inside a collapsed `<details>`:

    > [!WARNING]
    > ### `.coderabbit.yaml` has a parsing error
    > ... default settings were used instead.
    > Validation error: Too big: expected string to have <=250 characters at "tone_instructions"

Measured: `tone_instructions` is **894 characters against a 250 limit**, and one bad field
discards the **whole file**. Traced through every commit that touched it — introduced at 894 in
`7d87e13` (2026-08-23); every earlier revision has the field absent. So every review since then,
including PR #13, #14 and #15, ran on defaults.

**Why nobody noticed is the part worth keeping.** The reviews still looked right: CodeRabbit reads
`AGENTS.md` by default, so round 1 here cited *"As per coding guidelines"* for the digits rule and
for rule 4 — both of which live in `AGENTS.md` as well as in the dead yaml. **A mechanism that
runs, reports success, and measures nothing, whose output is indistinguishable from the working
one.** What is actually inert is everything the yaml adds over the defaults: the path-scoped
instructions, the exclusion list, and the prose-readability instructions that
`.agents/skills/work/SKILL.md` section 6 tells agents to act on.

Not fixed here — which instructions survive a 250-character budget is a decision about the
instrument that reviews every pull request. Task 139 carries it, and its `done_when` requires a
check that goes red on an invalid config, pinned both directions, because this failed silently for
a day across 3 pull requests.

## note 2026-08-24

## Review loop closed at 4 rounds, mergeState CLEAN

| round | landed | outcome |
|---|---|---|
| 1 | review object, 19m26s after push | 4 threads, 1 Major — all acted on, none declined |
| 2 | summary comment | 0 new threads |
| 3 | review object | 1 thread, 2 findings — 1 acted on, 1 declined with evidence |
| 4 | summary comment | 0 new threads |

**All 5 threads resolved.** `gates`, `controls` and `CodeRabbit` all **pass** at `fcc8c64`;
`mergeState=CLEAN`; 0 commits behind `origin/main`.

### The one thing declined, and the evidence

Round 3 called it an append-only violation to revise `WR-g1pong-round1-13-15`'s `replaced_by`.
Declined, because the change **this pull request makes to the register is purely additive**:

    git diff origin/main -- eval/withdrawn.json | grep "^-" | grep -v "^---" | wc -l   ->  0

0 lines removed, 1 entry added. The revision the comment points at is *between commits inside the
branch*, and the repository is squash-only (`allow_squash_merge=true`, `allow_merge_commit=false`,
`allow_rebase_merge=false`, read from the API), so `main` only ever sees one value of the field.
The register's own rationale is the deciding text — *"a consumer that applied it must keep being
able to"* — and no version of this entry has ever been published, so none was ever applied.

**Complying would have made the record worse**, which is the part worth keeping: the text to be
preserved was the one round 1's own Major finding condemned, advising `96 calls are $421.12` off a
2-aspect mean. An amendment would have left that retired guidance permanently in the register.
CodeRabbit did not contest the decline and round 4 came back clean.

**A general point for the next agent:** if append-only bound intra-branch edits, no register entry
could ever be revised in response to a review. The rule protects **published** entries.

### Two more corrections found by re-reading my own round-1 result

- `eval/RUNS.md` said *"the rows below show what that hides"* about the `g2_tetris3d` per-aspect
  rows, which sit **above** that note in the same table.
- The register's `replaced_by` still advised the `$421.12` projection round 1 had removed from
  every live document — the register would have recommended what the documents forbid.

Both are the same failure: a cross-reference that was true when written and was invalidated by the
edit two paragraphs away. Re-read the *whole* block after a review round, not only the lines the
comment names.
