---
id: 123
title: README publishes a cost result with no producer, and it is the last such number in the file
status: in_review
priority: 2
refs: 'README.md cost row, eval/findings/limits-and-cost.md #63, eval/tools/census.py, eval/runs/wg-g4c-2026-08-21T02-26-46, tasks/115'
done_when: a producer prints the cost result with the population it counted and a selftest that pins it in both directions; README cites the command beside the figure; and either the published figures are reproduced exactly or the differences are stated with which is right and why
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/9
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
