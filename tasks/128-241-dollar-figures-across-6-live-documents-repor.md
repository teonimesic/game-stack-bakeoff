---
id: 128
title: 241 dollar figures across 6 live documents report token valuations as money
status: done
priority: 1
refs: 'FINDINGS #159, eval/RUNS.md 132 figures, eval/judge/JUDGING.md 48, eval/PROTOCOL.md 28, DECISIONS.md 21, eval/AGENTS.md 9, AGENTS.md 3, eval/tools/census.py, eval/judge/judge_ledger.py, eval/tools/runstat.py'
done_when: each live document either states the figure as a token valuation with its unit named, or drops it; the producers print a label that cannot be read as expenditure; a check exists that would catch a new live document calling it spend, with its false-positive count on the live corpus measured and stated before it ships; and any conclusion resting on a dollar amount rather than on token counts is re-examined and the outcome recorded either way
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/13
established_by: 'Live documents no longer report token valuations as money: README at 0 dollar figures, PROTOCOL 28 to 5, and where figures remain (RUNS.md 130, JUDGING 49) the unit is named once at the top rather than annotated per line, with the count carrying its own producer. FINDINGS 159 is cited at the header. PR #13 - note it ran 6 review rounds against a ceiling of 5, none at the final head, and was conflicting so CI never ran; all gates were run at merge instead.'
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

## note 2026-08-23

## Done 2026-08-23 — what the next agent must not re-derive

**The unit is `tokval` and it has exactly one definition: `eval/tools/tokenvalue.py`.** All 11
producers import it, print bare numbers, and print `tokenvalue.DEFINITION` beside their output.
`--selftest` (25 pins) reads all 11 producer sources and fails on a money sigil in any of the
**3** forms Python can interpolate a value into a string, and it re-derives the producer list
from the tree so a new one shows up as a problem rather than as nothing. Do not add a second
spelling of the unit; change it here or not at all.

**`tokval` is only true of the figures this project GENERATES.** `research/03-rust-engines.md`
quotes W4 Games' console licence fees, which are real money. The first draft of AGENTS.md said
"every `$` figure in this project", and that was wrong — the review caught it. Any future
statement of the unit needs the same scope.

**The gate is `python3 eval/tools/docstat.py --money`, and it runs inside `--sweep`.** Its red
control is history, not a fixture: `--money --at f598726` reports **21** blocks, `HEAD` reports
**0**. The trigger is the NOUN, not the sigil, and the candidate table is in `DECISIONS.md` and
in `docstat.py`'s comment — `cost` (39 hits, open class), `price` (15, reddens the W4 rows), and
adding `pay` costs 2 false positives on idioms for no true positive. Shipped: `spend`/`charged`/
`billed`/`expenditure`, 21 blocks, **0 false positives**. The exemption is the id `#159`, scoped
to the claim block.

**Why `eval/RUNS.md` keeps 130 `$n` figures instead of respelling them.** They are the ledger a
reader compares runs by, and the ticket said so. The unit is declared once at the top. Anyone
who wants to respell them has to move the money-check trigger from the noun to the sigil first,
and then deal with `research/`'s real prices.

## The sweep bounds, and the measurement that closed the question

`--max-cost` is **retained as a named refusal at exit 2**, not deleted — argparse's generic
"unrecognized arguments" reads as a typo and invites a workaround, and three documents (one of
them the archive, which must not be edited) name the flag. `--max-rounds` and `--max-wall-min`
replace it and are written into every sweep summary beside `stopped_by`.

**Did the money ceiling ever truncate a stored sweep? No — 0 of 12.** No stored summary records
the ceiling it ran under, so it had to be answered from what each sweep did: a truncated sweep
did fewer rounds than it was configured for (`repeats` vs `--repeats`, `orders` vs
`games x aspects x orders`, `sequential` vs its configured pairs). The extraction was proved on
two synthetic summaries whose answer was stated in advance. That gap is now closed at source —
new summaries carry `bounds` and `stopped_by`.

**`--per-call-budget` is deliberately unchanged at 12.0 and this is the live open question.** It
still reaches each judge as `--max-budget-usd`, which is visible to the callee and instructs it
(#33). Removing it makes every future round non-comparable with the 97 on disk, so it needs a
pre-registration and a paired control — not a side effect of a relabelling. `judge.py`,
`judge_pairwise.py` and `judge_design.py` pass the same flag and were left alone for the stronger
version of the same reason: `judge.py` is the tier-3 path and changing what it is told re-opens
comparability for every stored grading.

## Two fail-open defects the review found, both now pinned

- **`runstat.py` summed a missing `agent.cost_usd` as 0.00** into the group total and mean while
  printing `n/a` in the row above it. `--selftest` is new, 10 pins, with the old expression
  evaluated beside the real aggregation as the mutant.
- **`tokenvalue.py`'s discovery knew f-strings only**, so `"$%.2f" % cost_usd` in an unlisted
  module was invisible to it and left the selftest green. That is the variant direction, not the
  mutant one.

## For the orchestrator

**A finding candidate, unnumbered** (this agent does not allocate): *no stored judge sweep records
the bound it ran under*, so "was this sweep truncated?" was unanswerable from the artifact and had
to be reconstructed from round counts. Answer over the 12 stored summaries: 0 short. Same shape as
`AGENTS.md`'s *"capture what the instrument DID"*.

**`eval/RUNS.md` gained a NINETEENTH comparability break** for the sweep-bounds change. Check the
ordinal against `main` before citing the number; cite the heading.

**`eval/RUNS.md`'s judge totals were stale** and are re-read from the producer: 97 rounds over 12
directories, 334.41, against a published 93 / 11 / 306.73 — the `wg-g4c-.../judge-blind-2026-08-23`
directory was missing from the table entirely.

**`tasks/130` was filed** from a review comment: the g1_pong round-1 mean is stated as both 4.39
and 4.38 (13.16/3, rounded up in one document and truncated in the other), on a figure whose
rounds have no surviving artifact. Deliberately not fixed here — which way it goes is a decision.
