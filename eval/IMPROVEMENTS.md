# Improvement loop — the evaluator

`IMPROVEMENTS.md` at the repository root is the same loop for the **product** — the starters and
the task prompts. This file is the loop for the **instrument**: graders, judges, the rubric, the
blinding, and the tools that produce the numbers. Guidance for either — the documents that say
how it is used — belongs to whichever loop it serves.

Each iteration is a hypothesis, a change, and a measurement that could have come out against it.
The falsification criterion is written **before** the measurement runs. A reverted change is a
successful iteration: it bought a real answer.

**The trigger is a change, not an occasion.** A finished matrix supplies most iterations and is
not the only source: a ticket, a sweep of the stored artifacts, or the loose end a previous
iteration handed on land here on the same terms. What was **observed** is a numbered finding in
`eval/FINDINGS.md`; what was **changed** is an iteration here, and one piece of work commonly
produces both.

## Iteration 1b — `ball.wall_bounce` produces false negatives on shallow serves

**Status: PRE-REGISTERED. Found while iteration 1 was blocked; measured on matrix data.**

### The defect

`bot_pong.ball_wall_bounce` idles up to 1200 ticks and requires a `wall_bounce` event
plus a `vy` sign flip. It assumes a ball left alone will reach a wall.

`g1_pong__godot__t0` fails it with **0 events** — while passing `paddle.deflects` with
6 paddle hits. The ball is ping-ponging horizontally between two centre-parked paddles
on a near-flat trajectory and never reaches a wall. The submission's source emits
`wall_bounce` correctly.

The bot waits for a condition instead of creating it. A submission that serves at a
shallow angle is penalised for a choice the task never constrained.

### Why my controls missed it

All three reference implementations were written by me, and all three serve steeply
enough that idle play hits a wall quickly. **A control suite written by the same author
as the assertions shares the author's assumptions.** This is the ceiling problem from
FINDINGS #21 in a new form: not "validated on easy artifacts" but "validated on
artifacts that happen to satisfy an unstated precondition".

### Hypothesis

`ball.wall_bounce` fails on submissions whose serve is near-horizontal, independent of
whether the submission implements wall bouncing correctly. If so it is a false-negative
generator and must not be scored in its current form.

### Falsification

If every submission that fails `ball.wall_bounce` also lacks wall-bounce logic in its
source, the criterion is correct and the Godot case is a genuine defect. I check the
source of every failing submission, not just the one that prompted this.

### Measurement (free, offline)

1. Across all 8 Pong trials, count `ball.wall_bounce` failures.
2. For each failure, grep the archived source for wall-bounce emission.
3. Any submission that emits it and still fails is a confirmed false negative.

### The fix, if confirmed

Stop waiting for a wall bounce and **cause** one. The task states that where the ball
strikes the paddle changes its outgoing angle, so the bot can drive a paddle to meet the
ball off-centre and impart vertical velocity, then look for the bounce. That tests the
same property without assuming anything about serve geometry.

Then re-measure both directions: the corrected criterion must still fail a submission
with no wall-bounce logic, or it has been weakened rather than fixed.

---

## Iteration 4 — which deterministic criteria have ever fired, and were they right?

**Status: PRE-REGISTERED. Tool built; runs when all 24 are evaluated.**

### Why

Three candidate false negatives are now known in the deterministic tiers:
`ball.wall_bounce` (fires only on shallow serves, never on a real defect),
`render.animates` (floor is contrast-sensitive, not motion-sensitive), and
`layer.clears` (already demoted - no correct implementation could satisfy it).

Three is not a list of bugs, it is a pattern: **criteria encoding assumptions about how
a game looks or behaves that the tasks never required.** The tiers were validated
against reference implementations written by the same author as the assertions, so
shared assumptions could not surface.

### Hypothesis

A material share of tier-1 and tier-2 criteria have **never failed any of the 24
submissions**, and of the failures that did occur, a material share are false negatives.
A criterion that never fires contributes nothing while appearing to; one that fires only
wrongly is worse than absent, because it silently penalises a legitimate design choice.

### Falsification

If nearly every criterion fires at least once, and nearly every failure is genuine on
inspection of the submission's source, the tiers are well-calibrated and the three known
defects are isolated bugs rather than a pattern.

### Measurement (free, offline, from stored results)

1. For every tier-1 and tier-2 criterion, across all 24 evaluations: how many
   submissions failed it.
2. Partition: never-fired / fired-and-genuine / fired-and-false-negative.
3. Genuineness is decided by reading the failing submission's archived source, not by
   assuming the criterion was right.
4. Report per game as well as overall - a criterion may be dead on one game and load
   bearing on another.

### What follows

- **Never fired across 24**: not evidence of correctness. Either the property is
  universal among competent submissions (so it cannot discriminate and is decoration),
  or it is untestable as written. Distinguish the two before removing anything.
- **Only ever fired wrongly**: remove or repair. It is actively harmful.
- **Fired and genuine**: keep, and note it as one of the few criteria doing real work.

---

## Adjudication log — every play-bot failure so far is a harness defect

Running tally. Each entry adjudicated against the failing submission's archived source,
not against the verdict.

| submission | criterion | verdict | why |
|---|---|---|---|
| `g1_pong__godot__t0` | `ball.wall_bounce` | FALSE NEG | shallow serve; ball ping-pongs between centred paddles and never reaches a wall. Source emits the event. |
| `g1_pong__unity__t0` | `determinism.replay`, `determinism.seed` | FALSE NEG | second probe session on an open Unity project; refused by the engine. Submission never tested. |
| `g1_pong__unity__t1` | `ball.wall_bounce`, `determinism.replay`, `determinism.seed` | FALSE NEG | both defects above, same trial |
| `g2_tetris3d__rust__t0` | `move.translates` | FALSE NEG | `min x 0 -> 0` — the piece was already against the left wall, so `move_neg_x` was correctly refused. The criterion assumes a push always moves. |

**Genuine defects caught: 0. Harness defects: 4.**

The shared shape: each criterion **waits for a condition instead of establishing one**,
and treats "the condition did not occur" as "the game is wrong".

- `ball.wall_bounce` waits for the ball to reach a wall
- `move.translates` assumes there is room to move in the direction it chose
- `determinism.*` assumes a second session can start

A criterion that depends on incidental state - where a piece happens to sit, what angle
a ball happens to serve at, whether a previous process has exited - measures that
incidental state, not the property it names.

### Fix for `move.translates`

Choose the direction with room. Read the piece's cells and the well width, push toward
whichever side has clearance, and require the shape to be preserved. If neither side has
room the piece spans the well and the check should be skipped rather than failed.

| `g2_tetris3d__unity__t1` | `piece.stacks`, `gameover.triggers`, `determinism.replay`, `determinism.seed` | FALSE NEG | project lock, verified individually |
| `g3_arena__rust__t0` | `enemies.chase` | FALSE NEG | distance to *nearest* enemy rose 75->202 because the closest enemy reached the player and was destroyed on contact, per spec. The criterion fails when chasing works best. |

**Running total: 16 criterion failures adjudicated, 0 genuine.**

The five distinct defects share one root cause: **each criterion measures incidental
state rather than the property it names.**

| criterion | names | actually measures |
|---|---|---|
| `ball.wall_bounce` | does the ball bounce off walls | whether the serve angle happens to reach a wall |
| `move.translates` | does a piece slide | whether the piece happens to have room that way |
| `enemies.chase` | do enemies approach | which enemy happens to be nearest at two instants |
| `determinism.*` | is the run reproducible | whether a second process can open the project |
| `piece.stacks`/`gameover.triggers` | do pieces accumulate / does it end | same |

The fix in every case is the same shape: **establish the condition, or track the
identity, instead of sampling ambient state.** Drive a paddle to create the bounce.
Choose the direction with room. Follow one enemy by id and treat its destruction as
evidence it arrived. Serialise sessions.

---

## The rule for fixing the sixteen: every repaired criterion needs a mutant

Rewriting a criterion from **observation** to **experiment** makes it easier to pass by
construction - that is the point of the fix. So the repair is only half done when the
criterion stops producing false negatives.

**Each fixed criterion must be re-validated in both directions:**

1. It passes every submission that has the property (the 24 archived submissions).
2. It **fails** a mutant with the underlying behaviour removed.

| criterion | mutant that must make it go red |
|---|---|
| `ball.wall_bounce` | remove the vertical reflection in `collide_walls` |
| `move.translates` | ignore the horizontal move inputs entirely |
| `enemies.chase` | make enemies move in a fixed direction, not toward the player |
| `determinism.replay` | seed from a non-reproducible source |
| `determinism.seed` | ignore the seed argument |
| `piece.stacks` | never add locked cells to the settled grid |
| `gameover.triggers` | never set `game_over` |

Sixteen false negatives is a bad outcome. Sixteen false negatives replaced by criteria
that can no longer fail is a **worse** one, and it would look like success. Mutants are
the only thing that tells the two apart.

---

## Iteration 5 — what task would discriminate at all?

**Status: PRE-REGISTERED, probe not yet run.**

### The evidence that motivates it

Pong and Tetris are **exact ties** on adjudicated scores: all sixteen submissions at
1.000, zero spread, zero within-cell variance. Two independent suites - the
spec-change tasks and these whole-game builds - now agree that four well-built
templates on Opus solve everything put in front of them.

### Hypothesis

More trials and stricter grading will not separate these stacks, because there is no
variance to resolve. Separation requires a task with a **failure mode the templates do
not already prevent.**

The templates prevent: nondeterminism (clippy bans, boundary tests, replay hashes),
sim/view leakage (compile-enforced), missing verification (a Stop hook), and API drift
(pinned version notes). A task whose difficulty lies in any of those is pre-solved by
the scaffold, not by the stack.

### Candidate task shapes, in order of how little the templates help

1. **Cross-cutting state over time** - save/load, replay a recorded session, rollback to
   a past tick. The starters ship a state hash but nothing that serialises and restores.
2. **Performance under load** - thousands of entities at a frame budget. Nothing in any
   template addresses throughput, and the stacks genuinely differ here.
3. **Incremental change against an existing large codebase** - the templates are small
   and clean; the differences between stacks may only appear at scale.

### Falsifier

If a cheap probe of one candidate shape produces the same all-1.000 tie, that shape is
not the answer and the hypothesis is wrong about where the variance lives.

### Cost discipline

A probe is **one task, one trial per stack** - four trials, roughly $50 - not a matrix.
Only a shape that visibly separates stacks at n=1 earns a full matrix.

---

## Iteration 2, re-prioritised: the design judges may be where the difference is

If every stack produces a functionally perfect game, then **the remaining differences
are exactly the ones only a subjective judge can see**: whether the result looks good
and feels good to play. That moves the design judge from a nice-to-have to the most
likely place a real between-stack difference exists.

It does not change the validation bar. It still ships only if it separates the tuned
fixture from the detuned one by more than its own run-to-run spread, and it still
carries no weight until that number exists.

## Iteration 6 — field judging on idiomatic stack use

Pre-registered before any judge ran.

**Context.** The old rubric's only measured signal was adjudicated as a screenshot
artifact (`FINDINGS.md` §26). Ten of its thirteen criteria asked about code quality and
produced zero information across 24 submissions. The subjective layer currently measures
nothing at all.

**Hypothesis.** Asking one specialist to rank the *whole field* of 8 submissions on a
single aspect — idiomatic use of its own stack — separates a field that per-submission
"is this good?" scoring could not. Idiomatic stack use is chosen first because it is the
only aspect whose subject is the variable under test.

**Falsifiers, any one of which kills it:**

1. **Ceiling.** All 8 submissions receive the same score, or **>70% sit at any one
   score** — not merely the top one. A judge that cannot separate a competent field has
   the wrong criteria, and re-running it will not fix that.

   *Amended 2026-08-14, before any specialist judge had been run, so no result informed
   it.* The original wording said "the top score", which would have passed a judge that
   put seven of eight submissions at the bottom. The amendment makes the falsifier
   strictly harder to satisfy; it does not relax anything.
2. **Order-invariance.** Re-running with a different presentation order moves scores by
   a mean of >1.0 point, or Kendall tau between the two orderings is < 0.5. A ranking
   that moves with presentation order is a presentation artifact.
3. **Mechanism.** Any separation that survives 1 and 2 must be adjudicated against the
   cited files, exactly as `look.feedback` was. A score whose evidence does not hold when
   the named file is opened is withdrawn, however consistent it is.

**Deliberate design choice.** The judge is told each submission's stack is unknown and is
instructed to score against *its own* stack's idioms. Cross-stack comparison is of
fluency, not of idiom sets. If this proves incoherent in the evidence, the aspect is
per-stack-only and cannot contribute to a cross-stack ranking — itself a reportable
result.

**Cost cap.** $12 per field call, 6 calls maximum (3 games x 2 orders) = $72 ceiling.
Sonnet, not Opus: the submissions were written by Opus, and a judge must not grade its
own model's work.

### Amendment 2026-08-16 — the plan changed BEFORE the result, and here is why

Recorded before the run finished, because a pre-registration amended after the numbers are
in is not a pre-registration.

- **The cost model was wrong, in the safe direction.** A field call costs **$2.82-$5.29**
  measured (mean $4.38), not $12. The $72 ceiling was built from a per-call *budget flag*,
  not from a measurement.
- **`--orders 2` was replaced by sequential sampling at `--max-runs 6`.** `JUDGING.md`
  specifies sampling until the decision resolves; `--orders N` cannot say whether a pair is
  `ORDERED`, `TIED` or `UNRESOLVED`, which are the verdicts the design turns on. The
  protocol had been implemented in `sequential.py`, self-tested, and **called by nothing**.
- **The game changed from three to one, and from `g1_pong` to `g2_tetris3d`.** Three games
  at full sequential depth prices at **$210 at the floor and ~$1,262 at the cap**, over the
  authorised ceiling. `g3_arena` was excluded on evidence rather than cost: it straddles the
  `syspolicyd` repair, so judging it would rank build conditions (FINDINGS #49). Of the two
  clean games, tetris is the harder one and is 8/8 at exactly 1.000 in a single build regime.
- **`--max-runs` cut from 24 to 6.** A truncated sampler reports `UNRESOLVED`, which is a
  weaker answer than `TIED` and must never be written as one. Stated here so nobody later
  reads an unresolved pair as an established tie.

**Falsifier 1 (ceiling) and falsifier 2 (order-invariance) have already fired once each on
`g1_pong`**, before this amendment: ceiling passes at modal fraction 0.625 against a 0.7
threshold on all three calls — one submission's worth of margin — and `architecture` fails
order-invariance at **tau 0.143** against the pre-registered 0.5 floor, with 4 of 8
submissions changing score between orders. Per the falsifier as written, `architecture`'s
ranking is a presentation artifact. It is carried into the tetris run rather than dropped:
if it fails there too, that is a stable property of the aspect and it should be reported as
**unusable**, which is a more useful result than a ranking.

---

## Iteration 7 — the null is now about the instrument, not the tasks

**Status: MEASURED 2026-08-16.** Iteration 5 pre-registered the hypothesis that *"more
trials and stricter grading will not separate these stacks, because there is no variance to
resolve."* Half of that is now confirmed and the other half is refuted, and the refuted half
matters more.

### What was measured

The twelve cells were compared **criterion by criterion** between their two independent
trials, which nobody had done — every previous comparison was of totals.

| | |
|---|---|
| criteria compared | **380** |
| cells whose totals differ | 0 of 12 |
| **criteria whose verdicts differ** | **0 of 380** |
| evidence strings that differ | **219 of 380 (58%)** |

### What that changes

Iteration 5 said there is no variance to resolve. **There is variance** — 58% of the
evidence strings differ, and they differ in substance, because the two submissions in a
cell are independent builds. What there is no *resolution* for.

> **The tiers do not report a tie because the submissions are identical. They report a tie
> because they cannot distinguish two submissions that are not.**

That is a different problem with a different fix. Iteration 5's remedy was a harder *task*.
The measurement says the ceiling is in the *instrument*: every criterion is binary, and a
binary criterion on work that is uniformly correct returns 1 for everything, whatever the
task. A harder task moves where the ceiling sits; it does not remove it.

### The falsifier this now carries

Iteration 5's probe stands — a task shape the templates do not pre-solve is still worth one
trial per stack. But it needs a second falsifier bolted on, or it will produce another
uninterpretable tie:

> **If the probe ties, check whether the criteria could have separated anything before
> concluding the task could not.** Report the within-cell per-criterion comparison alongside
> the between-stack one. A null from an instrument with zero within-cell resolution is not
> evidence of equality — it is the instrument's own noise floor being reported as a result.

### And it is why the graded criteria cannot simply be made stricter

Raising thresholds on binary criteria converts a ceiling into a floor and manufactures
failures that are properties of the threshold. The route that has actually produced
information twice is the opposite one: **criteria that report what they saw rather than a
verdict.** `enemy.kinds` now reports the wave it reached, which is what separates a
submission defect from the bot failing to establish its condition — and reading that
evidence string is how #46 was found at all.

## Iteration 8 — mutants have a blind spot, and it has a name

**Status: BUILT AND RUNNING, 2026-08-16.**

**Context.** #39 established that mutants catch criteria that *cannot fail* and miss criteria
that *pass for the wrong reason*. #46 adds a third class they cannot see, and it is the class
every adjudicated false negative in this project belongs to: **criteria that fail correct work
the reference does not resemble.**

A mutant removes the mechanism a criterion names. It cannot manufacture an input the criterion
mishandles. `ONE_KIND` collapses three enemy kinds to one and `enemy.kinds` goes red exactly as
designed — while the same criterion was failing six real submissions that ship four kinds,
because the reference showed all of them in wave 1 and the real games unlock them by wave.

**Change.** `bot_mutants.py` gains a **VARIANTS** suite: correct games the reference
deliberately does not resemble, where *every* criterion must still pass.

| variant | exercises | why it exists |
|---|---|---|
| a 104-tick opening title card holds the ball | `ball.moves` | copied from a real Godot submission; the old criterion failed it for doing the presentation work the task asks for |
| enemies faster than the player | `enemies.chase` | the only way to reach the contact branch, which the reference never takes |

**Hypothesis.** A variants suite finds false negatives that no mutant, reference run or
fixture test can, because it is the only member of the set built from behaviour the reference
does not have.

**It has already earned its place, in the same session it was written.** The second variant
exists because the contact branch of the repaired `enemies.chase` raised `KeyError` and
fail-closed a correct Godot submission to **0.000 on all 23 criteria** — after the reference,
all 36 mutants and the three session-lock controls were green. A real submission found it. A
variant would have.

**Falsifier.** If a year of variants never turns one row red while adjudication keeps finding
false negatives, the suite is decoration and the adjudication is doing the work.

**The standing cost of not having it**, stated so it is not re-litigated: two variants take
1.4 s to run. The defect they cover has cost, on the record, sixteen criteria in one sweep,
three more under the harder task, two more here, and one stack-correlated 0.000.

### RESULT 2026-08-16 — iteration 6 is falsified, on its own pre-registered terms

13 field calls, $46.79, five aspects x two orders on `g2_tetris3d`. *(Both figures are wrong and
are kept as written: the tetris field is 10 calls and $33.63, and the other 3 calls and $13.16
are `g1_pong`. FINDINGS #121. Nothing below depends on either.)*

**Falsifier 1 (ceiling) fires on three of five aspects.** `architecture`, `audio` and
`idiomatic` each put 6 or 7 of 8 submissions on one score on the *second* presentation order
while separating the field on the first. The falsifier was written as ">70% at any one score";
the readings are 0.875, 0.750 and 0.750.

**Falsifier 2 (order-invariance) fires on `architecture`**, which has no usable tau at all —
3 comparable pairs of 28 — with 4 of 8 submissions changing score between orders. On `g1_pong`
the same aspect measured tau 0.143. Two games, same behaviour: it is a property of the aspect.

**Falsifier 3 (mechanism) fires on `fun` and `idiomatic`.** Both survived every statistical
gate and both fail when the evidence is read: `fun`'s pacing number is 93-100% of the run in
every arm and its scores track run length (#52); `idiomatic` returns per-stack means identical
across two different games because the pack carries the stack in every file extension (#53).

**And the hypothesis itself is refuted.** It predicted that ranking the *whole field* would
separate what per-submission scoring could not. Pooled over five aspects and both orders, the
between-stack range of mean ranks is **1.70** and the mean gap between a stack's own two
trials is **2.05**. Field ranking discriminates — between **submissions**, not between
**stacks**, and not stably enough to order the submissions either.

> **The subjective layer reached the same null as the deterministic tiers, by a different
> route.** The tiers had no resolution below the cell. The judges have resolution below the
> cell and nothing above it. Four independent instruments now agree that four well-built
> templates on Opus are indistinguishable on these tasks.

**What would have to change before spending on this again**, in the order it would matter:

1. **A representative play session for `fun`**, separate from the criteria drive. Its current
   telemetry cannot answer a pacing question and no amount of sampling fixes that.
2. **Extension-blind packs for `architecture`**, which does not need the language. `idiomatic`
   cannot be blinded and must be reported as within-stack only, or not at all.
3. **A second game for every aspect.** `idiomatic`'s defect was only visible because the same
   aspect had been run on two games; four of the five have been run on one.
4. **Depth last.** `--max-runs 2` was enough to falsify three aspects. Sampling to resolution
   on an aspect that fails gate 1 or gate 4 buys nothing.


## Iteration 9 — the three gate failures repaired, and one of the repairs was wrong first

**Status: REPAIRED AND PINNED 2026-08-16. No judge call was made; the spend decision is the
user's and belongs against a repaired instrument rather than a promise.**

| # | what failed | repair | pin |
|---|---|---|---|
| 1 | `fun` scored a degenerate pacing number (#52) | dedicated 3000-tick play session; pacing over **world** events only | healthy 0.192 / dead **1.000** |
| 2 | `architecture` could read the stack off the extension (#53) | neutral `.src` extension for that aspect only | pack complete; **8 of 8 still identifiable by syntax** |
| 3 | `architecture` cited names found nowhere (#51) | brief requires pack paths; adjudicator splits reconstruction from fabrication | 11 of 11 reconstruction, **0** fabrication |

### The methodological result: the first repair of #52 was wrong, in the opposite direction

Replacing the criteria session with a real play session fixed the stated defect —
`longest_quiet_stretch_seconds` stopped being 93–100% of the run — and introduced a new one, in
the same metric, immediately. Pacing was computed over every event name, so a bot pressing keys
on a fixed cadence *manufactured* a fixed cadence of events. Against a deliberately dead game
it scored **0.005**, the healthiest reading possible.

**This is the third time in this project that a repair has been wrong in a way its own
motivating defect could not reveal** — `ball.moves` asserted velocity as a proxy for movement
(#34), `player.falls` accepted a flag instead of a height (#39), and now a pacing metric
measured the bot instead of the game. All three were caught by the same move, and only by it:

> **Pin the repair against the case that would make the NEW measurement lie, not against the
> case that made the old one lie.** A repair validated on the failure that motivated it has been
> validated on the one input guaranteed not to test it.

### What is still open, stated so it is not mistaken for done

- **`architecture`'s leak cannot be closed.** Syntax identifies the stack in all 8 submissions
  and syntax is what the judge must read. `idiomatic` is per-stack-only, permanently.
- **`g4_platformer` now has a play policy too**, so all four bots produce representative
  telemetry — but g4 has never been launched and its bot has never met a real submission.
- **None of this makes any aspect usable.** Per #55 the statistical gates will pass a repaired
  aspect and a broken one alike. The next spend must budget for adjudication of the **passes**,
  not more sampling.

## Iteration 10 — the pack budget is an unrevisited design choice, and it is OPEN

**Status: MEASURED, NOT DECIDED. Deliberately left open.**

`anonymise.py` fills a code pack in sorted path order until `max_chars = 160_000`. Every one of
the eight `g2_tetris3d` packs sits at that cap; across 60 stored submissions 32 dropped at
least one file, and the deficit is stack-correlated — unity mean 6.1 files against godot 1.1,
worst case 21 (#62).

The number was chosen once and never checked against a real pack. Two repairs are available and
they answer different questions:

1. **Raise the budget.** Simple, and it only moves the cliff — a larger submission hits it
   again, and the failure returns silently because it is invisible in the scores.
2. **Budget per bucket** (`sim`, `view`, `tests`, `other`), so no directory is starved by where
   its path happens to sort. Fixes the *mechanism*: the current defect is that alphabetical
   order decides what the judge sees.

(2) is better on the evidence, because the harm is not "too little code" but "an arbitrary
selection of code, correlated with stack".

**It is not decided here, and the reason is the discipline rather than indecision.** The
obvious move is to raise the number until the drop counts look acceptable, and that is fitting
the instrument to its data — the same failure as tightening a rubric after seeing which
submissions it fails. Whichever is chosen, it must be pinned: a field built under the new
budget must be checked for drops, not assumed to have none.

**Until then the completeness gate refuses to judge a code aspect on an incomplete field**, so
the cost of leaving it open is a refusal, not a wrong number.

---

## Iteration 11a: the completeness gate after the budget — repurpose, do not delete

**Context.** The 160,000-character pack budget was removed (#69). Drops are now 0 by
construction, so `pack_completeness`'s refusal can never fire on a field built today. A check
that cannot fail is #57, and leaving it would be worse than useless: it would read as protection.

**Two options were on the table. Argued, not picked silently.**

| option | what it costs |
|---|---|
| **delete the gate** | removes the only thing that would notice a cap returning. And a cap is exactly how this defect arrived the first time — not as a mistake, but as a *reasonable-looking guard on prompt size*. The next person worried about context length adds one, and nothing objects |
| **repurpose to assert `dropped == 0`** | keeps a gate that cannot fire on correct input — which is the thing #57 warns about — unless its ability to fire is pinned separately |

**Chosen: repurpose.** The asymmetry decides it. Deleting protects against nothing; repurposing
protects against the one failure mode with a demonstrated history in this repo, and its weakness
(never firing) is fixable by pinning that it *can* fire, which deletion's weakness is not.

**A gate that detected a defect becomes one that detects the defect's return.** The code is
unchanged; only its meaning and its message are. `files_dropped_for_length` stays in the
manifest for the same reason — it is now an invariant, not a diagnostic.

**Falsification.** The gate must refuse a manifest carrying a non-zero drop count. That is
pinned directly, because otherwise this iteration ships a check whose green is uninformative —
the precise error it is written to avoid.

**#62 stays valid and is not retracted.** It describes what was true of every round already run:
every stored code judgement was made on a truncated, stack-correlated sample.

## Iteration 11b: replace the ceiling gate with a standard error — proposed

**The claim.** #58's modal-fraction threshold is a crude proxy for the question anyone actually
has, which is *does this aspect separate these submissions?* It answers it by asking whether the
scores are too bunched, using a cutoff that sits in an unreachable gap, so it can pass an aspect
that separates nothing and fail one that separates something.

**The proposal.** Test separation directly. Repeat an aspect on the same field until the
standard error of a submission's mean score falls below the difference between submissions:

> **`SE = SD / sqrt(n)`. Repeats shrink SE. They do NOT shrink SD.**

That distinction is the whole proposal and must not be blurred: the judge's SD is a fixed
property of the instrument — its own reliability — and repeating cannot improve it. What
repeating buys is confidence about *where the mean is*. Report SD and SE separately, per aspect
and per submission; the SD has never been measured here and is a finding on its own.

**What it does NOT buy, and this is #63's lesson transplanted.** *Precision is not validity.* At
n=22, an aspect that tracks palette depth yields a precisely measured artifact — a tight
interval around the wrong quantity. `ux` correlates +0.528 with distinct-colour counts; more
repeats would make that correlation cleaner, not less confounded. **No number of repeats
converts a confounded aspect into a valid one.**

**The use this licenses.** Within-stack A/B — template v1 against v2, same stack, same task —
holds the stack constant, so a per-stack prior cancels out of the comparison. That is a sound
use of a judge with known priors, and it is what the template improvement loop actually needs.
**Cross-stack ranking remains barred** and no SE makes it permissible.

**Do not delete #58.** It explains every earlier round's ceiling verdicts, and those rounds are
in the record.

---

## Iteration 11c: why does capture geometry vary for the same id across runs? — MEASURE FIRST

**Not a fix. A question with a measurement attached, because fixing it blind is how #49 happened.**

Four capture geometries exist in the archive and each belongs to a different run: 420x640
(`unity__t1`, `wg-matrix-2026-08-13`), 768x576 (`rust__t0`, `wg-audio48-2026-08-14`), 720x540
(`ts__t1`, `wg-audio-2026-08-14`), and 640x400 for the other 32. This is upstream of #59 (a judge
that tracked distinct-colour counts), of the parity gate, and of the re-film decision.

**One hypothesis is already eliminated.** *The submission sets its own window size* — checked by
scanning both submissions' `.cs`, justfiles and shell recipes for resolution literals and for
`SetResolution`-style calls. **No resolution literal appears in either.** So the geometry is not
written down anywhere in the work; it is emergent.

**What that leaves, in the order they should be tested:**

| hypothesis | test |
|---|---|
| display scaling / Retina backing-scale at capture time | film one fixed submission on an external display and on the internal panel; compare IHDR |
| window manager gives a different default when a display is absent, asleep, or the session is detached | film with the display asleep and awake |
| engine default aspect from the scene camera, resolved at runtime | film the same submission under two engine versions |
| harness passes no explicit size, so the OS picks | read the capture recipe — cheapest, do it first |

The last is cheap and should be done before any of the others: **if the harness never specifies a
size, the answer is "whatever the OS gave us that day" and this is #49's class** — machine state
leaking into evidence — which would make every frame-derived number conditional on the day it was
captured, not just the four divergent ones.

**Do not "fix" it by forcing a size until the cause is known.** Forcing a size would make new
captures uniform and leave the archive's four divergences unexplained and unexplainable, which is
worse than the current state: it would look solved.

---

## Iteration 11d: judge the other three games — a VALIDITY test, not another precision gate

**The highest-value use of the repeats machinery, and it tests something the gates cannot.**

Every gate the subjective layer has been given — ceiling, independence, order-invariance,
reproducibility (mean self-tau +0.853) — measures **precision**: whether the instrument agrees
with itself. None measures **validity**: whether it is measuring the thing it names. #59 is the
proof that these come apart, since `ux` was precise, reproducible, order-invariant *and* tracking
distinct-colour counts.

**Tier 3 has only ever judged `g2_tetris3d` (#71).** Three games sit unused in the archive, and
grading them costs no new trials.

### The two hypotheses, stated so they can lose

| finding | hypothesis | what refutes it |
|---|---|---|
| **#53** | `idiomatic`'s stable per-stack ordering is a **language prior**, not a reading of the work | the ordering does NOT reproduce on `g3_arena` and `g4_platformer` — different work, same stacks |
| **#59** | `ux` measures **palette depth**, not user experience | its correlation with distinct-colour counts does not reproduce where renderers differ the same way |

**#53's test is the sharper of the two, and it is nearly free.** A prior attaches to the stack;
a reading attaches to the submission. Those make opposite predictions across a change of game,
and no amount of repeating on tetris can separate them — which is precisely why the layer's
existing gates have never touched it.

### Read the outcomes before running it

- **Ordering reproduces across games** → the prior hypothesis is supported and #53 hardens. This
  is the damaging outcome for the layer and must be reported as plainly as the other.
- **Ordering does not reproduce** → `idiomatic` is reading something submission-specific, and
  #53's strong form weakens. That would be the second positive result the layer has produced.
- **Ordering reproduces on one game and not the other** → the most likely result and the least
  quotable; report per game with pair counts, and resist averaging them into a verdict.

### Constraints carried in from what is already known

- **Report per game. Never pool.** Two independent reasons forbid it (#72 and the regime rule),
  and fixing one would not license it.
- Tier 3 stays **weight 0.00** whatever this returns. It is a question about what the instrument
  reads, not a bid to re-enter the score.
- Frame-reading aspects are unblocked on every game now that geometry informs rather than refuses,
  so `ux` and `fun_frames` can run on all four without re-filming.
- Code-reading aspects need the packs rebuilt uncapped first (#69); the stored manifests are still
  the capped ones.

---

## Iteration 12: comparing against `game-research-gpt` — axis 1 EXECUTED, axes 2-4 open

Task 11. The plan below was written before reading anything substantive, so the reading order was
fixed in advance and could not be steered by what turned out to be flattering. **Axis 1 has now
been executed and its results are at the end of this section.** The plan is left standing rather
than rewritten; one thing in it turned out to be wrong and is marked where it appears.

### What is actually there (measured, not assumed)

| directory | size | files | readable? |
|---|---|---|---|
| `evaluation/` | **30G** | **194,505** | no — run artifacts |
| `template/` | 63M | 2,600 | partly — mostly engine assets |
| `research/` | 53M | 86 | yes |
| `docs/` | 52K | 6 | yes |
| `scripts/` | 32K | 4 | yes |

**The 30G is not the comparison surface.** The readable surface is ~85K of prose plus a handful
of scripts. Any plan that starts by ingesting `evaluation/` is a plan that runs out of context
before it reaches an idea.

### The structural difference that frames everything else

Their `template/` is **single-stack Godot** — one `project.godot`, no `Cargo.toml`,
`package.json` or `Assets/`. But `evaluation/` contains `cross-engine`, `cross-engine-v3` and
`godot-defold-confirmation-v1` and `-v2`, so the cross-engine work is **Godot vs Defold**.

So: **they compare two engines deeply; this project compares four stacks broadly.** Neither is a
subset of the other, and a difference in their conclusions may be a difference in design rather
than a disagreement. The `-v1`/`-v2` and `-v3` suffixes suggest deliberate replication, which is
the single thing this project has least of — every finding here is n=1 on its own question.

### Reading order, cheapest first, stop when the budget is spent

1. `docs/adr/` and `RESEARCH_SYNTHESIS.md` — their decisions and conclusions. **Compare against
   `DECISIONS.md` and `README.md`.** Cheapest, highest information.
2. `research/decisions/` and `SOURCES.md` — how they source claims, against `research/AGENTS.md`.
3. `scripts/` (4 files) and `template/protocol`, `template/ops` — their harness discipline.
4. `evaluation/reports/` **only** — never the raw artifacts. Their conclusions, not their data.
5. Targeted greps into `evaluation/` for one question at a time, if one arises.

### Every entry gets a verdict, and both directions

For each difference: **adopt** (naming the verification below), **reject** (naming why), or
**open** (naming what would settle it). *"They do X, we do Y"* is a description and does not
count. And the comparison runs **both ways** — the deliverable includes what this project has
that theirs does not, because assuming the other side is ahead is how a regression gets imported.

### Verification, by axis — an import is not done when it is installed

| axis | how it must be proved here |
|---|---|
| judge/evaluator | re-grade stored submissions offline, before vs after. Free, 60+ submissions, 4 games |
| criterion | both halves of `judge/bot_mutants.py` — a mutant that reddens it AND a variant that keeps it green |
| template | fresh matrix (~$420) and a regime boundary. Prove the mechanism offline first |
| doc/process | name the `eval/FINDINGS.md` entry it would have prevented |

### Traps, each already paid for in this repo

- **Never import a number.** Their costs and scores come from a different harness, model, task
  set and machine. Importing one is #63 and #70 combined: a value quoted outside the scope that
  gives it meaning.
- **Never adopt a structure because it looks cleaner.** Name what it would have prevented.
- **Their replication discipline is the most likely genuine import**, and it is also the one that
  cannot be verified by re-grading — it is a process change, so it must name a finding here that
  n=1 produced and replication would have caught. #53 and #76 are both candidates.

### Where the plan was wrong

> *"Their `template/` is single-stack Godot ... so they compare two engines deeply."*

**Half right, and the half that is wrong matters.** `docs/RESEARCH_SYNTHESIS.md` records a matched
four-engine study — Godot 4.7.1, Defold 1.13.0, Bevy 0.19.0 and Unity 6000.0.45f1, 16 fresh agents,
four task contracts. That is **the same four-way shape as this project** on three of four stacks
(they run Defold where this project runs TypeScript). So it is a closer comparator than the plan
assumed, and the "a structure can be better for theirs and wrong for ours" discount applies less
than expected. Their *template* is single-stack; their *study* is not.

---

## Axis 1 executed — `docs/adr/`, `RESEARCH_SYNTHESIS.md` vs `DECISIONS.md`, `research/AGENTS.md`

Read in full: their `README.md`, four ADRs, `RESEARCH_SYNTHESIS.md` (301 lines), `research/SOURCES.md`.
Against: this project's `DECISIONS.md`, `research/AGENTS.md`, `eval/judge/RUBRIC.md`, `JUDGING.md`.

### Verdicts

| # | Their practice | What it replaces here | Verdict |
|---|---|---|---|
| 1 | **State which reweightings would change the answer.** Their decision matrix says outright *"increasing 2D/console weight can select Defold; making console/testing dominant can select Unity"* | Nothing. `overall = 0.31*tier1 + 0.69*tier2` is quoted in four documents and derived in none | **ADOPT — verified, and it paid immediately.** `judge/weight_sensitivity.py` built and run over 68 stored trials. FLIPS=0: no stored ordering depends on the weight. But 7 of 10 groups are UNIDENTIFIABLE — tier 1 returns ONE value across the whole group. **FINDINGS #92**, task 27 filed |
| 2 | **An immutable frozen record of what was evaluated** — `template-v3-{tree.json,source.tar.gz}` plus a protocol hash retained pre-outcome | `suite.json`, which a partial re-run overwrites | **ADOPT the property, not their mechanism — verified.** Asking the question found 3 of 18 stored runs whose manifest describes a different run; `wg-audio48`'s names a game with zero reports in its own directory. **FINDINGS #93**, task 30 filed (as "task 28"; renumbered since) |
| 3 | **Hard gates applied BEFORE scoring** — an option that fails a gate is not scored low, it is not scored | Tier 1 is inside the weighted score. It behaves as a gate (catches 0.0 and 0.857 outright failures) while being weighted as a discriminator | **OPEN — folded into task 27 as option (b).** Genuinely better *if* tier 1 is a gate, which #92 argues. Not adopted from this task because it is a rubric change needing mutants, not a doc edit |
| 1 | **State which reweightings would change the answer.** Their decision matrix says outright *"increasing 2D/console weight can select Defold; making console/testing dominant can select Unity"* | Nothing. `overall = 0.31*tier1 + 0.69*tier2` is quoted in four documents and derived in none | **ADOPT — verified, and it paid immediately.** `judge/weight_sensitivity.py` built and run over 68 stored trials. FLIPS=0: no stored ordering depends on the weight. But 7 of 10 groups are UNIDENTIFIABLE — tier 1 returns ONE value across the whole group. **FINDINGS #92**, task 29 filed and closed 2026-08-23: tier 1 is now a gate, `overall = tier2` (#123) |
| 2 | **An immutable frozen record of what was evaluated** — `template-v3-{tree.json,source.tar.gz}` plus a protocol hash retained pre-outcome | `suite.json`, which a partial re-run overwrites | **ADOPT the property, not their mechanism — verified.** Asking the question found 3 of 18 stored runs whose manifest describes a different run; `wg-audio48`'s names a game with zero reports in its own directory. **FINDINGS #93**, task 28 filed |
| 3 | **Hard gates applied BEFORE scoring** — an option that fails a gate is not scored low, it is not scored | Tier 1 is inside the weighted score. It behaves as a gate (catches 0.0 and 0.857 outright failures) while being weighted as a discriminator | **ADOPTED 2026-08-23, with one deliberate difference.** Tier 1 is now a gate and `overall = tier2` (task 29, FINDINGS #123). The difference: **a gate failure here does not remove the trial from the report.** Not scoring a failing option is right when you are choosing an engine and wrong when you are measuring one — every reason not to count a failure is a channel a bug can widen (rule 7), so the verdict is reported beside the score instead. What made it adoptable was not the argument but `judge/tier1_census.py`: 7 tier-1 failures in 68 trials, 5 of them lint or unit-test findings on games that scored 1.000 on tier 2 |
| 4 | **Reversal conditions on every decision.** Each ADR ends with what would re-open it | Partial. `DECISIONS.md` states them for tier 3's weight and the code-aspect bar; most table rows have none | **ADOPT, narrow scope — unverifiable as a benefit, and labelled so.** Cannot name a finding it would have prevented, so it is a taste change dressed as rigour if claimed otherwise. Adopted only where a decision rests on a measurement that could move. See below |
| 5 | **Source-kind taxonomy** — vendor fact / paper result / repository snapshot / project judgment, over a 301-URL manifest with SHA-256 of local copies | `research/AGENTS.md`: date it, source it, label unverified as unverified | **REJECT for the binary rule, ADOPT the taxonomy — OPEN on verification.** "Unverified" is binary; the failure mode is a *sourced* claim whose source is a vendor page treated as a measurement. `research/DECISION.md` got two eliminations wrong on the facts. Whether the taxonomy would have caught those is not established, so filing it would be asserting a benefit — left open |
| 6 | **Byte-for-byte preservation of the superseded synthesis** as a separate frozen file | `DECISIONS.md` replaces superseded content; git holds the history | **REJECT — mechanism-level reason.** `game-research-gpt` **is not a git repository** (verified: no `.git`). A frozen copy is their only history mechanism. Importing it here would add a second, manually-maintained history beside the one that already works |
| 7 | **Cohen's κ for inter-reviewer agreement** (κ≈0.643, 19/20) | Wilson-interval pair resolution (`JUDGING.md`), spread and instability figures | **REJECT.** κ answers "do two raters agree beyond chance"; this project's question is "has this pair resolved", which the Wilson protocol answers directly. Worse, κ over 2 raters × 20 binary decisions would here be computed over a ranking of 8 — a different object |

### Both ways — what this project does that they do not

Required by the plan, and not a courtesy. Three of these are load-bearing.

1. **They publish a four-engine ordering from n=1 per cell; this project refuses to.** Their
   `RESEARCH_SYNTHESIS.md` reports Godot 0.7875 > Defold 0.7500 > Bevy 0.5625 > Unity 0.5125 and
   says it "strengthens" the Godot default, while itself noting "each cell is only one stochastic
   run, each task has only one reviewer". `DECISIONS.md` bars the deterministic tiers from ranking
   stacks **at any gap**, on the measurement that 0 of 380 within-cell verdicts differ. Their
   caveat is a sentence beside the number; this project's is a prohibition on producing it.

2. **They disclose a one-arm gate defect and leave the affected scores in the headline mean.**
   Three non-Godot network cells "implemented credible independent loopback peers" but supplied
   `observations.independent_processes` as a Boolean or under a different key, so the frozen gate
   failed them. They say plainly this is "evidence about fresh-agent success under this contract,
   not a claim that those engines lack networking capability" — and the failed cells still sit in
   the mean that supports Godot. This project's handling of the identical shape (#49, `wg-arena3d`)
   was to declare the comparison **void** in `eval/RUNS.md`. Disclosure is not correction, and a
   defect that fires on the non-default arms of a study whose conclusion is the default arm is the
   one-arm-bias pattern this repo keeps a whole findings file for.

3. **Their weighted matrix scores are self-assigned judgments by the party that chose the weights
   and had a preferred answer**, on a 1–5 scale, decided by 4.10 vs 4.05 vs 4.05. Fixing weights
   before the spikes is real discipline and they did it; it does not constrain the scores. A
   0.05 margin on self-rated integers is the kind of gap this project's instrument is explicitly
   documented as unable to resolve.

4. **No mutant discipline.** Nothing in their readable surface asks whether a passing check *could*
   fail. `judge/bot_mutants.py` runs both halves — a mutant that reddens a criterion and a variant
   that keeps it green — and rule 15 exists because the mutant half alone missed 21 false
   negatives.

5. **No retraction log.** `eval/FINDINGS.md` keeps published-then-wrong numbers marked because
   someone may have acted on them. Their equivalent is a "disclosed revisions" directory, which
   is close, but their synthesis states current numbers without marking which superseded a
   published one.

Set against that: their **replication discipline** (`-v1`/`-v2` confirmation runs, `-v3`) remains
the thing this project most conspicuously lacks, exactly as the plan predicted. Every finding here
is n=1 on its own question. That is axis-3 work and is not settled by axis 1.

> **Corrected by axis 3, below.** Those suffixes were read off directory names. Their dispositions
> say the trees are unfinished, invalidated and unadmitted: **no confirmation run ever produced a
> comparative result.** They are ahead on having designed replication, not on having it. The
> second sentence stands — every finding here is still n=1.

### What was adopted, concretely

- `eval/judge/weight_sensitivity.py` — new, offline, free, `--selftest` with 12 checks including a
  positive control that finds a constructed crossover and a regression guard for a false-alarm bug
  the tool had on its first run.
- **A rule, `AGENTS.md` #16:** a weighted result must state what reweighting would change it, and
  a weight that cannot change anything is reporting that its tier has no variance. Placed in the
  root rules rather than `research/AGENTS.md` because it protects any published aggregate, not
  just the briefs — and it is paid for, by #92.
- **Reversal conditions**, candidate 4, adopted only for decisions resting on a measurement that
  could move — recorded in `DECISIONS.md` where they apply, and **labelled unverifiable**: no
  finding here is known to have been caused by their absence.

### Axes 3-4: NOT started

Axis 2 is below. Axis 3 (reporting under uncertainty) is partly pre-empted by the both-ways
section above. Axis 4 (harness mechanics) now has a concrete lead: task 30.

---

## Axis 2 executed — the template layer and what a building agent is told

Read in full, read-only: `game-research-gpt/template/AGENTS.md` (112 lines), `template/Makefile`,
`template/docs/AGENT_WORKFLOW.md`, `template/docs/TESTING.md`, `template/config/verify/fast.json`,
`template/config/versions.env`, `template/scripts/doctor.sh`, and the four files in
`scripts/evaluation/`. Against: `eval/starters/godot/AGENTS.md` and its `justfile` (the deepest of
the four), the other three `justfile`s, `judge/static.py`, `judge/audio.py`, `eval/PROTOCOL.md`
§"Before launching", and `research/10-stack-capability-matrix.md` §5, §6.11, §8.

**Their template is one project that has to get good. Ours is four starters that have to stay
comparable.** That difference decides most of the table below: several of their mechanisms are
right for a codebase with accumulated state and wrong for four trees the harness proves pristine
before every trial.

### Verdicts

| # | Their practice | What it replaces here | Verdict |
|---|---|---|---|
| 1 | **`expected_stdout_contains` on every gate command** — the manifest asserts a token the command can only print by having finished (`ARCHITECTURE_OK`, `E2E_SCENARIO_OK`, `REPLAY_SMOKE_OK`), on the stated principle that *"a bare exit code is not sufficient diagnostic evidence"* (`docs/TESTING.md:26`) | `build.compiles` and `verify.green` are exit codes and nothing else (#98) | **OPEN — the blocker is gone; installing the check is still a separate decision.** The measurement first came out against it: over 68 stored records, 17 of 62 green `verify` runs did not contain the recipe's own `✅ verify passed`, **15 of 16 on the Rust arm**, because `tail` kept `[-4000:]` of `stdout + stderr` and nextest fills stderr — the check would have been inert on exactly one arm (**FINDINGS #100**). Task 45 repaired the capture on 2026-08-23: the two streams are stored apart, each sampled on its own budget, so neither can starve the other (**FINDINGS #103**). Measured on one submission per stack, one execution rendered under both policies, the Rust gate writes **16 characters to stdout against 8638 to stderr** and its completion line survives now and did not before. **What is still undecided:** the token is only in records graded after that date — the 68 stored ones cannot be asked — so the check would apply forward only, and it is worth stating what it adds over `verify.green`'s exit code before it goes in |
| 2 | **`artifacts: [{path/glob, min_bytes, max_bytes, min_matches, fresh}]` per command** — a command that exits 0 without writing what it was supposed to write fails | Nothing general. Iteration 13 built `field.pack_matches_manifest` for judge packs specifically, after #95 | **REJECT for tier 1, on measurement.** The one criterion where it could bind is `render.frames`, and it already reads the artifact rather than the exit status. Partitioned over 68: `film` exit 0 with frames present, 66; `film` non-zero with no frames, 2; **zero disagreements in either direction.** Freshness is guaranteed by construction — `static.film()` captures into a fresh `mkdtemp` per submission |
| 3 | **`APPROVE=UPDATE_BASELINE` on golden updates**, plus a metadata sidecar hash that `verify-fast` re-checks, under *"verification never updates its own oracle"* | Prose only: `just bless` warns, and `starters/*/AGENTS.md` says "🚫 Never … weaken a determinism assertion or widen the golden budget", "delete a rule from `tools/boundary.gd`" | **REJECT — measured, 90 submissions, and it comes out against.** 76 of 90 stored submissions edited at least one file that decides their own tier-1 score. Every hunk was read. **Not one weakened an oracle:** the five `tools/boundary.gd` edits changed an error-message string to name a renamed file and removed no rule; the six `project.godot` edits changed name, description, window size and user dir, and **lowered no `gdscript/warnings/*` level**; the one `eslint.config.js` edit added `tmp/**` to *ignores*; and the two `tools/check.gd` edits **strengthened** the checker — they are the #98 repair. A mechanical guard would have prevented zero observed failures and blocked two submissions that fixed the grader |
| 4 | **`make doctor` — fail-closed toolchain preflight**, pinned versions and a SHA-256 of the test-framework tree, printing `UNAVAILABLE BY DESIGN; never inferred` for what it cannot check | `eval/PROTOCOL.md` §"Before launching" | **REJECT — this project is ahead, and the gap is the important half.** `doctor.sh` asserts *identity* (right binary, right version). PROTOCOL.md's machine row asserts *capability*: "**compile and exec a trivial NEW binary in each toolchain**, and run `just verify` in each of the four starters", plus `precampaign_smoke.py` running eight once-per-campaign commands unpiped. A version check could not have caught #49, which was `execve` gating, not drift |
| 5 | **A structured finish report** — behaviour delivered, design choices, exact commands and results, artifact paths *personally inspected*, remaining risks, *"do not claim Windows/iOS/PS5/Switch validation unless it actually ran"* | Nothing. `agent.final_text` is free-form; rule 11 records that four agents wrote an unverified-claims paragraph and nothing reads it | **DECLINED 2026-08-23, on the baseline the pre-registration required first.** All 90 stored `agent_result.json` read whole (`.result`, not the tail-truncated `agent.final_text`): 15 carry no agent-written message, the other 75 are all `completed`, and **31 of 75 (41.3%) already disclose** something unverified or a residual risk, 10 under a dedicated heading. The rate is stack-correlated — godot 3/15, rust 13/21, ts 4/23, unity 11/16 — which was the pre-registered "investigate before touching a starter" branch, and the investigation dissolves it: **19 of the 31 disclosures are the live path**, 11 Unity and 7 Rust, and agents claiming to have *driven the running application* are **15 of 23 for TS against 0 of 52 elsewhere**. The arms differ in how much is left to disclose, not in willingness. The experiment would be a fifteenth regime boundary and two fresh matrices (≥$842, since `wg-g4c-2026-08-21` at $421.00 sits behind four later boundaries) to move a number task 46 itself forbids reporting beside a tier-1 or tier-2 figure. Full argument in `eval/RUNS.md`, "DECLINED: requiring a finish-report section in the starters". **Re-open if** Rust and Unity agents gain a way to exercise their own live path |
| 6 | **A graduated gate ladder** — `verify-fast` inner loop, `verify-render/-network/-async/-export` conditional on what changed, `verify-all` before completion; plus `keep_going: true` so one pass yields the whole failure set | `just verify` is one gate; `just check` (~0.5s) and `just test-sim` (~1s) are the inner loop | **REJECT the ladder, on the starters' own recorded reasoning.** The one-command contract is deliberate and its cost is measured: `verify` runs `fmt`, not `fmt-check`, because a trial was lost to a red gate over a stray blank line. A ladder whose branches an agent must select is a second thing to get wrong. `keep_going` is already true where it matters — `static.collect()` runs `check`, `verify`, `lint`, `test` as four independent commands and scores all four |
| 7 | **Audio evidence split four ways** — asset / behaviour / routing / device, with device-level explicitly labelled unverifiable | Five asset-level criteria plus `audio.triggered` | **REJECT — already present, and its limit is already written down.** `judge/audio.py`'s `triggered_criterion` correlates the events a *driven run actually emitted* against the manifest and states in its own docstring that it "cannot hear the speaker". Routing and device are unreachable anyway: `research/10-stack-capability-matrix.md` §6.11 — `audio.py` decodes every clip to **mono** before analysis, and one of four stacks has no audio at its pin |
| 8 | **`make report --strict-declared-counts --fail-on-duplicate-tests`** — a suite that declares N tests must report N results | `tests.exist` (floor 8) and `tests.green` (requires `total_n > 0`) | **REJECT, one-arm by construction.** The `total=0` hole rule 1 names is already closed. The remaining idea — assert the *compiler* saw units, not just the test runner — has evidence on one arm only: Godot's `just check` prints `CHECK scripts=N failures=0` (n=16, N∈[19,33]) and nothing reads N, while TS prints nothing at all and Rust/Unity print prose. Installing it would grade the arm with the chattiest gate |
| 9 | **`archive_delta.py` / `reconstruct_submission.py`** — attested added/modified files, hashed, replayable into a submission | Every trial stores `diff.patch`, `diff.stat`, `tree.txt`, `submission.tar.gz` against a committed starter baseline (`wholegame.py:128-131`) | **REJECT — equivalent already, and it is what made the row-3 measurement possible at all.** Their pair exists because `game-research-gpt` is not a git repository (established in axis 1); this project's baseline is a real commit |
| 10 | **"Translate every acceptance phrase into an implementation state/action and an evidence check before coding"**, with the worked example *"if a task says 'title → play,' an auto-starting game with a decorative title is not equivalent"* | Nothing equivalent in any starter `AGENTS.md` | **OPEN — labelled unverifiable, and not filed.** It is a plausible instruction and there is no offline measurement that would show it helped: no stored artifact records whether an agent decomposed the prompt. Asserting a benefit here would be a change of taste wearing the costume of rigour. Folded into task 46 as a *second* arm only if that experiment runs |

### Both ways — what the template layer here does that theirs does not

1. **Four starters that are provably the same simulation.** `judge/starter_parity.py` drives all
   four through one input tape and compares per-tick state hashes — "if they diverge, the numbers
   in the bake-off are comparing four different games". Their template is single-stack, so the
   question cannot arise for them; but their *study* is four-engine, and nothing in their readable
   surface measures cross-engine starter parity.

2. **Every constraint states what it costs the agent, in turns.** `starters/godot/AGENTS.md` on
   headless rendering: *"The consequences, which will otherwise cost you a turn each"*, then the
   `--headless` trap, the `xvfb-run` workaround, the `frame_post_draw` hang, and "a skip is not a
   pass". Theirs is imperative throughout. Which produces better work is untested; which produces
   better *documentation of a known failure* is not in doubt.

3. **A flag is described by what it actually does.** The Godot `justfile` distinguishes
   `--audio-driver Dummy` ("listed in `godot --help` … what `--headless` itself selects") from
   Unity's `-disable-audio`, "which the standalone player accepts and ignores" — #61 written into
   the product. `doctor.sh`'s equivalent line, `PS5 / Switch SDK UNAVAILABLE BY DESIGN`, is the
   same instinct applied to a platform rather than to a flag.

4. **A machine-readable probe protocol.** `just probe` / `probe-file` / `film` emit one JSON trace
   line per tick with a fixed key order and finite numbers, which is what tier 2 drives and what
   `audio.triggered` reads. Their equivalent, `tools/blackbox.py` plus `compare_replay.py`, is a
   harness-side comparison rather than a contract the submission must satisfy.

5. **The starter's own gate is proved green on a pristine copy before every campaign**
   (`tools/starter_gate_control.py`). #98 is the finding that bought it. Three directions since
   task 47: green on pristine, red on a plant, and — on godot, the only stack whose `check` is a
   hand-written file loop rather than a compiler — the plant still slipping past a repair that
   narrows the gate's scope, which is what makes the RED row a discriminator rather than a mutant.
   A fourth since task 51, and it points at a different recipe: `just warm` and `just verify`
   must leave a pristine tree byte-identical. All three earlier directions read `just check`,
   which compiles and never writes, while `verify` runs `fmt` first in all four stacks and had
   been rewriting a file the agent never opened into the stored trial diff (#106). Its green
   half is gated on a planted mis-formatting the formatter must undo, because an arm with no
   formatter installed leaves the tree clean too.

### What was adopted, concretely

- **FINDINGS #100** — the `[-4000:]` over `stdout + stderr` truncation, and its one-arm shape.
  Found by designing the verification for candidate 1 before importing it, which is the only
  reason it was found at all.
- **Three tasks: 45** (repair the capture — the precondition for candidate 1), **46** (the finish
  report, pre-registered with its outcome table), **47** (tell an agent what to do when the
  starter's own gate is wrong, which is the case the never-list does not cover).
- **Nothing installed.** Seven of ten candidates are rejected on measurements taken here, and two
  of those measurements — 76 of 90 submissions editing their own grader with zero weakenings, and
  66/2/0/0 on `film` exit versus frames — are results this project did not previously have.

### Where axis 2 stopped

Everything above is done. Axis 3 is below.

---

## Axis 3 executed — how results are reported under uncertainty

Read in full, read-only: `docs/RESEARCH_SYNTHESIS.md` (301 lines),
`evaluation/cross-engine/results/FINAL.md`, `evaluation/reports/INSTRUCTION_REVISIONS.md`, and the
disposition READMEs of `evaluation/cross-engine-v3`, `godot-defold-confirmation-v1` and `-v2`.
Against: this project's `README.md`, `DECISIONS.md`, `eval/RUNS.md`, `eval/judge/JUDGING.md`.

### The premise this axis was given, and it does not survive contact

Axis 1 closed with *"their replication discipline (`-v1`/`-v2` confirmation runs, `-v3`) remains
the thing this project most conspicuously lacks"*, and axis 3 was set up to confront that
asymmetry. **The asymmetry is not there, and the correction is the first result of this axis.**

Read from the dispositions rather than from the directory names:

| tree | what it says about itself | modified |
|---|---|---|
| `cross-engine` | the delivered four-engine pilot. `Scope: descriptive n=1 evidence` | 13 Aug 19:48 |
| `cross-engine-v3` | *"unfinished, non-admitted historical work... no v3 score or outcome exists"*, an attempted 8-task x **3-repetition** expansion, RC3c terminal NO-GO | — |
| `godot-defold-confirmation-v1` | *"invalidated before decision"* — both reviewer sessions ended without an artifact, the analyser exited non-finite. Explicitly **not** a win, tie, equivalence or ordinary inconclusive | 14 Aug 11:48 |
| `godot-defold-confirmation-v2` | *"prospective implementation / no formal admission"* — designed, not run | 15 Aug 00:02 |

`-v1`/`-v2`/`-v3` are **not replicates that ran.** Every replication attempt terminated without a
comparative result: one unfinished, one invalidated, one unadmitted. Their delivered evidence is
`n=1` per cell with one reviewer per task, which their own `FINAL.md` states in its header.

They are genuinely ahead on having **designed** replication — a 3-repetition expansion and a
preregistered two-stage confirmation are more than this project has ever specified — and the part
that did not survive is the part this project lacks. That is a real and useful distinction, and it
is the opposite of a lead.

**And their top-level conclusion never learned any of it.** `docs/RESEARCH_SYNTHESIS.md` was last
written 13 Aug 19:50, sixteen hours before v1's invalidation was recorded; the string
*"confirmation"* appears **zero times** in their `docs/` or their root `README.md`. A reader of the
entry-point document cannot discover that a confirmation study exists, let alone that it came back
invalid, while that document says the n=1 ordering *"strengthens"* the default. The careful
disposition is real, and it is filed where only someone already looking for it would find it.

> **A caveat is worth what its distance to the number lets it be worth.** Theirs is four
> directories away. This project's equivalent failure is 250 lines away in one file, which is
> #113 — the same defect at smaller radius, and it took this reading to see it.

### Verdicts

| # | Their practice | What it replaces here | Verdict |
|---|---|---|---|
| 1 | **`FINAL-CORRECTIONS.json`** — an append-only machine-readable correction stored beside the frozen result, so a consumer can apply the delta and the frozen file is never rewritten | Nothing. A withdrawal is prose, in whichever document happened to be open | **ADOPT the property — and it found a live defect before being installed.** Designing the verification first turned up the withdrawn `1.70`/`2.05` tier-3 pair still published as current in `DECISIONS.md`, `JUDGING.md` and `README.md`'s own In-flight section. **FINDINGS #113**; tasks 54 and 55 |
| 2 | **A cross-document consistency check** is the obvious way to catch #113, and is not theirs — it is what a reader proposes on seeing their correction file | Nothing | **REJECT — built, measured, and it cannot work.** Over the six live documents: **52 table labels of 25+ chars carrying a number, 1 disagreement, and that one a false positive.** It misses #113 by construction, because the four restatements **agree**. Propagation and consistency are the same observation |
| 3 | **`Status:` / `Scope:` as the first two lines of a result document**, and `Interpretation: descriptive only` as a **column** of the aggregate table rather than a paragraph after it | `README.md` puts its scope in blockquotes below the table, and `RUNS.md` in a per-run ledger entry | **OPEN, and #113 is the argument for it.** The measurement that would settle it is available and was not run for cost of attention, not principle: for each published aggregate, the line distance to its scope. Worth doing only alongside task 54, which will move three of the sites |
| 4 | **Disclosing that a pre-registration was less pre than claimed**, with the three timestamps — formal start 16:44:10, protocol freeze 16:47:07, earliest finish 16:55:58 — and the conclusion stated exactly: *"a freeze before any completed formal outcome, but after admission/start"* | `JUDGING.md` pre-registers gates (#68) and states no timestamp relation to the data | **ADOPT, narrow — and it is cheap and offline.** The stored rounds carry mtimes and `JUDGING.md` carries dates; asserting the relation is a few lines. Not filed as its own task: it belongs to task 54, which is already rewriting that section, and a second task on one file would collide |
| 5 | **A named disposition for a study that produced no result** — `INVALIDATED_PREDECISION`, defined in advance by an *evaluator-defect rule*, and stated as *"not a Godot win, Defold win, equivalence result, tie, or ordinary statistical inconclusive"* | `eval/RUNS.md` records comparability breaks with ordinals; `README.md` calls the arena set *void* in prose | **REJECT the vocabulary, ADOPT nothing — this project is ahead and the gap is measured.** Their disposition is a label applied after the fact; `RUNS.md`'s ordinals are gated by `docstat.py --sweep`, which fails on a duplicate ordinal. A label a tool checks beats a label a document asserts |
| 6 | **`INSTRUCTION_REVISIONS.md`** — observation, the evidence that produced it, the change made, and *"these are not retroactively attributed to round-one"* stated at the top | Both `IMPROVEMENTS.md` files, plus `RUNS.md` regime notes | **REJECT — equivalent already, and this project's version carries more.** Theirs names the change; ours states the hypothesis, the measurement that could have come out against it, and what it did. The one line worth having — the non-retroactivity statement — is already what a comparability break in `RUNS.md` *is* |
| 7 | **A mean across four different task contracts** — 0.80, 1.00, 0.90, 1.00 reported as *"mean 0.925"*, and `Godot 0.7875` over four tasks whose rubrics differ | Barred here: the play-bot scores 13 criteria on pong and 22 on arena, so 1.000 is a different achievement per column (#72) | **REJECT — importing it would be a regression.** Listed for the both-ways record: this is rule 4 with the population heterogeneous by construction, and their own decision turns on 4.10 against 4.05 |
| 8 | **An "Evidence boundary" paragraph** — one sample per cell, one reviewer per task, one host, blinding limits, and a known bug with its blast radius bounded (*"adds generated noise to some Bevy deltas but does not affect criteria or reconstruction"*) | Scattered: `README.md` "What this does and does not license", `RUNS.md` per run, `FINDINGS.md` per defect | **OPEN — unverifiable as a benefit, and labelled so.** No finding here is known to have been caused by its absence, and #113's cause was distance, not absence. Filing it would be a change of taste dressed as rigour |
| 9 | **Naming what the study did NOT exercise, beside the result**, and forbidding other evidence from filling the gap: *"must not be reported as matched task evidence for those omitted areas"* | `README.md` "Not done" | **REJECT — present, and stronger.** "Not done" is a list; `DECISIONS.md` bars the deterministic tiers from ranking stacks **at any gap**, which is the prohibition rather than the inventory |

### Both ways — what this project does that they do not

Three of the axis-1 entries are theirs already (n=1 ordering published, a one-arm gate defect left
in the mean, self-assigned integers deciding a 0.05 margin) and are not restated. Four are new to
axis 3:

1. **A withdrawal is a first-class object here, and there it is a directory that stops being
   linked.** `eval/FINDINGS.md` keeps published-then-wrong numbers marked because someone may have
   acted on them, and `README.md` carries three explicit ⚠️ withdrawals in its headline table with
   the search that failed to reproduce each. Their `cross-engine-v3` and `confirmation-v1` say
   plainly what they are — and nothing that cites the conclusion those trees were meant to test
   mentions them.

2. **A number here has to have a producer.** #113 is the exception that names the rule: the one
   figure with no script behind it is the one that drifted through four documents. Their entire
   decision matrix is 36 self-assigned integers with no producer at all, by design, and the
   sensitivity analysis this project built for it (`judge/weight_sensitivity.py`, axis 1) has no
   counterpart there.

3. **The reproducibility of an aggregate is tested here, and the test has fired five times.**
   Four figures in `README.md`'s headline table were withdrawn for failing it — 20-of-24,
   380-paired-criteria, 0-verdict-differences, and 1.70/2.05 — and #113 is the fifth. Nothing in
   their readable surface re-derives a published number from stored artifacts.

4. **Method as a declared parameter.** #113 established that the tier-3 separation figure is four
   different quantities depending on two choices nobody had written down, and `judge/field_ranks.py`
   now reports all four. Their `FINAL.md` states a weighting (20/35/20/15/10) and never varies it.

Set against all of that: **they attempted replication and this project has not.** Every finding
here is still n=1 on its own question. That is unchanged by this axis — only the belief that they
had *achieved* it is.

### What was adopted, concretely

- **`eval/judge/field_ranks.py`** — new, offline, free. The producer the tier-3 separation figure
  never had. `--selftest` has six controls with hand-computed expectations, including a mutant, a
  permutation variant, and a negative control proving the usable-round filter can change an answer.
  Verified against stored data by reproducing **all ten cells** of `JUDGING.md`'s own per-aspect
  table, under one method and no other.
- **FINDINGS #113** — a withdrawn figure still published in three live documents, the four-method
  spread that replaces it, and why a consistency check is structurally blind to it.
- **Two tasks: 54** (retire the figure, and decide which method the project reports),
  **55** (the withdrawal register, with the design that avoids a stale allowlist).
- **Nothing else installed.** Five of nine candidates are rejected, two on measurements taken here;
  two are open and labelled unverifiable rather than filed.

### Verdict 1, closed 2026-08-23: the register exists, and its first catch was not the one predicted

`eval/withdrawn.json` and `docstat.py --withdrawn` are installed and gate `--sweep`.
**The hypothesis was that its customer would be the 1.70/2.05 pair.** By the time it ran, task 54
had retired that pair and the entry was green — the shape this repository keeps finding, a gate
installed on an already-repaired tree. Two things came out against that:

- **The register found a second live defect nobody had looked for.** Finding **#54** — two judges
  with no evidence in common ranking the field identically — was withdrawn in the archive on
  2026-08-17 and was still cited as current in **three** live documents six days later:
  `README.md`'s In-flight section, `DECISIONS.md`'s tier-3 bullet, and `eval/judge/JUDGING.md`
  114 lines above that same file's own withdrawal notice. The ticket named one of the three; the
  check found the other two. That is **FINDINGS #119**, and it is the same defect as #113 one
  level up: a retired *claim* rather than a retired *figure*.
- **It was measured RED on real data before being wired in.** At `25fe630`, the commit before task
  54 ran, `--withdrawn --at 25fe630` reports the pair published in exactly the three documents
  #113 names, and reports none of them at HEAD. A gate that has only ever been green cannot be
  distinguished from one that cannot fire.

**What it cannot do, stated rather than discovered later:** it does not separate *stating* a
retired figure from *asserting* it as current — nothing mechanical can, since they are the same
characters. It forces the author to declare which, in the block, for one parenthetical. Three of
the six hits on installation day were legitimate historical prose and were repaired by adding the
id. It is also blind to a paraphrase that drops the number, and to anything inside a fence.

### Where axis 3 stopped

Everything above is done. Axis 4 is below, and it closes task 11.

**One thread this axis opened and did not close, for whoever takes axis 4:** the stored judge
rounds' own `cost_usd` fields sum to $33.63 and $31.66 for the two `wg-tetris-judge-2026-08-17`
fields, while their `SEQUENTIAL.json` records `measured_cost_usd` 25.55 and 21.05. `README.md`
quotes 21.05 for the second and $46.79 for the first, which matches neither stored total. That is
cost accounting, which is axis 4, and it was left rather than chased.

> **Chased, and it was the whole of axis 4's yield.** All three numbers are explained and only
> one is a cost; see below and FINDINGS #121.

---

## Axis 4 executed — harness mechanics, and the axis that produced no import at all

Read, read-only: `game-research-gpt/evaluation/reports/` in full — `README.md`, `FINAL.md` (313
lines), `manifest-current.json`, `manifest.json`, `manifest-godot-study-frozen.json`,
`INSTRUCTION_REVISIONS.md` — plus the per-study `README.md` dispositions already read for axis 3.
Against: `eval/RUNS.md`, `eval/judge/field_sweep.py`, and every stored artifact under
`eval/runs/**` that carries a cost.

**The lead this axis was handed was "task 28", and there is no task 28.** The queue runs 27, 29,
30. Task 28 was filed by axis 1 for FINDINGS #93 and is **task 30** today — the same subject,
`suite.json` describing the last thing written into a directory. The task-id namespace collided
and was resolved by renumbering, and `docstat.py --renumbered` covers finding numbers only, so
nothing could see the citation break. Fixed here and in `tasks/11`. That is #118's shape in the
one namespace #118's tool does not reach.

### The framing, and it decides most of the table

**Their harness mechanics answer "can a third party verify this was not tampered with". Ours
answer "may these two runs be compared, and what did they cost".** Their report set is built for
custody: SHA-256 per published file, HMAC attestation with the key held outside the repository,
frozen baselines with replayable source deltas. There is no adversary here — the party running
the evaluation is the party reading it — and there is no third party to convince.

The measured consequence is one-directional and worth stating plainly: **their entire readable
report surface contains no cost accounting whatsoever.** Zero occurrences of a USD figure, a
token count, or a spend total across `FINAL.md`, `README.md` and `INSTRUCTION_REVISIONS.md`; five
uses of "budget"/"costs", all of them prose about licensing or console certification. This
project has a run ledger with two columns and a stated reason they differ. On the one axis where
a candidate import could have been expected, there is nothing on their side to import.

### Verdicts

| # | Their practice | What it replaces here | Verdict |
|---|---|---|---|
| 1 | **A content manifest — path, bytes, SHA-256, `captured_at` — over exactly the files that constitute a published result** | `suite.json`, which a partial re-run overwrites | **ALREADY ADOPTED as a property, axis 1, and it is task 30.** Re-verdicting it would be counting one import twice. Their *mechanism* (a hand-maintained JSON of hashes) stays rejected for the axis-1 reason: this is a git repository and that is a second history |
| 2 | **A frozen baseline plus per-submission source deltas, with a script that re-verifies the SHA-256 tree after every delta and restores file modes** — durability without keeping the workspaces | `eval/runs/**`, 129 GB of full work trees, gitignored and backed up separately | **REJECT — this project already made the stronger move and measured it.** #87/#90 decomposed the tree, #104 established the starter baseline is the part that cannot be rebuilt, and 7.5 MB of `git archive` baselines now stand in for 55 GB of work trees. Their scheme reconstructs a *submission*; the artifact this project loses is the *starter it was given*, which their deltas presuppose rather than preserve |
| 3 | **HMAC attestation of every report, key never in the repository, key ids and report hashes published** | Nothing | **REJECT — no finding here has a forging author.** Every defect in `eval/FINDINGS.md` is a mechanism measuring the wrong thing, never a party altering a result. An integrity control against an absent adversary is unfalsifiable by construction: it can never fire, so it can never be shown to work, which is rule 1's own definition of a check that certifies nothing |
| 4 | **Ignoring workspace trees while versioning manifests, attestations, score reports and deltas** | `.gitignore`, whose header states per entry whether it is regenerable build output or evidence too large to push | **REJECT — present and better instrumented.** Theirs states the policy in prose in a README; ours states it in the ignore file itself, and #87/#90 measured the split rather than asserting it |
| 5 | **`captured_at` on the manifest** — the result set says when it was frozen | `eval/RUNS.md`'s figures carried no read date except where an author happened to write one | **ADOPT, and it is the cheapest thing here.** Every cumulative figure in `RUNS.md` now carries the date it was read and the command that reads it. **What would show it helped:** a stale total is detectable by comparing the stamp against the newest run directory. It would have caught this one — see below |
| 6 | **No cost accounting at all** | A two-column run ledger with a stated reason the columns differ | **REJECT, and it is the both-ways entry of the axis.** Nothing to import. See below for what asking their question found on this side |

### What asking the question found HERE, which is the whole yield

Axis 4's return is not an import. It is that **the two judge fields' three disagreeing
accountings were a real defect, it generalised, and the fix is in the write path** — FINDINGS
#121, and the second time in this task that designing a verification found the defect before the
import did (axis 1 candidate 1, axis 3 candidate 1).

| number | what it is | verdict |
|---|---|---|
| $33.63 / $31.66 | sum of each stored round's `cost_usd` | **right**, and already what `RUNS.md`'s judge table carried |
| 25.55 / 21.05 | `measured_cost_usd` in `SEQUENTIAL.json` | a **ceiling counter for one invocation**; a round already on disk is charged $0.00 on purpose. Correct, and not a cost |
| $46.79 / $21.05 | published in `README.md`, `JUDGING.md`, `DECISIONS.md` | **both wrong as attributed.** $46.79 is two games; $21.05 is the resume-truncated counter |

Established from the sweep's own `sweep.log`, which prints `cumulative $0.00` after two aspects
whose four rounds were already on disk, and from the arithmetic closing to the cent both ways.
Then generalised: 5 of 11 stored sweep directories under-report, $69.93 in total, and the true
judge spend is **$306.73 over 93 rounds** against a ledger headline of $46.79.

Two further stale totals fell out of the same sweep, both correct when written and never re-read:
`RUNS.md`'s **~$1,547** and `README.md`'s **~$1,794** against a measured **$2,710.94**. The
`RUNS.md` figure was stale twice over — three runs that did not exist yet, and one that was still
building when it was read, which is the moving-row hazard stated four lines below it in the same
file.

### What was adopted, concretely

- **`eval/judge/judge_ledger.py`** — new, offline, free. Reports `field_cost_usd` and
  `charged_to_ceiling_usd` per sweep directory, classifies every gap, and refuses to print a
  per-call mean across heterogeneous fields. `--selftest` runs 21 expectations over 9 cases,
  including a negative control that goes red when the counter exceeds what is on disk, and a
  mutant of its own mtime heuristic.
- **`field_sweep.py` writes both names**, and calls `judge_ledger.field_cost_usd` to compute the
  second, so the harness and the ledger cannot become two accountings again.
- **Four documents corrected**, each with what it used to say: `README.md`, `eval/RUNS.md`,
  `eval/judge/JUDGING.md`, `DECISIONS.md`.
- **Nothing imported from `game-research-gpt`** except candidate 5, a read-date stamp. Four of
  six candidates are rejected on measurements taken here; one was already adopted in axis 1.

### The pre-registered verification, and it came out mixed

Written before the tool was run, which is the point:

> `judge_ledger.py` must reproduce `eval/RUNS.md`'s three published judge figures — $33.63,
> $31.66, $100.84 — exactly, **and** flag the directories whose stored counter disagrees, naming
> a gap that is a prefix of the execution order. Reproducing the figures while flagging nothing
> would make it a formatter, not a check.

Both halves hold: the three figures reproduce to the cent, five directories are flagged, and
every gap resolves to carried-over rounds with none unexplained and none missing.

**And the first version passed for the wrong reason on one of them.** Its mtime split identified
`pre`'s carried round correctly from mtimes 0.0006 s apart, left by a `cp` in alphabetical
order — which is also the execution order. Requiring the boundary to exceed 60 s makes `pre`
report AMBIGUOUS, which is the honest answer. A check that agrees with you for a reason you did
not intend is indistinguishable from one that works, and only the variant half of rule 15 asks.

### Both ways — what this project does that theirs does not, on this axis

1. **A run ledger exists at all, with two columns and a stated reason they differ.** Records
   versus `[built]` lines, and the note explaining that a retry overwrites what it replaces.
2. **Comparability is a first-class field.** `RUNS.md` marks which runs may be pooled and why
   not, gated by `docstat.py --sweep` on duplicate regime ordinals. Their manifests record what a
   file *was*, never what it may be *compared with*.
3. **A durability guard on the path that spends money.** `assert_out_root_durable` refuses an
   ephemeral `--out` because a $44 sweep once wrote the only copy of a finding's evidence into
   `/private/tmp`. Their durability story is about reconstruction after the fact.
4. **The cost of a measurement is priced before it is taken, per population.** Round 3 was
   projected at ~$93 from per-aspect means and came in at $100.84; a pooled per-call mean would
   have priced `idiomatic` at a third of its cost.

### Was a fifth axis warranted?

**No.** Five were planned and four exist. The unallocated fifth would have been a second pass
over `evaluation/runs/`, and the axis-1 measurement stands: 30 GB and 194,505 files, none of it
sanctioned reading, and the readable surface is exhausted. Task 11 closes here.

---

## Iteration 13: the completeness gate reads the function's INPUT, so add one that reads its output

**Context.** Iteration 11a repurposed `pack_completeness` to assert `files_dropped_for_length == 0`,
so a reintroduced character budget could not truncate silently. That reasoning was sound and the
gate still earns its place. What it did not ask is whether the *pack on disk* is the pack the
manifest describes — and it could not, because every number it reads was computed by `anonymise`
about the files it picked, before it wrote anything.

**What the gap cost.** `anonymise.build_pack` never cleared its destination, so nine evaluations
of `wg-g4c` left 23 files in 222 under labels no manifest lists, stack-correlated 10/8/3/2
(unity/godot/ts/rust), including seven copies of the `.codex` answer key #83 was closed on. Every
pass returned normally. **No gate the project owns opened the directory** (#95).

> **A gate on a component's input cannot see what its output accumulated.** The manifest and the
> pack are different objects and only one of them was ever read.

**Change.** `field.pack_matches_manifest` opens each stored pack and asserts set equality against
its manifest, per submission, frames included. `field.build_pack` refuses a code field that fails
it. `field.py packcheck --run R` runs it standalone. Three verdicts, and the middle one is not
collapsed into either neighbour: `clean`, `unmeasurable` (a pack with no manifest — 25 stored
submissions predate it), stale/missing named per submission and counted per stack.

`--allow-truncated` deliberately does **not** excuse it. That escape exists for the
capped-vs-uncapped control, where truncation is the experiment; a stale file is not an
experimental condition, and every reason not to count a failure is a channel a bug can widen.

**Falsification, and why a mutant was not enough.** A mutant that deletes the clearing code cannot
manufacture the input that produces this defect — the input is a *second pass with a changed file
set* (rule 15). `judge/pack_selftest.py` runs the real function twice over one destination with a
changed exclusion set, in both directions, plus frames, plus a planted stale file against a clean
negative control, plus a hand-rebuilt pre-fix pack that the check must still catch.

| run | result |
|---|---|
| `pack_selftest.py` against the unfixed function | **4 of 7 expectations unmet** |
| `pack_selftest.py` after the fix | 0 unmet, exit 0, mutant still caught |
| three passes over 8 real `wg-g4c` submissions, unfixed | **8 of 8 fail** |
| the same over 16 real submissions of two runs, fixed | **0 of 16 fail** |

**What would have caught it earlier.** Not a better gate — a cheaper habit. The `.src` filename
collisions this surfaced through had been visible in any pack listing; across the 43 checkable
submissions the labels collide **0 times** rebuilt from the manifests and **15 times** rebuilt
from disk. **List the artifact, do not only read the code that wrote it** — the same move that
found the mapping file inside a pack.

---

## Iteration 14: a blinding specified as a PROPERTY and implemented as a SUFFIX

**Hypothesis, stated so it could have come out against the change.** `architecture` is the one
aspect judged with `blind_language=True`, and its whole blinding was `tgt.with_suffix(".src")`.
If that rename were sufficient, a sweep of the stored packs for arm-naming extension tokens
*after* `neutralise` would return a small number explainable as noise. If it were a label rather
than a blinding, the number would be large and would sit in cross-file references — the places a
rename cannot reach.

**Measurement.** All 84 stored `judge_pack/code` directories, every file, `neutralise` applied:
**2,083 arm-naming extension tokens**. The four the ticket named reproduce to the digit — `.ts`
973, `.gd` 583, `.rs` 258, `.cs` 62 = 1,876 — over **76** packs, not the 78 the ticket claimed;
the count reproduced and the pack union did not.

**The part that was not in the hypothesis, and matters more than the part that was.** The densest
leak is not in agent-authored code. `field.build_pack` writes `CHANGED.txt` itself from
`git diff --stat`, and in the 8 stored `architecture` packs that one harness-written file carries
80 `.cs`, 78 `.gd`, 60 `.meta`, 43 `.ts` and 43 `.rs` — a complete list of the real authored
paths, sitting in a directory whose every file had just been renamed to `.src`.

> **When you ask what a pack leaks, ask what the PACKER added, not only what the submission
> carried.** Every blinding gate in this repository reads the submission's files. None reads the
> harness's own contributions to the same directory.

**Change.** `field.blind_extensions()`, applied through one `_text()` helper so no channel can be
blinded and another not, and reached only where `blind_language` is set — the repair could not go
in `neutralise`, which runs for every aspect and would have blinded `idiomatic`, whose entire
question is whether Rust reads like Rust.

**Two vocabularies, and neither derives the other.** What is *arm-exclusive* comes from the four
starters and is audited mechanically by the selftest, so the next engine format is a red test.
What can also be a *member name* comes only from the corpus, and it is what stops the obvious
version of this repair being worse than the leak: `.lock` is 108 `Mutex::lock()` calls and **0**
filenames, `.anim` is 128 `player.anim` accesses and **0** filenames. A starter census would have
listed both.

| run | result |
|---|---|
| `blind_ext_selftest.py` against the unrepaired `field.py` | **16 of 24 files leak, 28 tokens**, all 8 `CHANGED.txt` among them |
| after the change | 0 unmet expectations |
| mutant (`blind_extensions` neutered) | check 1 goes red — 16 files, 28 tokens |
| variant (`blind_language=False`) | byte-identical to `neutralise` alone; 16 files still name their extensions |
| re-sweep, 84 stored packs | 2,083 → **0**, with 81 `import.meta` declined and reported on its own line |

**And the thing the fixture could not have told me, found by pointing the finished repair at a
real run.** Two defects, neither reachable from the test data:

1. **`field.py pack` was passing the aspect's `sees` and not its `blind_language`.** The one
   entry point a human types produced a completely unblinded `architecture` pack — 199 of 207
   files keeping their real suffix, 663 extension tokens in content. `field_sweep.py` passed
   both properties at all three of its call sites, so no stored round is affected, and that is
   precisely why it survived: every test called `build_pack` directly, where the argument is
   explicit. **When an object gains a property, grep for every reader of its siblings.**
2. **`(?!\s*\()` was a false negative.** `// Usage: node tools/audio-manifest.mjs   (or: just
   audio-manifest)` is a filename, three spaces, and a parenthesis; the method-call guard read
   it as a call. One occurrence in 84 packs, and no fixture in this repository produces that
   shape. **A mutant asks whether a check can fail; only a variant asks whether it can still
   pass** — and the variant that found it was the finished code aimed at real data.

| control on a real run (`wg-g4c/g4_platformer`, 207 files) | result |
|---|---|
| `--aspect architecture`, before | 199 language-naming filenames, 663 extension tokens |
| `--aspect architecture`, after | **0** filenames, **11** tokens, all `import.meta` |
| `--aspect idiomatic`, before vs after | `diff -r` **exit 0** — byte-identical, the aspect that must not be blinded is untouched |

**What is still open, stated rather than left implicit.** The directory half — `public` 1,148,
`Assets` 128, `res://` 34 — is untouched at 1,561 segments (task 95). And **no stored
`architecture` round is language-blind**: this repair licenses new rounds and repairs none, which
is now written into `eval/RUNS.md` beside the `neutralise` caveat that has the same shape.

## Iteration 15: a total over two channels, and the one that was 100% signal

**Hypothesis.** Iteration 14 handed on a single number — 1,561 arm-naming directory segments
surviving `blind_extensions` in the 8 stored `architecture` packs — and a guess to go with it:
that an extension vocabulary can be audited against the starters mechanically and *a directory
vocabulary probably cannot*. If the guess is right, the repair is a hand-maintained list of
directory names with a collision census behind each entry, the way `_NOT_AN_EXTENSION` was built.

**Measurement, and it did not survive the partition.** The 1,561 is a mean over a heterogeneous
population, one level below where rule 4 usually fires — not over submissions, over *channels*:

| channel | a real path segment | the same word doing something else |
|---|---|---|
| `CHANGED.txt` | **182** | **0** |
| code content | 149 | **1,230** |

1,129 of the 1,148 `public` hits are the C# access modifier; 16 of the 17 `ProjectSettings` are
`ProjectSettings.globalize_path()`; `Assets` is `ResMut<Assets<Image>>` in Rust packs. **A total
that pools a 0% collision rate with an 89% one describes neither channel, and it is the number
that would have chosen the wrong repair** — a vocabulary, aimed mostly at words that are not
paths.

> **When a leak census returns one figure, partition it by WHO WROTE THE TEXT before choosing a
> repair.** The channel the harness authored and the channel the agent authored are different
> populations with different remedies available, and only one of them has ground truth on hand.

**Change.** `field.blind_changed_txt()`: under `blind_language`, `CHANGED.txt` is **rebuilt**
from the pack's own origin → label manifest rather than rewritten, so it reads
` sim/01.src | 42 ++--`. There is no directory vocabulary in the repair at all — the two failure
modes a vocabulary has (firing on a non-path, missing an unlisted directory) are both unavailable
to a table the packer itself wrote. Rows that map to no label are omitted; their count is not
shown to the judge and is recorded beside the pack as `changed_rows_dropped`.

| run | result |
|---|---|
| `blind_dir_selftest.py` with only `field.py` reverted | **28 segments survive, 32 rows cite a file not in the pack** |
| after the change | 0 unmet expectations |
| mutant (`blind_changed_txt` neutered) | check 1 goes red — 28 segments |
| variant (`blind_language=False`) | `CHANGED.txt` byte-identical to `neutralise` alone; 28 directory segments still there |
| fail-closed (one character broken in every manifest origin) | refuses, rather than writing an empty `CHANGED.txt` |
| re-sweep, 43 stored submissions with a diff and a manifest | **1,275 → 0**, per segment, 535 rows mapped and 1,186 omitted |
| real run, `wg-g4c/g4_platformer`, both packers | 207 files each, **8 files differ and all 8 are `CHANGED.txt`**; 330 → 0 segments; code channel 106 → 106 |

**The guess this iteration was handed turned out to be wrong, and the right answer was still no.**
A directory vocabulary read from `git ls-files` over the four starters *is* auditable: whole-segment
and path-adjacent, it finds 536 hits across all 84 stored packs with exactly **1** in an arm the
segment does not name. It was declined anyway, for a reason the feasibility question does not
reach — **the redaction it produces is stack-correlated by construction**: Godot 0, Rust 43,
Unity 228, TypeScript 265, because only some starters have arm-exclusive directories. A judge
seeing three packs with redacted paths and one without has been handed the partition by the
instrument (#62). `tasks/103` carries the measurement.

> **"Can this check be built?" and "should it run?" are different questions, and a feasibility
> answer looks like a decision.** The vocabulary was buildable and precise; what disqualified it
> was the shape of its output, which no amount of precision improves.

**Two things the fixture could not have said.** `blind_ext_selftest.py`'s fixture had carried
`"origin": "real/1"` since it was written, because nothing read the field — and a placeholder
origin maps nothing, so the new fail-closed guard fired on the project's own test data the first
time it ran. That is the guard working. The second: its `blind-changed-txt-neutral` check now
passes for a different reason than it was written for, since a manifest-built `CHANGED.txt` never
contained an extension for `blind_extensions` to remove. It is kept and **labelled in place** —
a check that quietly changed what it tests is this repository's central failure mode, and the
alternative to the comment is a green nobody can interpret.
