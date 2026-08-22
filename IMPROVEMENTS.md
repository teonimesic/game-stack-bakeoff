# Improvement loop

Each iteration is a hypothesis, a change, and a measurement that could have come out
against it. The falsification criterion is written **before** the measurement runs.
A reverted change is a successful iteration: it bought a real answer.

An iteration that ends "I improved X" with no number attached has measured nothing.

---

## Iteration 1 — does the play-bot tier notice a game no human can play?

**Status: PRE-REGISTERED, not yet run.**

### Why this first

The play-bot tier carries **0.69 of the grade** — more than everything else combined —
and it has only ever been validated against artifacts where the answer was obvious:
three reference implementations scoring 13/13, 13/13 and 15/15, and two broken controls
scoring 0/13. That is the identical ceiling error already written up for the LLM judge
in FINDINGS #21: reliability measured where reliability is cheap.

### The suspected gap

The play-bot reaches the simulation **only** through `just probe`. It never exercises
the view layer or the device-input path. Tier 1 checks that frames render and that
consecutive frames differ — but frames animate from the simulation alone, so a
submission whose keyboard handling is broken still passes.

The task's definition of done says *"`just run` opens a window and the game is actually
playable with a keyboard."* Nothing in the grading system tests that clause.

### Hypothesis

A submission whose probe path is correct but whose **view-layer keyboard-to-intent
wiring is severed** will score **unchanged** on tiers 1 and 2 — i.e. the grading system
cannot distinguish a playable game from an unplayable one.

### Falsification

If severing the keyboard path drops the tier-1 or tier-2 score **at all**, the
hypothesis is wrong and the tiers already cover this. I will report that outcome and
keep the tiers unchanged.

### Method

1. Take a completed matrix submission (extracted from its archive, so the original is
   untouched).
2. Sever only the view layer's keyboard-to-intent wiring. Do not touch the simulation,
   the probe, the tests, or the justfile.
3. Confirm the submission still builds and `just verify` is green — otherwise tier 1
   fails for the wrong reason and the experiment says nothing.
4. Run tiers 1 and 2 on both the pristine and the severed copy.
5. Compare per-criterion, not just totals.

Offline; no agent spend.

### Predicted result

Tier 1 unchanged at 9/9, tier 2 unchanged at 13/13, `overall` unchanged at 1.000.

### If confirmed

Add a criterion that exercises the real input path — the cheapest honest version is a
check that the view layer actually maps device input to the simulation's intent type,
since driving a real window from the harness is not portable across all four stacks.
Then re-measure: the severed copy must fail it and the pristine copy must pass it.
Both directions, or the new criterion is worth nothing.

---

## Iteration 2 — a design judge for aesthetics and game feel

**Status: PRE-REGISTERED, not yet built.**

### Why this is not a reversal of dropping the code judge

The code judge scored 13 binary criteria about code hygiene, and the deterministic
tiers already covered most of what it could see — so it was droppable at no loss.
Aesthetics and feel are the opposite case: **the play-bot can prove the ball bounces
and cannot tell you whether the game looks good or feels good to play.** No
deterministic tier will ever cover that. If it is to be measured at all, a subjective
judge is the only available instrument.

### What it sees

Not source code. The artifact as a player meets it:

- **Rendered frames as images**, several across a real play session, so motion,
  feedback and state changes are visible.
- **Play-bot telemetry as evidence of tuning**, not just correctness — pacing,
  time-to-first-meaningful-action, rally lengths, time-to-score, round duration,
  difficulty ramp, and whether anything ever stalls. Already collected; currently used
  only to assert things work.

### Criteria

Graded with stated anchors, not binary. Binary was right for "is there a placeholder";
it is wrong for "does this look good", where the information is in the middle.
Dimensions: visual coherence, readability of game state at a glance, feedback and juice,
pacing and tuning, polish (start state, end state, score, anything beyond a bare
mechanic).

### The measurement that decides whether this tier is worth anything

Two fixtures **differing only in the judged dimension** — same game, same mechanics,
same tests passing:

* **tuned**: legible palette, visible score, sane ball speed, visible feedback on events
* **detuned**: ball ~3x too fast, no visual feedback, low-contrast colours, no score
  readout

### Falsification

**If the design judge cannot separate the tuned fixture from the detuned one, it
measures nothing and does not ship.** I will report that plainly rather than keeping it
as a diagnostic that looks like signal.

Separation must exceed run-to-run noise: the tuned-vs-detuned gap has to be larger than
the spread across repeated judgings of the *same* fixture. A difference smaller than the
instrument's own variance is not a difference.

### Also required before it can be trusted

- Validate on **borderline** artifacts, not just the two extremes — a gorgeous and a
  broken submission will both judge unanimously and prove nothing (FINDINGS #21).
- Report **run-to-run variance on identical input** and forward/reverse instability
  **separately**. Subjective criteria are expected to be noisier; the question is
  whether they discriminate despite the noise, not whether they are quiet.
- Check every criterion is **exercised**. A criterion answered identically every run
  because the question never arose has not been tested.

### Weight

**None, pending validation.** Deciding a weight before knowing whether it separates a
well-tuned game from a badly-tuned one would repeat exactly the error that made the
code judge worthless at 0.10.

---

## Iteration: make Unity's `lint` answer the same question twice (FINDINGS #66)

**Not yet applied.** `starters/unity` is the product under measurement; editing it is a regime
boundary and requires re-running `verify_blind.py` and `starter_parity.py`. Filed here so the
change is made deliberately, between matrices, rather than mid-analysis.

### The observation

`g4_platformer__unity__t1`'s agent ran the gate it was told to run and was told it passed:

```
✓ lint: all assemblies compile clean
✅ verify passed
```

The same tree, extracted from its own `submission.tar.gz` into an empty directory, fails
`just lint` with exit 1 and five `CA1861` errors. The tarball and the work tree are byte-identical
on the offending file. The Editor assembly was not re-analysed after the agent's edit, so
violations that were still in the file never reappeared.

### The hypothesis

> **Unity's `lint` recipe reports the state of the build cache, not the state of the code.
> Forcing the analyzer to re-run will make a cold and a warm `just lint` agree.**

Candidate change: have `lint` build with analyzers forced (a clean or non-incremental
compile of the Editor and player assemblies) rather than accepting whatever the cache holds.

### MEASURED 2026-08-22 — hypothesis confirmed, mechanism named

Run on `g4_platformer__unity__t1` (`wg-g4c-2026-08-21`), a tree known to hold five CA1861
violations. Three arms, same submission, one copy each:

| arm | `Library/` state | `just lint` | wall |
|---|---|---|---|
| **A** — as it is today | full warm cache | **exit 0**, "all assemblies compile clean" | 8.9s |
| **B** — `Library/ScriptAssemblies` deleted | asset cache kept | **exit 0** — still wrong | 4.9s |
| **C** — whole `Library/` deleted | cold | **exit 1, all five CA1861 reported** | 10.9s |

**The cause is `tools/unity-compile.sh` copying `Library/` into its scratch project.** It already
compiles against a copy, to dodge Unity's project-wide lock, and strips only `artifacts/` and the
lock — so the warm build cache travels with it and Unity re-uses cached analysis for assemblies
it considers unchanged. A violation still in the file is never re-reported.

**Arm B is the informative negative.** Deleting the compiled assemblies is not enough; the
analysis is cached elsewhere under `Library/`. A surgical fix aimed at `ScriptAssemblies` would
have looked principled, changed nothing, and shipped as a repair.

### The cost objection did not survive measurement

This entry worried that a cold compile would slow `verify`, which agents run often, and that a
slower gate gets run less. **Measured: 10.9s cold against 8.9s warm — two seconds.** The worry
was reasonable and it was wrong.

The fast inner loop can still be preserved exactly: scope the change to `STRICT=warnings`, so
`just lint` (the authoritative gate) goes cold while `just check` (errors only) stays warm.

### The change, PREPARED AND NOT APPLIED

One line in `starters/unity/tools/unity-compile.sh`, immediately after the copy:

```sh
# The copy inherits Library/, so Unity re-uses cached analysis and a violation still in
# the file is never re-reported (#66). The strict gate must answer from the code.
[ "$STRICT" = "warnings" ] && rm -rf "$WORK/proj/Library"
```

`starters/` is the product, so applying this is a **regime boundary**: it needs
`judge/verify_blind.py`, `judge/starter_parity.py` and a `eval/RUNS.md` comparability note, and
no future matrix would pool with any previous one on Unity. **Awaiting a decision.**

**Pins to run with it, both directions:** arm A must go exit 0 → exit 1 with five CA1861, *and* a
tree with no violations must stay exit 0. Without the second, this is a gate proved only in the
failing direction.

**One consequence, stated plainly:** with this applied, `g4_platformer__unity__t1` becomes a
genuine `verify.green` failure rather than a template defect — that submission really does ship
code failing the project's own strict gate. #66 remains valid as a description of what the agent
was told at the time, which is what made it not-a-submission-defect *then*.

### The original falsifier, kept

On a tree **known** to contain violations, run `just lint` warm and cold and compare exit codes.
The change is only justified if they currently disagree and agree afterwards.

Two outcomes and what each would establish:

| outcome | reading |
|---|---|
| cold and warm disagree now, agree after | the defect is incremental analysis, and the fix holds |
| they agree now | #66 has another cause and this change is cosmetic — **do not ship it** |

The second is a real possibility and must be checked first: the evidence for #66 is a clean
*extract*, which differs from the work tree in more than cache state, and that difference has not
been isolated. **Establish the mechanism before changing the product.**

### What it cuts against

It makes `verify` slower, and `verify` is the command the templates ask agents to run often —
the justfile says so in its own header. A slower gate is run less, and an agent that stops
running the gate is a worse outcome than a gate that is occasionally stale. If forcing analyzers
costs more than a few seconds, the honest fix may be a separate `lint-cold` recipe used by the
grader, plus wording in the template that the fast path is incremental.

### Scope

This is not a `g4` problem. The gate has been green on the Unity arm across four matrices and
nothing has ever compared its answer to a cold build, so **"Unity passed lint" has never been the
claim it appeared to be**. `starter_parity.py` compares recipe *text*, not recipe
*reproducibility*, which is why it never fired — a second gap worth its own iteration.
