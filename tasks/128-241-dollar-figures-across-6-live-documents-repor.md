---
id: 128
title: 241 dollar figures across 6 live documents report token valuations as money
status: todo
priority: 1
refs: 'FINDINGS #159, eval/RUNS.md 132 figures, eval/judge/JUDGING.md 48, eval/PROTOCOL.md 28, DECISIONS.md 21, eval/AGENTS.md 9, AGENTS.md 3, eval/tools/census.py, eval/judge/judge_ledger.py, eval/tools/runstat.py'
done_when: each live document either states the figure as a token valuation with its unit named, or drops it; the producers print a label that cannot be read as expenditure; a check exists that would catch a new live document calling it spend, with its false-positive count on the live corpus measured and stated before it ships; and any conclusion resting on a dollar amount rather than on token counts is re-examined and the outcome recorded either way
---

The account is a subscription, so no per-token charge applies. agent.cost_usd is exactly sum(modelUsage[*].costUSD), a list-price valuation the CLI computes from token counts whatever the billing arrangement. README and DECISIONS.md were corrected at the point the misnaming had changed a decision; the other 241 figures and the 8 producers that print them still say dollars and spend. The token counts are real and every comparison built on them stands - what is wrong is the unit and the noun.

## note 2026-08-23

## Extended 2026-08-23 — the limits, not just the labels

`DECISIONS.md` now carries "No run is bounded by a money figure; token counts and time are
measured, not capped". Two things follow that this ticket must also do:

**Replace the money bounds in `eval/judge/field_sweep.py`.** `--max-cost` defaults to 60.0 and
`--per-call-budget` to 12.0, and the sweep refuses a call when `spent + per_call > max_cost` — so
a sweep truncates at roughly $48 of *valuation*, stopping part-way through its evidence on a
threshold nobody is charged for. Bound it by something finite instead: round count, wall clock, or
rate-limit capacity. **Keep printing the token totals** — they are the measurement and they stay.

**Do not simply raise the numbers.** A larger ceiling in the same unit is the same defect further
away, and this project has a name for tuning a parameter until it stops firing.

**Check whether any stored sweep was truncated by it** before assuming none was. `GATES.json`
carries `charged_to_ceiling_usd`; the blind field read 27.68 and stopped because it finished, not
because it hit anything. If a stored sweep did stop short, its evidence is incomplete and that is
a comparability note for `eval/RUNS.md`, not just a code fix.

**The build side is already right and needs no change.** `MAX_BUDGET_USD = None`, bounded by
`--max-turns 1000`, which is invisible to the agent and truncates rather than instructs. Do not
"tidy" it into a symmetric money cap.

**Token counts and wall clock are NOT the target of this ticket.** They are real, they are the
only per-trial resource numbers the harness has, and they are how output gets weighed against
resource used. Renaming the unit must not become deleting the measurement.

## note 2026-08-23

## Updated 2026-08-23 — a new producer landed that prints dollars, and two documents were already corrected

**`eval/tools/cost_census.py` now exists** (task 123, PR #9) and prints the cost figures with a
`$`. It is the producer this project asked for and it is **also an instance of what this ticket is
about**: it reports a list-price valuation of token counts in a unit that reads as money. Include
it in the sweep. Its `--selftest` states expected values as literals and 21 mutants pin it, so
changing what it prints means updating both.

**Two documents are already done and must not be re-done:**
- `README.md` — the result row states token usage, names both #159 and the seven-group scope, and
  cites the producer.
- `DECISIONS.md` — the harder-task row no longer cites a spend, and two new sections were added:
  *"No run is bounded by a money figure"* and *"The cost route is re-opened"*.

**The remaining live documents**, from `grep -c '\$[0-9]'` at the time of filing: `eval/RUNS.md`
132, `eval/judge/JUDGING.md` 48, `eval/PROTOCOL.md` 28, `eval/AGENTS.md` 9, `AGENTS.md` 3.
**Re-count before you start** — this tree moves daily and that is the whole lesson of #144.

**`eval/RUNS.md` is the hard one and it is not a find-and-replace.** It is the run ledger: per-run
figures are what a reader compares runs by. They stay, with the unit named once at the top rather
than annotated 132 times. A note on every line would be worse than the defect.

**What the unit actually is**, for whatever wording you choose: `sum(modelUsage[*].costUSD)`, which
the CLI computes from token counts at published API rates regardless of billing. Verified to the
digit on a stored record. It is a valuation, not a charge, and the token counts underneath it are
real.

**Do not delete the numbers.** They are the only per-trial resource measure the harness has. #159
says the unit is wrong, not the measurement — and `DECISIONS.md` now records that tokens and wall
clock are kept deliberately.
