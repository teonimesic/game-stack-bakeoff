# Documentation and rubric defects

A document naming something that does not exist is confidently wrong and will be
followed. Prose is executed by a person, and a person gets no argparse error.

> Index and the distilled rules: `../FINDINGS.md`


## #21 — an LLM judge's verdict stability is a property of the ARTIFACT, not the rubric

This is the most transferable result this project has produced, and it generalises to
any rubric-based LLM evaluation, not just game grading.

### The measurement

The same judge, the same thirteen binary criteria, the same model, run six times over
each of two submissions with nothing changed between runs:

| submission | score min–max | spread | instability | criteria contested |
|---|---|---|---|---|
| a good agent-built Pong | 1.000 – 1.000 | **0.000** | 0.000 | 0 / 13 |
| the `broken` control fixture | 0.000 – 0.308 | **0.308** | up to **0.462** | 5 / 13 |

On the contested artifact, **six of thirteen criteria disagreed with themselves on
presentation order within a single run**, and the aggregate score varied by 0.308
across runs — roughly a third of the scale.

Crucially, the *same criteria* behave differently on the two artifacts.
`code.function_size`, `code.magic_numbers`, `code.comments` and `code.robustness` were
rock-solid 6/6 on the good submission and flipped on the broken one. Nothing about the
rubric changed.

### The result

**Criteria agree when the answer is obvious and diverge when it is borderline.**
Stability is therefore not a property of the rubric, the model, or the prompt — it is a
property of how clear-cut the artifact is.

Two consequences follow, and both are traps:

1. **Measuring judge reliability on clear-cut fixtures systematically overstates it.**
   A validation suite built from an obviously-good and an obviously-broken example will
   report high agreement, because those are exactly the cases where agreement is cheap.
2. **The reliability you measure is highest precisely where you need the judge least.**
   If the artifact is unambiguous, a script can usually classify it. The judge earns
   its place only on borderline work — and that is where its verdicts are least stable.

### We made this exact error, in our own validation gate

The gate for shipping the judge tier was a discrimination test over three fixtures:
`ref_pong` (good), `ref_adversarial_pong`, and `broken`. It passed cleanly — 0.92 /
0.62 / 0.23, monotone separation — and `ref_pong` came back with **instability 0.000**.
That figure was reported as evidence the judge was sound.

It was evidence of nothing except that `ref_pong` is unambiguous. The tier was
validated on the easy end of its own range, and the number that looked most reassuring
was the least informative one in the set. The failure only surfaced when a variance
study was run against a *contested* artifact, and by then the tier had already been
weighted and reported.

### What to do instead

* **Validate a judge on borderline artifacts, not on the extremes.** Deliberately
  construct submissions that sit near the boundary of each criterion. If you cannot
  construct them, you do not yet know what the criterion means.
* **Report per-artifact stability, never a single global reliability figure.** A mean
  instability across a fixture set is dominated by whichever fixtures were easy.
* **Treat a low instability reading as a statement about the artifact.** It says the
  case was clear; it does not say the instrument is good.
* **Sharpening the questions does not fix it.** Three criteria here were rewritten to
  remove unstated thresholds. On the contested artifact the corrected rubric was *more*
  unstable than the original (0.308 vs 0.154). Better questions are still worth having;
  they are not a route to stability.

### Why the tier was dropped from the score

Two independent arguments, kept separate because they fail differently:

1. **It cannot reorder anything.** Bounded contribution 0.10 against a tightest
   adjacent gap of 0.0622 on the deterministic tiers. True regardless of noise.
2. **Its aggregate is noisiest exactly where it would matter** — the result above.
   True regardless of weight.

The judge still runs on all 24 matrix submissions and its per-criterion verdicts and
evidence strings are reported. What is discarded is the *aggregate number*. The
per-criterion output remains genuinely useful: on `broken` it correctly and stably
failed eight criteria, quoting the fixture's own docstrings and the pixel-identical
frames. **The detail was informative; the total was noise.**

---


## 38. A document that names a component which does not exist

`RUBRIC.md` — the file that is supposed to be the subjective layer's contract — carried this
table, written 2026-08-14:

| aspect | judge |
|---|---|
| Gameplay & fun | `fun` |
| Game feel & responsiveness | **`feel`** |
| Difficulty & tuning | **`tuning`** |
| Audio | `audio` |
| Visual coherence | **`look`** |
| UX & onboarding | `ux` |
| Idiomatic stack use | **`idiom`** |
| Code quality | **`code`** |

`aspects.py` defines five: `fun`, `ux`, `audio`, `idiomatic`, `architecture`. **Five of the eight
names in the contract do not exist**, one exists under a different name (`idiom` / `idiomatic`),
and one that does exist (`architecture`) is absent from the table. `field_sweep.py` takes
`choices=sorted(ASPECTS)`, so `--aspects feel` is rejected by argparse.

### Why this is its own entry and not filed under carelessness

Every other defect in this catalogue is a mechanism that runs and measures nothing. This one does
not run at all — and it is worse than saying nothing, because **a document is executed by a
person, and a person does not get an argparse error.**

The failure mode is concrete and was one step away. The brief for this session said: *"if `fun`,
`feel`, `ux` and `idiomatic` produce the same ordering, that is one judge with four names."* That
instruction was written from the table, names a judge that cannot be run, and would have produced
either a crash or — worse — a three-aspect independence result silently reported as four. An
independence gate is precisely where a phantom aspect does damage: the gate's whole job is to
count how many *distinct* judges there are.

Note the direction of the error. The table is not out of date; it was **never** true. It describes
the layer that was designed rather than the layer that was built, and nothing connected the two.

### What made it findable, and what did not

It was not found by reading `RUBRIC.md`, which is internally coherent and reads well. It was found
by asking the code what it accepts:

```
python3 -c "from aspects import ASPECTS; print(sorted(ASPECTS))"
```

That is the same move as #32, where the judge pack's answer key was found by **listing the
directory** rather than reading the code that filled it. Two instances now: when a document
describes a component, verify it against the component, not against the document's own coherence.

### Swept for the same defect

The check is mechanical, so it was run across every doc rather than only the one that failed:

| layer | result |
|---|---|
| aspect ids | `RUBRIC.md` wrong (fixed); `JUDGING.md`'s implemented table correct — it lists exactly the five |
| criterion ids in `RUBRIC.md` vs the three bots plus `static.py`/`audio.py`/`checks.py` | all present, except `look.feedback` and `look.legible`, which are retired vocabulary from the withdrawn 13-criterion judge and are labelled as withdrawn |
| `--flags` named in any doc vs every harness argparse | all resolve; the one exception is Godot's own `--headless` |
| backticked file paths in any doc | all resolve |

So the defect was confined to one table, and the sweep is the evidence for that rather than an
assumption. **Run the sweep after writing any doc that names code.** It costs seconds and it is
the only check in this project that can be complete.

---

---

## 70. A trial id is not a key, and two runs' `g2_tetris3d__unity__t1` are different games

*(The two runs are `wg-matrix-2026-08-13` and `wg-audio48-2026-08-14`.)*

A re-film was about to be avoided by a clever, free substitution: the judged
`wg-matrix-2026-08-13` field had one submission captured at 420x640 against a 640x400 field,
and `wg-audio48-2026-08-14` held a 640x400 capture of *the same submission id*. Use those frames
instead. No filming, no regime mix, no cost.

**Pinned before relying on it, and the pin failed.** The two are not the same work:

| | `wg-matrix-2026-08-13` | `wg-audio48-2026-08-14` |
|---|---|---|
| files in submission | 266 | **442** |
| files present in only one | 6 | **182** (a whole `Assets/Audio/` tree) |
| same path, different content | — | **27**, including `Assets/Sim/Sim.cs` |
| prompt | 5,889 bytes, **0** audio mentions | 7,507 bytes, **8** audio mentions |

`wg-audio48` set an audio requirement that `wg-matrix` did not. **The id denotes a different
task, a different prompt and different code.** Substituting those frames would have put a
different game's pixels into the judged field — and it would have looked completely fine,
because the id matched and the geometry matched.

> **An id is a name within a run, not an identity across runs.** The instinct that "the same
> submission was filmed twice" is the same instinct that read "IMPROVEMENTS iteration 1b" as
> unambiguous when two files share that name — a defect this project already fixed once by
> requiring paths, recurring in a namespace nobody had thought of as a namespace.

### It had already cost a round of confusion

#59 cited `g2_tetris3d__rust__t0` filming at 768x576 with no run named. Measured from PNG IHDR
bytes across the archive, **four geometries exist and each belongs to a different run**:

| id | geometry | run |
|---|---|---|
| `g2_tetris3d__unity__t1` | 420x640 | `wg-matrix-2026-08-13` |
| `g2_tetris3d__rust__t0` | 768x576 | `wg-audio48-2026-08-14` |
| `g2_tetris3d__ts__t1` | 720x540 | `wg-audio-2026-08-14` |
| everything else (32) | 640x400 | all runs |

Two people reading the same finding disagreed about which submission diverged, and **both were
right about different runs.** The third case was named by neither.

### Fixed

- #59 and the citations in #66, #67 and #68 now name their run.
- `docstat --sweep` fails on a trial id cited with no run in section scope, as a **ratchet**: the
  count may fall, never rise. An allowlist of specific ids would be a channel a bug can widen
  (rule 7); a number that can only decrease is not.
- The ratchet was first set to 20 against an actual 18, and **a planted bare id passed**. A guard
  with headroom is not a guard. It is set to the exact count and pinned in both directions.

### The same defect again, in a second namespace: a pack LABEL is not a key across rounds

2026-08-22, verifying the Unity refutation (#76). A reviewer pooled scores **by pack label** over
two rounds, resolving them through only the **first** round's mapping — and got a clean, plausible
table putting Unity 1st on `g3_arena` where the correct answer is 3rd.

`build_pack` **reshuffles the label→submission mapping independently for every round**; that is
the entire point of an order seed. So `A` in round 0 and `A` in round 1 are different
submissions, and averaging them averages different games' scores together. The result does not
look wrong — it looks like a tidy contradiction of a correct finding.

> **Two namespaces now, same rule.** A trial id is a name within a run. A pack label is a name
> within a *round*. Neither is an identity, and both produce plausible tables when treated as one.
>
> **Any analysis joining scores across rounds must resolve every score through its own round's
> mapping.** Every stored round already carries `submissions[].submission`, resolved at judging
> time — use that field, never `label`.

**Guarded, because it is greppable**: `docstat --sweep` fails any module that reads multiple
rounds (a `rep*`/`seed*` glob) and also indexes `["label"]`, which is wrong by construction.
Pinned both ways.

**What made the disagreement resolvable** is worth recording next to the error. The refutation had
controlled for the n confound — tetris restricted to consecutive round-pairs, Unity topping 6 of 6
windows at n=2 — rather than dismissing it. A result that has already survived its most obvious
objection can absorb a contradiction and locate the fault; one that has not simply becomes a
standoff.

**The re-film decision reverts: the substitution is invalid.** Either film, accepting that it
creates a *third* geometry for that id, or do not judge that field on frames — which the parity
gate now enforces without anyone remembering to.

---

## 80. Two durable records that quietly lost content: a shell-substituted evidence string and an overwritten task

Both on 2026-08-22, both writing to a record meant to outlive the session, both silent.

### The evidence string that executed itself

Closing task 07 with `tasks.py done 07 "...so \`just lint\` and \`just verify\` answer from the
code while \`just check\` keeps its warm cache..."` — written inside double quotes, so the shell
treated each backticked phrase as **command substitution**. `just` ran three times in a directory
with no justfile, printed `error: no justfile found` to stderr, and substituted **empty strings**.

The stored record became *"so / answer from the code while  keeps its warm cache"*. Three phrases
gone. `tasks.py` reported success, because from its side nothing failed: it received a string and
wrote it faithfully.

> **The corruption happened before the tool that owns the record ever saw the data.** No amount of
> validation inside `tasks.py` would have caught it — the string it was handed was already wrong.
> The three `error: no justfile found` lines were the only signal, and they looked like noise from
> an unrelated command.

Prose destined for a durable record should be written **to a file**, not passed through a shell
argument. Where it must go through a shell, single-quote it.

### The task that was overwritten by a concurrent writer

`tasks.py add` computed the next id by reading the directory and then called `write_text`, which
truncates. Two agents adding a task at the same time both computed `12`, and **one task vanished
with no error from either side.**

Fixed: exclusive creation (`open(..., "x")`), and on collision take the next free id and retry —
checking the **id**, not the filename, because the same number with a different slug is still the
same task. Pinned: a decoy squatting id 18 is left intact and the new task lands on 19.

### What the pair have in common

Neither was a bug in the thing being written to. One was corrupted upstream by the shell; the
other by a writer that never asked whether the destination already existed. **A record is only as
durable as the weakest step in the path that reaches it**, and both weak steps were outside the
component that looked responsible.

This is the same shape as #62 — a field nothing read — but worse in one respect: there, the data
was present and ignored. Here the data was **destroyed**, and the destruction left a success
message behind.

### A game is not a field either: the same defect one level up again

2026-08-22. `fun`'s rounds were reported as having read pre-repair telemetry, and tier 3's only
positive result (#68) was briefly marked compromised. **It was not.** The wrong field was
inspected.

`g2_tetris3d` is not a field. It is a **game with four stored fields in different states of
repair**:

| run | representative telemetry |
|---|---|
| `wg-matrix-2026-08-13` | **0 of 8** |
| `wg-audio-2026-08-14` | 0 of 3 |
| `wg-audio48-2026-08-14` | **8 of 8** — re-driven 2026-08-17, deliberately, before the judge round |

The rounds read `wg-audio48`. Established by **fingerprint**, because the stored round does not
record which run it judged: all **7 of 7** `quiet_fraction_of_run` values and **4 of 4**
`events_per_second` values quoted in #68's evidence appear in `wg-audio48`'s stored telemetry, and
**none** appears in `wg-matrix`'s.

> **A trial id is not unique across runs; a GAME is not unique across runs either.** Same rule,
> third namespace. And the failure mode is the one this session keeps producing in new costumes:
> **a claim true of one population, quoted about another.** It appeared as code-vs-evidence in
> `DECISIONS.md` — "the confound is gone by construction" described the code and was read as
> describing the field — and immediately again as evidence-vs-evidence across two runs of the
> same game.

**Fixed at the source rather than by being more careful.** `run_field` recorded the game and not
the run, so no stored round could answer "which field was this?". `build_pack` had the run in its
mapping record all along; `field.py` now carries `mapping["run"]` into every stored round. The
fingerprint match was only possible because the evidence quoted numeric telemetry — a round whose
aspect cites no numbers would have been unresolvable.

**What made this recoverable was insisting the answer come from the round files rather than from
either party's reasoning.** Both readings were coherent, both were argued from real evidence, and
one was wrong. The values decided it in a single query.
