---
id: 122
title: Task 70 is marked done and 458 lines of its work never reached main
status: done
priority: 1
refs: branch task-70-ranking-ban-threshold at bd2014c, eval/judge/paired_verdicts.py (absent from main), eval/judge/discrimination.py (on main, a DIFFERENT 194-line file), DECISIONS.md deterministic-tier ranking ban, tasks/70
done_when: either the branch's work is landed on main and the two discrimination.py versions are reconciled with a stated reason for whichever survives, or task 70 is reopened with what is actually missing written into its body; and a check exists that would have caught a task marked done whose branch is not an ancestor of main, with its false-positive count on the live queue measured and stated before it ships
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/8
established_by: 'Task 70''s branch is landed - paired_verdicts.py is on main and the branch is an ancestor. The ticket''s claim of two divergent discrimination.py versions was wrong: main''s copy was byte-identical to the branch''s merge base and the branch adds 137 lines, so it was a superset, not a divergence. tasks.py check now classifies every done ticket''s branch LANDED/ORPHANED/NOT_CHECKED, measured at 6/1/112 on the live queue with 0 false positives before shipping. tasks_control 79 to 100 rows. PR #8.'
---

Found 2026-08-23 while clearing stale worktrees. tasks/70 has status done with an established_by naming a scoped recount of 5 of 436 paired criteria, and its branch bd2014c is NOT an ancestor of main. The branch carries 678 insertions across 5 files, including eval/judge/paired_verdicts.py at 458 lines, which does not exist on main at all. eval/judge/discrimination.py DOES exist on main but is a different 331-line file against the branch's 194 - so the work is partially absent and partially divergent, which is worse than wholly absent because a reader checking one path finds something. A queue entry saying done for work that is not on main is the stale-queue failure the heartbeat warns about, and nothing detected it: no gate compares a closed ticket against the tree.

## note 2026-08-23

## What must not be re-derived, and the traps in this one

**Do NOT delete the branch.** It is the only copy of `paired_verdicts.py`. It has no worktree
now, so nothing is holding it; `git log task-70-ranking-ban-threshold` still reaches it.

**Do not merge it blind.** It forked before a large amount of work: `README.md` went 643 → ~370
lines and was restructured twice, `DECISIONS.md` gained many sections, the skills moved to
`.agents/skills/`, and the findings log went from #19-#132 to #19-#157. Its `README.md` and
`DECISIONS.md` edits will conflict, and taking either side wholesale is how a real result gets
discarded.

**The claim to adjudicate is whether the work is still CORRECT, not just whether it merges.**
Its subject — the within-cell verdict variance that would re-open the deterministic-tier ranking
ban — has moved since it was written. `WR-paired-verdict-tie` in `eval/withdrawn.json` carries
the per-scope replacement figures, and `README.md`'s result table now cites the register rather
than restating them. Re-run its numbers against today's `eval/runs` before landing any of them
(`AGENTS.md` rule 5, and #144: citing a producer is not running it).

**Two files named `discrimination.py` are not two versions of one file until you check.** Main's
is 331 lines and predates the branch's 194-line one; they may be unrelated work that collided on
a name. Diff them before assuming either supersedes the other.

**On the gate half of `done_when`:** the trigger is *a ticket whose status is `done` and whose
branch is not an ancestor of `main`*. That is a closed property, which this project's tally says
is the kind that comes in at zero false positives — but **measure it on the live queue and say
the number** before shipping, because five triggers have now been measured and three of the five
were unusable (#140, #142, #146 at 26, 8 and 49; #152 and #156 at 0). Note the obvious
complication: most closed tickets have had their branch **deleted**, so "not an ancestor" is
unanswerable for them and must read as NOT CHECKED rather than as a pass.

## note 2026-08-23

Both halves of `done_when` are done, on branch `task-122-land-task-70`.

## Half 1: the branch is landed, and the "two discrimination.py versions" were one

**There was no collision to adjudicate.** `main`'s `eval/judge/discrimination.py` is
**byte-identical to the branch's merge base** (`23be12c`) at **194 lines**; the branch adds
**137** lines to it, reaching **331**. `git diff 23be12c main -- eval/judge/discrimination.py`
is empty. This ticket's `refs` and body had the two line counts the wrong way round and read
them as divergence -- **that is the only thing in this ticket that was wrong, and it is worth
knowing because it is what made the task look larger than it was.** The merge of
`task-70-ranking-ban-threshold` into `main` conflicts in exactly 2 files, not 5.

**Conflict resolution, and the reason for each side:**

| file | taken | why |
|---|---|---|
| `eval/judge/discrimination.py` | branch (clean, +137) | main never touched it |
| `eval/judge/paired_verdicts.py` | branch (new, 458) | exists nowhere else |
| `eval/judge/JUDGING.md` | branch, auto-merged, then corrected | see below |
| `DECISIONS.md` | branch's rows, **inside main's table** | main gained 2 rows in the same table (`The code half of the directory leak`, `A saturated tier-2 group`) and rewrote the `Tier 1 gates` row for task 75. Taking either side wholesale loses one of those |
| `README.md` | **main, whole. The branch's hunk is discarded** | task 107 removed run-particular information from the front door; the branch's evidence table names runs, per-run costs and trial counts. Its substance -- that the claim now has a producer -- landed as the `how to re-derive it` column of the row already there |

## Everything re-measured, 2026-08-23, against `<main>/eval/runs`

Not read off the branch. Rule 5, and #144: citing a producer is not running it.

  * `paired_verdicts.py --selftest --runs-root ...` -- **20/20 checks, 5 corpus pins**, all green
  * `paired_verdicts.py --runs-root ...` -- the nine-group table reproduces to the digit
  * `discrimination.py --selftest` -- **6/6**: positive, boundary, variant, mutant
  * `discrimination.py <run>` over the 5 runs with completed pairs -- **0 CROSSES**

**Two corrections to what the branch published**, both now on the branch:

1. *"over all 9 stored groups: 0 cross -- every one sits at range 0.0000"* counted a group the
   test never asked. `wg-audio` `g2_tetris3d` has **one** gate-green stack and prints
   **`NOT ASKED`**. The test is asked of **8** of the 9, and 0 cross; **5 of the 8 are
   four-way**, the other 3 compare 2 or 3 stacks. `NOT ASKED` is a third value and is not a pass.
2. The `wg-arena3d` Rust submission fails on **`E0502`, a borrow-check error** on
   `velocity.0 += (target - velocity.0) * PLAYER_ACCEL` in `crates/sim/src/lib.rs` -- not a type
   error. The rest of that adjudication is exact and was verified against the stored report:
   22 of 23 criteria excused by `is_harness_failure`, `audio.triggered` the lone survivor, and
   it IS the whole 0.0435 gap.

`JUDGING.md`'s replacement sentence was also wrong in the same direction -- it gave the floor's
lower bound as *"0 of 112"* when 5 of the 9 groups are at 0.00% on denominators of 30 to 148.

## Half 2: the gate, and its false-positive count

`tasks.py check` now calls `landed_status(tid, refs, is_ancestor)` for every `done` ticket.
**Three values**: `LANDED`, `ORPHANED` (exit 1), `NOT_CHECKED` (counted, printed, never a pass).

**Measured on the live queue BEFORE it shipped**, 121 tickets, 119 `done`:

    6 LANDED   1 ORPHANED   112 NOT_CHECKED     0 false positives, 1 true positive

The true positive is task 70. **The broken state was established first** (rule 14): the gate was
written and run while `main` still lacked the branch, and it came back exit 1 naming task 70. It
is exit 0 on this branch because the merge commit landed the work -- which is the control in the
other direction.

**Bases: `main`, `origin/main`, and the INVOKING CHECKOUT's HEAD, de-duplicated by SHA.** The
first version wrote a bare `HEAD` into the list; `TASKS` is the main checkout, so `HEAD` asked
there is `main` under another name and the census line printed two bases where there was one --
rule 12 inside the fix for a rule-12 defect. `_caller_head()` resolves HEAD at `ROOT`, and the
dedup compares SHAs. Without the caller's HEAD the gate is unfixable from the branch that fixes
it, which is how a gate gets bypassed.

**Pinned in both directions.** `tasks_control.py` direction 11: **11 predicate rows** (including
`task-7-` not claiming `task-70-*`'s branch AND the reverse) and **4 end-to-end rows** on a real
scratch git repository with one merged and one orphaned branch in the same queue. The control
goes 79 rows -> 94, 0 FAILED, 0 NOT CHECKED. `tasks_mutants.py` goes 21 -> 25 mutants, all
caught, inert control still SURVIVED:

  * `orphan_reads_as_not_checked` -- 3 red
  * `missing_branch_fails` (the VARIANT half: accusing a deleted branch) -- 6 red
  * `landed_census_never_printed` -- 3 red
  * `bases_deduped_by_name` -- 1 red

## What this cannot see, so nobody reads more into a green

It asks **reachability, not content**. A branch merged `-s ours`, or one a later commit reverted,
reads `LANDED` with its work absent. The known false positive is a **squash merge** -- 0 of the 7
surviving branches were squashed. If the repository starts squashing, the trigger stops being the
right one; it does not want a wider tolerance.

## A finding the orchestrator should number

**A queue entry and the tree can disagree by silence, and no consistency check can see it.**
Task 70 read `done` for **4h 39m** (`bd2014c` 09:37:02 to `5476723` 14:16:06, 2026-08-23) over
678 insertions across 5 files `main` had never seen, including a 458-line tool that existed on no
other branch. Nothing detected it; a person clearing stale worktrees did. The shape is the same
as #119's: **the two sides do not contradict each other, one of them is just absent**, so the
only detectable property is a positive test somebody wrote. The control in both directions and
the false-positive count are above; the decision is in `DECISIONS.md`, *"A closed ticket is
checked against the tree"*.

## note 2026-08-23

CI measured something the operator's machine could not, and it is a limitation of the gate,
not a bug in it.

**A verdict is relative to the refs the caller can see.** On the same commit, the same day:

| where | bases that resolved | verdict |
|---|---|---|
| operator's checkout | `main`, this checkout's HEAD | **7 LANDED / 112 NOT_CHECKED** |
| CI run `32656195661` | `origin/main`, this checkout's HEAD | **6 LANDED / 113 NOT_CHECKED** |

The difference is **task 70**: its branch was never pushed, so from CI no `task-70-*` ref exists.
**The defect this gate was written to catch reads `NOT_CHECKED` in CI**, correctly. The
load-bearing instance is therefore the **git hook in the checkout that holds the branches**, and
CI is a weaker copy of it rather than a second opinion -- a green CI run does not cover this.
`landed_status`, `DECISIONS.md` and `.agents/skills/tasks/SKILL.md` all say so now.

The same run also showed **`main` failing to resolve on a CI checkout while `origin/main`
carried it**. That fallback was an argument when it was written and is a measurement now.

**One stale count found on the way**: `controls.yml`'s step was named *"the five mutants
tasks_control's rows must catch"* while there were 21, and this task makes it 25. It names the
property now; `tasks_mutants.py --list` is the producer. Its header budget is re-measured from
521s to 685s.

**Note for whoever waits on `controls`**: the workflow's concurrency group **cancels the
in-flight run when a new commit is pushed**, measured here -- run `32656195639` went to
`cancelled`. Waiting for a run whose head you are about to supersede buys nothing.

## note 2026-08-23

Review round 1 on PR #8 found **three real defects in the code this ticket added**, and two of
them were the rules being cited while writing it. Recorded here because the next agent should
not re-derive them.

**1. A control that does not travel the subject's path is a control over a different subject.**
`evaluate.overall_score` rounds to 4 decimals. `ranking_test` compared floats against `1/N`, so
a one-criterion gap at `N=13` arrived as `1.0000 - 0.9231 = 0.0769` against `0.076923...`:

    RUNTIME PATH  -> DOES NOT CROSS
    SELFTEST PATH -> CROSSES      (built 12/13 unrounded, never went through load())

The `BOUNDARY` row was green against a value `load()` cannot produce. **A tolerance cannot fix
this class** -- the shipped `1e-9` is four orders of magnitude below the rounding error, and one
wide enough to absorb it would swallow real gaps. Tier 2 IS a pass count, so the test now works
in integers: `k*(max_s - min_s) - 2*sum(d) >= 2k`. **No stored verdict changed** -- 8 asked, 0
cross, before and after.

**2. `N` was `max(n_scored)` over the whole game while the comparison ran on the gate-green
subset** -- rule 4, a denominator from a population that had been filtered afterwards. It is
established over the selected stacks now, and survivors that disagree give `NOT ASKED`.

**3. `_caller_head()` asked at `ROOT`, which comes from `__file__`.** The work skill tells an
agent to run the MAIN copy of the tool by absolute path, under which its own branch is never
consulted and the orphan it has just landed cannot be cleared -- the repair path this base exists
to keep open, dead. Both addresses are asked now.

> **And the fix for 3 contained something worse, which its own new control row caught within a
> minute.** A SHA from `Path.cwd()`'s repository is not an object in the queue's repository, so
> every `merge-base` exited 128, the three-valued reader turned that into `NOT_CHECKED`, and
> **the entire gate went silent while printing what reads as a clean queue.** Each caller HEAD
> is now required to exist in the repository the ancestry query runs against.

**4. `merge-base` errors were collapsed into "not an ancestor".** Verified: `0` ancestor, `1`
not, `128` missing ref. `_is_ancestor` is three-valued now. **Its first mutant SURVIVED**,
because the rows handed `landed_status` a lambda returning `None` and never ran `_is_ancestor` --
a consumer pinned without its producer, the `tasks/106` shape. That row calls it against a real
repository now.

**Declined, with the reason in the thread**: atomic writes for the `paired_verdicts` fixture.
It is a `tempfile.TemporaryDirectory` written and read in one single-threaded process.

**Found while re-running, not raised in review**: `paired_verdicts.py`'s docstring said
`wg-g4c-capgate` reads *"six times the floor anything else shows"*. Re-derived, 12/140 is
**8.57%** against a highest real rate of **2.86%** -- three times. Six only appears by comparing
raw counts across different denominators, which is the refusal listed two paragraphs above it in
the same docstring.

Final: `tasks_control` **79 -> 100 rows**, `tasks_mutants` **21 -> 28**, all caught, inert control
still SURVIVED. One mutant anchor drifted during the repair and the runner **refused to apply it**
rather than reporting a pass for a check that never changed -- that guard is worth its space.

## note 2026-08-23

Review round 2 (the last -- the skill budgets two) raised 4 more, 3 acted on and 1 declined.

**A real crash.** `load()` records `n_scored = 0` for a submission with no scored play-bot
criteria; two such gate-green stacks reached the arithmetic and raised **`ZeroDivisionError`**.
Reproduced first, then fixed: `NOT ASKED`, reported. An aggregate over a population that does
not exist is not a tie and is not a crash.

**A header that claimed more than the function enforced.** `ranking_test` prints
*"adjudicated, gate-green, **completed**"* and filtered only on the first two. `main()` already
excludes non-completed rows before calling, so nothing on the shipped path was wrong -- the
reviewer's *"those rows can produce CROSSES"* is false for `main()`. **The point stands anyway,
and it is worth carrying: a guarantee that lives only in the caller is one the next caller will
not have, and a function that prints a claim about its population should enforce it.** Both
directions pinned -- a `max_turns` pair is gated out, AND the identical gap still crosses when
both trials completed, or the repair is a deletion.

**Declined, and the real ambiguity fixed the other way round.** The reviewer wanted `PR #8`
rewritten as the reference-style `[#8]`. In a live document `#NN` is a **finding** citation and
`linkcheck.py` resolves it against `eval/findings/`; findings run **#19-#157**, so `[#8]` would
be a reference-style link to a finding that does not exist. Complying would have created the
dangling citation the convention exists to prevent. The `#` is gone instead -- it reads "pull
request 8" -- with that reasoning recorded beside it.

`discrimination.py --selftest` is **12 rows** now, from 9. **No corpus verdict changed at any
point across either round**: 8 groups asked, 0 cross, and the DECISIONS.md nine-group table and
its per-group figures are exactly as first measured.

## The state at handback

Branch `task-122-land-task-70`, 5 commits including task 70's own `bd2014c`. PR 8.

| gate | result |
|---|---|
| `tasks.py check` | 0 |
| `tasks_control.py` | **100 rows, 0 FAILED, 0 NOT CHECKED** (from 79) |
| `tasks_mutants.py --selftest` | **28 mutants, 0 survived**, inert control SURVIVED (from 21) |
| `discrimination.py --selftest` | **12/12** |
| `paired_verdicts.py --selftest --runs-root` | **20/20, 5 corpus pins** |
| `docstat --sweep` / `--findings` / `--withdrawn` / `linkcheck` | 0 |
| CI `gates` | success on every head pushed |

**What the orchestrator should verify against the artifacts rather than this account**: that
`git merge-base --is-ancestor task-70-ranking-ban-threshold main` exits 0 after the merge, and
that `python3 eval/tools/tasks.py check` run **in the main checkout** reports task 70 as LANDED
rather than ORPHANED. The gate is only load-bearing where the branches are -- in CI it reads
NOT_CHECKED, measured.
