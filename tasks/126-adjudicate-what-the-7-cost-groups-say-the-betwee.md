---
id: 126
title: 'Adjudicate what the 7 cost groups say: the between-stack range exceeds the within-cell floor in 5 of 7, and ts is cheapest in 5 of 7'
status: in_testing
priority: 2
refs: 'eval/tools/cost_census.py, README.md cost row, DECISIONS.md ''The cost route is re-opened'', eval/findings/limits-and-cost.md #63, eval/RUNS.md, tasks/123'
done_when: the ordering question is decided one way or the other with the statistic named and its dependence structure stated (runs, not groups, as the independent unit - say what n you treated as independent and why); a negative result is a complete answer and closes this; README's cost row and DECISIONS.md's 'The cost route is re-opened' section are updated to whatever is established, with the producer command beside every figure and run in the same session; and if the conclusion is that cost DOES separate the stacks, that is a finding number and it changes the count of instruments reaching the null in README's result section
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/12
established_by: 'Adjudicated: the ordering does NOT resolve. Exact permutation of stack labels within a cluster, post-hoc-safe statistic, n=4 runs (ticket''s unit) p=0.0156 which IS the design floor; n=4 games p=0.0469; n=2 connected components of run-and-game p=0.25 which is also that design''s floor, so at the honest unit no outcome could have reached alpha. ts leads 5 of 7 but its margin is below that group''s own noise floor in 5 of 5. README cost row, README route row, DECISIONS.md section and reversal condition, and eval/AGENTS.md all updated; producer is cost_census.py --ordering, 39 mutants all caught with a named failure, census output byte-identical to main; gates.yml SUCCESS on final head a84d12c, controls.yml SUCCESS on two earlier heads and still running on the final one; 5 review rounds, the fifth clean.'
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

## note 2026-08-23

## The adjudication, and why it is a refusal rather than a result

**Decided: the ordering does not resolve, and no reading of the stored tree can make it.**
Producer `python3 eval/tools/cost_census.py --ordering` (shipped in this task; `--json` too).

**The statistic.** Exact permutation test on usage ranks, stack labels permuted **within a
cluster** and held constant across every group in that cluster. Null: which stack got which
of a group's four cells is arbitrary. The leader was chosen **post hoc**, so the statistic is
*the smallest rank sum any of the four stacks reaches* — the version that carries its own
multiplicity. `ts` rank sum **10**, null expectation **17.5**.

**n, and why.** The ticket named the run. That is **n = 4**. But the runs are not independent
of each other, which the ticket did not anticipate: **3 of the 4 games recur across runs**, so
a stack cheap on one game contributes the same evidence twice. Three units, reported side by
side because the tool must not pick one for you:

| unit | n | p post-hoc-safe | smallest p the design can return |
|---|---|---|---|
| run directory | 4 | 0.0156 | **0.0156** |
| game | 4 | 0.0469 | 0.0156 |
| connected component of run **and** game | **2** | **0.25** | **0.25** |

**Two reasons this is unresolved, not significant.**

1. At the run unit **the observed p IS the design's floor** — `4 x (1/4)^4`. `ts` holds the
   cheapest column in all four runs, the most extreme outcome available. Anything short of a
   perfect sweep returns the next attainable value, above 0.05, and **dropping any single run
   puts the floor at 0.0625** — no subset of 3 runs could have reached alpha whatever it said.
2. **6 of the 7 groups are one connected component**, where the smallest attainable p is
   **0.25**. At that unit the question is **not answered no; it is unasked.**

**The lead is also inside the noise.** Where `ts` leads, its margin over the runner-up is
**15% to 94% of that group's own within-cell floor — above it in 0 of 5.** Consistency of an
ordering and a lead that beats the noise are different claims; only the first was ever testable
here.

**README's count of instruments reaching the null does NOT change.** This route reaches no null
either — which is exactly what its row already said.

## Do not re-derive these

- **The closed forms.** With k stacks and m clusters an unbroken lead has probability
  `(1/k)^m` for a stack named in advance and `k*(1/k)^m` post hoc. Every selftest fixture's
  expected p is one of these, written down before the tool runs. The corpus numbers are
  `1296/331776` and `5184/331776` and they are exactly `1/256` and `1/64`.
- **`attainable_min` is closed-form, not read off the enumeration.** Permutations are
  independent per cluster, so the smallest total one stack can be driven to is the sum of each
  cluster's smallest column. The enumeration then counts against it, so the two disagree if
  either is wrong.
- **Why there is still no mean rank.** Task 123's refusal stands. This does not replace it with
  an average; a permutation test over clusters is the thing a mean was refused for being unable
  to be.

## What tripped me, so it does not trip the next agent

- **Adding these pins broke the EXISTING `drop_field` mutant** from `caught (67 named
  failures)` to `caught (0 named failures — traceback)`. Cause: an O6 pin subscripted
  `got["leader_margins"][0]`, a `TypeError` when the ordering could not be produced — and a
  selftest crash **loses every failure collected before it**, because they print at the end.
  Read a fixture's rows through a guard that records a named failure. Established against the
  pre-change checkout first (rule 14).
- **`runner_up` was set only on rows where the leader led**, so the `leader_is_dearest` mutant
  died on a `KeyError`. Every margin field is now present on every row unconditionally.
- **Two guards refuse the same empty population.** `no_groups_guard` mutated away is still
  refused — by the stack-set guard, with a message naming the wrong thing. The refusal pins
  assert the **message**, not the exception type; a type-only check was satisfied by whichever
  guard fired.
- **`cost_census_mutants.py` went 21 -> 35 and 2.0s -> 6.4s.** Both figures are in its
  docstring; the count is `len(MUTANTS)` and re-derives itself.

## A finding for the orchestrator to number — NOT allocated here

> **A design's smallest attainable p-value is a property of its cluster structure, and it can
> rule a question out before any data is seen.** The 7 stored cost groups look like 7
> observations and are **2** independent clusters, because the games recur across runs. At that
> structure the smallest post-hoc p obtainable is `4 x (1/4)^2 = 0.25` — **no outcome
> whatsoever could have reached alpha = 0.05.** The 5-of-7 headline is simultaneously the most
> extreme result the corpus can produce **and** not evidence. Measurement:
> `python3 eval/tools/cost_census.py --ordering`, the `smallest p this design could return`
> line, exact over 576 assignments. It generalises past cost: **any** adjudication over these
> run directories inherits the same 2-cluster ceiling, so "re-read the stored tree" is not a
> route to settling a between-stack question, whatever the quantity.

## What would settle it, and it is not a re-reading

**4 qualifying groups sharing neither a run nor a game** restores a 0.0156 floor with
independent clusters behind it. The stored tree cannot be rearranged into that. Recorded as the
reversal condition in `DECISIONS.md`.

## Not established

- Whether TypeScript really uses fewer tokens. The corpus cannot decide it.
- Whether any ordering effect is the **stack** rather than the starter or the task. The
  permutation test rejects label exchangeability and cannot attribute it.
- `.github/workflows/README.md` states `gates.yml` **takes 51.9s**. That is measured from CI
  runs, and this task adds ~4.3s locally to the `cost_census_mutants` step. I did not rewrite
  it from a local measurement on a different machine; the honest re-read is this PR's own
  `gates.yml` duration.

## note 2026-08-23

## Corrections to the note above, and what review round 1 found

**The CI figure, measured properly.** The note above said "~4.3s locally" and left it there.
The isolated step measurement is better and it is this: `cost_census_mutants` runs **2s on
`main`** (gates run 32665742872) against **12s on this branch** (gates run 32669818592), read
from the per-step timings in `repos/.../actions/runs/<id>/jobs`. So `gates.yml` gains about
**10s** on the CI runner, not 4.3s.

**I did not change `.github/workflows/README.md`'s `51.9s`, and the reason is a measurement.**
Run-level wall clock cannot settle it: the last 10 successful `gates.yml` runs on `main` span
**54s to 78s**, which is wider than the delta being attributed. Attributing a run-level number
to my change would be a single-variable attribution across noise larger than the effect
(`AGENTS.md` rule 8). The real defect is that the figure has **no producer**, so nobody can
tell what population it was measured over. **Filed as task 129.**

**Round 1 of review found a real defect in this task's own code**, and it is the one worth
carrying forward:

> `leader_margins` decided who led a group with `means[0][1] == leader`, and `means` sorts on
> `(mean, stack)` — so **two stacks at the same mean were separated by their NAME**, and the
> one that won that tiebreak was recorded as leading the group by $0.00.

The tell was already visible in the output and nothing read it: on a tied group the tool
reported `groups_led = 1` and `times_cheapest[leader] = 0` **at the same time**. Two counts of
one claim, disagreeing, and both were printed. Leadership now comes from the tie-aware rank
(`r[leader] == 1.0`) — the rule `times_cheapest` already used. **The stored corpus has no ties,
so every published figure is unchanged**; the defect was latent, and would have fired the first
time two arms landed on the same mean.

Mutant `leads_by_alphabetical_tiebreak` restores the old expression, and measured, the O5 pin
is the only check that reddens it.

**`margin_where_it_lost`'s search text had to move in the same commit.** A mutant whose search
text drifts prints `NOT APPLIED` and tests nothing. Any change to a line a mutant names is a
change to that mutant.

**"Exact permutation" was true only at the current corpus size.** A fifth stack takes m=4 to
**207,360,000** assignments and a fifth run takes k=4 to **7,962,624**, both over the
`EXACT_ASSIGNMENT_LIMIT` of 2,000,000 that selects the seeded-sample path — and **both are
recorded re-open conditions in `DECISIONS.md`**. So the word would have gone false exactly when
the question was re-opened. Corrected at all 3 sites; the output reports its own mode and
`DECISIONS.md` states it for the run it records.

**Mutant count 21 -> 37**, all caught with a named failure, control green.

**The variant/mutant pairings in `cost_census_mutants.py`'s docstring are measured**, not
assigned: each mutant was run and the `FAIL` labels it reddens were read off. Do not hand-pair
them if the table is ever extended.

## note 2026-08-23

## Review rounds 2 and 3 — three lessons the next agent should not re-derive

### Round 2: a guard on the far side of the resource it guards

`_permutation_test` built `list(itertools.permutations(range(k)))` and the full per-cluster
vector table, **then** compared the assignment count against the limit that exists to prevent
exactly that. Measured at k=10 over one cluster: **2085 MB** peak RSS deciding after, **24 MB**
deciding before. Both structures return identical numbers, so no pin on a return value can see
it — the pin has to be on the RESOURCE (rule 13).

### Round 3: three Major findings on one path, and the right answer was to delete it

The findings were (1) `resolves` comparing a 50,000-draw estimate against `ALPHA`, so a true p
near 0.05 decides by luck of the draw; (2) `ru_maxrss` is a process-**lifetime** high-water
mark, so my own memory pin would sit at zero once anything earlier allocated more — a check
that stops working without ever going red; (3) the eager-allocation mutant reaching 2 GB
unbounded inside the sweep.

**All three were about scaffolding no stored data exercises.** Every qualifying design in the
corpus is 331,776 assignments — exact. So `--ordering` now **refuses above its enumeration
limit** instead of sampling, which is the answer this tool already gives for a missing tree.
Finding 1 disappears with the estimate. Finding 3 shrank from 2 GB to ~140 MB. Finding 2 is
fixed properly: peak RSS is measured in a **fresh child process** that imports the module under
test **by path**, so a mutated copy measures itself.

> **The generalisable part: when a review finds three defects in one mechanism, ask what the
> mechanism is buying before patching it three times.** The sampled path served a hypothetical
> re-open condition and cost three Major defects plus 12s of every CI run. Deleting it removed
> all three and took the sweep from 17.9s to 5.7s.

**If someone re-opens this with a fifth stack or a fifth run, the tool will refuse, and that is
deliberate.** `k=5, m=4` is 207,360,000 assignments and `k=4, m=5` is 7,962,624 — both past the
limit. Widening the corpus means implementing a sampled test **with a confidence bound**, not
raising the limit. The refusal message says so.

### The defect worth more than any of the three, found while fixing them

**`render_ordering` referenced a field the producer had stopped emitting. `--ordering` died on a
`KeyError` while `--selftest` reported `ok (0 failures)`.** Nothing in the selftest had ever
called the renderer — every pin read the result dict.

> **A producer and its report are two components. Pinning one is not pinning the other**, and
> the report is the part a person actually runs. O7c renders a fixture and asserts the lines
> that decide the adjudication survive; `render_drops_the_fragility_line` proves that row can
> go red.

### Mutant search text is code, and it drifted three times

`margin_where_it_lost`, `drop_ordering_field` (twice) and `render_drops_the_fragility_line` all
went `NOT APPLIED` after an edit to a line they name. The sweep caught every one and refused to
count it as a pass, which is the mechanism working — but **treat any edit to a line a mutant
names as an edit to that mutant.**

### My own pins raised instead of naming a failure, three times

`first_margin`, the refusal helper, and the render pin each had to be wrapped so a missing
field records a NAMED failure. A selftest that crashes **loses every failure collected before
it**, because they print at the end — so a traceback is strictly worse than a FAIL row even
though both exit non-zero. This is `drop_field`'s lesson and I re-learned it three times in one
task.

### Final state

38 mutants, all caught with a named failure, control green. Base `--selftest` ~0.2s, sweep
5.7s locally. Census output byte-identical to `main` throughout. Every published figure re-read
and unchanged: **0.0156 / 0.0469 / 0.25**, fragility floor **0.0625**, `ts` leads **5 of 7**
and beats its own noise floor in **0 of 5**.

## note 2026-08-23

## Review round 4, and the shape all four rounds share

Round 4 found the case rounds 2 and 3 both missed, and it is the cleanest statement of the
defect:

> **`EXACT_ASSIGNMENT_LIMIT` budgets `(k!)**m` — a count of ASSIGNMENTS, which is a TIME
> cost. Materialising a table of relabelled vectors costs `k! * m` of them, which is a
> MEMORY cost. The two decouple at high k with low m**, so a design is comfortably
> **accepted** by the limit and still allocates hundreds of megabytes. 9 stacks over 1
> cluster is 362,880 assignments against a limit of 2,000,000.

Measured, same input, identical result (`p_named = 0.111111` both ways):

| | grew | elapsed |
|---|---|---|
| materialising | **199 MB** | 0.31s |
| streaming | **0 MB** | 0.15s |

The enumeration no longer materialises. It descends the clusters, draws each permutation
from `itertools.permutations` as a generator, and carries the running vector down. Memory
is O(k·m) at any k, and it is **faster**, because partial sums are shared by the subtree
below them instead of recomputed per assignment.

**An allocation-specific limit was the obvious alternative and would have been worse** — a
second thing to get wrong, guarding a quantity that did not need to exist.

**The pin covers BOTH sides of the limit, and only one of them catches this.** The refusal
path (9 stacks, 2 clusters) never reaches the allocation, so the accepted design beside it
(9 stacks, 1 cluster) is the row that matters. Both run in a child process under a 60 MB
ceiling.

## What all four rounds had in common

Rounds 2, 3 and 4 were the same defect seen three times: **a guard whose trigger names a
different quantity from the resource it protects.** Round 2 was the guard on the wrong side
of the allocation; round 3 was a p-value threshold applied to an estimate; round 4 was a
limit on time protecting against memory. None of the three was visible from the return
value — every one needed a pin on the RESOURCE.

> **When a review finds several defects in one mechanism, ask what the mechanism buys before
> patching each one.** The sampled path cost three Major findings and 12s of every CI run to
> serve a hypothetical. Deleting it removed all three.

## Three procedural things that cost me time, so they should not cost the next agent any

1. **Mutant search text is code.** `margin_where_it_lost`, `drop_ordering_field` (twice),
   `render_drops_the_fragility_line`, `p_any_is_p_named` and `p_excludes_the_observed` all
   went `NOT APPLIED` after an edit to a line they name — including a bare re-indentation.
   The sweep refused to count any of them as a pass, which is the mechanism working.
   **Treat any edit to a line a mutant names as an edit to that mutant.**
2. **My own pins raised instead of naming a failure, three times.** A selftest that crashes
   **loses every failure collected before it**, because they print at the end — so a
   traceback is strictly worse than a FAIL row even though both exit non-zero. Read a
   fixture's result through a guard that records a named failure.
3. **A producer and its report are two components.** `render_ordering` died on a `KeyError`
   while `--selftest` was green, because every pin read the result dict and nothing had ever
   called the renderer. The report is the part a person runs.

## Final state

**39 mutants**, all caught with a named failure, control green. Base `--selftest` ~0.2s;
sweep ~6s locally; the `cost_census_mutants` CI step measured **10s** at round 3 against 2s
on `main` (see task 129, which corrects an earlier 47s reading of mine). Census output
byte-identical to `main` throughout all four rounds.

**Every published figure re-read at the final head and unchanged:** p = **0.0156** (run),
**0.0469** (game), **0.25** (connected component); fragility floor **0.0625**; `ts` leads
**5 of 7** and beats its own within-cell noise floor in **0 of 5**.

## note 2026-08-23

## Round 5 came back clean, and then CI caught what the local sweep could not

**Round 5: "No actionable comments were generated."** That is the clean round the procedure
says to stop on, after 4 rounds that each found real defects.

**But the head round 5 reviewed was RED in CI**, and the failure is worth carrying because
it is a shape no local run can produce:

> **`materialise_the_assignments` was caught on macOS and SURVIVED on the Linux runner.**
> The pin compared the child process's **TOTAL peak RSS** against 60 MB. A total carries the
> interpreter's own baseline, and that differs by platform — so the same allocation landed
> above the ceiling on one machine and below it on the other. **A threshold calibrated on
> the machine you are sitting at is not a threshold.**

It now measures the **GROWTH** across the call — the child reads `ru_maxrss` before and
after and returns the difference — which cancels the baseline and is the quantity the pin
was always about. Against a 25 MB ceiling:

| | shipped (streaming) | mutant (materialising) |
|---|---|---|
| accepted `k=9 m=1` | 0.0 MB | **97.3 MB** |
| refused `k=9 m=2` | 0.0 MB | 0.0 MB |
| corpus `k=4 m=4` | 0.0 MB | 0.0 MB |

**The refused row reads 0.0 under the mutant on purpose** — the allocation sits after the
refusal raises, so **only the accepted arm can catch it**. `limit_checked_after_allocation`
is the mutant the refused arm catches, and it still does. Two arms, two mutants, neither
redundant.

The mutant also now restores **both** structures the code used to build (the permutations
list and the relabelled table) rather than only the table, so it is a faithful restoration
rather than a cheaper stand-in that happened to sit near the boundary.

`_refusal_in_child` is renamed `_permutation_in_child`: it runs an accepted design as well
as a refused one, and the old name described half of what it does.

> **The generalisable rule, and it is rule 12 with a machine axis: a check whose verdict
> depends on a baseline is a check that reports the baseline.** Measure the delta, and prove
> the mutant reddens on the platform the gate runs on — a local mutant sweep cannot tell you
> that.
