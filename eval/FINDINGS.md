# Eval findings

Findings #19-#89 from building and running this evaluator. **Check whether a
number has been retracted before trusting it.**

The entries live in `findings/`, grouped by the shape of the failure rather than by date,
because the shapes repeat and the dates do not matter. Citations are by number and
resolve through the table below.

| file | covers |
|---|---|
| [certifies-nothing](findings/certifies-nothing.md) | measurements that ran and certified nothing |
| [one-arm-bias](findings/one-arm-bias.md) | defects that fire on one arm and look like a result |
| [fail-open](findings/fail-open.md) | guards, repairs, and the ones that failed open |
| [limits-and-cost](findings/limits-and-cost.md) | limits, cost, comparability |
| [documentation](findings/documentation.md) | docs and rubric naming things that do not exist |
| [early-single-stack](findings/early-single-stack.md) | the superseded 2026-08-10..12 phase, incl. two retractions |

---

## The one pattern

> **A mechanism that runs, reports success, and measures nothing.**

Most of what follows is an instance. Three variants are worse and are worth naming
separately:

- **It produces a number, and the number is wrong** (#19). Indistinguishable from a real
  result at the moment you act on it.
- **It passes for the wrong reason** (#39). Invisible to a mutant suite, because the
  mutant breaks the reason the criterion was never testing.
- **It fails open** (#31). Every other defect here costs you trials; this one costs you
  the result.
- **It runs after the thing it was fixing** (#47). It reports success, truthfully, in
  twenty-four places, and changes no number.

## The test is what the artifact does, not what the account covers

> **A hypothesis that explains everything you have looked at is not thereby correct.**

The pit hypothesis for #82 explained the evidence string, named a real defect in the bot,
predicted exactly which submissions would fail, and produced a general principle that is true and
worth keeping — *the penalty is indexed to how good the level is*. Every part of that survived
scrutiny. It was still the wrong cause, and the fix built on it changed the score by nothing: the
re-grade came back byte-identical.

What separated the account from the truth was **ten lines of instrumentation against the
artifact** — opening a probe session and printing where the bot was and which enemy it had
chosen. Not more reasoning about the output. The same move settled #81 (hashing the evidence
strings showed 4-of-4 distinct, killing the caching story) and #83 (grepping the pack for tokens
showed the judge was inferring, not copying).

Three of the last four findings turned on running something against the real object rather than
reasoning further about its output. **When a hypothesis fits, that is the moment to go and watch
the thing run**, because a fitting hypothesis is exactly what stops people looking.

## The rules, in the order they would have saved the most

1. **A negative control is necessary and not sufficient.** `total=0 passed=0` is
   indistinguishable from correctly failing. Every task needs a positive control, and
   ideally an adversarial one.
2. **Never infer a process's state from its artifact's state.** Check the exit code the
   process reported.
3. **A pipeline's exit status is the last stage's.** And never `cmd || echo 0` — a
   fallback that turns an error into a plausible in-range number.
4. **Never compute a mean over a population you have not established is homogeneous.**
   Partition by terminal status first.
5. **Never quote a value you did not just read from its source.**
6. **A guard whose trigger names an external cause cannot fire on an internal one** — and
   looks like a fix.
7. **Every reason not to count a failure is a channel a bug can widen.**
8. **Change one thing.** Except a ceiling that may be binding: raise those, and let the
   measurement tell you whether they were.
9. **A control shares the assumptions of the thing it controls** unless you deliberately
   make it not. Ask what would make the control fail; if the answer is "the same thing
   that would make the check fail", it is a second copy of the check.
10. **A stack-correlated pattern is the shape a harness defect takes here.** **Six for
    six.** Not reportable without a named causal chain in the code.
14. **An artifact is MORE order-invariant than a judgement, not less.** Never promote a judge
    on stability; the reliability metrics are anti-correlated with validity over the range
    that matters (#55).
11. **A repeated identical measurement across independent subjects is not corroboration.**
    It is the signature of a shared cause, and the shared cause is usually the instrument
    (#45, #46, #50).
12. **A mutant suite is necessary and not sufficient; a variants suite is the other half.**
    Mutants ask whether a criterion can fail. Only a correct game the reference does not
    resemble asks whether it can still pass (#46, #48).
13. **Partition by terminal reason, and also by anything about the world that changed while
    the run was in flight.** A run is not a controlled experiment merely because it is one
    command (#49).

## Every finding

| # | claim | in |
|---|---|---|
| **19** | the failure mode that is worse than measuring nothing | [certifies-nothing](findings/certifies-nothing.md) |
| **20** | I leaked rubric vocabulary into the starter myself, and the guard caught it | [one-arm-bias](findings/one-arm-bias.md) |
| **21** | an LLM judge's verdict stability is a property of the ARTIFACT, not the rubric | [documentation](findings/documentation.md) |
| **22** | a summary statistic that was arithmetically correct and referentially empty | [certifies-nothing](findings/certifies-nothing.md) |
| **23** | I check other people's work and assert my own | [certifies-nothing](findings/certifies-nothing.md) |
| **24** | a permission change created a measurement confound, and nothing connected them for two days | [one-arm-bias](findings/one-arm-bias.md) |
| **25** | a harness defect that can only fire on one arm is bias, not noise | [one-arm-bias](findings/one-arm-bias.md) |
| **26** | The judge's only measured signal was a screenshot artifact | [certifies-nothing](findings/certifies-nothing.md) |
| **27** | The fix for a measurement defect belongs in the thing that lied, not only in the metric | [fail-open](findings/fail-open.md) |
| **28** | A capture that frames against a viewport which has not been realised yet | [fail-open](findings/fail-open.md) |
| **29** | Sixteen false negatives, repaired — and the repair found two latent bugs that would have made the harness fail OPEN | [fail-open](findings/fail-open.md) |
| **30** | A guard whose trigger names an EXTERNAL cause cannot fire on a failure with an INTERNAL one — and looks like a fix | [one-arm-bias](findings/one-arm-bias.md) |
| **31** | The first defects in this project that would have failed OPEN | [fail-open](findings/fail-open.md) |
| **32** | The blind judge's pack contained the answer key | [one-arm-bias](findings/one-arm-bias.md) |
| **33** | The spending cap is an INPUT to the agent, not an external kill | [limits-and-cost](findings/limits-and-cost.md) |
| **34** | Making the task harder created a false negative in a criterion that had never fired | [certifies-nothing](findings/certifies-nothing.md) |
| **35** | The invisible limit became the binding one, and nothing announced the inversion | [limits-and-cost](findings/limits-and-cost.md) |
| **36** | The retry overwrote the record of the thing it was retrying, and the ledger lost the money | [fail-open](findings/fail-open.md) |
| **37** | Two agreeing readings said "stalled"; the descendants said "compiling" | [certifies-nothing](findings/certifies-nothing.md) |
| **38** | A document that names a component which does not exist | [documentation](findings/documentation.md) |
| **39** | The mutant caught what the reference, the fixture's own tests and the bot's own run all missed | [certifies-nothing](findings/certifies-nothing.md) |
| **40** | A stack-correlated pattern is the SHAPE a harness defect takes here | [one-arm-bias](findings/one-arm-bias.md) |
| **41** | A shared preamble edited for one game silently changed all four tasks | [one-arm-bias](findings/one-arm-bias.md) |
| **42** | The calibration trial was an outlier, and one trial cannot calibrate a 1.6x-variance process | [certifies-nothing](findings/certifies-nothing.md) |
| **43** | A resource that looks per-trial and is not — twice, on two stacks, invisibly | [one-arm-bias](findings/one-arm-bias.md) |
| **44** | The blinding scanner cried contamination on a clean $1,727 matrix | [fail-open](findings/fail-open.md) |
| **45** | The artifact under measurement was stored somewhere with a lifetime shorter than the measurement | [one-arm-bias](findings/one-arm-bias.md) |
| **46** | Two criteria failed six submissions for four kinds of enemy the bot never lived long enough to meet | [certifies-nothing](findings/certifies-nothing.md) |
| **47** | A repair that named the right cause and ran after the measurement it was fixing | [fail-open](findings/fail-open.md) |
| **48** | Two findings were reintroduced by the agent that had both of them open in front of it | [certifies-nothing](findings/certifies-nothing.md) |
| **49** | The arena matrix straddles a machine repair, and the split is exactly the stack split | [one-arm-bias](findings/one-arm-bias.md) |
| **50** | Two independent agent runs produce identical grades in every cell — the instrument has no resolution below the cell | [certifies-nothing](findings/certifies-nothing.md) |
| **51** | The adjudication gate counted a judge's honest citations as fabrications, and doubled its own number | [certifies-nothing](findings/certifies-nothing.md) |
| **52** | The best-behaved subjective judge was ranking how long the play-bot happened to run | [certifies-nothing](findings/certifies-nothing.md) |
| **53** | The blinded judge can read the stack off the file extension, and `idiomatic` scores the stack rather than the submission | [one-arm-bias](findings/one-arm-bias.md) |
| **54** | Two judges with no evidence in common produced the same ranking, twice — **WITHDRAWN, did not replicate** | [certifies-nothing](findings/certifies-nothing.md) |
| **55** | Statistical validation of a judge cannot tell a judge that reads its evidence from one that does not | [certifies-nothing](findings/certifies-nothing.md) |
| **56** | The pre-launch gate had not run since the configuration changed under it | [certifies-nothing](findings/certifies-nothing.md) |
| **57** | A guard that had been red for months, on a condition the project had formally decided was acceptable | [certifies-nothing](findings/certifies-nothing.md) |
| **58** | The ceiling gate's threshold sits in a gap the field cannot land in, and half the field sits on its edge | [certifies-nothing](findings/certifies-nothing.md) |
| **59** | The last surviving subjective aspect was ranking palette depth | [one-arm-bias](findings/one-arm-bias.md) |
| **60** | The tool that measures whether measurement is happening was pointed at the old location | [certifies-nothing](findings/certifies-nothing.md) |
| **61** | Two tasks were marked complete having guarded the path that was already safe | [fail-open](findings/fail-open.md) |
| **62** | Every code pack was truncated, the amount varies by stack, and the record has said so since the first matrix | [one-arm-bias](findings/one-arm-bias.md) |
| **63** | A noise floor estimated from one cell was wrong by a factor of seven | [limits-and-cost](findings/limits-and-cost.md) |
| **64** | The count that proved the gate was costly counted the documentation | [limits-and-cost](findings/limits-and-cost.md) |
| **65** | The docstring said every criterion establishes its condition, so nobody checked the one that did not | [certifies-nothing](findings/certifies-nothing.md) |
| **66** | Unity's `just verify` told the agent its work was clean; the same tree fails from a clean extract | [one-arm-bias](findings/one-arm-bias.md) |
| **67** | `(0, 0)` is a plausible position, so an empty rectangle scored as one | [one-arm-bias](findings/one-arm-bias.md) |
| **68** | The subjective layer's first positive result, and the control that made it readable | [certifies-nothing](findings/certifies-nothing.md) |
| **69** | The pack budget removed: more than half of some submissions was never shown to the judge | [one-arm-bias](findings/one-arm-bias.md) |
| **70** | A trial id is not a key, and two runs' `g2_tetris3d__unity__t1` are different games | [documentation](findings/documentation.md) |
| **71** | The subjective layer has only ever judged one game out of four | [certifies-nothing](findings/certifies-nothing.md) |
| **72** | A 1.000 on pong clears 13 hurdles; a 1.000 on arena clears 22 | [certifies-nothing](findings/certifies-nothing.md) |
| **73** | A tally: eleven vacuous checks, and what they have in common | [certifies-nothing](findings/certifies-nothing.md) |
| **74** | The capped-vs-uncapped test could not answer its question, and the reason was the ceiling | [certifies-nothing](findings/certifies-nothing.md) |
| **75** | A threshold placed where the data cannot land — #58's shape, one level up | [certifies-nothing](findings/certifies-nothing.md) |
| **76** | The Unity pattern was the field, not the stack — refuted by a $8.29 re-grade | [one-arm-bias](findings/one-arm-bias.md) |
| **77** | Rebuilding an old pack against a moved starter reclassifies template code as authored work | [one-arm-bias](findings/one-arm-bias.md) |
| **78** | `ux` tracks distinct-colour count on all three games it has been run on | [one-arm-bias](findings/one-arm-bias.md) |
| **79** | `idiomatic` has a real stack-level component, but #53's contrast between stack and submission was backwards | [one-arm-bias](findings/one-arm-bias.md) |
| **80** | Two durable records that quietly lost content: a shell-substituted evidence string and an overwritten task | [documentation](findings/documentation.md) |
| **81** | The rule-9 alarm on unity was mis-framed: repeats of one subject measure reliability, not agreement | [certifies-nothing](findings/certifies-nothing.md) |
| **82** | The play-bot was blamed for not crossing pits; it was picking targets it could not reach | [certifies-nothing](findings/certifies-nothing.md) |
| **83** | The answer key was in the judge's pack again: `.codex` hook scripts carried the trial id | [one-arm-bias](findings/one-arm-bias.md) |
| **84** | A criterion can measure the play-bot's input policy instead of the submission | [certifies-nothing](findings/certifies-nothing.md) |
| **85** | A per-tick filter will fire during a state the agent itself created | [certifies-nothing](findings/certifies-nothing.md) |
| **86** | What a round cannot say about itself, and why prose is not a substitute for a field | [documentation](findings/documentation.md) |
| **87** | A directory's size is not the size of the thing you are protecting | [limits-and-cost](findings/limits-and-cost.md) |
| **88** | #84's two other candidates were measured and both are clean | [certifies-nothing](findings/certifies-nothing.md) |
| **89** | `knockback.applied` scored a deliberate design branch as an absent feature | [certifies-nothing](findings/certifies-nothing.md) |
| **90** | The judge pack directory is never cleared, so nine evaluation passes left ten percent stale files | [one-arm-bias](findings/one-arm-bias.md) |

---

## Adding one

Number it next, put it in the file whose shape it matches, and add a row above. State the
claim in the heading as a sentence someone could disagree with — not "bug in bot_pong"
but what was believed, what was true, and how the gap stayed invisible.

Retractions stay, marked. A published number later proven wrong, and a published reading
of evidence later overturned, both remain — someone may have acted on them.
