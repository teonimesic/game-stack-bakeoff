# Eval findings

Findings #19-#134 from building and running this evaluator. **Check whether a
number has been retracted before trusting it** — `eval/withdrawn.json` is the machine-readable
half of that, and `docstat.py --withdrawn` enforces it over the live documents.
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
| **90** | #87's decomposition fixed the number and got the boundary wrong, in the direction that loses evidence | [limits-and-cost](findings/limits-and-cost.md) |
| **91** | Three of four mutants were inert because the real data never reached the branch they broke | [certifies-nothing](findings/certifies-nothing.md) |
| **92** | A scored tier that returns the same number for every submission, and the weight in front of it | [certifies-nothing](findings/certifies-nothing.md) |
| **93** | `suite.json` describes the last thing written into the directory, not the run | [documentation](findings/documentation.md) |
| **94** | A guard that succeeded three times while three agents took the same number | [certifies-nothing](findings/certifies-nothing.md) |
| **95** | A judge pack is a numbering, not a set, so re-evaluating a run left nine passes stacked on disk | [one-arm-bias](findings/one-arm-bias.md) |
| **96** | The gate written for #95 was exit-0 vacuous at every address but the right one | [certifies-nothing](findings/certifies-nothing.md) |
| **97** | Four of the nine performance fields had been written on every submission since the first matrix, and nothing ever read them | [certifies-nothing](findings/certifies-nothing.md) |
| **98** | The Godot template's own gate was red before any agent touched it, and only that arm paid | [one-arm-bias](findings/one-arm-bias.md) |
| **99** | A second copy of the skills for an agent that was never here, never once in sync, invisible to every tool | [documentation](findings/documentation.md) |
| **100** | The stored evidence for `verify.green` drops the gate's own "passed" line on 15 of 16 Rust submissions, because stdout is truncated before stderr | [one-arm-bias](findings/one-arm-bias.md) |
| **101** | The TypeScript capture page never ran its own determinism script, and the defect filed instead was the opposite of the truth — radius zero on all 26 stored submissions | [one-arm-bias](findings/one-arm-bias.md) |
| **102** | A submission the judge never disagreed with gets an error bar of zero, and then out-resolves everything | [certifies-nothing](findings/certifies-nothing.md) |
| **103** | #100 was repaired in the file it named, and the same merged buffer is still in the runner that stores the agent's own gate | [one-arm-bias](findings/one-arm-bias.md) |
| **104** | The only record of the starter a run was given is a git commit no archive contains, and the reclamation rule says to delete it | [limits-and-cost](findings/limits-and-cost.md) |
| **105** | Of 27 unread exit statuses 24 were deliberate, and one of the three that were not was the lint category itself, green on two of the three ways ruff can fail to run | [fail-open](findings/fail-open.md) |
| **106** | Two pristine starters are not format-clean, so `just verify` rewrites a file the agent never touched and every stored trial diff carries the hunk | [one-arm-bias](findings/one-arm-bias.md) |
| **107** | Godot's capture path cannot show presentation state that accumulates across ticks and Bevy's can, so the two arms differ in what a filmed frame can contain — **radius measured 2026-08-23: it is 1 vs 3, ts and unity behave as godot does** | [one-arm-bias](findings/one-arm-bias.md) |
| **108** | The pre-campaign parity gate collected `just test`'s exit code and read only `passed/total`, so a stack whose toolchain was absent printed `0/0` and the tool still reported no drift | [certifies-nothing](findings/certifies-nothing.md) |
| **109** | Unity's batchmode editor runs an FMOD CoreAudio output whatever the manifest says and whatever `-disable-audio` says, so the flag's stated reason is not something it achieves | [fail-open](findings/fail-open.md) |
| **110** | The three.js capability called the largest measured effect in the matrix was measured at 167x this task set's geometry, against a baseline nobody would write, for a field that cannot resolve it | [certifies-nothing](findings/certifies-nothing.md) |
| **111** | The reference half of the doc sweep had never read a skill: its corpus was built with `glob`, which does not descend into dot-directories, so 0 of the always-loaded instruction documents were ever checked | [certifies-nothing](findings/certifies-nothing.md) |
| **112** | The repaired capture page had a second live copy, and no commit in the project's history had ever touched it — a fork, not a mirror, so nothing could be gated on equality | [documentation](findings/documentation.md) |
| **113** | A withdrawn tier-3 figure is still the published separation result in three live documents, and a cross-document consistency check cannot see it because propagation IS agreement | [certifies-nothing](findings/certifies-nothing.md) |
| **114** | The runner's merged capture is repaired and the reader audit found the field had no readers at all, which is why a stack-correlated loss survived four matrices | [one-arm-bias](findings/one-arm-bias.md) |
| **115** | The replacement for the withdrawn tier-3 pair was correct and the sentence explaining it was not, and that sentence is the ground #113 fell back on | [certifies-nothing](findings/certifies-nothing.md) |
| **116** | The re-sync trigger named an event, so the verified second copy missed the one class the project had just proved it could not rebuild — and two files it did hold had verified as stale prefixes | [documentation](findings/documentation.md) |
| **117** | Forty-four task files failed a YAML parse loudly and nine failed silently, returning a truncated value that looked like an answer | [certifies-nothing](findings/certifies-nothing.md) |
| **118** | Fixing a finding-number collision by renumbering is what creates the dangling reference, and it still resolves — 10 renumbers, 27 stale citations across eight corpora, and the third of them that history cannot decide | [documentation](findings/documentation.md) |
| **119** | A claim withdrawn in the archive was still cited as current in three live documents six days later, and every citation resolved — so the fix is a declared withdrawal register, keyed on an id, not any consistency check | [documentation](findings/documentation.md) |
| **120** | One function guarded the prompt snapshot and overwrote the manifest eleven lines below it — 5 affected directories, not #93's 3, and #93's third row is a UTC string compared against a local-time name | [documentation](findings/documentation.md) |
| **121** | A budget ceiling and a bill are different questions, and one variable answered both under the bill's name — three accountings of one judge field, 5 of 11 stored sweeps under-reporting by $69.93, and a published $46.79 that is two games | [limits-and-cost](findings/limits-and-cost.md) |
| **122** | Retiring a suite would have deleted the only copy of what its trials were asked to do: 71 stored trials record `task: "t1_rally"` and 0 files under `eval/runs/` contain the prompt | [documentation](findings/documentation.md) |
| **123** | In 68 trials the 0.31-weighted tier deducted for a property of a playable game five times, and every one was a lint finding, a unit test or an ink-coverage window | [certifies-nothing](findings/certifies-nothing.md) |
| **124** | The findings index split into two tables and the sweep that checks the log was green on it — every row resolved, and what broke was the thing holding them together | [documentation](findings/documentation.md) |
| **125** | A guard stated as a resource was implemented as a layout, so reusing it verbatim would have broken two documented readers | [fail-open](findings/fail-open.md) |
| **126** | A near-miss heading check could not tell a rename from a forgotten copy, produced two rows, and both were false — in opposite directions | [certifies-nothing](findings/certifies-nothing.md) |
| **127** | The producer built to stop a count going stale globbed one level deep and lost 15% of the tree — 137 records against a true 161 — and the cross-check that certified it had been produced by the same glob | [certifies-nothing](findings/certifies-nothing.md) |
| **128** | Tier 2 saturates because the task is finished, not because the criteria are too few: 5 of 10 groups return one value, every selective failure in the corpus is from the first matrix, and four harder criteria built from the task's own unchecked requirements passed 8 of 8 | [certifies-nothing](findings/certifies-nothing.md) |
| **129** | Rule 11's first implementation found a one-arm starter defect in its first pass that a hand pass over the same corpus had missed | [one-arm-bias](findings/one-arm-bias.md) |
| **130** | A hook that passes and a hook that never ran leave the same artifact, and the guard had been verified from file presence | [certifies-nothing](findings/certifies-nothing.md) |
| **131** | The anonymiser's stack vocabulary was a list of SPELLINGS, so the Rust arm shipped `CARGO_MANIFEST_DIR`, `crates/sim` and `clippy.toml` into 22 of 84 blind packs — and 9 of 9 architecture rounds with a file-open log opened one | [one-arm-bias](findings/one-arm-bias.md) |
| **132** | A field name that collided with an unrelated one let a false claim about it survive every grep | [certifies-nothing](findings/certifies-nothing.md) |
| **133** | A focus guard installed as an autoload minimised the window the godot render tests read pixels from; macOS then returned the same stale frame to every capture, 6 of 9 tests failed blaming the arena transform and the particle system, and the 2 that passed were the reproducibility tests | [one-arm-bias](findings/one-arm-bias.md) |
| **134** | The gate over the findings figure checked the RANGE and the COUNT went stale beside it, spelled in words where no check could read it — and the first mutant showed the check had two implementations | [certifies-nothing](findings/certifies-nothing.md) |

---

## Adding one

Number it next, put it in the file whose shape it matches, and add a row above. State the
claim in the heading as a sentence someone could disagree with — not "bug in bot_pong"
but what was believed, what was true, and how the gap stayed invisible.

Retractions stay, marked. A published number later proven wrong, and a published reading
of evidence later overturned, both remain — someone may have acted on them.
