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
