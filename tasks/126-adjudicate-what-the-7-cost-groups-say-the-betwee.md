---
id: 126
title: 'Adjudicate what the 7 cost groups say: the between-stack range exceeds the within-cell floor in 5 of 7, and ts is cheapest in 5 of 7'
status: todo
priority: 2
refs: 'eval/tools/cost_census.py, README.md cost row, DECISIONS.md ''The cost route is re-opened'', eval/findings/limits-and-cost.md #63, eval/RUNS.md, tasks/123'
done_when: the ordering question is decided one way or the other with the statistic named and its dependence structure stated (runs, not groups, as the independent unit - say what n you treated as independent and why); a negative result is a complete answer and closes this; README's cost row and DECISIONS.md's 'The cost route is re-opened' section are updated to whatever is established, with the producer command beside every figure and run in the same session; and if the conclusion is that cost DOES separate the stacks, that is a finding number and it changes the count of instruments reaching the null in README's result section
---

Task 123 shipped eval/tools/cost_census.py, the producer README's cost result never had. It reproduces every published figure to the cent and disagrees with the scope around them. README said 'the one measure taken on all four stacks at once'; there are 7 such (run, game) groups in the stored tree, the published 42% ratio is the LOWEST of them, the seven run 42% to 254%, and the between-stack range EXCEEDS the within-cell noise floor in 5 of 7. The mechanism half of #63 survives - cost tracks turns at r = 0.65 to 0.97 in all 7 groups, and turns vary by up to 165 inside one stack's cell - but the ratio half, which is what reached the null, does not. README and DECISIONS.md now say the route is re-opened. What nobody has adjudicated is the ordering the same producer prints: the TypeScript arm has the LOWEST stack mean in 5 of the 7 groups (mean cost rank ts 1.43, unity 2.29, godot 3.14, rust 3.14). That is not a test and must not be published as one: the 7 groups are not independent - 3 come from wg-matrix, 2 from wg-audio48 - and every cell is n=2, so a within-cell gap is the range of two samples and the floor built from four of those is itself very noisy. #63's own lesson is that a floor estimated from too few cells can be wrong by a factor of 7. This costs NOTHING to settle: the producer is offline, no trial is bought, and the answer is a reading of 56 stored trial records that already exist.

## note 2026-08-23

## Updated 2026-08-23 at dispatch — what the producer already prints, and the two traps

`eval/tools/cost_census.py` landed with task 123 and prints everything this ticket asks about.
**Run it first; do not rebuild the census.** `--selftest` states its expected values as literals
and `cost_census_mutants.py` pins it with 21 mutants.

What it prints today, re-run at dispatch:

    range as a percentage of the floor   42% - 254%; the range EXCEEDS the floor in 5 of 7
    r(cost, turns)                       0.653 - 0.971
    widest turn span in any one cell     165 turns
    per-cell spread, over 28 cells       1.02x - 2.15x
    cost rank per group, 1 = cheapest:
      godot [2,3,4,3,4,2,4] cheapest in 0 of 7
      rust  [4,4,3,4,1,4,2] cheapest in 1 of 7
      ts    [1,1,1,1,2,3,1] cheapest in 5 of 7
      unity [3,2,2,2,3,1,3] cheapest in 1 of 7

**TRAP 1 — the groups are not independent, and the tool says so.** 3 of the 7 come from one run
and 2 from another, every cell is n=2, and they span different games under different budget caps.
The tool deliberately prints **no mean rank** because a mean over them is the one number here that
could be re-quoted as a result (rule 4). **Do not compute one.** If you conclude anything about
`ts`, it has to survive being stated per group.

**TRAP 2 — the quantity is not money and the correlation is not a finding.** `cost_usd` is a
list-price valuation of token counts on a subscription account (#159), and `r(cost, turns)` is
arithmetic: the figure is computed from tokens and tokens scale with turns. **Do not report the
correlation as evidence of anything about stacks.** Write in token-usage terms.

**What a real result would look like**, and either outcome closes this: `ts` is cheapest in 5 of 7
groups **and** that holds when the groups are read one at a time with their n and their regime —
or it does not, and the 5-of-7 is an artifact of which runs happen to be in the tree. Chance for
one arm to lead a 4-way group is 25%, so 5 of 7 is suggestive and 7 non-independent groups at n=2
cannot carry it alone. **Saying so plainly is a complete answer.**

**Buys no trials.** This is offline adjudication over stored records.
