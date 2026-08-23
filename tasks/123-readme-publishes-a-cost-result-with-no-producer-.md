---
id: 123
title: README publishes a cost result with no producer, and it is the last such number in the file
status: done
priority: 2
refs: 'README.md cost row, eval/findings/limits-and-cost.md #63, eval/tools/census.py, eval/runs/wg-g4c-2026-08-21T02-26-46, tasks/115'
done_when: a producer prints the cost result with the population it counted and a selftest that pins it in both directions; README cites the command beside the figure; and either the published figures are reproduced exactly or the differences are stated with which is right and why
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/9
established_by: 'eval/tools/cost_census.py reproduces every published cost figure to the cent and refuted the sentence around them: there are 7 (run,game) groups where all four stacks ran at once, not 1; the published 42% is the lowest of them; they run 42-254%; and the between-stack range exceeds the within-cell floor in 5 of 7. The half that reached the null does not survive. 21 mutants all caught. Merged with FINDINGS 159, which independently corrected the unit - the r=0.65-0.97 correlation is arithmetic, not a mechanism. PR #9.'
---

Task 115's agent said this in as many words and did not file it: the cost row's figures - the between-stack range as a fraction of the within-cell noise floor, the correlation between cost and turns, and the turn spread - reproduce exactly from the stored trial records, but only via an ad-hoc script that was not shipped. README cites the finding for the field and the method rather than a command. By AGENTS.md's own rule that is the defect, not a shortfall: a quantity with no producer goes stale forever rather than for an hour, and FINDINGS 144 measured that failing twice in one day on a figure whose producer existed and simply was not run. It is now the ONLY number in README with no way to re-derive it.

## note 2026-08-23

## What was measured, 2026-08-23 — do not re-derive it

**Shipped `eval/tools/cost_census.py`.** Run it against the main checkout; a worktree has no
`eval/runs/` and the tool exits 2 rather than reporting 0.

    python3 eval/tools/cost_census.py                    # from the main checkout
    python3 eval/tools/cost_census.py --runs-dir <abs>   # from a worktree
    python3 eval/tools/cost_census.py --selftest         # 14 mutants, 3 variants, 0.1s

### The published figures reproduce exactly. The scope around them did not.

Every figure in `eval/findings/limits-and-cost.md` #63 came back to the cent: the per-stack table
(`unity 48.23/54.00/1.12x/5.76/51.12`, `ts 40.88/55.05/1.35x/14.18/47.97`,
`godot 42.92/66.16/1.54x/23.24/54.54`, `rust 36.16/77.60/2.15x/41.43/56.88`), the `$21.15` mean
within-cell gap, the `$8.91` between-stack range, `42%`, `r = 0.971`, turns `205-370`, `$421.00`
over 8 `completed` trials.

**What did not reproduce is `README.md`'s sentence around them** — *"on the one measure taken on
all four stacks at once"*. There are **7** `(run directory, game)` groups in the stored tree where
all four stacks ran with >= 2 completed trials per cell, **56 trials in total**:

| group | floor | range | ratio | r(cost,turns) | widest turn span | cheapest -> dearest |
|---|---|---|---|---|---|---|
| `wg-arena3d` / `g3_arena` | $10.50 | $20.88 | **199%** | 0.863 | 240-369 rust | ts, godot, unity, rust |
| `wg-audio48` / `g1_pong` | $8.06 | $10.04 | **125%** | 0.897 | 175-233 godot | ts, unity, godot, rust |
| `wg-audio48` / `g2_tetris3d` | $5.00 | $12.68 | **254%** | 0.906 | 225-265 godot | ts, unity, rust, godot |
| `wg-g4c` / `g4_platformer` | $21.15 | $8.91 | **42%** | 0.971 | 205-370 rust | ts, unity, godot, rust |
| `wg-matrix` / `g1_pong` | $1.31 | $1.96 | **149%** | 0.746 | 87-109 unity | rust, ts, unity, godot |
| `wg-matrix` / `g2_tetris3d` | $2.97 | $2.84 | **96%** | 0.653 | 95-125 unity | unity, godot, ts, rust |
| `wg-matrix` / `g3_arena` | $2.86 | $3.06 | **107%** | 0.814 | 80-115 unity | ts, rust, unity, godot |

**42% is the lowest of the 7. The range EXCEEDS the floor in 5 of 7.** `#63` itself never claimed
exclusivity — it says *"first matrix"*, which was true — so the scope was introduced when the
finding was summarised into the front door. `AGENTS.md`'s shape exactly: a figure quoted
correctly, about a population nobody had counted.

**The mechanism half of #63 survives, and is now measured on 7 groups instead of 1**: cost tracks
turns at `r = 0.653 to 0.971` in every group, and turns vary by as much as **165** inside one
stack's two trials. What does not survive is *"the between-stack range is small against its
floor"* — the half that reached the null.

### The thing that is NOT adjudicated, and must not be published as a test

The same producer prints **mean cost rank per stack: ts 1.43, unity 2.29, godot 3.14, rust 3.14**
— the TypeScript arm has the lowest stack mean in **5 of the 7** groups and is never worse than
3rd. **This is a read of the means, not a test**, and the tool's own output says so:

- the 7 groups are **not independent** — 3 come from `wg-matrix`, 2 from `wg-audio48`;
- every cell is **n=2**, so a "within-cell gap" is the range of two samples, and a floor built
  from four of those is very noisy. That is #63's own lesson pointed back at itself.

For scale only, and not as a result: under a null of random ordering with 7 *independent* groups,
rank 1 in 5 of 7 is p ~ 0.013 — but treating runs rather than groups as the unit leaves n=4, and
the calculation stops being worth doing. **Filed as `tasks/126`.** It is offline and buys nothing.

### `r(cost, bash-commands) = 0.852` reproduces, and its input is not in this repository

It comes back **0.8516** counting `Bash` `tool_use` blocks in the `claude` CLI transcripts —
per trial: godot 97/104, rust 151/77, ts 66/94, unity 91/65. **It is deliberately not in the
producer.** Its only input is `~/.claude/projects/-Users-stefano-game-research-work-<run>-<trial>/
*.jsonl`, which is outside the repository, unversioned, deletable by the CLI, and not in
`eval/tools/evidence_set.py`'s definition of evidence. A producer whose input can vanish is a
producer in name only. **If the project wants this figure to survive, the transcripts have to
become an artifact the harness stores** — that is a separate task nobody has filed.

### A withdrawal-register entry is warranted and I could not land it

`eval/withdrawn.json` needs an **archive** anchor stating the retired claim in full, and the
archive files I can write from a worktree (`tasks/`) live in the **main checkout**, not on the
branch — so `docstat.py --withdrawn` would be green in `main` and red on the PR. Drafted for
whoever lands it, anchored on this ticket once it is committed:

    {"id": "WR-cost-one-measure",
     "withdrawn": "2026-08-23",
     "kind": "claim",
     "claim": "the cost result's scope stated as 'the one measure taken on all four stacks at
               once', with a between-stack range 42% of its own noise floor",
     "match": ["the one measure taken on all four stacks at once"],
     "anchor": "tasks/123-readme-publishes-a-cost-result-with-no-produce.md",
     "declared_in": "DECISIONS.md, 'The cost route is re-opened, and a group is (run, game)'",
     "replaced_by": "python3 eval/tools/cost_census.py. 7 qualifying (run, game) groups, 56
               trials. The ratio runs 42% to 254% and the between-stack range EXCEEDS the
               within-cell floor in 5 of 7; 42% is the lowest of the 7. The mechanism holds on
               all 7: r(cost, turns) = 0.653 to 0.971."}

Note the `match` regex is the **scope sentence**, not the figure — `42%` is correct for its group
and #63 may state it freely.

### Design decisions a later reader would otherwise re-derive

- **The unit is `(run directory, game)`.** A floor is a property of a population: pooling across
  runs mixes budget-cap regimes (#33), pooling across games mixes task sizes. Never pooled, only
  reported side by side.
- **A cell with one trial has NO gap and the group is refused.** Contributing `$0.00` would
  deflate the floor and inflate the ratio — fail-open, in the direction that manufactures a
  difference. Mutant 1 of 14 pins it; on the synthetic tree it takes a floor of $8.00 to $6.00.
- **`turn_span` is three-valued.** `None` (no turn record) is not `0` (one turn record). My own
  first selftest expectation got this wrong and the tool was right.
- **Pearson returns `None`, never `0.0`,** where it is undefined, and is refused below 3 points.
- **A zero floor gives no ratio**, not a number.

### Controls, both directions

`--selftest` states every expected value as a **literal** before measuring (rule 12's corollary:
a control that imports its expectation from its subject is not a control). Green: `ok (0
failures)`. Red: **14 mutants**, each producing named FAIL rows, unmutated control green —
thin-cell guard, `terminal_reason` partition, whole-game/spec-change partition, Pearson-returns-0,
Pearson min points, refuse-not-zero, agent-authored trees counted, one-level glob, game pooling,
min-gap floor, swallowed JSON, spread division on `$0.00`, missing `cost_usd`, first-two-trials
cell gap. **3 variants** (a `$0.00` trial, a record with no cost field, an uneven 3-trial cell)
all pass, and mutants 12-14 exist to prove those rows can go red.

**The selftest was hardened after the first mutant sweep**: 3 of 14 crashed it with a traceback
instead of reddening a row. `measure()` and `only_group()` turn any raised exception into a named
failure, so all 14 now diagnose themselves.

### Gates and CI

All green unpiped, and all green on the **unmodified** tree first, so no pre-existing red was
absorbed: `docstat.py --sweep`, `--findings`, `--withdrawn`, `linkcheck.py`, `tasks.py check`,
`lint.py --gate --rule invalid-syntax`. `cost_census.py --selftest` (0.1s) is wired into
**CI fast** in `.github/workflows/gates.yml`; `.github/workflows/README.md` records why the tool
itself is not, and notes in passing that **`census.py --selftest` is in neither CI nor the
deliberately-excluded table** — an existing gap, not a decision, and not fixed here.

### What needs a finding number at merge

The scope failure above. Claim: *a figure reproduced to the cent while the sentence around it
described a population of 1 where the tree held 7, and the producer that would have shown it did
not exist.* Measurement, control and both directions are in this note and in the PR body.

## note 2026-08-23

## note 2026-08-23 — the PR's final head, and two corrections found by my own rule

The branch is `task-123-cost-result-producer`, PR #9, final head `55a0901`. Four commits:

| commit | what |
|---|---|
| `9704ecf` | the producer, README, DECISIONS.md, eval/AGENTS.md, CI |
| `eb4fbaa` | `cell_gap_ratio` per group, and the selftest's drift guard |
| `a6337e6` | **the docstring said "6 of 7"; the tool prints 5** |
| `55a0901` | **README's resolution row said "the other 6 groups disagree"; 5 do** |

**The last two are the same error twice, committed by me, inside the file that exists to
prevent it.** One group sits at **96%** — below the line but visually adjacent to it in a
rendered table — and both times I counted the rows by eye instead of reading
`groups_where_range_exceeds_floor` out of the producer I had just written.

> **A producer does not stop you writing the wrong number. It only makes the wrong number
> findable.** Both were found by re-running the tool and diffing its output against my own
> prose, which is a step, not a property of having built the tool.

The one figure that moved between the hand calculation and the producer is the worst
one-cell floor error: eyeballing the rendered table gave **32.9x**, the tool gives **33.0x**
(the rendered gaps are rounded to the cent). `eval/AGENTS.md` states 33.0x.

## note 2026-08-23

## note 2026-08-23 — rule 12 fired on the review poll, in a shared scratchpad

**The review poll was silently repointed at another agent's pull request mid-run.**

`.claude/skills/work/SKILL.md` §6 gives the poll recipe with `PR=<n>` as a literal. I wrote
it to `scratchpad/pollreview.sh` — a generic name in a directory **shared with every
concurrent session** — and a concurrent agent working task 124 wrote its own copy to the
same path with `PR=10`. My background loop calls the script by path each iteration, so from
that moment it was polling **PR #10, `task-124-ci-path-filter-and-minutes`**, and reporting
`not yet` about it. Exit 0 throughout. Nothing in the output named the PR.

That is `AGENTS.md` rule 12 exactly — a correct method aimed at an address nobody
re-verified — and it is the *shared mutable address* variant, which the rule's own table of
five instances does not contain.

**What replaced it**, at `scratchpad/task123-poll-pr9.sh`:

- **named for the ticket and the PR**, so a collision is a different file rather than a
  silent overwrite;
- it **asserts the address before believing the answer** — `headRefName` must equal
  `task-123-cost-result-producer`, or it exits 1 with `WRONG PR` rather than returning a
  poll result;
- every line of output carries the head sha it read.

Control, both directions: against `PR=9` it returns `not yet (... head=55a0901)` at exit 0;
the same script with `PR=10` returns `WRONG PR: #10 is 'task-124-ci-path-filter-and-minutes'`
at **exit 1**.

> **A poll result that does not name what it polled is not a result.** The skill's recipe
> hardcodes the PR number and prints only the sha, so a wrong `PR=` is invisible in the
> output — and a scratchpad is a shared address. Worth folding the branch-name assertion, or
> at least "print the PR you polled", back into `.claude/skills/work/SKILL.md` §6.

## note 2026-08-23

## note 2026-08-23 — rebased onto main; two conflicts, both real content

`main` moved while this was in flight (task 122 merged, PR #8), and the branch stopped
merging. `git merge-tree --write-tree origin/main HEAD` reported conflicts in `README.md`
and `.github/workflows/README.md` **before** any rebase — worth running, because
`gh pr view --json mergeable` said nothing until the push.

Rebased rather than merged. Final head **`7bcf4ec`**, `mergeable=MERGEABLE`, PR diff still
exactly the same 6 files, 817 insertions.

Both conflicts were content, not whitespace:

| file | what collided | resolution |
|---|---|---|
| `README.md` | task 122 rewrote the **row above mine** — the paired-trials row now names `eval/judge/paired_verdicts.py` instead of the withdrawal register. My change is the **cost row** | kept main's paired-verdicts row **and** my cost row. Verified `paired_verdicts.py --selftest` is exit 0 on the rebased tree |
| `.github/workflows/README.md` | task 122 added a *deliberately-not-in-CI* row for `paired_verdicts.py`'s corpus half; I added one for `census.py`/`cost_census.py` | kept both rows |

The `Measured` table merged cleanly and already carries my `cost_census.py --selftest` row.

**The rebase also caught the "6 of 7" error a third time**, in the sentence introducing the
instrument table: *"a figure true of one group and not of the six others like it"*. Same
mistake, third location, and I had already fixed it twice in this session. It now reads *"a
figure from the single most favourable of the seven comparable groups"*, which states the
relation rather than a count I keep getting wrong.

> **When a figure has resisted three attempts to phrase it, stop phrasing it as a count.**
> `5 of 7` and `the lowest of 7` are both correct and only one of them is easy to get wrong,
> because the group at **96%** is below the line and looks above it in a rendered table.

Gates re-run green after the rebase: `docstat --sweep/--findings/--withdrawn`, `linkcheck`,
`tasks.py check`, `lint --gate --rule invalid-syntax`, `cost_census --selftest`,
and main's own `judge/paired_verdicts.py --selftest`.

## note 2026-08-23

## note 2026-08-23 — review round 1: 8 comments, 6 acted on, 2 declined

Head `453e8c3`. CI was green on `7bcf4ec` before this round (`gates` 51s, `controls` 10m59s).

### The one that mattered: the mutant count had no producer

`DECISIONS.md` said *"14 mutants and 3 variants"*. The reviewer read the selftest's own
`# Direction` comments and said **11**. **Neither number was checkable** — the mutants lived
in a scratchpad that dies with the session, and a mutant is a modification *of the tool*, so
no count read out of `cost_census.py` could have been right either.

> **This ticket is about a figure with no producer, and I published one inside the paragraph
> that states the rule.** The rule does not fail by being absent. It fails because "the
> mutant count" does not look like "a quantity", and the trigger in `AGENTS.md` is a
> property — *how much of anything the project has* — that a reader has to recognise the
> instance as belonging to.

Shipped **`eval/tools/cost_census_mutants.py`**, matching `bot_mutants` / `tasks_mutants` /
`disclosure_mutants`. The count is `len(MUTANTS)` = **19**; `--list` prints it; 1.5s, no
corpus; wired into CI fast.

**Running it found what the hand sweep had hidden.** 2 of the 19 were exiting non-zero via a
**traceback** rather than reddening a named check — both reading `across_groups[...]` past a
field the mutant had renamed. A by-hand pass scores those as *caught*: exit non-zero, mutant
detected. They were telling me nothing about which mechanism had gone.

> **Exit status is not diagnosis.** The suite now requires **at least one named failure** per
> mutant, not merely a non-zero exit, and reports any mutant that merely crashed. That
> distinction is invisible to a person running mutants by hand, because they read the
> traceback and know what it means — the next session does not.

### The other five acted on

| # | defect | why it was invisible |
|---|---|---|
| 2 | `--min-trials-per-cell 1` / `--min-stacks 1` accepted | **the thin-cell fail-open, reachable by a flag instead of by data.** The guard I was proudest of could be turned off from the CLI |
| 3 | no `stack`, or a non-numeric cost, raised `KeyError`/`TypeError` | `main()` catches only `CostCensusError`, so a parseable-but-unusable record gave a traceback where a named, fail-closed error belongs. `cost_usd: true` is covered — **a bool is an int in Python** and would have averaged as 1.0 |
| 4 | exceedance counted off the **percentage** | a zero-floor group has no percentage, so a group whose range exceeds its floor *as completely as a group can* dropped out of the count. **Fail-open, understating how much the stacks disagree** |
| 5 | `render()` formatted `None` with `:.0f` | the DATA path was right and the tool died on the way to the terminal. **The selftest never called `render()`** |
| 6 | the pooled **mean stack rank** | rule 4, and the reviewer was right |

**On #6.** I had published `mean_cost_rank` with a printed disclaimer. The disclaimer does not
survive re-quotation, and 7 groups over 4 runs and 4 games under different budget caps are not
a population anyone has shown homogeneous. Replaced with the rank **vector** and a count of
firsts — same information, cannot be read as a statistic, and it is what `tasks/126` needs:

    ts     [1, 1, 1, 1, 2, 3, 1]   cheapest in 5 of 7

### The two declined, each with a measurement

**Reference-style `[#63]` links in `eval/AGENTS.md` and `DECISIONS.md`.** `linkcheck.py`'s
`LIVE_DOCS` is 4 files and `eval/AGENTS.md` is not one — the link would be checked by nothing,
which `DECISIONS.md` calls worse than a bare number. `DECISIONS.md` **is** live and has **0**
reference definitions against **37** bare `(#NN)`. Making exactly the suggested edit:
`linkcheck.py` exit **1**, `shortcut reference #63 has no definition in this file`; reverting
it, exit **0**.

**Atomic writes in the selftest's `_write()`.** The guideline's resource is *a durable artifact
with more than one writer*. `_write()` is called only from `selftest()`, single-process, into a
`TemporaryDirectory` that is deleted on exit. Complying would be the rule audit's own failure
mode — a trigger re-derived from the mechanism (`os.replace`) rather than the resource.

### Found while wiring CI, and not mine

`.github/workflows/README.md` said the `gates.yml` budget was **42s** and states in the line
below that *the budget IS the sum of the rows*. Those 17 rows summed to **37.9s**. Nothing
re-adds them, so it drifted — **the same defect as this ticket, one directory over.** With my
2 rows the true sum is **39.5s**, which the table now says, with a note. There is still no
producer for it; a `--budgets` flag on something would be a small task.

Every published figure is unchanged: the full run over `eval/runs` is byte-identical before
and after this round.
