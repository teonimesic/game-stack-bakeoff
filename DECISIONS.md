# Decisions

What is decided and why. Current state only.

**[user]** = decided by the project owner. **[agent]** = routine judgement call made in the work.

---

## Scope

| Decision | By |
|---|---|
| 2D **and** 3D, local **and** multiplayer, macOS/iOS/Windows | [user] |
| Console support is **aspirational**, not gating | [user] |
| Open source preferred, not mandated | [user] |
| No stack is mandated — everything is compared empirically | [user] |
| Deliverable is the **full loop, run autonomously** | [user] |
| Netcode: **Elixir for meta-services, Rust for realtime** | [user] |
| Determinism is **enforced**, not encouraged | [user] |

Determinism drives the clippy bans, the boundary tests, and the replay hash chains. The requirement
is **within-stack** determinism only — cross-stack hash equality is not achievable and is not a
goal. Unity's 1-ULP divergence is a Mono/ARM64 property (FMA contraction) not reachable from source.

## Stacks under measurement

Four, each with its own fine-tuned template: **Rust + Bevy 0.19**, **TypeScript + three.js**,
**Unity 6**, **Godot 4.7**.

Each template is tuned to its own stack's strengths rather than parity-ported, so agents get the
best chance of success on their stack's own terms. Tasks are held similar across stacks so the
comparison stays fair.

Eliminated: Unreal (binary assets an agent cannot diff, multi-minute compiles), Zig/Stride/Flax/
KorGE/O3DE (pre-1.0 churn, near-zero training density). See `research/DECISION.md`.

Godot needs a display server for render verification — `--headless` genuinely cannot capture, but
windowed capture works. Material, not disqualifying.

## How measurement works

| Decision | By |
|---|---|
| Evals run the **`claude` CLI directly**, not the SDK | [user] |
| Building agents run on **Opus** | [user] |
| Tasks are **whole-game builds** ("build 3D Tetris"), not spec changes | [user] |
| A **hidden judge** grades gameplay and codebase quality; building agents must not know how they will be graded | [user] |
| The **template layer and judge layer are distinct** | [user] |
| Tasks are **independent**, run in **parallel**, in the **background** | [user] |
| Prompts are **semantically identical but stack-native**, not byte-identical | [user] |
| `--setting-sources project` is mandatory | [agent] |
| **Stack-native covers stack facts, never harness facts.** A mechanism wired identically in all four starters must be described in all four guides | [agent] |

Byte-identical prompts are not neutral — they end up written in one stack's vocabulary and bias the
comparison. `--setting-sources project` is empirically verified: without it the operator's global
`~/.claude/CLAUDE.md` leaks into every arm.

The third row is where that principle was being over-applied. "Stack-native" is what licenses four
different Bevy/three/Unity/Godot API sections and Godot's headless limitation — things true of one
stack. It does **not** license one arm knowing about the Stop hook while three do not, which is
what happened for as long as the hook existed (task 78): `.claude/hooks/verify-gate.sh` and the
`"Stop"` wiring are byte-identical across the four trees, and only `starters/rust/AGENTS.md` said
so. Wording still differs per stack; silence is the thing forbidden. Enforced as an axis rather
than a habit — `judge/starter_parity.py::mechanism_findings`, keyed on **every event wired in
every starter**, so the next hook is covered by the rule that caught this one.

**A harness mechanism whose success path is silent records what it DID, outside the tree it
acts on.** The Stop gate was the case: exit 0 leaves nothing in the transcript, so "the gate is
live in all four arms" had only ever been established from the file existing (task 78). The four
hooks now append `invoked` plus a verdict to `$STARTER_HOOK_LOG`, which `wholegame.py` addresses
into the trial's **artifact** directory and never into the trial tree — the tree becomes the
graded diff, and a log written there is #106's contamination wearing an audit trail's clothes.
The address is asserted in code before launch and the outcome re-measured per trial, because
those are two different questions. The guides were deliberately not told: it changes nothing an
agent should do, and telling it would be an observer effect on the thing being measured.

## What the task asks for

| Decision | By |
|---|---|
| **The arena task is 3D, analog and spectacular** — a bounded volume, movement and aim on all three axes, continuous −1..1 input, gamepad and mouse, three behaviourally distinct enemy kinds, materialisation before an enemy is dangerous, a score multiplier, and stated on-screen requirements | [user] |
| Tasks require **audio** — looping music, a distinct effect per declared event, a `just audio-manifest` contract | [user] |
| Tasks require **presentation and experience** — a game someone would want to play, not a demonstration that the mechanics exist | [user] |
| Everything the player sees **must appear in `just film` frames** | [user] |

The first matrix produced an exact 24-way tie: four well-built templates on Opus solved
everything put in front of them, so there was no variance left to resolve. Audio and
presentation are added because they are work the templates do **not** pre-solve — no
starter ships a single sound, and none shipped a HUD example that reached the frame
capture until 2026-08-14.

**Runs before and after this change are not comparable on any tier.** The task is
different, tier 1 has 14 criteria instead of 9, and tier 2 has one more. Same treatment
as the allowlist change.

The **arena rewrite of 2026-08-15** is a second, narrower break and applies to `g3_arena`
alone: tier 2 goes from 15 criteria to 22, and the eight arena submissions built before it
answer a different question. They are archived rather than discarded — they are the only
arena data under the $48 regime — and the 3D set is graded separately. Its play-bot is
rewritten and twelve of the new criteria are pinned by mutants; the analog criterion caught
a real defect on its first run, in the reference fixture's own probe.

## Matrix configuration

| Decision | By |
|---|---|
| **Targeted Bash allowlist** — `just`, `cargo`, `pnpm`, `git`. Not `bypassPermissions` | [user] |
| **2 trials per cell — 24 trials** | [user] |
| Engine-heavy selections (godot/unity) build at **`--parallel 2`**, not 4 | [agent] |
| **`--max-turns 1000`, and NO budget cap** | [user] |

`--max-budget-usd` is **visible to the agent and instructs it** — token usage rose 1.54× on
Tetris when the stated ceiling went from $25 to $48. `--max-turns` is invisible and merely
truncates. Any stated budget is an instruction, so only an absent one is neutral; 1000 turns
bounds a trial near $130 of token valuation, which is a runaway backstop rather than a ceiling.
And on a subscription account the figure names nothing scarce, so a capped agent was conserving
a resource that does not exist — see *"No run is bounded by a money figure"* below.

Resource use under this configuration is **lightly measured** — every prior figure was taken with
a budget instruction in force. Calibrate before committing a matrix. See `eval/PROTOCOL.md`.

**Runs under different caps are not comparable** on token usage, turns, or anything downstream of how
much work the agent chose to do, and every cost figure this project has published is partly a
measurement of its own cap. Treat any change to the pair as a task change. The regimes so far are
$25, $48, and (from now) none.

**The 250-turn limit had already become the binding constraint at $48**, which is what prompted
raising it: `g3_arena__rust__t1` stopped at 251 turns and $35.75 with $12 of its stated budget
unspent (FINDINGS #35). At that point the run was governed by the invisible flag while appearing
to be governed by the visible one — the inverse of the regime the $48 cap was chosen for.

Without an allowlist, agents lose ~30% of turns to denials — including being blocked from running
their own verify gate, which makes them under-report their own completeness. The allowlist cuts
that to 9.8%. It does **not** reduce cost: per-trial spend is unchanged, so it buys better-verified
output rather than cheaper output.

Runs with and without the allowlist are **not directly comparable**.

## Grading

Three tiers. Blinding is verified mechanically by `eval/judge/verify_blind.py`.

| Tier | Weight |
|---|---|
| Programmatic — builds, gate green, lints, tests, frames render and animate | **GATE** — pass/fail, not scored |
| Play-bot — a scripted bot drives thousands of ticks and asserts the game plays | **1.00** |
| LLM judge — one specialist per aspect, each ranking a whole eight-submission field | **0.00** — diagnostic only |

### Tier 1 gates, it does not score — decided 2026-08-23

`overall = tier2`. Tier 1 held **0.31** from this repository's first commit until then, quoted in
four documents and derived in none of them; git history holds no derivation either, so there was
nothing to state and the question became what the tier is for. Two offline sweeps, both able to
come out the other way, and both re-runnable:

Both figures below are what the producers printed **on 2026-08-27**, over 69 stored submissions;
they are live counts, so re-run the commands rather than trusting the date. The decision was taken
on the 68-submission corpus of 2026-08-23, which held every group but the scene; the scene added an
eleventh group of one, and no verdict moved.

- `python3 eval/judge/weight_sensitivity.py --all --runs-root <main checkout>/eval/runs` —
  **FLIPS=0** at every weight in (0,1), but **8 of 11 groups UNIDENTIFIABLE**: tier 1 returns one value across the whole group, so the weight is inert
  for the reason that matters least (#92). It sweeps the *open* interval, and the gate regime is
  w1=0, so this tool cannot settle what the change does — see the next one.
- `python3 eval/judge/tier1_census.py --runs-root <main checkout>/eval/runs` — 69 stored
  submissions, **8 with any tier-1 failure**, and in **0 of 11 groups do both tiers vary among the
  trials tier 2 could measure**. Comparing the two schemes
  pairwise at w1=0: **0 orderings reversed, 3 coarsened, 8 identical** (#123).

Six of those eight failures were a lint finding, three of a submission's own unit tests, or an
ink-coverage window; the 5 games among them all scored **1.000** on tier 2, and the sixth is the
scene, which is not a `completed` trial and is not pooled with them. The other two were the #49
build failure, whose tier-2 zero is the same fact told twice.

**The ink ceiling `tasks/168` removed fired on 2 of the 8**, and the census reads stored records,
so it counts what tier 1 DID. Re-graded, one of the two leaves the failing set outright and the
other keeps the 3 failures of an interrupted build; `eval/RUNS.md` holds both. Removing a tier-1
failure can only reduce tier-1 variance, so neither re-grade can give a group a varying tier 1.

Tier 1 is a floor test and is now reported as one: `gate: PASS`, or `FAIL` with the failing ids.
**A gate failure does not deduct and does not exclude the trial** — deducting restores what was removed, excluding is a reason not to count a
failure (rule 7). `build.compiles` and `probe.responds` are marked *blocking*, because the play-bot
drives through `just probe` and cannot produce independent evidence without them.

`RUBRIC.md` carries the full derivation and the condition that re-opens it: the census prints
`DISCRIMINATES` the moment a tier-1 criterion with real headroom exists. **Stored scores were not
rewritten** — 14 of the 68 submissions stored on the day the regime changed would move, largest
0.2273; that is a count of that date's corpus, not a live one — and the regime boundary is in
`eval/RUNS.md`.

**The judge is unweighted for two independent reasons, either sufficient:**

1. **It cannot reorder anything.** Bounded contribution 0.0154 against a tightest adjacent gap of
   **0.0667** — recomputed on tier 2 alone after tier 1 left the score, per game over the 24
   `wg-matrix` records; dropping tier 1 widens every gap. Holds regardless of noise. (The older
   0.0622 is not reproduced by that method and its own method is unrecorded; `JUDGING.md` has the
   table.)
2. **It is noisiest exactly where it would matter.** Score spread 0.308 and instability up to 0.462
   on a contested submission, against 0.000 on an uncontested one. Holds regardless of weight.

Its per-criterion verdicts are still reported and are genuinely useful — it catches surviving
placeholders, tautological tests, and pixel-identical frames that no deterministic tier sees.

**The general result behind this** (FINDINGS #21): *an LLM judge's verdict stability is a property
of the artifact, not of the rubric.* Criteria agree when the answer is obvious and diverge when it
is borderline — so validating a judge on clear-cut fixtures systematically overstates its
reliability, and the reliability you measure is highest exactly where you need the judge least.
Rewriting the three unstable criteria did not fix it; the rewrite made a contested submission
*less* stable.

### `render.nonempty` is a floor with no ceiling, and no tier-1 bound is class-dependent — decided 2026-08-27

**Because tier 1 gates, a mis-calibrated bound does not cost a fraction of a score.** It stops a
correct submission being scored at all. So the question *is this bound a property of the artifact,
or of games?* is asked of all 14 tier-1 criteria, and the answer is code —
`static.TIER1_BOUND_POPULATION`, gated by `static.assert_tier1_bounds_declared()` — rather than a
paragraph somebody re-derives. **8 carry no bound, 6 carry one that transfers, 0 are
class-dependent.**

`render.nonempty` scored mean ink coverage inside `0.001–0.85` for every task from this
repository's first commit until `tasks/163`, which removed the ceiling for **scenes** on
2026-08-26. That range was derived in no document, no comment and no commit message. **The
decision: for every task class, the floor stays, the ceiling is removed, and a test for a frame
set in which every frame is a single colour replaces it.**

**The floor is a property every starter shares** — their own `renders a non-empty frame` test, and
a placeholder marker covering 0.0015 of a 640x400 frame — so it transfers, and a blank frame fails
in either class.

**The ceiling was removed because `mean_ink` does not measure how much was drawn.**
`ink_coverage` counts pixels differing from **one** reference colour per frame, so the quantity is
a property of the palette:

| frames | measures | which half decides |
|---|---|---|
| solid white, magenta or black — "the render broke and filled the screen" | **0.0**, in any colour | the **floor** |
| a gradient with a subject on it — a night platformer's sky | **0.679** | neither; it passes |

A high reading means the palette has no dominant colour, and a full screen reads at the bottom of
the scale rather than the top.

**And the ceiling was not a blank-frame guard either, which is the measurement that settles it
rather than the argument.** 12 frames each holding a single colour have drawn nothing, and under
the reference in force at the time `mean_ink` read 0.0, 0.91667 or 0.5 depending only on how those
colours were *arranged* against frame 0's (`WR-ink-arrangement-0-91667` — the arrangement stopped
moving the number when the reference did, later the same day). `0.001–0.85` admitted **2 of the 3**
non-zero arrangements. A bound on this quantity was never what stood between the grader and a
blank render.

**So the criterion asks the question directly instead.** `png.Image.is_flat` reads each frame
against **its own** mode, `analyse_frames` counts them as `flat_frames`, and `render.nonempty`
fails when every frame is flat — all 4 arrangements, whatever their ink. **0 of the 67 stored frame
sets contain a flat frame**, so the added half moves no stored verdict, and `flat_frames` absent is
a third value: a record written before 2026-08-27 is re-graded on the floor alone and its evidence
says so.

Every number above is a checked row in `eval/judge/ink_window_control.py` (`MECHANISM_ROWS`,
`BLANK_RENDERS`, the `flood` fixture) rather than a sentence here, so the derivation goes red if
`ink_coverage` changes.

**Corroborated by what 0.85 had ever done.** The producer is `python3
eval/judge/ink_window_control.py --runs-root <main checkout>/eval/runs`; its population is
`tier1_census`'s — **69 submissions**, the most recent grading of each, from 85 on disk with 16
superseded and held out. It reports them **per class, never pooled: `game: n=68`, `scene: n=1`**.
Every ink figure in this section is the **frame-0 reading the stored record holds**, which is what
each ceiling verdict was decided against; the reference moved later the same day, and
`--reference-shift` prints both. 4 firings:

| | mean ink | what it was |
|---|---|---|
| `wg-arena3d` `g3_arena__rust__t0`/`t1` | 0.0, **floor** | 0 frames — the #49 build failure, which `render.frames` reports in the same record |
| `wg-g4c` `g4_platformer__godot__t1` | 0.881, **ceiling** | a night platformer over a gradient sky. Tier 2 = 1.000 |
| `wg-scene-s1ts` `s1_parallax__ts__t0` | 0.966, **ceiling** | the first scene, drawing what it was asked to draw |

**Among the 2 ceiling firings: 0 true positives and 2 false negatives.** The 2 floor firings are
true positives and are counted separately — both are the #49 build failure at 0 frames, which
`render.frames` reports in the same record, so the floor has never fired on a frame that was
rendered at all.

**Within the game class**, the 68 game values are also a continuum rather than 2 populations. The
scene is the 69th and stays its own population, here as everywhere: no aggregate crosses the task
classes. **The split is inferred, not read** — the producer prints `task_class` read from the
record on **1** of the 69 and `_class_of`'s reading of the trial id on the other **68**, so every
sentence here about *the game corpus* rests on the id shape. The 6 highest are 0.679, 0.703, 0.736, 0.772, 0.828 and 0.881, every one of them
`g4_platformer` — the one game whose background scrolls across the whole frame — and the largest
gap among those 6 is 0.0555. **0.85 fell in a gap of 0.0536, between 2 trials of that same game**,
so what it separated was a **task** and not a quality. The 7th value down is `g3_arena__rust__t0` at 0.60285, 0.076 below the 6th.

**It was removed, not widened.** Widening it to admit `g4_platformer__godot__t1` would have been a
threshold chosen from the subject that exposed it; no number on this measure means *too full*, so
there is no number to choose. `ink_window_control.py` carries the restored 0.85 as a mutant.

**The cost, paid deliberately:** an offline re-grade changes the derived gate verdict of `wg-g4c`
`g4_platformer__godot__t1` from `FAIL 1/14` to `PASS 14/14`. **The stored record still holds the
FAIL and nothing under `eval/runs/**` was rewritten** — `eval/RUNS.md`'s *`render.nonempty` lost
its ink ceiling* break holds both readings side by side.

**What re-opens it.** Re-open this decision only if `eval/judge/ink_window_control.py` reports a
ceiling firing that is a real defect. The frame set must contain no flat frames — every frame drew
something — and the play-bot or the scene probe must condemn the submission too. The output
recorded on 2026-08-27 holds 2 ceiling firings, and neither meets that test.
`eval/judge/RUBRIC.md` holds the table.

### `mean_ink` measures each frame against its own background, not against frame 0's — decided 2026-08-27

**The decision: `analyse_frames` takes a background per frame**, so `mean_ink` is the fraction of a
frame that is not its own background. It used to take one background from frame 0 and apply it to
all 12, making `mean_ink` departure from the *first frame's palette*. Nothing derived that choice,
here or anywhere else, and the criterion it feeds asks whether the frames contain something other
than a blank background — a question about each frame.

**2 measurements decided it, both taken on the pre-change code before it was changed:**

| | against frame 0's mode | against each frame's own |
|---|---|---|
| 12 frames, frame 0 uniform black, the other 11 uniform white with one 2x2 speck — 4 pixels of 256000 drawn | `mean_ink` **0.91665**, `flat_frames` 1 of 12, `render.nonempty` **PASS** | **0.00001**, **FAIL** |
| the stored corpus: frames reading *exactly* 1.00000, the value a frame gets when its clear colour differs from frame 0's | **14 of 804**, in 3 sets, whose own modes give 0.04336, 0.03777 and 0.44721 | **0 of 804** |

The first is fail-open and both halves of the criterion admitted it — a frame with a speck is not
flat, so `flat_frames` cannot see it either. The second is rule 12's signature: a census returning
one saturated value across the population it exists to discriminate is reporting the instrument.

**The objection, and why it dissolves.** A per-frame mode moves when a drawn subject grows past the
background in area — and so does frame 0's, which is the same computation on one arbitrary frame.
The fixed reference does not avoid that error; it freezes one frame's version of it and applies it
to 11 frames it was never measured on. What it buys is stability across a set, and nothing consumes
`per_frame_ink` as a time series: change between frames is `render.animates`, measured separately
by `differs_from`.

**The cost.** **10 of the 67 stored frame sets move** and **0 verdicts move** — the lowest value
under either reference is 0.00811, 8x the floor. The producer is `python3
eval/judge/ink_window_control.py --runs-root <main checkout>/eval/runs --reference-shift`;
`eval/RUNS.md`'s *`mean_ink` moved to a per-frame background* break holds the 10 rows and the
regime boundary they create.

**This is a regime break and not a withdrawal.** The stored figures remain true of the records that
hold them — they are what the grader that ran computed — so they are not retired, only incomparable
with what the grader computes now, which is what `eval/RUNS.md` exists to record. The one figure
that *is* retired is `0.91667`, because it was never a property of any render:
`WR-ink-arrangement-0-91667`.

**The all-flat half is now redundant rather than independent, and is kept.** `png.Image.is_flat` is
`ink_coverage(own mode) == 0.0`, the floor's own per-frame term, so all-flat implies `mean_ink` 0.0
implies below the floor. It stays as the fail-closed direction, and because `flat_frames` reports
*how many* frames were blank, which a mean cannot. `ink_window_control.py` asserts the implication
over every fixture and arrangement rather than leaving a comment promising it.

**What re-opens it.** A submission whose drawn subject reliably exceeds its background in area, so
the per-frame mode tracks the subject and a valid render reads near 0. Nothing in the 67 stored
sets is one — the 7 highest of the 66 game sets are all `g4_platformer`, whose gradient sky has no
modal region at all, which is a different mechanism. Run `--reference-shift` to look.

**`task_class` stays in `BOUND_POPULATIONS` with 0 members.** It is the value a future
class-dependent bound declares, and `assert_tier1_bounds_declared()` is what makes declaring it
safe — a criterion that claims one without a per-class table fails.

**`static.collect` still takes the class**, because it also picks the capture length and the audio
criterion set. Two different wrong-class failures, caught in two different places: an
**unregistered** class is refused by `static.assert_task_class` before a toolchain is spent, and a
**registered but wrong** one — a scene routed as a game — is caught by
`eval/tools/scene_runner_control.py`, which spies on what the runner hands down. Neither is a
tier-1 bound reading the class, because none does.

### A saturated tier 2 is reported as a completion certificate, not repaired — decided 2026-08-23

Tier 1 becoming a gate left `overall = tier2`, and tier 2 is itself at the ceiling. **This is
accepted as a property of the current task set rather than treated as a rubric defect**, because
both repairs available inside the rubric were measured and neither works.

`python3 eval/judge/tier2_census.py --runs-root <main checkout>/eval/runs` is the producer — the
analogue of `tier1_census.py`, 17 expectations including a positive control, a variant and three
mutants. Its output **re-read 2026-08-27**, over 69 stored trials — **68 games and 1 scene**; the
decision was taken on the 68-trial corpus of 2026-08-23, before the scene added an eleventh group
of one, and no verdict moved. **Re-run it rather than trusting the date**: these are live counts,
and the date says when they were last read, not that they are still right.

**A `(run, game)` group is single-class by construction**, so the 11 groups are 10 game groups and
1 scene group, nothing is compared across the boundary, and every count below can be read back to
its class:

- **5 of 11 (run, game) groups return a single tier-2 value** across every trial tier 2 could
  measure:
  `wg-audio` g1/g2, `wg-audio48` g1/g2, `wg-g4c` g4 — **all 5 are game groups, 35 of the 68
  games**.
- 12 trials failed anything; **2** were whole-trial (the #49 build failure, one fact recorded N
  times) and **10** were selective. **9 of the 10 are from `wg-matrix-2026-08-13`**; the 10th is
  the scene's `layers.depth_ordered`, the false negative `tasks/162` repaired, which the census
  still counts because it reads stored records (`eval/RUNS.md` holds the re-grade). Tier 2 has not
  separated two submissions in any run since `wg-matrix`.
- **Promoting a withheld diagnostic cannot help.** `layer.clears`, `score.rewards_clears` and
  `stage.completes` take a single value — `False` — on all 7 group-criterion pairs where they are
  recorded, so scoring one lowers every submission in its group by the same amount and leaves the
  ordering as flat as it was.
- **Nor can more criteria of the same kind.** Four candidates, each drawn from a requirement the
  g4 prompt states and no criterion checks, were driven against all 8 `wg-g4c` submissions:
  attack cannot be re-triggered mid-swing, enemies patrol, the `land` event fires, and replay
  determinism under a played 900-tick tape instead of the idle 300. **8/8 pass on every one**, and
  the reference passes them too, so they can go green and nothing goes red (#128).

> A binary criterion asks whether a mechanic exists. When every submission implements every
> mechanic, a tier made of them returns one number — and it is right to.

**So on a saturated group `overall` certifies completion; it does not rank.** No stack ordering may
be drawn from one at any gap, which is the same bar the within-cell result already sets below —
this is a second, independent reason for it, arrived at from the tier rather than from cell
agreement. Trials in a saturated group are still reported, still gated, and still judged.

**What it costs, named.** 35 of the 68 stored game trials — including all 16 of `wg-audio48` and
all 8 of `wg-g4c`; the 1 scene is not among them — bought a certificate rather than a ranking, at trial prices in `eval/RUNS.md`. The
fourth game is the sharpest instance: `g4_platformer` was added because *"Pong, Tetris and arena
all tied; a game exercising different systems is the most plausible remaining route to
discrimination"* (below), and **20 of its 20 scored criteria have never failed**. The route was
plausible and it is now measured closed.

**What re-opens this**, in the tool rather than in prose: `tier2_census.py` prints `SEPARATES` the
day no group is flat. The remedy it points at is a **harder task**, not a longer rubric, and that
is a separate decision with its own spend — filed, not taken here.

### The tier-3 separation figure is reported under `rank` + `pool` — decided 2026-08-23

*"Does an aspect separate the stacks?"* is answered by a between-stack range against a
within-stack gap. **That quantity has two free parameters, not none.** `value` is what a round
asserts about a submission — its `score`, or its `rank` in the field. `order` is whether the
rounds are averaged before the spread is taken (`pool`) or after (`perround`). Four
combinations, four different numbers, and they disagree about the sign.

`eval/judge/field_ranks.py` is the producer. **Every published figure for this quantity must
come out of it and must be quoted with the field, the `value` and the `order`** — a pair quoted
without its method names one of four quantities, which is how a pair matching none of them came
to be published in four documents at once (#113).

**There is a third parameter and it is the POPULATION.** A directory of rounds is not one
population, and **2** different properties put a round outside it. Decided 2026-08-23 (task
90) and extended 2026-08-24 (`tasks/146`): both properties **declare themselves to code** in
`eval/judge/aspects.py`, a pooled figure covers what is left, and `field_ranks` names the
aspects each figure is over — and every aspect it excluded, with the reason — in its own output.
The guard is `field_ranks.assert_poolable`, which raises rather than silently dropping, and an
aspect id `aspects.py` does not define is treated as **unmeasurable rather than scored**.

| property | field | why it is out | instance |
|---|---|---|---|
| it is a **control** | `Aspect.control_for` | a control's scores mean something only against the aspect it controls, so pooling it is rule 4 | `fun_frames` |
| it is **cross-stack barred** | `Aspect.cross_stack_bar` | the judge is told which stack it is looking at, so a *between-stack* reading of it is meaningless — and a pooled figure is exactly a between-stack range | `idiomatic` (#53), `framework_fluency` |

**The bar was in prose from #53 and in code from task 135, and the pooled figure ignored both
until `tasks/146`.** A live document stating an aspect may not be ranked across stacks, beside a
number that ranked it across stacks, is a disagreement no consistency check can see — the two
statements are about different things. Excluding it **strengthened every published claim and
retired no conclusion** — the two superseded pooled pairs themselves are retired, as
`WR-tier3-pool-pre` and `WR-tier3-pool-post`. Across the 9 stored directories that produced a
pooled figure, 3 held nothing but barred rounds and now report `UNMEASURABLE` instead of a full
separation table — **1** of them carried the widest between-over-within reading the tool had
ever returned anywhere in the stored tree, and it was a pure barred reading. On
`wg-tetris-judge-2026-08-17` **3 of the 8 readings flip**, every one of them from
*between exceeds within* to *no separation*. `eval/RUNS.md`'s comparability note for
2026-08-24 holds the before-and-after figures; they are stated there and nowhere else.

**When one pair is quoted, it is `rank` + `pool`.** Three grounds:

1. The tier's output is an **ordering** — each specialist ranks a whole eight-submission field.
   Ranks are the units the layer asserts; the scores are an intermediate.
2. The scores **ceiling**. On seed 1, `architecture` puts 7 of 8 submissions on one score and
   `audio` and `idiomatic` put 6 of 8 (`JUDGING.md`, gate 1). A between/within comparison on a
   saturated scale is compressed by the saturation; a rank comparison is not.
3. `pool` is the population the documents already meant. The withdrawn line's own words were
   *"pooled over five aspects and both orders"*, and `README.md`'s replacement is pooled.

`JUDGING.md`'s two per-aspect tables stay under `score` + `perround`, which is the only method
that reproduces them, and are now labelled with it. **Mixing methods in one section is
acceptable; mixing them unlabelled is not** — and note that a `pool` figure is *not* the mean of
any per-aspect table, so the two must never be presented as summarising one another.

### A harder task is PRICED here, and gated behind a free pre-test — decided 2026-08-23

Tier 2 is the only scored tier and it saturates, so the remedy proposed has been a harder task.
**A harder task costs a matrix, so this entry brings the price and the one measurement that
decides whether the money would buy anything. The spend itself is the operator's call and is not
taken here.**

**First, the corpus is flatter than the group count says.** Tier 2 has produced **no selective
failure anywhere in the 69-trial corpus that survives adjudication.** `wg-matrix-2026-08-13` is
the only run where tier 2 ever separated submissions, and its 9 selective-failure trials carry
**38 criterion-failures**: 22 are a probe that died before tick 0 (both Unity arena trials,
detected by signature), and the other **16 are every entry in `ADJUDICATED` in
`eval/judge/audit_criteria.py`, all 16 marked `false_negative`** — the criterion fired on correct
work. The **7 distinct criteria** involved (`ball.wall_bounce`, `move.translates`,
`piece.stacks`, `gameover.triggers`, `determinism.replay`, `determinism.seed`, `enemies.chase`)
are each marked `REPAIRED` in `CONSTRUCTIBLE_FAILURE` in the same file, for that reason.

**The census reports 10 selective-failure trials, not 9, and the 10th does not weaken this.** It
is the scene's `layers.depth_ordered` — a false negative `tasks/162` repaired, adjudicated the
same way and by the same standard, and still stored as a FAIL because nothing under `eval/runs/`
was rewritten.
`python3 eval/judge/discrimination.py eval/runs/wg-matrix-2026-08-13T14-02-50` prints an
**ADJUDICATED spread of 0.0000 in all three games**, against a raw 0.2308 / 0.3077 / 0.7333.

The same thing is visible without adjudication, on one field, across one day: `wg-g4c-capgate`
re-grades the eight `wg-g4c` work trees, and `g4_platformer__ts__t0` scores **14 of 20 on
2026-08-22 and 20 of 20 on 2026-08-23** — the same submission, the same 20 criteria, the
play-bot repaired in between. **Observed tier-2 spread has tracked the play-bot's false-negative
rate, not the submissions.**

**Second, the reason it saturates is structural, and it constrains what a harder task must be.**
Every tier-2 criterion is derived from a bullet the prompt states; agents build to the prompt; so
the tier returns one value by construction. **The prompt is tier 2's answer key.** Four more
criteria of that family were measured against the `wg-g4c` trees and passed 8/8 (task 65). It is
not a shortage of criteria.

**Third — and this is what decides the design — the criteria are not short of resolution.** Over
the eight `wg-g4c` submissions, **16 of the 20 scored criteria already record more than one
distinct numeric evidence vector, and 8 of them record eight distinct vectors on eight
submissions.** The underlying measurements discriminate perfectly. What they discriminate on is
the problem:

| criterion | what its numbers vary over, across the 8 submissions |
|---|---|
| `attack.faces` | hitbox offset, 22.0 to 32.0 px |
| `jump.leaves_ground` | rise in 8 ticks, 44.6 to 66.8 |
| `invuln.window` | i-frame gap, 43 to 80 ticks |
| `enemy.damages_player` | starting health, 4 or 5 |
| `player.falls` | first platform edge, x=300.0 to x=560.0 |
| `player.walks` | walk distance in the window, 143.2 to 182.5 |

Every one is a **free design parameter the prompt does not give a direction for.** Scoring any of
them ranks the four stacks on jump height and hitbox width.

> **A criterion has headroom only if the quantity it observes lies on an axis the prompt names a
> DIRECTION for.** A stated mechanic gives an axis with no direction and every submission at the
> same point; a free parameter gives an axis with no direction and every submission at a
> different point. Neither is a quality scale. Adding resolution to a criterion on an
> undirected axis manufactures a ranking out of design freedom.

**The one criterion with headroom is `stage.completes`, made graded rather than binary** — the
fraction of the stage the bot reaches. Three tier-2 criteria sit at the **floor** rather than the
ceiling, and all three are `diagnostic_only` for the same reason, that the bot cannot play well
enough: `layer.clears` and `score.rewards_clears` (tetris, `False` on all 19 trials where
recorded) and `stage.completes` (platformer, `False` on all 8). **`stage.completes` is the only
one of the three whose underlying quantity is a fraction on a directed axis.** A line was either
cleared or not; there is no meaningful "how far towards a line". The stage has a length, the goal
is at the end of it, and the prompt states the direction — *"Reaching the far end of the stage
clears it."*

**The free pre-test has run — task 83, 2026-08-23, published as #139 — and it answers both
questions: do not buy the harder task, and do not promote the criterion.** It cost no trials: the
eight `wg-g4c` work trees survive under `~/game-research-work/` and were re-driven offline.

The bot was first repaired until it could actually pursue the goal — cross the pits with a **held**
jump, stop at swinging range and kill what stands in the way — in four steps, each measured on all
eight. `stage.completes` remains `False` on all eight; these are the fractions of the goal reached:

| | `godot t0` | `godot t1` | `rust t0` | `rust t1` | `ts t0` | `ts t1` | `unity t0` | `unity t1` |
|---|---|---|---|---|---|---|---|---|
| bot as shipped | 0.225 | 0.143 | 0.206 | 0.290 | 0.256 | 0.178 | 0.158 | 0.203 |
| **bot repaired** | **0.803** | **0.591** | **0.417** | **0.609** | **0.686** | **0.274** | **0.617** | **0.401** |

**Not all eight at 1.000 — none of them reaches it — so the goal is not too easy, and a harder
task is not justified on this evidence.** The numbers are spread, and the spread is nonetheless
**not** the discrimination the old first row promised, for two measured reasons:

- **The ordering is not stable under a change to the instrument.** Spearman ρ between the shipped
  bot's ranking of the eight and the repaired bot's is **0.405**, exact permutation p = 0.163 over
  all 8! orderings — at n=8 the old ranking carries no demonstrable information about the new one.
  `godot t0` moves 6th → 8th, `unity t0` 2nd → 6th, `godot t1` 1st → 4th.
- **8 of 8 runs end having taken exactly `hp0` hits, with no victory.** The run length is set by
  the health pool, so the scalar is `(health pool × distance travelled per hit taken) ÷ goal_x`.
  Health pool is 4 or 5, `goal_x` is 2300 to 3500, distance-per-hit is set jointly by enemy spacing
  and by how badly the bot fights. **Two free design parameters over a third** — the fraction is on
  a directed axis, but the quantity that terminates the run is not.

> **The three-way pre-test was missing a cell, and it is the cell the measurement landed in: a
> spread that moves when the instrument does.** *Spread ⇒ the tier can discriminate* is sound only
> if the spread is a property of the subjects. Ask of any new scalar not merely whether it
> separates, but whether **improving the instrument reorders it**. That check is free, it runs
> offline, and here it came out against the hypothesis it was built to support.

Two things the repair does establish, and both are worth keeping:

- **The levels were never the constraint** (#139). Every gap in all eight is crossable by the submission's
  own physics: measured jump reach with the control **held** is 93.5 to 141.8 units against a
  widest gap of 110, while a one-tick press reaches 29.0 to 88.4. A variable-height jump is
  answered by how long the control is held, and the bot had been asking every submission for its
  shortest possible arc.
- **`ref_platformer` could not have caught that.** `stage.completes` passes on the reference under
  the broken bot *and* the repaired one, because the reference is a level the shipped bot clears by
  construction. `eval/G4-PLATFORMER.md` predicted this in writing — "it says nothing about whether
  it traverses eight unknown level layouts" — and the numbers now confirm it. A control that shares
  the assumption it is controlling for (#37).

**To re-open promotion:** the three awkward reference levels the rubric already demands, **and** a
bot that does not terminate on health exhaustion in 8 of 8. Until then the criterion measures how
long the instrument survives, not how much stage there is.

**What the alternative would consume, read from `eval/RUNS.md` on 2026-08-23.** The judge side
is **0** — tier 2 is deterministic and tier 3 carries no weight — so this is agent trials only.
The figures are token valuations, not money (#159); what a fresh matrix really commits is days of
wall clock and a share of rate-limit capacity:

| | |
|---|---|
| one clean 8-cell field, standing regime (no cap, `--max-turns 1000`, `--parallel 2`) | **`wg-g4c` — $421.00**, 8/8 `completed`, per trial $36.16 to $77.60, wall 55.7 to 86.3 min |
| the last game actually added, all in | **$698.21** — `wg-g4` $211.64 (stopped at 4 of 8) + `wg-g4b` $65.57 (8/8 `api_error`, a null) + `wg-g4c` $421.00. **Two of the three runs produced nothing gradeable** |
| raising the bar on an existing game instead | the same order. The arena rewrite's field, `wg-arena3d`, was $374.05 for 8 `completed` — but that run straddled the #49 machine repair, so its *cost* is contaminated as well as its grades and it is not a clean price |

**So a fifth game, or a raised bar, is one matrix if the first field lands clean and three at the
only precedent we have, n=1.** Engineering effort — prompt, play-bot, mutants and variants — is on
top and is unmeasured; nothing in this project counts it.

**The ordering was the decision, and it was the right way round.** The pre-test ran first because
a matrix committed before it would have been committed on the assumption that a graded criterion
discriminates — and that is precisely the assumption the pre-test refuted, in one afternoon and
with no trials at all, against an alternative of one to three matrices.

## Task set and judging protocol

| Decision | By |
|---|---|
| Add a **fourth game: a 2D sprite platformer with attacks** (Castlevania-style) | [user] |
| `stage.completes` is **diagnostic, not scored**, until it passes three awkward reference levels | [agent] |
| Subjective judges **run repeatedly until the decision resolves**, not a fixed number of times | [user] |
| The judging layer **stays in Python** — no Workflow port for now | [user] |

The platformer stresses machinery the other three games do not: sprite sheets and animation state
machines, attack hitboxes with active frames, knockback and invulnerability windows, platform
collision. Pong, Tetris and arena all tied; a game exercising different systems was the most
plausible remaining route to discrimination. **It has now been run once and it tied too** — all 8
`wg-g4c` submissions score 1.000, and 20 of its 20 scored criteria have never failed (#128). The
hypothesis was worth testing and is answered: different systems do not separate these stacks.

Repeated judging resolves per **pair** with a Wilson interval, not per score, and stops sampling a
pair once it resolves. Protocol and its limits are in `eval/judge/JUDGING.md` — including that at
affordable N the instrument can detect an ordering but **cannot statistically prove a tie**, which
is the outcome this project is most likely to reach.

## What the deterministic tiers may and may not be used for — decided 2026-08-16

**Decided [agent], on measurement, and it constrains every claim this project can make.**

Comparing the two independent trials in each cell criterion by criterion, over the tiers that
gate or score and **per (run, game), never pooled** — `python3 eval/judge/paired_verdicts.py
--runs-root <main checkout>/eval/runs`, completed cells only:

| run | game | paired | verdict differences | evidence differences |
|---|---|---|---|---|
| `wg-matrix` | pong | 88 | **2** (2.27%) | 58 |
| `wg-matrix` | tetris | 96 | **1** (1.04%) | 56 |
| `wg-matrix` | arena | 96 | **1** (1.04%) | 62 |
| `wg-audio48` | pong | 112 | **0** | 55 |
| `wg-audio48` | tetris | 120 | **0** | 65 |
| `wg-arena3d` | arena | 148 | **0** | 99 |
| `wg-audio` | pong | 84 | **0** | 41 |
| `wg-audio` | tetris | 30 | **0** | 18 |
| `wg-g4c` | platformer | 140 | **4** (2.86%) | 93 |

The two submissions in a cell are different artifacts and the instrument mostly returns the same
grade on both — "mostly", not "never". **The within-cell noise floor is a range across nine
groups, 0.00% to 2.86%, not one number**; `wg-g4c-capgate`'s two arms are excluded from all of it
because they carry no trial JSONs and return diff lists byte-identical to each other, which is
what copies do, not what two independent trials do.

> ⚠️ This table replaces **`wg-matrix` 436 paired / 5 verdict differences** and **`wg-audio48`
> 232 / 0** as the figures this section rested on. Both reproduce exactly (they are pinned in
> `paired_verdicts.py --selftest --runs-root ...`) and **neither may support a claim about the
> deterministic tiers**: 156 of `wg-matrix`'s 436 — **35.8%** — are LLM-judge criteria at weight
> 0.00, while `wg-audio48`'s 232 contains **none**, because that run was never judged. The two
> were quoted side by side as one measurement and span different tier sets. Deterministic-only,
> the same runs read **280 paired / 4** and **232 / 0**. Separately, `5 of 436` is a rate pooled
> over three games with different criterion counts, which `eval/RUNS.md` bans.

| may be used for | may not be used for |
|---|---|
| establishing that a submission works — it caught a game that does not compile and two whose own gate is red | ranking stacks, at any gap |
| catching a criterion that cannot fail (mutants) or one that fails correct work (variants) | claiming two stacks are equal — a null on an instrument with no within-cell resolution is not evidence of equality |

**A stack-correlated pattern remains an instrument defect until a mechanism is named in the
code. That is now five for five** (#25, #26, #28, #43, #49), and the fifth is the entire
spread of the arena matrix.

Consequences already applied:

- `wg-arena3d`'s numbers are **not comparable across stacks** — the run straddles a machine
  repair whose split is exactly the stack split. `eval/RUNS.md` carries the detail.
- The agent's closing message must be read before grading, and since 2026-08-23 the harness
  reads it: `wholegame.py report` prints each trial's located passages beside its score, via
  `eval/tools/disclosure.py`. It reads `artifacts/<trial>/agent_result.json` → `.result`
  **whole**, never `agent.final_text`, which is that message's last 3000 characters — and
  `wg-arena3d`'s own disclosure of this mechanism sits at character 0 of 3912, where the
  truncated field cannot see it. It is a locator, not a classifier; `quiet` is not a verdict
  and `no message` is a third value, not silence.
- The work root is no longer under `$TMPDIR`, which reaped the artifact under measurement
  (#45), and `assert_work_root_sane()` refuses any ephemeral path.

## Where instructions live

Instructions to agents are **written in files, not delivered in messages**, so they can be improved
across sessions rather than re-invented each time. See `AGENTS.md`.

| Instruction | File |
|---|---|
| Launching, watching and stopping a run | `eval/PROTOCOL.md` |
| The subjective layer and its gates | `eval/judge/JUDGING.md` |
| Criteria, tiers and weights | `eval/judge/RUBRIC.md` |
| Every run's cost and comparability | `eval/RUNS.md` |

### One real copy of each skill, at `.agents/skills/`, reached by symlink — decided 2026-08-23

`.agents/skills/<name>/SKILL.md` holds the **only real copy** of each skill. `.claude/skills` is
a **symlink** to that directory. `docstat.py --sweep` exits 1 on any real `SKILL.md` outside the
authoritative root, and also on a `.claude/skills` that is missing, dangling, or a real directory.

`.agents/` is the cross-tool convention — the same one that makes a root `AGENTS.md` readable by
several agent CLIs — so Codex, Claude and anything else read one source rather than a copy each.
**No `.codex/skills` or `.Codex/skills` exists as a real folder**; a second path to the skills is
a symlink or it is nothing.

**This is not a reversal of #99, it is that finding's own escape clause.** #99's objection was
never to a location. It was to a **copy**, and its three measurements still stand: the only
Codex-adjacent sibling — `game-research-gpt` — has no `.agents/`, no `SKILL.md` and no root
`AGENTS.md`, so it was never a reader; the mirror was **never once in sync**, with `add-game` 39
lines short in the initial commit and `tasks` and `prune` absent entirely; and after the initial
import it took **0 edits that changed a procedure, against the authoritative tree's 6**. The
finding closed by saying *add a pointer, never a copy*. This inverts which end holds the pointer
and leaves the count of copies at exactly one. A symlink has no second file to get edited.

**Which end holds the real files was decided by measurement, not by preference.** Against
`claude` 2.1.220, one uniquely-named probe skill per layout, every tool but `Skill` denied so the
content could not arrive by reading the file:

| layout | skill loads? |
|---|---|
| real `.claude/skills/<n>/SKILL.md` (the old layout, positive control) | yes |
| real `.agents/skills/`, `.claude/skills` a symlink to it — **shipped** | yes |
| real `.agents/skills/`, `.claude/skills/<n>` each a symlink | yes |
| real `.agents/skills/` only, no `.claude/skills` (negative control) | **no** |
| real `.claude/skills/`, `.agents/skills` a symlink to it | yes |

The whole-directory symlink was chosen over the per-entry one because it needs no upkeep: a new
skill is one new directory, where the per-entry layout would need a matching symlink added by
hand every time, and a rule you have to remember is a rule that will fail.

**The negative control is why the gate checks the pointer.** Claude Code does not discover
`.agents/skills` on its own. With the symlink deleted the nine skills are still present, still at
the authoritative address, and every file-counting check reads clean — while no agent can load
one. `eval/tools/skill_layout_control.py` pins the gate red on all five ways this breaks: a real
copy elsewhere, a copy at the wrong nesting depth inside the authoritative root, the pointer
deleted, the pointer dangling, and the pointer replaced by a real directory of copies.

**The mirror came back by a git merge, not by outside tooling.** After the 2026-08-23 deletion,
`.agents/skills` reappeared, tracked, as nine pure additions in the commit merging task 101 —
a branch forked before the deletion, so the merge restored what it had never seen removed. It is
worth knowing because the diagnosis on sight was "some tool outside the repository regenerates
this", which would have been unfixable from inside the repo; the true cause is ordinary and the
layout is now merge-safe, because a branch carrying a real `.claude/skills/` directory conflicts
with the symlink rather than silently shadowing it.
### The documentation is gated on structure and on names, never on prose — decided 2026-08-23

Eleven documentation linters were measured against this repository and produced **over 14,000
alerts and two defects**. Both defects came from tools that check *structure or schema*; every
prose rule that fired was house style, a false positive on this project's vocabulary, or a
readability score. `research/11-doc-linting-for-agents.md` has the per-tool numbers.

So no prose linter, no readability gate, no `markdownlint` config. `eval/tools/docstat.py
--sweep` is the whole gate, and it asks only two things:

| | question | bought with |
|---|---|---|
| **references** | does a flag, aspect or criterion a doc names exist? | `RUBRIC.md` named five judges that do not (#38) |
| **census** | does a doc claiming to name every aspect name every aspect? | `RUBRIC.md` and the `evaluate-run` skill said five while `ASPECTS` held six and `--aspects fun_frames` was accepted (task 79) |
| **structure** | does the file parse as the thing it is read as? | 5 of 7 skills had unparseable frontmatter; `AGENTS.md` rules 10-16 detached from their own list |

**References and census are the two directions of one question, and the second is the one that
hides.** A doc naming a judge that does not exist is caught the moment anyone looks for the
name. A doc *denying* a judge that does exist resolves perfectly, reads as authoritative, and
costs the reader the control they never ran — `--sweep` printed `6 aspects known` and exit 0
for as long as two documents said five. A census claim is only visible because somebody
**declared** it exhaustive, which is the same mechanism the withdrawal register rests on.

**The census trigger is scoped to the PREDICATE, not to the quantifier, and that is a measured
choice rather than a stylistic one (task 92, #140).** It shipped as three alternations — the three
wordings the two defective documents happened to use — and of 14 planted census claims, each
false in exactly the way the check exists to catch, it fired on **2**. These two passed:

```
The five judge aspects are `architecture`, `audio`, `fun`, `idiomatic` and `ux`.
There are five aspects: `architecture`, `audio`, `fun`, `idiomatic`, `ux`.
```

The obvious repair fails harder: a trigger built on the quantifier, a cardinal or `all`
governing `aspects`, caught 10 of the 14 and turned **26 correct live lines red, with no true
positive among them** — in this corpus a counted plural `aspects` almost always describes what
*ran*, *cost* or *failed*, as in DECISIONS.md's own `All five aspects were run over a full
eight-submission field`. What a census has and a run description does not is an existence,
identity or definition predicate in the present tense with the enumeration adjacent, and
copula / existential / `define` are closed classes, which is what makes that statable as a
property instead of a growing wordlist. **Measured after the change: 14 of 15 plants red, 0 red
across the 152-document swept corpus, and 6 across all 2090 markdown files in the checkout —
all 6 archive-exempt and all 6 true statements of a superseded census.**

> **The fence above is load-bearing, and the widened trigger's first live firing proved it.**
> This paragraph quotes two false censuses as examples, `--sweep` went red on it, and that is
> the check working: a live document may not state a census it does not mean, and the declared
> way to show one is inside a ``` fence, where a line is an example rather than a claim. The
> same exemption is why the archive may quote the superseded five freely.

**What it deliberately still misses, with the price of closing it.** A bare `aspect`-headed
table listing five ids with no sentence above it is invisible. The structural trigger for that
was written and measured at **9 false positives** on live docs — every one a legitimate
per-aspect results table over the subset a particular round ran. Nine false positives to close
a gap that has never occurred is the trade this file already refused when the path check was
deleted rather than tuned quiet.

**The flag census reads every skill, and the widening was decided by a cost that moved
(task 149).** The backticked-flag half is gated file-wide on 4 harness script names, which
admitted 4 of the 10 `SKILL.md` files — leaving the documents where commands and flags are most
densely written mostly unchecked. It now reads all 10 `SKILL.md` files, at a cost of 0 correct
lines. *reads* is how many of the 29 backticked mentions of a real flag of ours a trigger would
look at; *rows* is how many correct lines it turns red:

| trigger | reads | rows |
|---|---|---|
| the retired 4 harness names, file-wide | 10/29 | 0 |
| one of our scripts named on the same line | 2/29 | 0 |
| one of our scripts in the same section | 26/29 | 0 |
| SHIPPED: every skill | 29/29 | 0 |

**Every row cost something when this was measured six hours earlier, and admitting all 10 cost
8** — `gh`, `git` and `just` flags argued about in prose, which is the shape this file refuses
above. The exclusion was written, and then all 9 of those tokens entered `FOREIGN_FLAGS_EXACT`
on `main` (`6bfc80b`) for an unrelated reason: ticket prose was reddening the sweep with the
same flags. **An exclusion argued from a cost of 8 does not survive the cost becoming 0**, and
the asymmetry decides it — the exemptions are the fail-open half and were paid for regardless,
while widening the trigger is the fail-closed half. Declining the coverage would have paid the
price and taken nothing for it.

`python3 eval/tools/docstat.py --selftest` is the producer, and pins compare this table against
the live census in both directions: that a phantom flag in a skill naming no harness is caught,
and that no candidate costs a row. **The second is the one to watch.** A skill that starts
discussing a new tool's flag turns the sweep red on correct input, which is how a gate gets
disabled; the repair is `FOREIGN_FLAGS_EXACT`, not narrowing the trigger back.

What is still excluded is ordinary documents naming none of the 4 harness scripts. Widening
that to the closed class `_our_script_names()` still loses at 13 candidate rows over the
reference corpus, 11 of them in `tasks/`. `.agents/skills/audit-docs/SKILL.md` states both
halves for an auditor; this entry is the authority for the measurement.

Two boundaries hold the structure half at 0 false positives, and both are the same rule — *a
gate that fails on correct input gets disabled*:

- It asks about a continuation under a **2+ digit** ordered marker, not about indented blocks in
  general. The general form fires on `tasks/` files where nothing is wrong.
- The **formatting** rules do not read `eval/findings/`, `eval/FINDINGS.md` or `eval/RUNS.md`.
  The archive records what was true when it was written, including the broken shapes it is
  about; reformatting one to satisfy a gate edits evidence.

  This exempts the archive from **house style, not from being findable.** Five checks do read
  it, and each asks whether a citation still resolves rather than whether the prose is tidy:
  a finding number is defined once; every number has exactly one row in the `eval/FINDINGS.md`
  index and vice versa; that index renders as **one table**; every live statement of the
  range — `AGENTS.md`, `README.md` and the index's own opening line — names the same highest
  number; and every live statement of **how many there are** matches how many there are.

  Three of those are ones the others could not see. A blank line between two rows ends the
  table under CommonMark, so the rows below become a second, headerless table that no renderer
  shows as part of the index — while the row count, the set reconciliation and `grep` are all
  unchanged. The range was spelled in three files with only one of them checked, so the
  index was repaired while `AGENTS.md` went on saying `#19-#110`. And **a range is not a
  count**: `#19-#132` is equally true of 114 findings and of 40, which is how `README.md`
  carried a count of *thirty-seven* for eleven days past a green range gate (#134,
  `WR-readme-findings-count`). Each was green on a real defect, so each now carries a red
  control: **`--sweep` runs the pins itself** on every invocation, `docstat.py --selftest`
  prints them, and `eval/tools/findings_control.py` runs the command out of process against a
  tree whose answer is written down first.

### A stranded edit tail is caught as a REPETITION, over live and archive — decided 2026-08-23

An edit that rewrites a sentence **wrapped across several lines** and replaces only the lines it
touches leaves the last line of the old sentence stranded below the new one. One instance is
known: line 6 of `eval/FINDINGS.md`, the file every session is told to read first. It is not a
wrong claim and not a stale number, so neither the withdrawal register nor any consistency check
applies — a half-sentence disagrees with nothing.

**`tasks/99` specified the trigger as *"a strict suffix of the sentence ending on the line
above"*, and measured against the real blob that trigger does not fire.** At `1f6fb65` the
stranded line reads `number has been retracted before trusting it.**`, while the sentence ending
on the line above it ends `...enforces it over the live documents.` The fragment is a suffix of
the sentence that was **deleted**, whose head still sits three lines up — not of anything ending
above it. Writing the ticket's trigger would have shipped a gate that is green on the only
instance of the defect anyone has seen. **The ticket was the bug, and the reason it was caught is
that the red pin was required to come from a blob rather than a reconstruction:** a defect retyped
from memory would have been retyped into the shape the trigger already assumed.

The property shipped instead: an unfenced, non-structural prose line of **≥5 words whose
normalised text already appears verbatim in the paragraph above it**. The orphan is a
*repetition* — that is what half a replaced sentence is — and repetition is a closed property of
the text rather than a vocabulary, which is what the census-trigger section above asks for.
**0 false positives over the whole reference corpus, live and archive** — 188 documents when
last re-derived by `python3 eval/tools/docstat.py --sweep`, which runs it on every invocation.
The tighter variant additionally requiring the line to end its paragraph also measures 0, so the
looser one ships — same measured cost, strictly more coverage. This is the first open-shaped
trigger tried here that opens at 0 rather than at 8, 18 or 26 (#140, #142, #146).

**Scope includes the archive, deliberately against the rule two sections up.** The formatting
gates exempt `eval/findings/` because reformatting an archived entry edits evidence. A
half-sentence left by a botched edit is not evidence of anything — it is damage — and the one
instance was *in* the archive. A findings entry quoting such a defect would sit in a fence, which
is masked.

The pins are in `_orphan_tail_pins`, run by `--sweep` on every invocation and printed by
`--selftest`: red on the real blob, green on the same file at HEAD, and four green variants that
are ordinary markdown repetition — a duplicate line inside a fence, a table restating a term in
consecutive rows, a sentence repeated in two *different* paragraphs, and two list items sharing a
stem. The corpus traversal is controlled separately from the function: an orphan planted in
`README.md` and in `eval/findings/documentation.md` takes `--sweep` to exit 1 naming both.

### A half-applied rewrite is caught as a 12-word window repeated inside ONE claim — decided 2026-08-23

The section above catches a stranded *line*. It does not catch the second shape of the same
damage, and the gap was measured rather than assumed: a rewrite applied to **half of one bullet**
leaves the old text and the new text side by side inside a single claim, joined at neither a line
boundary nor a sentence boundary. `DECISIONS.md` at `75dde71` carried `40 of 56 matrix trials at
the ceiling with *zero* variance, not merely near it (#92)` twice, eight lines apart in one
bullet, once continuing `. **What to do about it...` and once ` — and became a gate...`. Task 116
removed it by hand.

**Every gate in the repository was green on the tree that carried it** — `--sweep`, `--findings`,
`--withdrawn`, `--renumbered`, `linkcheck.py`, `tasks.py check` and `withdrawn_control.py` all
exit 0 before and after the repair — **and so does the stranded-tail check written for the sibling
defect**, re-measured at HEAD: 0 hits on the pre-fix blob. The reason is structural. The
duplicated span starts mid-sentence and ends mid-sentence, so no line of it and no sentence of it
recurs whole; an exact-match rule over repeated sentences scores 0 on the defect *and* 0 on the
live corpus. That was the obvious property and it is a complete false negative.

The property shipped instead: **any 12-word window occurring twice inside one paragraph, list
item or frontmatter key**, with fenced lines, GFM table rows and cross-key frontmatter repeats
excluded. Repetition is again a closed property of the text; the free parameter is the window,
and **it was chosen on the live false-positive count, not on which size sounds more general** —
the census-trigger section above, applied to a number instead of a regex.

The producer is **`python3 eval/tools/integrity_census.py --windows`**, and the figures below are
its output over the 188 reference documents the corpus held when it was last run:

| window | corpus hits | distinct phrases | windows on the real defect |
|---|---|---|---|
| 10 | 3 | 1 | 7 |
| 11 | 0 | 0 | 5 |
| **12** | **0** | **0** | **4** |
| 14 | 0 | 0 | 2 |
| 16 | 0 | 0 | 0 — the defect is invisible from here up |

**The hits at 10 are the shape this check will keep meeting, and they are why the window is not
smaller:** `DECISIONS.md`'s own headroom blockquote is an *antithesis* — "a stated mechanic gives
an axis with no direction and every submission at the same point; a free parameter gives an axis
with no direction and every submission at a different point" — where the repetition carries the
argument. Correct prose does this. 11 also measures 0 and 12 ships instead, because 11 sits
directly on that boundary and 12 keeps a word of margin at each end while still clearing the real
defect by three.

**Two columns, because the hit count answers the wrong question.** When the window was chosen the
corpus was 183 documents and 10 gave **1** hit; at 188 it gives **3**, and every one of the three
is that same antithesis — quoted twice in this file and once in `tasks/119`, both times *because*
it was named as the false positive that set the boundary. The corpus acquired no new kind of hit;
it acquired copies of the one already counted. **A trigger that fires on a passage which correct
documents QUOTE grows its own false-positive count by being documented**, and reading that growth
as evidence of an open class would argue for widening a window that has not moved. The count that
decides a retune is therefore the **distinct-phrase** column: 1 at window 10, and 0 from 11 up.

**Scope is live and archive**, for the section above's reason. **The frontmatter rule is one
block per KEY, not a mask over the header**: `_claim_blocks` sees no blank line in a YAML header
and returned the whole of `tasks/42` as one window, where `done_when` states a goal and
`established_by` reports it met — the queue working as designed, and the archive's only hit at 12.
Masking the header outright also measures 0; per-key ships because it is strictly more coverage
at the same measured cost, and `established_by` is routinely a paragraph on one line.

**Neither integrity check subsumes the other, and that is why both run.** Each was measured
against the other's real instance:

| | stranded tail | duplicate fragment |
|---|---|---|
| `1f6fb65:eval/FINDINGS.md:6` | 1 hit | **0** |
| `75dde71:DECISIONS.md:745` | **0** | 4 hits |

The orphan's repeated run is **6 words**, far below any window this side of the false-positive
floor — the corpus turns red at 10 and this defect would need 6. Merging the two into one
parameterised rule is the obvious next move and it would lose one instance or the other, so
`_duplicate_fragment_pins` asserts the top-right cell rather than leaving it as a sentence here.
If that cell ever moves it is not a defect; it means this section's reason for running two checks
has to be re-derived.

Pins in `_duplicate_fragment_pins`, run by `--sweep` and printed by `--selftest`; controls and
mutants in `eval/tools/fragment_control.py`. The red pin is the **real blob**, and its expectation
— line 745, four windows — is stated in the control rather than computed from the blob by the code
under test. The eight mutants each flip a row that names them; `one_block` is the one worth
quoting, because dropping the block scope takes the corpus from 0 hits to **676**.

### Both integrity gates are kept on a measured base rate, not on the census at HEAD — decided 2026-08-23

Each measures **0** over the corpus at HEAD, and a gate whose triggering case has not occurred is
indistinguishable, from inside, from a gate that cannot fire. The pins answer half of that: each
one fires on a real historical blob. What nothing could answer was *how often does this defect
actually happen*, because **the tree at any one commit holds only the defects nobody has repaired
yet** — both known instances were fixed, so both are invisible to any census of HEAD, and that is
precisely why the count is 0.

The population that can answer it is **every version of every reference document**, and
`python3 eval/tools/integrity_census.py` is the producer. Over 1,551 distinct (version, path)
pairs, spanning 219 paths and all 451 commits reachable from `--all` when it was last run:

| | incidents | versions carrying it | corpus at HEAD |
|---|---|---|---|
| stranded tail | 1 | 34 | 0 |
| duplicate fragment | 1 | 55 | 0 |

**The denominator moves with every commit and the incident count has not moved at all** — two
runs 20 minutes apart read 1,543 and 1,551 versions, the same 1 and 1. Re-derive it rather than
quoting this table; what it is evidence for is the rate, not the digits.

**A version is not an incident and a span is not either.** An unrepaired defect is re-counted in
every version of its file, and one rewrite is seen as several *overlapping* windows of itself —
the duplicate fragment reports 4 spans for what is one bullet edited once. Summing either figure
measures how busy the file was. Incidents are therefore grouped on the set of versions a span
appears in, which is what overlapping views of a single rewrite share; the tool prints the
ungrouped span count beside it, because that grouping is a heuristic and two separate defects
introduced and repaired together would collapse into one.

**The denominator is the whole of a base rate, and the first enumeration of it was quietly 22%
short.** `git log --all --name-only` is the obvious way to list every version of every document
and it **omits a merge commit's file list by default**, so `.agents/skills/update-readme/SKILL.md`
— tracked, and introduced by merge `6129034` — appeared in no revision at all: 216 paths and 1,196
versions against a true 218 and 1,543 on the same tree. It named no error while doing it. The
census now walks
every commit's **tree**, and `enumeration_control` asserts that every reference document tracked
at HEAD appears in the result, because HEAD's file list is the one membership that can be stated
in advance. **A census aimed at a population nobody checked returns a confident number** — rule 12
with the address being the population itself.

**So the decision is to keep both gates on a base rate of 1 incident each over the whole history
of the corpus, not to retire them for measuring 0 at HEAD.** That is a real rate over a real denominator rather
than an absence, and it is the number to re-derive before anyone proposes deleting either — the
same command, over the corpus as it stands then. The census exits 0 on a historical hit by
construction: everything it can find was repaired before it was written, so it is a census and
never a gate.

### The producer for the findings count is `docstat.py --findings` — decided 2026-08-23

`census.py` counts the stored tree and refuses in an agent worktree, where `eval/runs/` is
gitignored — which is exactly where documents get edited. The findings log is a corpus of
markdown, so its producer lives in the tool that already parses it.

**The gate and the producer are one function.** `_check_findings_integrity` returns
`findings_census(...)["disagreements"]` plus the two things a census does not express: the
index's *structure*, and which lines an over-indexed number sits on. The first draft had two
implementations of the same reconciliation, one gating and one producing;
`findings_control.py --mutate no_count_check` deleted one of them and all ten controls stayed
green. A duplicated mechanism buys half a gate and no way to tell which half was removed.

**A count in a live document must be written in digits.** A cardinal spelled in words is
reported as ungateable rather than ignored, because a digits-only check would let the next
stale figure past by being written out in full — which is what the one real instance did.

**A live document states the range once.** `_check_range_in` validates every occurrence it
finds, so N identical correct copies are N passes: an evil merge duplicated the row in
`AGENTS.md` and `README.md` on 2026-08-23 and `--sweep` was green on both, and the same merge
shape recurred while task 88 was in flight. The cost of the rule is that a document wanting to
state the range in two places must instead point at the one that does.

### The findings count is read from the log's ADDRESS, not from one wording — decided 2026-08-27

**Every live document's statement of how many findings there are is reconciled against
`python3 eval/tools/docstat.py --findings`.** The triggers are the phrase `N numbered findings`,
and any cardinal governing a plural noun on an unfenced line that names the log by one of its 3
addresses — the range sentence `Findings #A-#B`, the path `eval/FINDINGS.md`, or the producer
command. The **range** is still required in `RANGE_DOCS` alone, where not stating it is itself a
defect; the **count** is read across every live document, where saying nothing is normal.

**If a line names the findings log but carries a number that is not the findings count, the gate
goes red — put that line in a ``` fence, or reword it.** Inside a fence a line is an example
rather than a claim, which is the same exemption the aspect census declares above. 4 shapes need
no exemption because they are already green: a line number inside the log's own path, a singular
noun, a cardinal and a plural noun in different table cells, and a date.

**The trigger is scoped on the ADDRESS because the quantifier alone is unusable, and that was
measured.** *red* is how many correct lines a candidate turns red; **`python3
eval/tools/docstat.py --count-triggers` is the producer**, and it re-derives the whole column.
*pins wrong* is how many of the pin cases in `_findings_census_pins` a candidate gets wrong, with
the word-form trigger held constant so the digit trigger is the only variable; `python3
eval/tools/docstat.py --selftest` prints those pins and there were 19 of them on 2026-08-27, the
day this was decided. Both columns are over the **count corpus** — `_count_corpus()`, the live
corpus plus `RANGE_DOCS`, which adds only the archived `eval/FINDINGS.md` because `AGENTS.md`
and `README.md` are live already. `--findings` prints its size on every run, and it was 58
documents that day.

| candidate | red | pins wrong |
|---|---|---|
| the enumeration `N numbered findings` alone | 0 | 2 of 19 |
| the same list plus one noun, `N (numbered )?(findings\|entries)` | 6 | 1 of 19 |
| the QUANTIFIER: a cardinal governing `findings\|entries` up to 2 words away | 13 | 0 of 19 |
| **SHIPPED:** the enumeration, **or** a cardinal governing a plural noun on a line naming the log | **0** | **0 of 19** |

**Every red line in the rejected rows is a false positive** — untriaged `lint.py` findings, Bevy
migration entries, `eval/RUNS.md`'s undeclared scored entries, and this file's own worked example
of why a range is not a count. The quantifier misses nothing the shipped trigger catches and costs
13 correct lines to do it: the census-trigger section's result reproduced exactly, *the obvious
property is strictly worse than the list it was meant to fix*. 3 identifiers are a closed class in
the way a vocabulary of English verbs is not, which is what makes the conjunction free. Widening
the corpus from 3 documents to 58 also costs 0, so it is fail-closed at no price.

**The quantifier row cost 12 lines when this entry was drafted and 13 when it was finished**, and
the 13th is a sentence in `AGENTS.md` written to document this very decision. That is why the
producer exists rather than a number: an open-class trigger's cost grows with the corpus, so a
figure measured once describes a tree that no longer exists. Re-run `--count-triggers` before
quoting any row.

**The fence-or-reword rule fired twice on the author while this entry was being written**, on
sentences counting the triggers and the range documents beside the log's own address. Both were
reworded rather than fenced. That is the shipped trigger's whole cost, and it lands hardest on
the documents that explain it.

**What this deliberately still misses, with the price of closing it.** A count spelled in words is
read only in the `numbered findings` wording — scoping the word form on the address costs 2 false
positives on the count corpus, so `AGENTS.md`'s instruction to write counts in digits is the
mechanism instead. A count governing no plural noun is invisible, and no candidate reached it at
0 cost.

**What forced this.** `README.md` line 187 carried a count 28 short of the log with the producer
named in the same sentence, while a count of the same fact 128 lines lower — phrased `N numbered
findings` — was gated and correct. One wording read and one not, in one file. The citation is what
made it dangerous: a reader had every reason to treat the figure as derived.

`python3 eval/tools/findings_control.py` is the out-of-process control, over a tree whose answer
is written down before the tool sees it. Its `ENTRIES` and `WIDER CORPUS` rows each carry the
variant that must go back green, `REFUSES` covers a tree `git` cannot list, and `HOSTILE GIT_DIR`
carries its own red half. `--mutate no_scoped_count` and `--mutate count_corpus_is_range_docs`
restore the 2 halves of the old behaviour, and each is killed only by the rows that name it.

### A corpus figure in a live document is CURRENT or DATED, and which one is a choice — decided 2026-08-27

A count of the stored corpus can move when a trial lands. **Classify each figure as CURRENT or
DATED, one figure at a time.** Do not update every figure, and do not date every figure — the
sentence decides which it is.

| the sentence is | it must | why |
|---|---|---|
| present tense, or under a *what it reports today* heading, or introduced as a producer's output | **match the producer, re-run in the same session, and carry the date it was last read** | a reader who runs the command and gets a different number cannot tell a stale document from a broken tool. The date is provenance, not permission: a live count is still expected to match, and *"today"* means nothing in a document read later |
| the evidence a decision was taken on, or a measurement of a fix at the moment it landed | **name its date and its population, and not be updated** | overwriting it erases the population the decision rests on, and the decision then cites evidence nobody can reconstruct |

A decision entry may carry both: the *heading* dates the decision, and the evidence bullets under
it may be re-run and marked as current, provided the entry says the corpus has moved and whether
the verdict moved with it. *Tier 1 gates, it does not score* and *A saturated tier 2 is reported
as a completion certificate* are both in that shape.

**A census reads STORED gradings, so a criterion repair does not reach it.** `tier1_census.py`,
`tier2_census.py` and `ink_window_control.py` all report what the instrument DID, and nothing
under `eval/runs/` is rewritten when a criterion changes. 3 stored verdicts are currently against
rules that no longer exist — 2 `render.nonempty` ceiling firings (`tasks/168`) and the scene's
`layers.depth_ordered` (`tasks/162`). **A live document quoting one of them says so and points at
`eval/RUNS.md`**, which holds the re-grades beside the as-graded records. The alternative —
quoting the re-grade as though the producer printed it — makes the document and the tool disagree
with no way for a reader to tell which is wrong.

### A citation of a renumbered finding is reported, never gated — decided 2026-08-23

`docstat.py --renumbered` asks the one question the two above cannot: does a name still *mean* what
its author meant? A finding number reassigned at merge leaves every earlier citation pointing at a
stranger and **still resolving**, so no reference check can see it (#118).

It is a warning in `--sweep` and a command of its own, on the same footing as `tasks.py check`'s
reachability warning. Three reasons, and the first two are why it could not be a gate even if
someone wanted it to be:

- **Only about a third of what it reports is decidable.** The merge that renumbers writes the new
  heading and the closing task's evidence string in one commit, and a commit has no internal order.
  Where the citing author's tree was never committed at all — a collision live in two worktrees —
  history holds no answer of any kind.
- **Its evidence is `git blame`**, which dates the last edit of a line, not the writing of a
  citation. `-w` closes the reformat case. Any other content edit that leaves the stale number in
  place launders it, so the check fails closed: it loses recall, never accuses falsely.
- The undecidable list **contains correct citations by construction** and can never reach zero. A
  permanent block of output that cannot be cleared is how a reader learns to skip a command.

**Never renumber a finding to make it green.** The number in `eval/findings/` is the published one;
the citation is what is wrong. The renumber map is derived from git on every run and is not written
down anywhere — a hand-kept list of moved numbers would go stale exactly like the citations it
describes.

### The undecidable half's verdicts are recorded, because they cannot be derived — decided 2026-08-23

The list that can never reach zero has a second cost: it gives the reader no way to tell a row
somebody has already adjudicated from one nobody has ever looked at. Task 102 read all **51** rows
at that revision — **15 were wrong**, and the other **36** cost a full pass to establish and were
about to cost the next reader the same pass. `_check_renumbered_citations` already exhausts what
history can say about them; what decides a row is reading its sentence against the heading in
`eval/findings/`. So the verdict is **recorded**, in `eval/renumber_triage.json`, on the same
principle as the withdrawal register above: *the only detectable property of an adjudication is
that somebody wrote it down.* `--renumbered` prints `UNTRIAGED` first and the recorded verdicts
after, so what a reader must read is what is new.

**Keyed by the citing text, never by a line number.** A line number is invalidated by any edit
above it, which would unpair every entry in a document and present 36 adjudicated rows as
untouched — a wall of false work, indistinguishable from real work. The anchor must itself contain
the citation, so it cannot drift onto a neighbouring sentence.

**The register gates inside `--sweep`, and only on whether an entry still resolves** — its file
exists, its anchor matches exactly one line, and that anchor contains the citation it claims. The
*verdict* is a judgement and is never re-checked. `eval/tools/triage_control.py` runs 14 controls,
each red demonstrated before the green was believed, plus the two variants that decide the design:
a citation whose line number moved by 40 lines still pairs, and so does one sitting past column
96 — the excerpt `--renumbered` prints is truncated there, and matching against it instead of
against the line put 4 adjudicated rows in the untriaged list on the first run.

### A withdrawal is declared in a register, and the live/archive split is a decision — decided 2026-08-23

A retired figure cannot be found by comparing documents. Its restatements **agree**, with each
other and with the original, to the digit — a cross-document figure-agreement check over the six
live documents found 52 labelled figures, 1 disagreement, and that one a false positive, and it
could not see the withdrawn tier-3 pair it was built to catch (#113). Propagation and consistency
are the same observation. So a withdrawal is **declared**: `eval/withdrawn.json`, one entry per
retired figure or claim, append-only, imported from `game-research-gpt`'s `FINAL-CORRECTIONS.json`
(`eval/IMPROVEMENTS.md`, axis 3). `docstat.py --withdrawn` gates on it.

**The exemption is the entry id and nothing else.** Not a file, not a line — lines move. Not a
marker word: `withdrawn`/`superseded`/`retracted` is an enumeration, and an enumeration already
failed here on one inflection of one verb, where the aspect check exempted `planted` and went red
on `planting`. A live document that needs to state a retired figure cites the id in the same
block, and that is the only way to be green.

**This does not distinguish stating from asserting as current, and nothing mechanical can** — they
are the same characters. It makes the author declare which, in place, for one parenthetical. Three
of the six hits on the day it was installed were legitimate historical prose in a live document,
including `JUDGING.md`'s own withdrawal notice; all three were repaired by adding the id, which
also warns the reader who lands on that line instead of the one who reads 114 lines further down.

**LIVE and ARCHIVE, decided here because a gate with an undeclared scope is a gate whose scope
drifts.** The archive records what was believed when it was written and may state a retired figure
freely; everything else is live.

| | documents |
|---|---|
| **ARCHIVE**, exempt | `eval/findings/`, `eval/FINDINGS.md`, `eval/IMPROVEMENTS.md`, `IMPROVEMENTS.md`, `CLEANUP-LOG.md`, `tasks/`, `eval/runs/` |
| **LIVE**, gated | every other tracked markdown — `README.md`, `DECISIONS.md`, `eval/RUNS.md`, `eval/judge/RUBRIC.md`, `eval/judge/JUDGING.md`, `eval/PROTOCOL.md`, `research/`, `eval/starters/`, `.agents/skills/` |

`tasks/` is archive because a retired figure can be a task's whole subject — task 54's `done_when`
states the pair three times, correctly. The list lives in `ARCHIVE_PATHS` in `eval/tools/docstat.py`
and is asserted against this table by `eval/tools/withdrawn_control.py`, so the two spellings cannot
drift apart silently (rule 12).

**The whole-file archive exemption is the one document-scope exemption in the sweep, and it is
deliberate.** Document-scope is how the aspect check next door once went vacuous — a single
legitimate disclaimer silenced every check in its file. Inside a live document nothing is exempt by
file: the only exemption is an id inside the block, and the block ends at a blank line, at a
blockquote's own blank line, at a fence, or at the next top-level list item.

---

## Open

- **The matrix result.** No stack ranking exists, and the deterministic tiers cannot produce
  one — see above. Tier 3 is the only remaining layer that could.
- **Statistical power.** With 2 trials per cell, if two stacks land within ~0.015 this design
  cannot separate them. The earlier spec-change suite already failed to separate four stacks that
  all scored 6/6.
- **The rubric ceiling — MEASURED and now DECIDED on both tiers, but only one of them is fixed.**
  There are **11 (run, game) groups: 10 game groups and 1 scene**, and a group never holds both
  classes. Tier 1 is at the ceiling on **61 of the 69 stored submissions** — 61 of the 68 games,
  and 0 of the 1 scene — and its 8 failures sit in 4 of those groups. It returns a *single* value
  across every measurable trial in **8 of the 11**
  (`python3 eval/judge/tier1_census.py --runs-root <checkout>/eval/runs`, re-read 2026-08-27; #92
  is the narrower reading, over the 56 matrix trials that existed then). **What to do about it was
  decided on 2026-08-23: tier 1 became a gate** (see "Tier 1 gates, it does not score" above, and
  #123). The ceiling did not go away; it stopped being reported as a score.
  **Tier 2 is at the ceiling on 5 of 11 groups, all of them game groups, 35 of the 68 games**
  (`python3
  eval/judge/tier2_census.py --runs-root <checkout>/eval/runs`, same day), and it now carries the
  whole weight. That half is not fixed and will not be fixed inside the rubric: both in-rubric
  repairs were measured and neither works (#128), so a saturated group is reported as a completion
  certificate (see "A saturated tier 2 is reported as a completion certificate" above). **What
  stays open is the task**, priced by task 74 — not the criteria and not the weights.
- **Whether the subjective layer earns a weight — ANSWERED 2026-08-16, and the answer is no.**
  All five aspects were run over a full eight-submission field for **$33.63** — the sum of that field's own stored rounds. The $46.79 previously here was the whole of 2026-08-16 across two games (#121). Three fail the
  ceiling gate on one presentation order; `fun` and `idiomatic` fail adjudication (#52, #53).
  The redundancy reading — `architecture` and `ux` ranking the field identically while sharing
  no evidence — **carries no weight here and is withdrawn**: it did not replicate, and the
  decision never rested on it (#54, register `WR-arch-ux-redundancy`). And
  **no aspect separates the stacks at a magnitude that could matter**: recomputed by
  `eval/judge/field_ranks.py` over both stored fields of `wg-tetris-judge-2026-08-17`, the
  between-stack range **never exceeds the within-stack gap by more than 15%** across the **8**
  readings, on a field the deterministic tiers score identically. Reported pair, `rank`+`pool`:
  **1.3125 against 2.5625** pre-repair, **1.8750 against 2.0938** post-repair. Both are over the
  **4** poolable aspects; `idiomatic` is cross-stack barred and no longer enters a pooled figure
  (`tasks/146`, and the population row under "Grading" above).
  **This is a magnitude, not a direction, and the change matters.** The bullet used to read
  *"its between-stack range is smaller than its within-stack spread"* — an inequality that
  **reverses in 1 of the 8 readings**, and reversed in 4 of the 8 while the barred
  aspect was in the pool. That argument is retired rather than restated with better
  numbers: a comparison whose sign is decided by a free method parameter cannot license a
  conclusion in either direction, and honouring the bar moved the sign on 3 readings without
  anyone touching the method. **The weight is unchanged; only its stated reason is.** The
  two grounds under "Grading" above never depended on this field at all — a bounded contribution
  of 0.10 against a tightest adjacent gap of 0.0622, and an aggregate noisiest exactly where it
  would matter — and #83 means neither round is defensible as blind regardless. The withdrawn
  pair is FINDINGS #113; the "within ~10% in both" reading that briefly stood in for it is wrong
  on one of the two fields and is #115. Both stay in the log and appear in no live document as a
  measurement.
  **Tier 3 stays at weight 0.00**, now on measurement rather than on argument. All three
  prerequisites were then BUILT and the layer re-run (2026-08-17, $31.66): `fun` has a
  representative play session and its confound is gone by construction, `architecture` packs
  are extension-blind, `idiomatic` is accepted as within-stack only. **The verdict did not
  change** — only `ux` clears every gate, and gate 0 (reproducibility, added the same day)
  shows ceiling verdicts flipping on provably unchanged input in 3 of 6 clean repeats.
  Re-opening now requires repeats at a fixed order, not more aspects.
  **Verified 2026-08-22 by fingerprint, after a false alarm.** The `fun` rounds were briefly
  reported as having read pre-repair telemetry. They did not. `g2_tetris3d` exists as four stored
  fields in different states of repair, and the wrong one was inspected: `wg-matrix-2026-08-13` is
  `representative` on 0 of 8, but the rounds read **`wg-audio48-2026-08-14`**, which is 8 of 8 and
  was re-driven on 2026-08-17 for precisely this reason. Matched on values rather than on
  reasoning: all **7 of 7** `quiet_fraction_of_run` figures and **4 of 4** `events_per_second`
  figures quoted in #68's evidence appear in `wg-audio48`'s stored telemetry and **none** appears
  in `wg-matrix`'s. **#68 stands as reported.**
- **g4, the platformer — LAUNCHED, and the question it was added to answer is ANSWERED: no.**
  Three runs and **$698.21** of agent trials: `wg-g4` $211.64 (4 of 8 cells, stopped), `wg-g4b`
  $65.57 (8/8 `api_error`, a null), `wg-g4c` $421.00 (8/8 `completed`) — re-derived 2026-08-23 by
  summing `total_cost_usd` over `eval/runs/wg-g4*/artifacts/*/agent_result.json`, which reproduces
  `eval/RUNS.md`'s per-trial $36.16-$77.60 for `wg-g4c`. **#42's $800-1,900 priced a 24-trial
  matrix and is not the comparable figure**; what was bought is one 8-cell field plus two runs
  that produced nothing gradeable. **The result is a tie**: all 8 `wg-g4c` submissions return
  **tier 2 = 1.000** — the scored tier under the gate scheme — and 20 of the 20 scored g4
  criteria have never failed (#128), so a game exercising
  sprite animation, hitboxes and platform collision separated the stacks no better than Pong,
  Tetris and arena did. See "A saturated tier 2 is reported as a completion certificate" above.
  **What stays open is a harder task, priced and not bought** — the row in "Reversal conditions"
  below states what would buy it.

## Code-reading aspects are within-stack only — permanently, not pending a better anonymiser

**Decided 2026-08-22, on measurement.** `idiomatic` and `architecture` may be used to compare
submissions **within one stack**. They may never contribute to a cross-stack claim, and this is
not a defect awaiting repair.

> **The within-stack permission is conditional on the field's packs matching their manifests,
> and the condition is a property of the pack ON DISK NOW — not of the run, and not of a round
> already taken.** `wg-g4c-2026-08-21T02-26-46` failed it with 23 stale files in 222 (#95) and
> **passes it since the 2026-08-23 re-pack**: 199 files, `stale=0`, `clean=True`, with the
> starter-drift exclusion set computed and corroborated rather than guessed (`eval/RUNS.md`).
>
> **A re-pack licenses new rounds, never stored ones.** The 30 `wg-aspect-reliability` rounds
> read the 222-file field; nothing can re-run their reading, so their `idiomatic` and
> `architecture` orderings stay unreadable. Within-stack code comparison on this field means a
> round taken after the re-pack.
>
> Check before relying on this permission, at the run you are actually reading, and check it
> again if anything re-packed since:
> `python3 eval/judge/field.py packcheck --run eval/runs/<run>` — exit 0 clean, 1 dirty, 2 if it
> could not evaluate the address you gave it (#96). It takes a **path**, not a run name.

### The measurement

Across 26 stored code-aspect rounds, 208 evidence strings, counting strings that name their own
stack's real tokens (`Bevy`, `MonoBehaviour`, `Godot`, `THREE`, `@export`, `InputMap`):

| aspect | blinding | strings naming the real stack |
|---|---|---|
| `idiomatic` | real extensions, by design | **134 of 144 (93%)** |
| `architecture` | `blind_language=True`, `.src` paths | **13 of 64 (20%)** |

**The substitution works and is worth keeping** — 93% → 20% is not nothing, and an earlier
reading that "no anonymiser helps" was wrong. But the residual 20% is unfixable, and the reason
is decisive: `Godot`, `GDScript`, `MonoBehaviour`, `UnityEngine`, `THREE` are **absent from the
architecture pack**, verified over 2.2M characters — yet the judge writes *"Rust/Bevy."*,
*"Unity/C#."*, *"Godot/GDScript."* anyway. It is not copying a token that slipped through. **It is
identifying the language from the syntax and naming the engine itself**, and on one occasion
wrote *"EngineBehaviour = renamed MonoBehaviour"* — decoding the substitution and reporting what
had been replaced.

### Why no better anonymiser exists

Syntax cannot be removed without paraphrasing the code, and paraphrasing changes the thing being
judged. A stronger cipher is still a cipher against a reader that breaks it. For `idiomatic` the
point is sharper still: the aspect asks whether the code is written the way its language is
normally written, so **the aspect whose subject is the variable under test cannot be blinded to
that variable.** Blinding it would not make it fair; it would make it meaningless.

### What follows, and what does not

- **Barred: any cross-stack ordering from a code aspect.** Not because the judgement is
  necessarily wrong — it may be a real reading of the work — but because it can never again be
  *defended* with "it cannot be a prior, the judge is blind". That defence is unavailable
  permanently.
- **Permitted: within-stack A/B** — template v1 against v2, same stack, same task. A per-stack
  prior is constant on both sides and cancels. This is the same argument that licenses the
  repeats work, and it is what the template improvement loop actually needs.
- **`architecture`'s `blind_language=True` stays**, because 20% is better than 93% and the
  cost is zero. Keeping a partial defence is not the same as trusting it.

### The question this retires

#53 asked whether `idiomatic`'s stack ordering is "a language prior rather than a judgement of
the work". **That question was mis-posed**: it assumed the judge did not know the stack. It does,
in 93% of strings, by its own account. The ordering may still be a real judgement — #79 found it
reproduces across four games with zero contradictions — but "blind, therefore not a prior" was
never available as an argument, and no experiment can restore it.

**A limit that cannot be removed is a decision, not a finding.** #53 and #83 record how it was
discovered; this records what is now done about it.

---

---

## The templates are measured at each stack's best, not at a common floor — decided 2026-08-22

**Every template showcases the best its own stack can do. It is not held to a capability floor
shared by all four.**

The alternative was a common floor: every template exposes only what all four stacks can do,
which keeps the comparison tightly controlled and measures the stacks on shared ground. That was
rejected. It answers a question nobody is asking — *how do four engines compare when each is
restricted to what the weakest can do* — and the headline it produces ("these four are
indistinguishable") is then partly an artifact of the restriction.

**What is now being measured: what a competent agent can build in each stack when the template
does not hold it back.** That asymmetry is the subject, not a confound to be designed away.

**The survey it was decided ahead of has now run** (`research/10-stack-capability-matrix.md`,
2026-08-23), and it corrects two of the examples this decision was originally stated with:

- **Ray tracing is not reachable in any arm on the measurement machine.** Bevy has the Metal
  ray-query feature and `bevy_solari` still cannot initialise (it needs `BUFFER_BINDING_ARRAY`,
  which wgpu 29 sets only on Vulkan) — and it fails open with a `warn!`. Unity measures
  `supportsRayTracing = False` and ships no Metal acceleration-structure path. three.js has no
  WebGPU under the capture harness. Godot has the API but no scene-renderer integration. The
  clause "ray tracing where the platform supports it" therefore selects nothing.
- **Native physics is the inverse of how it reads.** Godot ships Jolt in-tree but Godot Physics
  is the default; Unity ships PhysX. Both are one pin change away — and **neither can be used
  where game rules must live**, because `Sim.asmdef`'s `noEngineReferences` and
  `tools/boundary.gd` forbid it. Bevy and three.js, which ship no physics, are the two that
  *could* pin a deterministic solver inside `sim`.

Native particle systems remain a real and large asymmetry: Godot ships them, Unity's is one
manifest line, Bevy and three.js have none at any effort below writing one.

**What this costs, stated plainly so it is not discovered later:**

- A cross-stack difference is no longer attributable to the stack alone. It is attributable to
  *the stack as exercised by this template* — and the template author's judgement about what
  "best" means becomes a variable. This was always partly true; deliberately diverging templates
  make it matter more.
- The defence is that "best" must be **sourced, not asserted** — see
  `research/10-stack-capability-matrix.md` and `research/AGENTS.md`'s sourcing rules. A capability
  included because it is documented and reachable is defensible; one included because it seemed
  impressive is not. The survey also lists ten cells it could **not** establish; those are not
  available for "best" until someone settles them.
- `judge/starter_parity.py` must continue to REPORT capability divergence rather than fail on it.
  Under this decision, divergence is the design; a guard that reads it as drift would be wrong
  and would be switched off, which is worse.

**This decision does not license showcasing what cannot be observed.** `ux` — the aspect most
sensitive to visual richness — was retired for correlating +0.53 to +0.73 with distinct-colour
count (#59), so prettier output moves that metric in the direction that looks like improvement,
for the reason it was retired. What the pipeline *can* now see about capture cost and capture
geometry is the next section; what it still cannot see, and why, is the `DECLINED` register in
`judge/capability.py`. **A capability change must name the field that would move if it worked**,
and if the only candidate is a palette-coupled one, it cannot be shown to have helped.

**Implemented, 2026-08-23, in all four arms.** Rust is on Bevy's own default feature set, so
the arm can render a lit 3D mesh and open an audio device — neither of which it could do at the
old pin, on a task set where two of four games are 3D and audio is a scored criterion. Godot
exposes `GPUParticles2D` through `view/fx.gd`. Unity carries `com.unity.modules.audio` and
`com.unity.modules.particlesystem` and exposes Shuriken through `Assets/View/Fx.cs`, so the two
engines that ship a native particle system both expose it and `AudioSource` compiles for the
first time — it was a hard compile error (`CS1069`) through every matrix graded before this
date, on a criterion that is scored. TypeScript adopts nothing: three 0.185 ships no emitter,
and its batching primitives are documented with the measurement instead, because on the
rasteriser the harness actually uses `InstancedMesh` buys ~6% and `Points` is already five lines
away.

The regime notes and the measured costs are in `eval/RUNS.md` (twelfth and thirteenth
comparability breaks); the hypotheses, the falsifiers and **the register of capabilities
surveyed as available and deliberately not adopted** are the task-26 and task-52 iterations in
the root `IMPROVEMENTS.md`.

**One operating rule came out of doing it, and it decides the cases the survey does not.**

> **A template exposes what its stack SHIPS. It does not implement what its stack lacks.**

Lowering a capability from E2/E3 to E1 for something the engine already contains is exposing it;
writing the subsystem is manufacturing one, and it would erase the asymmetry this decision exists
to measure. It is why Godot and Unity get a particle helper and Rust and three.js do not: neither
ships a particle system at any effort below writing one, and a template that wrote one for them
would be reporting a fact about four template authors.

**Its corollary, learned in task 52: a capability the stack already ships in one line is
documentation, not scaffolding.** Exposing means removing the cost of discovering something; it
does not mean wrapping something that has no cost to discover. `Points`, `InstancedMesh` and
sprite atlasing are all E1 in their arms, so what the template owes an agent about them is the
number that tells it which to pick — for ts, that one batched `InstancedMesh` is 6% cheaper than
N separate meshes on SwiftShader and one `Points` is 10x, at the geometry counts this task set
actually reaches. A wrapper would add surface without adding reach.

---

## Performance is measured from outside the submission, and none of it is scored — decided 2026-08-23

**The harness measures the cost of the evidence it collects. The submission is never asked to
report a number about itself.**

Task 25 proposed extending the probe contract in `starters/_shared/` so each stack reports its own
performance fields. Rejected, and the reason generalises past this case:

> **A field the subject reports is a field the subject can fail to report, and that failure
> correlates with stack** — #62, #72, #77, this project's most repeated defect. A field measured
> by a mechanism identical for all four arms cannot produce a stack-correlated gap; the gap would
> have to be in the harness, where one repair covers every arm. **Uniformity by construction beats
> uniformity by instruction.**

Two consequences that made the choice cheap as well as right: no starter changes, so this is **not
a regime boundary** and every stored run stays in the comparison; and four of the nine fields turn
out to have been recorded on all 68 stored submissions already, unread (#97).

`judge/capability.py` holds the contract — nine fields, each with its unit — plus the gate
`no_stack_correlated_gap()`, which fails if a declared field is ever absent for any reason other
than the submission's own capture failing. `judge/capability_selftest.py` carries its mutant and
its variant.

**No frametime and no fps field, at any point.** The four arms do not render the judged frames on
comparable hardware: Rust, Unity and Godot draw on the M3 Max, the TypeScript arm draws on
**SwiftShader, a CPU rasteriser** (`research/10-stack-capability-matrix.md` §3). A frametime field
would report the renderer backend wearing the costume of a stack result. `just film` is also not a
real-time loop in any arm — twelve single frames of a deterministic replay — so there is nothing
steady to time. `DECLINED` in that module records this and the other six candidates, each with the
measurement that would move it back in.

**Nothing here is a criterion, and `judge/RUBRIC.md` weighs none of it.** Capture is cheap and
reversible; scoring changes what agents optimise for and is a regime boundary. A criterion
introduced alongside its own measurement has no baseline to be calibrated against.

Its reversal condition is in the table at the end of this file.

---

## What in `eval/runs/` is evidence — decided 2026-08-22

**A file under `eval/runs/` is evidence until something in the tree itself proves it can be
regenerated, and the proof must name a producer that declared the file its own output.**

Two proofs are accepted, both being the toolchain speaking about its own output: a `CACHEDIR.TAG`
with a valid signature at a directory root, and the work tree's own `.gitignore`. Anything no
proof reaches is copied.

Stated as a rule rather than a list of directories because an enumeration misses the next stack
and fails in the direction that loses evidence. It is applied by `eval/tools/evidence_set.py`;
`eval/PROTOCOL.md` says when to re-sync and `#90` says what this replaced.

Measured on that rule: 14,270 files, 1.118 GB of 138.164 GB — 99.19% of `eval/runs/` is
regenerable. **Reclaiming the 137 GB remains task 10's call**, and nothing was deleted here.

**When to re-sync is decided by the resource, not by an activity — revised 2026-08-23.** The rule
was *"after any run completes"*, and the starter baselines (7.5 MB, the only record of what
starter each agent was given, #104) were created by a **repair**, so the copy verified complete at
00:08 did not contain them at 04:24 (#116). The trigger is now *the evidence set has grown or
changed, whatever made it move*, with `backup_evidence.py --verify-only` as the mechanical form —
it re-classifies and a non-zero missing count is the signal, so nobody has to judge what counts.

**The copy is deliberately additive.** `rsync` runs without `--delete` and nothing removes from
the destination, because a mirror that faithfully reproduces an `rm -rf` protects against nothing.
The cost is that it becomes a superset; `DEST_ONLY.txt` at the destination lists every such path
so a stale file cannot pass for a current one, and reconciliation happens at the source or not at
all.

**Where the copy goes is still open.** The current copy at `/Users/stefano/game-research-evidence`
is on the same physical disk as the original and is therefore not a backup — it survives `rm -rf`
and a bad `git clean`, and nothing else. This machine has no external disk, no `rclone`/`restic`
remote, and its only cloud target is the operator's personal iCloud Drive, which is not somewhere
project evidence belongs. Every evidence file is under 50 MB, so an external disk or a private
GitHub repo would each work without LFS; both need the operator's go-ahead.

---

## A wrong stored manifest is marked, never repaired — decided 2026-08-23

**Configuration records in `eval/runs/` are append-only when written and read-only afterwards.**
Six stored directories hold a manifest that does not describe them (#93, #120). None was edited.

**Why not repair.** For `wg-matrix`, `wg-arena3d` and `wg-g4` the original was destroyed and no
honest replacement exists — a manifest reconstructed today is an inference wearing the name of a
contemporaneous record, and every later reader would take it at face value. For `wg-audio48` the
original *does* survive as `suite-full-matrix.json`, and it was still not promoted: renaming it
over `suite.json` would leave the directory looking as though nothing had ever gone wrong, which
is the state the audit exists to distinguish from a healthy one.

**What replaces the repair.** Each carries a `MANIFEST-DEFECT.json` written by
`eval/tools/manifest.py mark`, holding what was measured, what survives, and — only under
`reconstructed_*` keys, never under a `suite*.json` name — what the reports say the run was. The
marker stores the exact issue list it acknowledges and the audit re-measures and compares every
run, so it can acknowledge an unchanged known state and cannot hide a change. That is what keeps
it from being a suppression list.

**What would re-open it.** A stored manifest whose original is recoverable *byte for byte* from
something written at run time — a build log quoting it, or a copy in the evidence set predating
the overwrite. Then promoting it is a restoration rather than a reconstruction, and the
distinction this decision rests on disappears.

---

## Append-only has two shapes, and the directory decides which — decided 2026-08-23

The guard from the decision above is stated as a resource: *any durable record of what a
measurement was configured to be, or of what it measured, is append-only.* Two more writers had
the overwriting shape and are now covered — judge-sweep summaries (`GATES.json`,
`SEQUENTIAL.json`, `REPRODUCIBILITY.json`) and the three records at the evidence destination
(`MANIFEST.sha256`, `DEST_ONLY.txt`, `MEASURED.json`). **Neither is regenerable in practice: the
inputs move.** A sweep's gate-0 verdict belongs to the rounds that existed when it ran, and what
the copy held last week cannot be recomputed from what it holds today.

**They do NOT take the same layout as `suite.json`, and that is the decision.** `write_manifest`
pins the canonical name to the *first* record. Applied here it would have been a defect wearing
the shape of a fix:

| | pinning would have done | consequence |
|---|---|---|
| `MEASURED.json` | canonical = the first sync ever | `PROTOCOL.md` instructs a reader to take the evidence count from that name; it would hand back a stale number, and nothing would disagree with it |
| sweep summaries | canonical = the first invocation's ceiling counter | `judge_ledger.explain_gap` looks for the carried-over rounds at the *head*; against a first-invocation counter the gap is the *suffix*, so every resumed sweep returns `UNEXPLAINED` and exits 1 |

So `tools/manifest.py` carries both, in one file, with the criterion written next to them:
**pinned where the directory has an identity the record is named for** (a run directory is named
for one launch, and a later launch must not take the name); **rolling where the directory
accumulates** and its record states the position as of the last invocation. Nothing is destroyed
under either.

Two consequences worth stating because they are the ones that would otherwise be re-derived. An
**identical restatement is not a new record** — `write_rolling` compares the bytes and writes
nothing when they match, which is what keeps `--verify-only` from adding a 1.1 MB checksum
manifest every time it is run against an unchanged set. And the kept copy is stamped from a
timestamp **inside** the record where there is one, falling back to mtime only for plain text: a
`cp` rewrites every mtime in glob order and produces a clean, ordered, meaningless chronology,
which is the defect `judge_ledger.MIN_SPLIT_S` exists for.

**What this does not do.** Stored records written before the repair are untouched — no sweep
directory was given a reconstructed history, for the same reason no stored manifest was repaired.
The guard is forward-only.

---

## The harness lint baseline is a recipe, not a gate — decided 2026-08-23

**`python3 eval/tools/lint.py` is the recipe.** It runs the pinned rule set over the harness and
prints every site with its file and line. `prune_scan.py --only lint` still gives the per-rule
totals; both call the same `run_ruff()` in `prune_scan.py`, and `LINT_SELECT`, `LINT_ROOT` and
`LINT_EXCLUDE` are spelled once, there.

**It exits 0 with findings.** A gate added while the codebase still violates it is a gate that
gets switched off, and switching it off is silent. `--gate` exists so whoever wires one later
need not edit the tool. **CI now calls it, for one rule only** — see the CI decision below.

**What the baseline means, and what it does not.** `PLW1510` and `BLE001` were triaged to **0**
on 2026-08-23: every `subprocess.run` under the lint root stated its `check=`, and every blind
`except Exception` that remained carried a `# noqa: BLE001` naming why the exception set is open
there. A new hit from either rule is therefore a site nobody has considered — and **re-measured
later the same day there are 11 of them**: 10 `PLW1510` (`judge/blind_dir_selftest.py`,
`judge/blind_ext_selftest.py`, `judge/starter_parity.py` x2, `tools/disclosure_mutants.py`,
`tools/findings_control.py`, `tools/tasks_control.py` x3, `tools/tasks_mutants.py`) and 1
`BLE001` (`tools/tasks_control.py:497`). Re-derive with `python3 eval/tools/lint.py --counts`
rather than quoting this paragraph. The other findings — `B905`, `F401`, `F541`, `B007`, `B023`,
`F841` — were **not** triaged and are a standing backlog, not a clean baseline. The reasoning is
in #105 and in `eval/tools/lint.py`.

> **A triaged-to-zero baseline decays in hours at this parallelism, and nothing was watching it.**
> That is the argument for the CI decision below rather than an argument against the baseline.

**`eval/judge/fixtures/` is out of scope**, alongside `eval/runs/`. Those are stand-in
*submissions* — the same class of artifact as `eval/starters/*/`, one of them deliberately
defective — and linting the object of measurement is measuring the thing being measured. They
contributed 14 of the 30 `BLE001` and 3 of the 11 `B905`, every one of them an idiom a fixture
needs.

---

## The gates run in CI and in git hooks, in three tiers — decided 2026-08-23

Every verification command here used to run only when somebody remembered to. That is a check
with a duty cycle, and the rate was measured above zero twice in one session: a commit was
pushed while `docstat.py --findings` was exit 1, and the stale-citation rows in `--sweep` stayed
red across several merges.

**The register of what runs where, and of every gate deliberately left out with its reason, is
`.github/workflows/README.md`.** It is not restated here — a second copy is a second source of
truth. What is decided:

**3 tiers, split on a budget rather than on coverage** — the hooks in seconds, the fast CI
tier around a minute, the slow one in minutes. A hook nobody bypasses is worth more than a hook
that covers everything, and `--no-verify` is one flag. **A hook checks the CONTENT; CI
additionally checks the CHECKERS** — a control over a tool changes only when the tool changes.

**So the hooks run a strict, small subset, and the register NAMES it rather than describing it —
decided 2026-08-25, task 153.** Both tiers run documentation and queue checks and nothing else;
the command list, the counts and the coverage gap are in the register, produced by `python3
eval/tools/ci_minutes.py --hooks`. The register described the tier with an adjective instead —
*"the full `gates.yml` set"* — which had never been true of anything. **The repair is not to run
more.** Widening `pre-push` to the whole workflow makes it minutes long and turns `--no-verify`
into a habit, which costs the tier its whole value; deriving its list from `gates.yml` behind a
cheapness marker adds a second selector to maintain for the same handful of commands. What the
tier was missing was not coverage but a **checkable** description, so `.githooks/run-gates.sh`
prints its own list under `GATES_LIST_ONLY=1` and `ci_minutes.py --selftest` asserts the
register's table equal to it — red when a gate is added to either alone. **An adjective is the
shape no check can read**; a hook whose published list is asserted against the hook is one a
reader can act on, and the coverage gap is then stated rather than implied.

**No hook timing is published, and the workflow tiers are published as a SPREAD — decided
2026-08-25, tasks 129 and 153.** A point figure in that table was wrong every time it was read:
across the last 12 successful runs of each workflow on `main` the range is tens of seconds wider
than any step this repository adds, so a single reading is one draw from that band and the
difference between two of them supports no inference about a change. The hook figures were worse
still — local wall clock on one machine, and two readings of `pre-push` minutes apart on the same
host differed by more than the whole `pre-commit` tier costs. The register carries the spreads,
the population and the command that re-derives them, and points at `gh pr checks <n>` for the
pull request in front of you.

**The hooks are installed by hand, with `git config core.hooksPath .githooks`, and are not
installed by anything automatic.** `core.hooksPath` lives in the shared git config, so one
invocation arms the main checkout and every agent worktree at once. That is a change to how
every concurrent agent's commits behave and it is the operator's to make.

**`tasks.py check` blocks in a real checkout and warns in a linked worktree**, because
`tasks.py` resolves the queue to the main checkout: from a worktree it reads state your commit
does not contain and peers are editing. It went red mid-session on a peer's `in_review` while
this was being built.

**CI gates `lint.py --gate --rule invalid-syntax` and not the full pinned set.** Wiring 64
findings in on day one teaches everyone to skip CI. `invalid-syntax` is the subset that is at
zero and can still go red. What would widen it is triaging the 11 `PLW1510`/`BLE001` sites
above, not relaxing the rule.

**`fetch-depth: 0`, measured.** At depth 1, `tasks_control` exits 3 with 5 of 28 rows
`NOT CHECKED`, `withdrawn_control` exits 1, `dead_private_control` exits 3 and `tasks_mutants`
exits 2 — established against a `file://` depth-1 clone of a full clone, so the trees were
byte-identical and history was the only variable, with `git rev-parse
--is-shallow-repository` asserting the depth rather than a commit count implying it.

**Nothing in CI spends money, drives the `claude` CLI, or needs a stack toolchain.** That rules
out `starter_parity.py`, `parity_selftest.py` and `starter_gate_control.py` (325s, and it drives
Godot, cargo, pnpm and Unity), and `evidence_set_control.py` and `disclosure_mutants.py`, which
need `eval/runs/` and correctly exit 2 without it.

**The repository is PUBLIC, so Linux Actions minutes are free and unlimited** — read with
`gh repo view teonimesic/game-stack-bakeoff --json isPrivate`, never remembered. The design stays
lean anyway, because what a merge now waits on is wall clock in front of a required check rather
than a bill: `ubuntu-latest`, push narrowed to `main`, `cancel-in-progress`, and the slow tier
behind a path filter plus a nightly cron.

**What CI has consumed has a producer: `python3 eval/tools/ci_minutes.py`.** Consumption is read
from the Actions API per job, rounded up to the whole minute, and printed with the window it
counted over. The projection that used to stand in the register was arithmetic over 2 guessed
run-rates and is replaced by a measured total, not by a better estimate. 2 traps are encoded in the tool rather than in prose because
both return plausible numbers: `run_duration_ms` is the run including its queue wait, and
`billable.UBUNTU.total_ms` — the field named for exactly this quantity — read **0 for 58 of 58
runs**, so anything summing it reports "0 minutes consumed" and is indistinguishable from a
repository that has never built.

**`controls.yml`'s path filter is evaluated over the whole pull-request diff, and that is kept
deliberately — decided 2026-08-23, task 124.** A `pull_request` run is evaluated against the
MERGE of head into base, so the question a filter must answer is "has anything the slow tier
reads changed since it last ran", not "did this push touch `eval/`". Measured: of 19 `controls`
runs on pull requests, 2 of the 13 with a predecessor push were bought by the accumulated diff —
and in **2 of those 2**, `main` had moved in a filtered path inside the window, including
`eval/tools/tasks.py`, which `tasks_mutants.py` mutates — and 62% of `main`'s commits that day
touch a filtered path, so the exposure is continuous. Narrowing the filter to the latest push
would therefore have been fail-open on every measured opportunity, for at most 16 of 220 minutes.
**And the wasted-run count does not grow**: re-read later the same day with the analysed
population up from 13 to 16, it was still 2 — a one-off from the branch that was editing the
CI's own documentation, so the case for narrowing weakens as the denominator climbs.

**The filter moved out of `on: paths:` and into a step on 2026-08-24, task 131 — and the
population it is evaluated over did not change.** A workflow whose `paths:` do not match produces
**no check at all**, not a passing one, and `controls` is a required check, so a pull request
touching only `tasks/` or a root document waited on a check that could never arrive; updating the
branch could not help, because nothing would ever produce it. Measured at PR #14's head: two
`gates` check runs, **zero** `controls`. `controls.yml` now triggers on every pull request and
its first step, `ci_minutes.py --scope`, diffs the merge commit against its first parent — which
is exactly what `paths:` matched against — and writes `relevant=true|false` for the steps below.

**This supersedes the step-gating form rejected the day before, and the objection to it was
right.** That form buys its saving with a green `controls` run that executed no gate, which is the
one pattern this project exists to catch. 3 things answer it, and none of them is the saving:

1. **The guard is `!= 'false'`, never `== 'true'`.** An output the scope step never wrote reads
   as the empty string; `== 'true'` skips on it, `!= 'false'` runs. The only way to skip is for
   the scope step to have run and said so. Every unknown — an unreadable diff, an empty diff, a
   non-`pull_request` event — runs the whole suite.
2. **`push` to `main`, `schedule` and `workflow_dispatch` are never filtered.** Nothing waits on
   those, so latency is not a cost there, and running unconditionally is what checks the filter's
   claim. A wrong filter is therefore wrong for at most one merge rather than indefinitely.
3. **The step prints what it read** — the filter, the changed paths, the verdict — so a skipped
   run is auditable afterwards instead of being a silent green.

`ci_minutes.py --selftest` pins the wiring in both directions, and its closing line is the
producer for how many mutants and variants it carries. The two-job form stays rejected and is now
rejected twice over: it was arithmetically worse when minutes were metered (+25 to save 16), and
a second job is a second check that can be absent.

**Every mode of `ci_minutes.py` REFUSES the flags it does not read, rather than making `--scope`
honour `--json`.** `MODE_ACCEPTS` states which of `--json`, `--cache` and `--no-timing` each mode
reads; `main` checks the invocation against it before dispatching and exits **2** naming the
combination.

Refusing was chosen over honouring for 2 reasons. `--scope` already has a machine-readable
channel and it is the one the workflow reads — `relevant=` in `$GITHUB_OUTPUT` — so a second
format would have no consumer and would have to be kept in step with the one that has. And
honouring `--json` answers the instance while leaving the shape: `--scope --gates`,
`--selftest --json` and `--path-filter --no-timing` were all exit 0 on a discarded flag, which is
the enumeration-versus-property failure the rule audit is about.

**The workflow gate asks the scope step's `run:` line the same question**, reading it as a command
rather than as text: the script token must resolve, against the repository root, to
`eval/tools/ci_minutes.py`; in front of it there must be nothing or one `python`/`python3` named
alone or absolutely; and `--scope` must be among the arguments with every other flag one `--scope`
reads. It tokenises the way a shell does, **newlines included**, because a `#` comment ends at its
line and a flattened multi-line block would let one hide a second command that overwrites
`relevant`. A substring test accepted `--scope --json`, `echo eval/tools/ci_minutes.py --scope`
and `nested/eval/tools/ci_minutes.py`, none of which produces a scope decision from this tool.

**The lever if latency ever binds is the slow tier's `pull_request` trigger, not its path
filter.** `python3 eval/tools/ci_minutes.py` is what decides that on current data: it reports
minutes by workflow and by workflow x event, and the `controls` x `pull_request` cell is the one
the lever acts on.

---

## The four `template*/` trees and the spec-change suite are retired — decided 2026-08-23 [user]

**The four original trees — `template/`, `template-ts/`, `template-unity/`, `template-godot/` —
are deleted, and with them `eval/run-bakeoff.sh` and `eval/archive-and-rerun.sh`, the only two
things that could launch a spec-change trial.**

**Why, and it is not tidiness.** They were a *fork*, not a copy: a finished Pong per stack,
diverged from `eval/starters/*` in every source file. A copy can be gated on equality; a fork
cannot, so nothing compared them and nothing could. Measured: **0 of the 105 commits since the
repo import touched any `template*/` directory, against 6 that touched `eval/starters/`** (#112).
The consequence was not hypothetical — a capture-page defect repaired in `eval/starters/ts` on
2026-08-22 was still live in `template-ts` a day later, and was found by hand, not by a gate
(#112, task 48). **A second tree with a dormant consumer has nothing pulling it back into line,
and the cost of keeping it is paid every time the live tree is repaired.**

The suite they fed was already answered: it **failed to separate four stacks that all scored
6/6**, it has not run since 2026-08-12, and the programme decision that tasks are whole-game
builds rather than spec changes was taken before that. Keeping a fork alive for an experiment
that returned a null and is not being repeated is paying maintenance for nothing.

**What was deliberately KEPT, and why each.** Retiring a suite is not the same as deleting its
evidence, and the two look identical from a file listing:

| Kept | Because |
|---|---|
| `eval/runs/bakeoff-*`, `core-*`, `archive-run1-*` | 71 trials in 12 run directories. The results |
| `eval/suites/*.toml`, `eval/suites/prompts.py` | **The sole copy of what those 71 trials were asked to do.** A trial record stores `task: "t1_rally"` and no prompt text; 0 files under `eval/runs/` contain it (#122) |
| `eval/holdout*/`, `eval/variants/` | The answer key and the ablation arm — what "score 1.00" and "arm no_api_notes" meant |
| `eval/runner.py`, whole | `judge/static.py` imports its capture policy by path. Two truncation policies in one repository is #100, which came back as #114. It is also the definition of the measurement the 71 stored verdicts report, and `report` / `regrade.py` still read them. `run` and `check-suite` now exit 2 naming the retirement instead of raising three frames down |
| `eval/BAKEOFF.md`, `eval/FINE-TUNING-BRIEF.md` | The suite's design, which is the context those results are read in |

**`eval/starters/*/` are untouched and are not substitutes.** They are the whole-game product and
the subject of the comparison; they carry no finished game for a spec change to modify.

**Deletion here is recoverable and that is load-bearing.** The trees are in git across 139 commits
and pushed to `origin/main` — `git log -- template-ts` resolves, and `a3d0fd1` and `ee8625f` are
both on the remote. This is the property #104 did not have, where the only record of a starter was
a commit no archive contained. **A deletion whose recovery you have verified is a different act
from one whose recovery you assume.**

**Known cost, stated rather than discovered later:** `template-ts` received the capture-page
repair on 2026-08-23 (#112, task 48, commit `ee8625f`) — about 500 lines of porting, six hours
before this. That work is discarded. It was correct to do and correct to discard: it closed the
instance, and this closes the shape.

**The deletion did not survive its own merge, and the mechanism is worth keeping (task 111).**
The retirement commit `e86e09d` was complete: `git ls-tree -r e86e09d` matches **0** paths under
`template*/`. So does its other merge parent, `5afeb31`. The merge `f315f7e` nonetheless carried
**5** — `template-ts/.eslintcache`, `template-ts/public/main.js` and three build outputs under
`template-unity/tools/analyzer/bin/`. They came from neither parent; they came off the disk.
**Each tree carried its own `.gitignore`, and deleting the tree deleted the ignore rules that
had been hiding its build output** — `template-ts/.gitignore` listed `public/main.js` and
`.eslintcache`, `template-unity/.gitignore` listed `/tools/analyzer/bin/` — so a `git add -A`
at merge time saw an eslint cache, a 1.2M bundle and a compiled analyzer with its `.pdb` for the
first time, and staged them. From `f315f7e` (2026-08-23 08:35 -0300) until this repair the same
day, `AGENTS.md` stated `template*/` is deleted while 5 paths were tracked on `origin/main`, and
nothing could disagree: **no gate reads the tree for a claim a document makes about it.** It was
caught by a person configuring a code reviewer, not by a check. The 5 are now removed, and the
root `.gitignore` carries
`template*/` so a leftover build tree in an old checkout cannot be re-committed. Reproduced in
both directions on 2026-08-23: with the entry, `git add -A` over three replanted artefacts stages
nothing; without it, the same command un-deletes all three.

> **Deleting a directory deletes its `.gitignore`, which un-ignores every build artefact still
> on disk beneath it.** The removal and the loss of the guard land in the same commit, and the
> re-add lands in the next one — where it reads as an unrelated file, not as a botched deletion.

---

## A blind pack's `CHANGED.txt` is rebuilt from the manifest; the code half is not rewritten — decided 2026-08-23

**The question the ticket left open (task 95): map `CHANGED.txt` through the pack's own manifest,
drop it for blind aspects, or rewrite its text?** The measurement that chose is a partition, not a
total. Of the 1,561 arm-naming directory tokens surviving `blind_extensions` in the 8 stored
`architecture` packs, **182 sit in `CHANGED.txt` and every one is a real path segment**, while
1,379 sit in agent-authored code of which only 149 are paths — `public` is the C# access modifier
1,129 times.

**Mapped, not dropped and not rewritten.** `CHANGED.txt` is the one channel where the harness
holds ground truth: `pack.manifest` is an origin → label table the packer wrote, so every row can
be restated as ` sim/01.src | 42 ++--` with no vocabulary and no regex. Dropping the file instead
would discard per-file churn for the 196 of 424 rows that name files the judge can open, on the
aspect — `architecture` — that most needs to know which structure is authored. Rewriting the text
would need a vocabulary that is complete over a tree the pack cannot see.

**Rows that map to nothing are omitted and their count is not shown.** 228 of 424 rows name files
outside the pack. That count runs 53 and 43 for the two Unity submissions against 15 and 15 for
the two TypeScript ones, so reporting it — like reporting the `git diff --stat` summary tail — hands the
judge a partition of the field nobody chose to measure (#62). It is recorded beside the pack as
`changed_rows_dropped`, and zero mapped rows is a refusal rather than an empty file.

**The code-content half is NOT repaired. Feasibility was not the reason, and neither — it turns
out — is the per-arm density the decision was first written against (task 103).** Four candidates
were measured over the 9 independent stored fields:

| candidate | godot | rust | ts | unity | per-arm density | isolates an arm |
|---|---|---|---|---|---|---|
| arm-exclusive vocabulary from `git ls-files` | 0 | 43 | 265 | 228 | infinite | 6 of 9 fields |
| every starter directory, shared included | 271 | 102 | 830 | 273 | 8.9x | 9 of 9 |
| vocabulary-free: every path component | 831 | 927 | 1701 | 668 | 2.8x | 9 of 9 |
| the same, minus the four bucket labels | 428 | 690 | 1021 | 668 | 2.1x | 9 of 9 |

*Isolates* means a **strict** threshold on one pack's redaction count separates a whole arm from
the other six, measured per field, against **7.1%** by chance. Nothing measured comes near it.

> **The statistic the first version of this decision named was one no judge can see.** Per-arm
> density is an aggregate over the whole corpus; a judge is shown eight packs and how redacted
> each one looks. A vocabulary-free rewrite drives the aggregate from infinite to **2.1x** and
> leaves no arm at zero — satisfying the reversal condition exactly as it was written — while
> making the per-field figure **worse**, 9 of 9 against 6 of 9. It does not close the channel; it
> moves the leak from Godot's zero to TypeScript's extreme, where it is just as readable and
> costs 2,807 redactions instead of 536. **Optimising a proxy that the protected party never
> observes is the shape of a fix that measures nothing.**

The census is part 6 of `judge/blind_dir_selftest.py`, run with `--runs-root`, so the decision has
a producer; it pins the published table and refuses a `--runs-root` that is not the corpus. The
table **excludes `bin`**, the one arm-exclusive segment that fires in all four arms, because 19 of
its 26 hits are `#!/usr/bin/env` shebangs rather than the Rust starter's `src/bin/`; with it the
table reads 9/50/265/238. `tasks/103` holds the working.

**What is left unblinded is smaller than it looks.** Code aspects are already barred from every
cross-stack claim (below), and the judge names the engine correctly in 20% of `architecture`
evidence strings from **syntax alone**, with the tokens verifiably absent. The residue this would
have removed sits underneath a signal that is unremovable and already conceded.

**Scope, stated because it is easy to assume otherwise:** this licenses new rounds and repairs
none. Every `architecture` round stored in this repository read a `CHANGED.txt` listing the real
authored tree.

---

## Pull requests are reviewed by CodeRabbit, and the config is exclusion-only — decided 2026-08-23

**[user]** that agent work should be reviewed before it is merged. **[agent]** everything below
about how. `.coderabbit.yaml` at the repository root is the whole in-repository half; the other
half is a GitHub App authorisation that only the operator can perform, and `tasks/108` holds the
steps.

**`path_filters` carries exclusions and never an inclusion.** Per the schema those patterns also
drive a sparse checkout, so 1 positive pattern turns the list into an allowlist and blinds the
reviewer to everything not named — including `.coderabbit.yaml` itself. An exclusion-only list
cannot do that.

What is excluded, and the population each pattern covers (`git ls-files`, 673 tracked files,
2026-08-23 — re-run it, this tree moves daily):

| pattern | files | why |
|---|---|---|
| `!eval/instrfollow/runs/**` | 115 | committed stored evidence — 1 JSON record per trial. Data, not source |
| `!eval/findings/**`, `!eval/FINDINGS.md`, `!eval/IMPROVEMENTS.md`, `!IMPROVEMENTS.md`, `!CLEANUP-LOG.md` | 10 | archives. A figure published and later proven wrong **stays** there, so a comment flagging one is a false positive with certainty, not with probability |
| `!eval/runs/**` | **0** | gitignored, so it matches nothing today. Kept as a second guard, and the firing case is constructible: `.gitignore` changes, or 1 record is committed as a fixture |

**`eval/instrfollow/runs/` is the stored evidence that can actually reach a diff, and `eval/runs/`
is not** — the opposite of what is easy to assume. `eval/runs/` is 129G and gitignored;
`git ls-files eval/runs` returns 0. Rule 12: the address is an input to the check.

**`tasks/` is reviewed, against the archive list.** It is an archive by `ARCHIVE_PATHS` in
`eval/tools/docstat.py`, and excluding it would also drop it from the sparse checkout — leaving
the reviewer assessing a one-task branch with no access to its brief. The ticket is the only
written statement of what the diff was supposed to do. The false-positive risk is handled by a
`path_instruction` telling the reviewer not to correct figures there.

**`eval/starters/*/` is reviewed too, not excluded, and its instruction redirects what is asked.**
It is the experimental material, so "this could be better" is out of scope by construction. What a
reviewer *can* do there is procedural and valuable: ask whether a change to 1 of the 4 stack trees
was made to the other 3, and whether the regime-boundary gates named in `AGENTS.md` were run.

**`reviews.review_details: true`** is the only setting changed for a reason particular to this
project rather than to code review: it makes each review state which files it ignored, so *"did
our own filters swallow the change?"* is answerable from the artifact. That is `AGENTS.md`,
"capture what the instrument DID".

**`knowledge_base.{learnings,issues,pull_requests}.scope: local`.** All three default to `auto`,
which resolves to **global** on a private repository — what CodeRabbit learns here would be
applied to unrelated repositories on the same account. Same reason skills may not live in
`~/.claude`.

**`code_guidelines.filePatterns` enumerates 6 files rather than globbing `**/AGENTS.md`.** That
glob matches 8, and 4 of them are `eval/starters/{rust,ts,unity,godot}/AGENTS.md` — the product,
not standards this repository holds itself to. It is an enumeration, which is normally the wrong
shape, and it goes stale in exactly 1 way: **a new folder-scoped `AGENTS.md` outside
`eval/starters/` has to be added to it.**

**`reviews.tools` shipped empty and now disables exactly 1 analyser: `skillspector`.** Disabling
`markdownlint` and `languagetool` over 173 markdown files was the obvious first edit and it was a
guess; the first reviews were the measurement, and they came out against a tool nobody had
predicted.

PR #2 was the first pull request whose diff touched a skill. Over its 3 rounds the reviewer posted
**11** review comments, **5** of which carried an attached SkillSpector 2.5.1 block, and **0** of
which were raised *by* SkillSpector — every attachment rode inside a comment that existed for
another reason. Round 1 alone: **8** comments, **5** of them on a `SKILL.md`, **2** carrying an
attachment, and both of those 2 host comments were true positives acted on in `ce4a12c`. The
attachments held **14** findings from **2** rules and **0** of the 14 were true positives:

| rule | of 14 | where it fired |
|---|---|---|
| `[AS3] Skill Enumeration` | 10 | `dispatch/SKILL.md` lines 10-11 and `tasks/SKILL.md` lines 48-49 — the blocks where a skill names another skill's file |
| `[P7] Indirect Prompt Extraction` | 4 | the same line every time: the heading `## 6. Improve this skill as you use it` |

**That is a false positive by construction, not a false-positive rate.** `AGENTS.md` requires
every skill to name its authoritative file and requires `work`, `dispatch` and `tasks` to name
each other, so AS3's trigger is a property this repository's always-loaded rules mandate: it fires
on every future skill diff and can never be right here. There is no peer-skill trust boundary to
protect — 1 operator, 1 repository, and skills authored by dispatched agents and merged by hand.

**What decided it against *"attachment-only noise costs nothing"*, which is the honest objection
and is why `tasks/117` existed at all.** The attachment carries a remediation — *"Remove all code
or instructions that list or read other skills' files or directories"* — inside a block headed
*"Prompt for AI Agents"* telling the reader to verify each finding and fix the still-valid ones.
An agent working `.agents/skills/work/SKILL.md`'s review loop has to re-derive on every skill pull
request that this particular finding contradicts `AGENTS.md`. That is the cost `AGENTS.md` names:
*a check that fires where nothing is wrong spends exactly the attention that a check firing
correctly needs.* The schema offers `enabled` and no per-rule switch, so it is all or nothing.

**`markdownlint` and `languagetool` stay enabled, and the guess against them is still a guess.**
Over the same 3 rounds `markdownlint` produced **0** findings and `languagetool` produced **1** —
`[locale-violation] AFTERWARDS_US` on `dispatch/SKILL.md` line 134, preferring American
*afterward* — which never became a review comment. 1 of 1 is a rate over n=1, and unlike the 2
SkillSpector rules it is not wrong by construction: the same tool can find a real typo.

**A `path_instruction` was aimed at an address that no longer exists, and nothing could see it.**
`.coderabbit.yaml` scoped its skill rule to `.claude/skills/**/SKILL.md`, and PR #2's *"Keep
status facts in the authoritative document"* comment names `Path instructions` as its source — so
the rule had fired and was working. Task 114 then made `.agents/skills/` the single real copy and
left `.claude/skills` a symlink, which git tracks as **1** mode-120000 blob: the pattern went from
matching the skills to matching **0** tracked files, and the rule stopped existing silently. This
is `AGENTS.md` rule 12 — the address is an input to the check — so it is now asserted in code
rather than promised in a comment. `python3 eval/tools/coderabbit_config.py` reds any path
instruction covering 0 tracked files, **and on a config with no path instructions at all** — the
`total=0 passed=0` case, which it returned success on until PR #4's review caught it. `--control`
is **5** pins: green on the shipped config over its 8 instructions, and red on 4 mutants — 3
renames each killing a different address, plus the emptied block. `path_filters` is out of scope:
an *exclusion* matching nothing is a guard held against a future state, and `!eval/runs/**` is one
on purpose.

**What the first review actually did, on PR #1, 2026-08-23 — because a configuration that has
never caused a review is a mechanism that runs and measures nothing.** It posted 1 actionable
comment across a 2-file diff, and the comment was a **true positive against this repository's own
rules, not against a style guide**: the section you are reading spelled its counts as *single*,
*one*, *three* and *six*, and `AGENTS.md` requires a count in a live document to be written in
digits, because no check can read a cardinal spelled in words — the failure that let a stale
findings figure survive 11 days. The reviewer derived that rule from `DECISIONS.md` through
`code_guidelines.filePatterns` and cited it as its source. The counts are now digits.

**The boundary applied when fixing it, because the rule does not state one:** digits wherever the
number is a quantity of something in this repository that could change; words where the word is an
indefinite article or a compound modifier naming no population — *a one-task branch* stays.

`profile: chill` produced no prose comments on the markdown files, which is weak evidence against
the guess that `markdownlint` and `languagetool` need disabling, and not enough to act on.
`review_details: true` worked as intended: each review listed which path instructions and which
learnings it used, so what the reviewer consumed is on the record.

**Over 3 rounds on PR #1 the reviewer posted 2 actionable comments, both true positives, and 0
false positives — and the 2 came through the 2 different mechanisms configured here.** The first
was sourced from `Coding guidelines`, i.e. `code_guidelines.filePatterns`, and applied the digits
rule. The second was sourced from `Path instructions` and applied the `**/*.md` rule — *comment
only when a document states something FALSE* — to catch `README.md` saying `.coderabbit.yaml`
"drops the archives" when `tasks/` is an archive this config deliberately keeps reviewable. A
reviewer with the default configuration would have had neither rule available.

**The rate limit is a real constraint on a parallel queue and belongs in `tasks/109`:** the plan
allows **10 included reviews per hour**, and each review round reports what is left. Across 3
rounds on this 1 pull request the counter read **9, then 8, then 6** — so 4 of the hour's 10 went
on 1 PR, and the third round consumed 2. **The cost is per review round, not per pull request,
and it is not 1 per push**; anything that assumes a fixed rate should read the counter instead.

> **That counter is not a durable artifact, and `tasks/109` had to stop depending on it.**
> Re-read from PR #1's stored reviews and issue comments on 2026-08-23, the text is no longer
> anywhere in either — CodeRabbit edits its summary comment in place, so what was true when it
> was read is unrecoverable afterwards. The measurement above stands as what was observed; the
> procedure bounds **review rounds per task at 2** rather than reading a counter it cannot rely
> on finding.

---

## An agent hands back a pull request, and the queue has 5 statuses — decided 2026-08-23

**The operator's specification:** *"agents should pick up tasks, then submit PRs, then trigger
code rabbit reviews, then address whatever coderabbit recommends, then submit it as ready to be
merged for you to verify and merge"*, with the ticket moving through *todo, in progress, in
review, in testing, done*.

Before this, an agent committed to a `task-<id>-<slug>` branch and the orchestrator merged it
with `git merge --no-ff`. No pull request was opened and nothing external read the diff.

| Decided | Rejected, and why |
|---|---|
| `STATUSES = ("todo", "in_progress", "in_review", "in_testing", "done")` | Keeping `open`/`in_flight` as the stored names and adding only the 2 new states. It costs no migration, and it leaves the tool's vocabulary permanently disagreeing with the operator's, so every document carries a translation table — the shape this project calls a rule that must be re-derived by each reader |
| **`open` and `in_flight` are accepted permanently and map on read**, not for a migration window | A clean cutover. The queue is shared across worktrees while each worktree holds its own possibly-older `tasks.py`: an agent forked before the rename runs `start`, writes `in_flight`, and every peer's `check` goes red at once on a file none of them touched |
| `check` **fails** an `in_review` ticket with no `pr` field | Leaving the link to the report. The state exists so the orchestrator can find the pull request from the ticket; without the field it is a status that has stopped being a locator |
| The heartbeat's metric **keys keep the old names** (`tasks_open`, `tasks_inflight`) while the statuses are renamed | Renaming the keys with the statuses. The heartbeat's output is read as a diff against the previous hour, and a renamed key is one series ending at 0 and another starting from nothing — 12 tasks' worth of apparent movement in an hour where nothing happened |
| Merging through `gh pr merge`, not `git merge --no-ff` | A local merge. The pull request is the durable record of what was reviewed and what was declined; a local merge closes it by inference |
| The reviewer's comments are **weighed against `AGENTS.md` and `DECISIONS.md`, and declined in the thread when they contradict one** | Applying every suggestion. An agent that complies by default will eventually loosen a test, which the global instructions forbid outright |

**The verification standard does not move.** `dispatch/SKILL.md` says *verify against the
artifacts, not against the report*, and a review is a second opinion on the code with no access
to the artifacts. *"It passed review"* is exactly the shape this project calls a mechanism that
runs and reports success.

**How an agent knows a review has finished**, and this is the part that was measured rather than
designed: **a landed review has 2 shapes, and reading only 1 of them times out on the good
outcome.** The address is always the full 40-character head sha from `gh pr view --json
headRefOid` — `tasks/108`'s poll loop compared a **7-character** sha against the **5-character**
abbreviation in the walkthrough prose and reported *"not reviewed"* through 8 polls after the
review had landed, rule 12 against a poll loop when the API had the exact address all along. But
comparing it against the reviews API's `commit_id` is only half the check: **when CodeRabbit finds
nothing actionable it creates no review object at all** and edits its summary issue comment
instead. So the check is a disjunction — a `coderabbitai[bot]` review object **with a non-empty
body** at the head sha, **or** a `coderabbitai[bot]` issue comment naming the head sha that does not
carry the *review in progress* marker — and it reports **which arm fired**. This entry is what
the check has to satisfy; **`eval/tools/pr_review_state.py` is the check**, and
`.agents/skills/work/SKILL.md` invokes it.

**A review object is not the same thing as a review.** When `coderabbitai[bot]` replies to a
comment, GitHub creates a review object to hold the reply and stamps it with the pull request's
**current head**: empty body, 1 reply, no top-level comments. So the review arm reads
`select(.body != "")`. Without it, declining 3 of a round's comments made the poll report `LANDED`
33 seconds after the next push, on a round that had not started.

The body separates the two cleanly. Counted 2026-08-23 over every pull request this repository has
had — **23** `coderabbitai[bot]` review objects, **15** real with bodies of 2829-18578 characters
and **8** reply containers whose body length is **0**, with no overlap:

```bash
ALL=""; for PR in $(gh pr list --repo "$REPO" --state all --limit 100 --json number --jq '.[].number'); do
  P=$(gh api --paginate "repos/$REPO/pulls/$PR/reviews") || exit 1; ALL="$ALL$P"; done
jq -s '[.[][] | select(.user.login=="coderabbitai[bot]")]
       | {objects: length, real: ([.[]|select(.body != "")]|length),
          containers: ([.[]|select(.body == "")]|length),
          real_body_min: ([.[]|select(.body != "")|(.body|length)]|min),
          container_bodies: ([.[]|select(.body == "")|(.body|length)]|unique)}' <<<"$ALL"
```

**The count grows with every review, so re-run it rather than quoting this line.** The first two
times it was stated here it was wrong in both directions — counted by eye off a printed table
rather than by the command, at `16 real, 6 containers` against a true `14, 8`. That is this file's
own rule about quantities, failing on the session that was writing it down.

**Neither arm alone covers this repository's own pull requests.** Both arms against every PR at its
head sha, 2026-08-23 (`tasks/121`):

| PR | real review object at head | comment names head, not in progress | fires |
|---|---|---|---|
| #1 | yes, 3 objects | **no** — its body carries only `4f95b`, and no 40-character sha at all | review |
| #2 | yes | — | review |
| #3 | **no** | **no** | **neither, correctly** — 2 commits were pushed after the last review at 16:25:14Z and never reviewed |
| #4 | **no** — its only object at head is a reply container | yes | comment |
| #5 | **no**, 0 review objects | yes | comment |
| #6 | **no**, 2 objects and neither at head | yes | comment |

The version that read only the review arm returned `false` on #5 and #6 — 2 of the 5 heads that had
in fact been reviewed — and would have spent its full deadline on each, on the *clean*
outcome, which is the common one. It also returned `true` on #4, where no review of that head
exists; the comment arm is what makes that verdict true.

| Rejected | Why |
|---|---|
| *"the summary comment names the head sha"* on its own | **Fail-open, and it fired on first use** — it reported `LANDED` 31 seconds after a push, mid-review, because CodeRabbit writes the head sha into the comment while the round runs and the *"No actionable comments"* line below it is still the previous round's verdict. Measured again live on PR #7: while its round ran, the sha-only arm read **1** and the shipped arm **0**, for 317 seconds |
| Dropping the 40-character guard now that a 2nd arm exists | `contains("")` is true for every string, so an empty head would report every pull request reviewed. The reviews arm failed *closed* on the same input; adding the comment arm made that guard protect against a fail-open defect rather than a slow one |
| Reading page 1 only, as the original did | `gh api` returns 30 records without `--paginate`, and the review at the head sha is the newest — the first to fall off. PR #6's reviews at `per_page=2`: 2 records unpaginated, 10 paginated |
| `gh api --paginate --slurp --jq` | `gh` rejects `--slurp` alongside `--jq`. The pages are aggregated by an external `jq -s` over a here-string rather than a pipe, because a pipeline's exit status is the last stage's |
| Counting any `coderabbitai[bot]` review object, as the original did | A reply creates one, stamped with the current head. **The agent trips this by following §6 of the skill, which tells it to reply to what it declines** — the same shape as the comment arm's `select(.user.login...)`, which the agent tripped by quoting the string it was matching |
| Reading the deadlock notices through the same check | *Reviews paused* and *Review limit reached* carry **0** 40-character shas between them — which is why they cannot trip the comment arm, and why they still need their own heading extractor |

**The deadlock to design against is the reviewer's auto-pause**, not a slow review. CodeRabbit
pauses a branch it considers under active development, and the notice lands in the PR's *issue*
comments rather than in its reviews — so an agent that pushes a fix per comment can wait forever
for a review that will never come because it was too productive. The procedure batches fixes into
one push per round, detects the pause by its own text, and resumes with `@coderabbitai review`.

| Would re-open this | The observation |
|---|---|
| The 5-value vocabulary | An orchestrator finding it still cannot tell whose turn it is, or a state that no ticket ever occupies for more than a moment. `in_review` and `in_testing` are cheap to retire; `todo`/`in_progress` are not |
| The legacy aliases | Nothing. They cost one dict and they close a class of failure that is invisible until it hits every agent at once |
| The bound on the wait | A round that finishes having never been observed in flight, or one still in flight past an hour. Both are evidence about the reviewer, and neither is fixed by a larger constant |
| Merging through `gh pr merge` | A conflict pattern the PR route makes worse than the local one. Conflicts already resolve locally on the branch and then merge through the PR |

**The flow was run end to end on its own ticket: PR #2**, the first pull request opened by the
procedure it adds. Round 1 posted **8 actionable comments; 7 were acted on and 1 was declined
with a measurement** — the declined one asserted that new `E702` lines make `ruff check` fail,
where 4 lines of that shape already stood at the merge base and no ruff configuration or gate
exists in the tree. Two of the 7 were defects in this project's own terms: an empty `$HEAD` after
a failed `gh pr view` makes the poll answer `false` about a question it never asked (jq's
`index("")` is `null`, measured), and `in_testing` was gated for a `pr` in neither the code nor
the prose while being the state the orchestrator merges from.

**Review time scales with the diff, and no constant was enough to size the wait.** PR #1: 2
files, acknowledged 31s, reviewed **2m 30s**. PR #2: 17 files and 615 insertions, acknowledged
49s, reviewed **6m 15s**. A 15-minute bound was set at 2.4x the slower of those. Task 130's agent
then polled PR #15 **29 times**, reported no review and handed the work back as ready; the review
was submitted at **19m26s** on a 4-file documentation diff, carrying four threads and one Major
naming a real rule-4 violation, and `required_conversation_resolution` on `main` is the only
reason it did not merge unreviewed on a green tick.

**So the wait is bounded on SILENCE, not on elapsed time.** The in-progress marker is an
observable signal that a round is running — it was present throughout that 19m26s — so
`pr_review_state.py --wait` allows **20 minutes** while no round has ever been seen in flight and
**60 minutes** once one has, and the observation **latches** because CodeRabbit rewrites the
summary comment mid-round. Expiry is `UNRESOLVED` at exit 13, which is a result to hand back
rather than a silence to mistake for one.

| Rejected | Why |
|---|---|
| Raising the constant | The same defect at a larger value. A bound derived from a handful of observations cannot distinguish *not finished* from *never coming*, which is the question the agent actually has |
| Recomputing the bound from the latest poll | The marker comes and goes while the round runs, so a non-latching bound expires at the quiet timeout mid-round. `latch_not_sticky` pins it |
| A quiet timeout long enough to cover a slow review | It is the deadlock detector. Making it generous makes the *paused* and *limit reached* cases slow instead of the slow case fast |

---

## The review poll is a tool that asserts its own address — decided 2026-08-24

**Decided [agent], `tasks/127`, on measurement.** The poll above was a shell recipe agents copied
into a scratchpad file. It hardcoded `PR=<n>` and printed only a head sha, so **the pull request
it was polling appeared in no line of its output.** On 2026-08-23 two concurrent agents wrote
their copies to the same generic path; the first loop silently began polling the second's pull
request and reported `not yet` at exit 0 for 16 polls. Had that review landed it would have
reported `LANDED`, and the next step in the procedure is to read the review and act on it.

Re-measured 2026-08-24, the retired recipe answers `LANDED by review object at <sha>` at exit 0
for **both** PR #9 and PR #10, with nothing in either line distinguishing them.
`pr_review_state.py --pr 10 --branch task-123-cost-result-producer` answers `WRONG PR: #10 is on
branch 'task-124-ci-path-filter-and-minutes'` at exit 1, and the same command against #9 answers
`LANDED_REVIEW`.

| Decided | Rejected, and why |
|---|---|
| A **tool** taking the address as an argument | A better-named scratchpad file. The failure is not a bad name — it is the interval between writing an address down and using it, and a name does not shorten it |
| **Assert** the branch, *and* print the pull request, branch and full head sha on every line | Printing alone, which `tasks/127` offered as the alternative. An assertion fails closed at the moment of use; a printed line is only as good as the reader who looks at it, and the consumer of this verdict is the next step of a procedure. Printing stays as the audit trail |
| Exact equality on `headRefName` | Containment. `task-12` is a prefix of `task-127-…`, and task ids here collide that way by construction |
| `--expect-head`, refusing to poll until `headRefOid` agrees | A `sleep` after `git push`. #165: `gh pr view` returns the previous head for seconds after a push, and a sleep makes that race less likely while leaving it fail-open |
| `NOTICE` ranked **below** both landed arms | Treating a deadlock heading as authoritative. CodeRabbit edits comments in place: PR #6's `Review limit reached` was measured on 2026-08-23 and is no longer extractable, while PR #9 carries a stale `Reviews paused` beside the review it really has |

**The known-answer proof is the table above, and it was written before the tool existed.**
`python3 eval/tools/pr_review_state.py --census` prints which arm fires at every pull request's
head; run 2026-08-24 it agrees with all **6** rows of the per-pull-request table, including #3,
where both arms correctly read false. It returns **3** distinct verdicts over 17 pull requests —
6 `LANDED_REVIEW`, 6 `LANDED_COMMENT`, 5 `NOTICE` — so it is discriminating rather than
reporting the instrument.

`python3 eval/tools/pr_review_state.py --selftest` is **100** offline checks including **21**
variants; `python3 eval/tools/pr_review_state_mutants.py` removes **51** mechanisms one at a time
and every one goes red. The selftest reports the checks and the variants, the mutant tool
reports the mechanisms, and all 3 are `len()` of what ran — run them rather than quoting this
line.

**The same question was asked of every other recipe in `.agents/skills/` that writes a file it
later reads back.** Only one other had the shared-mutable-address shape:
`audit-docs/SKILL.md`'s planted-phantom control backed up `judge/JUDGING.md` to a fixed name in
the system temp directory and restored **into the repository** from it — so two audit passes at
once restore each other's copy, and one may still carry a planted phantom. It now uses `mktemp`,
which cannot collide. The rest are safe for a reason worth naming: `git commit -F`,
`git merge --no-ff -F` and `gh pr create --body-file` all write a file whose **only reader is the
next command in the same block**, and each is already followed by a read-back of what the command
actually stored. A short interval with a verification at the end of it is not the same defect as
an interval with none.

---

## A failed review round is a verdict of its own, and `--ignore-notice` governs stopping only — decided 2026-08-26

**Decided [agent], `tasks/165`, on measurement.** A round that starts and dies leaves a `Review
failed` alert callout and a rewritten summary comment. That summary carries no in-progress marker
and the failure block **writes the new head sha into its own body**, so the pair satisfies the
comment arm exactly and a dead round is indistinguishable from a clean one (#185). The procedure's
next step is to act on the review, so the branch proceeds as though it had been read.

**The flag named the mechanism, not the property.** `--ignore-notice` exists so a pool-exhaustion
pause cannot stop every poll instantly, and that reasoning stands. It also covered a notice with
the opposite meaning, because what it tested was *is there a notice* rather than *was this head
reviewed* — this file's own rule about triggers, inside the tool written to fix the previous
instance of it.

| Decided | Rejected, and why |
|---|---|
| `REVIEW_FAILED`, a **verdict** at exit 14, ranked above the comment arm | A kind of `NOTICE`. A notice is a diagnostic the landed arms outrank; this one has to *outrank* a landing, which is the opposite precedence |
| Ranked **below** `LANDED_REVIEW` and `IN_FLIGHT` | Ranking it first. A review object at the head means the head was reviewed whatever callout is beside it, and CodeRabbit edits comments in place; a marker at the head means the replacement round is already running, so the wait should wait rather than ask again |
| `--ignore-notice` decides **stopping** and nothing else — it can never produce a landing | Removing the flag, or adding a second one for this heading. Removing it trades a false landing for a poll that never returns; a second flag repeats the defect at a new name |
| A failed round is detected by its HTML marker **or** its alert heading — 2 signals, for the same reason a landing is read 2 ways: either alone can be wrong later | Either alone. A reworded heading and a renamed marker are both plausible, and each arm covers the other's failure |
| **Each failure block is dated by the last sha in it** — *"the head commit changed during the review from `<old>` to `<new>`"* — and a comment suppresses the comment arm when any of its blocks is about the head | Reading every failure on the pull request: a **previous** round's callout then suppresses a landing that really happened. Or scoping to the comment carrying the head: a failure posted in a comment of its own then reads as a clean landing, which is the defect itself. The block says which head it died on, so neither trade-off has to be made. It must come from the BLOCK — CodeRabbit writes the failure into the same summary comment that names the current head elsewhere |
| **A block naming no sha counts**, because it cannot be dated | Dropping it. That is fail-open exactly where the evidence is missing; the cost of keeping it is a wait that expires loudly (rule 7) |
| **The ambiguous case stays a landing**: no notice, a summary naming the head, no review object is `LANDED_COMMENT` | Requiring a review object. A clean round creates none, and the table above counts 3 of 6 reviewed heads reaching only that arm — the requirement would spend the full bound on the common good outcome |

**So the comment arm keeps its authority and is narrowed by exclusion, one observed mechanism at
a time**: not a landing while the in-progress marker is on it, and not a landing while a failure
callout is on the pull request. That decision is written beside `--ignore-notice` in
`pr_review_state.py`, which is where the next reader will be standing.

**The extraction is pinned against the real artifact, not against a fixture describing it.**
`pr_review_state.selftest` holds a verbatim `coderabbitai[bot]` failure block and classifies it at
the head that block names; `tasks/165` records where those bytes were read from and what a live
reconstruction did and did not show.

> **When one artifact serves two states, the repair is an exclusion, never a flag.** Every hole
> found in this poll has been the same shape — an artifact that exists for more than one reason,
> read as though it existed for one: a sha with no run (#162), a head the API had not caught up
> to (#165), a paused pool that reads as silence, and a failed round that reads as a clean one.

| Would re-open this | The observation |
|---|---|
| Dating a failure by its own block | A failure block naming a sha that is not the head it died on, so a real failure goes unseen at the head it belongs to. A block with no sha cannot go unseen — undated blocks count |
| `--ignore-notice` covering the failure for stopping | A round that dies twice in a row, where the second failure is invisible because the flag carried the wait past it. The remedy is `@coderabbitai review` **once**, and the poll after it is the flagged one |

---

## A closed ticket is checked against the tree, and "no branch" is a third value — decided 2026-08-23, second test added 2026-08-24

> **This entry's reversal condition has fired: the repository is squash-only.** Ancestry alone
> reads `ORPHANED` for every merged ticket whose ref survives, so a second test sits beside it.
> Ancestry stays, because it is still the whole answer for the `git merge --no-ff` refs already
> stored.

**Decided [agent], on measurement, after task 70 sat at `done` over 678 insertions across 5 files
that `main` had never seen** — including `eval/judge/paired_verdicts.py` at 458 lines, which
existed nowhere else. The exposure was **4h 39m**, `bd2014c` at 09:37:02 to `5476723` at 14:16:06
on 2026-08-23, and it ended because a person clearing stale worktrees happened to look. Nothing
compared a closed ticket against the tree, and the failure is invisible from either side on its
own: the queue says merged, and the tree disagrees by silence.

`tasks.py check` now reads, for every `done` ticket, whether any `task-<id>-*` ref has reached
the tree. `landed_status` returns **three values**:

| verdict | means | `check` |
|---|---|---|
| `LANDED` | a `task-<id>-*` ref has landed — its tip is an ancestor of the base, **or** its change is already on the base | counted |
| `ORPHANED` | such a ref exists and none of them has landed by either test | **exit 1**, naming the ref |
| `NOT_CHECKED` | no such ref survives, **or git could not answer** | counted and printed, **never a pass** |

**Two tests, because the repository has used two merge flows and refs from both survive.**
`_is_landed` asks `_is_ancestor` first, which is the whole answer under `git merge --no-ff`, and
then `_squash_landed`, which is the whole answer under `gh pr merge --squash`: a squash writes a
commit with one parent and a tree of its own, so **the tip it landed is not an ancestor of it**,
and nothing a later squash does changes that. `_squash_landed` renders `merge-base..ref` as one
diff and asks whether its
`git patch-id` is among the patch-ids of the commits the base gained since — which is the same
question ancestry was standing in for, asked about the change rather than about the commit.

Every arm is three-valued and for one reason: **a git failure is not a "no".** `merge-base
--is-ancestor` uses exit 0 and 1 for the answer and everything else for a failure; collapsing 128
into "not an ancestor" would make `check` exit 1 naming a ticket whose ancestry it never
established — rule 2, a state inferred from something that is not a report of it. `_squash_landed`
degrades the same way, and `_is_landed` lets an unanswered arm outrank a `False`.

| Decided | Rejected, and why |
|---|---|
| Three values | Two. A merged branch is normally deleted, so a two-valued check would report **112 of the 119** closed tickets as verified while verifying nothing — rule 1's `total=0 passed=0` with a plausible denominator |
| The trigger is *a `done` ticket whose branch has neither landed as a commit nor as a change* | Anything keyed on the ticket's `pr` field, or on merge-commit messages. Both are open classes of text; a ref name, an ancestry test and a patch-id are closed. `gh pr view <n> --json mergeCommit` names the squash commit directly and was rejected on top of that: it needs the network and an authenticated `gh`, and `check` runs in a git hook and in CI, where an unavailable answer would become a third population of NOT_CHECKED with nothing to distinguish it from a clean queue |
| `main`, `origin/main`, **and the invoking checkout's `HEAD`**, any of which counts | `main` alone. It makes the gate unfixable from the branch that fixes it: the agent landing an orphan cannot turn its own `check` green before the orchestrator merges, and a gate that stays red through correct work gets bypassed as a habit. In the main checkout and in CI all three are the same commit, so the condition is unchanged exactly where it is enforced |
| The caller's `HEAD` is taken from **both the process's working directory and the file's own checkout**, de-duplicated **by SHA**, and **each is required to exist in the repository the ancestry query runs against** | Any single address. A bare `HEAD` asked at `TASKS` is `main` under another name — two bases printed where there is one (rules 9 and 12). `ROOT` alone is worse: it comes from `__file__`, and the work skill tells an agent to run the **main** copy of the tool, under which its own branch is never consulted and the orphan it just landed cannot be cleared. The existence check is not defensive tidiness — without it a SHA from an unrelated checkout becomes a base, every `merge-base` exits 128, and the three-valued reader turns **the whole gate silent**, which reads as a clean queue. `tasks_control`'s own caller-HEAD row caught that |
| It **fails** rather than warns | A warning. The false-positive count is 0, and the one true positive is a published tool that existed on no branch anyone would look at |

**Measured on the live queue before it shipped**, 2026-08-23, `python3 eval/tools/tasks.py check`
over 121 tickets: **119 `done` — 6 LANDED, 1 ORPHANED, 112 NOT_CHECKED. 0 false positives, 1 true
positive**, and the true positive is task 70. **That population moves within the hour** — a peer
closing a ticket took it to 120 `done` / 8 LANDED before this was merged — which is why the census
is printed on every run rather than pinned anywhere. Measuring first is not a formality here: the
obvious widening of the census trigger turned **27 correct lines red with no true positive among
them** (#140), and the flag gate's was **8 false positives against 0 true** (#142). Both of those
triggers were open classes of English; a ref name and an ancestry test are not.

**What it cannot see, stated so nobody reads more into a green than is there.** It asks
*arrival*, not *survival*: a branch merged `-s ours`, or one whose changes a later commit
reverted, reads `LANDED` with its work absent from the tree today. That is rule 15's variant half
and the failure message says *read the branch diff* rather than *merge it*. The known false
**negative** is a squash whose diff differs from the branch's own — the base moved under a file
the branch also edited, and the merge resolved the overlap — which reads `ORPHANED` with its work
present. That direction costs attention rather than evidence, which is the side of rule 7 to be
on.

> **A verdict is relative to the refs the caller can see, and CI can see fewer — measured, not
> supposed.** On the same commit on the same day, the operator's checkout read **7 LANDED / 112
> NOT_CHECKED** and CI run `32656195661` read **6 LANDED / 113 NOT_CHECKED**, because task 70's
> branch was never pushed. **The defect this gate exists to catch reads `NOT_CHECKED` in CI** —
> correctly, since from there the ref does not exist. The load-bearing instance is therefore the
> **git hook in the checkout that holds the branches**; CI is a weaker copy, not a second
> opinion, and a green CI run does not cover this. The same run also showed `main` failing to
> resolve there and `origin/main` carrying it, which is what that fallback is for.

Pinned in both directions by `tasks_control.py` directions 11 and 11c — predicate rows including
the `task-7-` / `task-70-` prefix variants in both directions and the three-valued arms, plus
end-to-end rows on real scratch repositories, one of which runs the tool with its cwd in a
worktree the file does not live in. **Direction 11c performs a real `merge --squash`** over 4
refs, because the defect has two faces and each needs both directions: a **local** branch and a
**remote-tracking** ref, each squash-merged and each genuinely unmerged. Only the remote face
heals on `fetch --prune`; the local one survives until somebody deletes it by hand, so a fixture
carrying one face proves less than it looks. The control goes 79 rows to 111.

**The base range is rendered once per `(base_sha, rev)`, not once per ref.** Measured
2026-08-24 over 12 orphaned refs on a 60-commit range: `check` is 288ms with ancestry alone,
1070ms with the squash arm, and 720ms once the pair is cached — and unchanged at 1037ms when
the refs fork from different commits, which is the measurement that says the cache is doing
what it claims and nothing else. **A git failure is never cached**: a stored `None` would turn
one transient error into every later ref's verdict, which is rule 7's fail-open channel.

**And one row says something about this repository, not only about a fixture built to agree with
it:** `399280e`, a real squash merge on `main`, has exactly **one** parent — which is why the tip
it landed is not an ancestor of it — and it is on `main`, so any clone with the history has it.
A shallow one does not, and the row says NOT CHECKED there rather than passing.

**The deleted tip is opt-in, and the reason is this ticket's own defect one level up.**
`--live-squash-refs` adds 4 rows against PR #16's actual objects: `58df942` is an ancestor of
nothing, its change is on `main`, and `_is_landed` therefore reads `LANDED` — measured 2026-08-24,
115 rows, 0 failed. `delete_branch_on_merge` removed that branch, so no clone that did not perform
the merge can fetch the tip, and an unconditional row would report NOT CHECKED — **exit 3** — on
every machine but one. A gate red for a reason unrelated to the change in front of it is the thing
that got this defect ignored in the first place.

14 mutants in `tasks_mutants.py` cover it: excusing an orphan, accusing a deleted branch,
computing the census without printing it, de-duplicating the bases by name, reading a git error as
"not an ancestor", asking the caller's HEAD only at the file's address, accepting a base from a
foreign repository, never asking the squash arm, claiming every ref has landed, reading a git
error in the squash arm as a clean "no", swallowing the third value in the composition, reading
`patch-id`'s commit-id column instead of its patch-id column, dropping `rev` from the cache key,
and caching a failure.

3 constraints on the rows and the `kills` lists, each of which a mutant walked through
before it held:

- **Every arm is called at its own address, not only through its consumer.** A row handing
  `landed_status` a lambda never runs `_is_ancestor`, so the error-branch mutant is invisible to
  it — the `tasks/106` shape. The producer rows run against a real repository where a missing
  ref exits 128.
- **A `kills` entry must name a row the mutant can reach.** Where two arms degrade the same way
  — for a ref git cannot resolve, both return `None` — a mutation of one is invisible one level
  up, so the composition carries its own mutant rather than borrowing the arms'.
- **A variant that moves two things at once cannot say which one the check is reading**
  (rule 8, inside a control). The cache-key row advances `main`, holding the fork point fixed;
  comparing one fork point against two bases moves `merge-base` as well, and both halves of the
  key change together.

| Would re-open this | The observation |
|---|---|
| The three-valued shape | `NOT_CHECKED` falling to near zero, which would mean branches are being kept. Then the two-valued check is the stronger one |
| Failing rather than warning | A false positive on the live queue. The count is printed every run, so it is observable rather than remembered |
| Patch-id as the second test | A false `ORPHANED` on the live queue from a squash whose diff was rewritten by conflict resolution. The census is printed every run, so the count is observable rather than remembered |
| Reading merge state from refs at all | `delete_branch_on_merge` being turned off, which would leave every merged branch present and make ancestry-plus-content the routine path rather than the residue |

---

## An unreachable private method in `eval/judge/` is deleted, never exempted — decided 2026-08-23

`eval/tools/dead_private_control.py` is a gate over `eval/judge/`: 0 unreachable private methods
out of 118. The reason it is a gate rather than a report is #136 — a repair to
`PlatformerBot._approach`, which no tree that defined it ever called, produced a byte-identical
re-grade that was then read as evidence against the pit hypothesis for #82. The check goes red on
`9fc044a`, the commit that published #82.

Three choices inside it, each with the alternative that was measured and rejected:

| Decided | Rejected, and why |
|---|---|
| It lives in a `*_control.py`, not in `lint.py` | `lint.py` exits 0 with findings by deliberate decision (the row below), and its `--gate` flag has no caller. A check that must go red does not belong behind one that must not. The control shape also carries the red pin and the green pin in one run, which is what the task asked for |
| **Reachability** from roots outside any private method's body, not "is this name referenced anywhere" | #136's per-method census names a cluster's tip and calls the rest live. Measured on the real `ArenaBot` corner cluster at `03cdb90`: shallow names 1 of 3, reachability 3 of 3 |
| The two hits were **deleted**. No allowlist, no marker, no exemption of any kind | An allowlist is a fail-open channel (AGENTS.md rule 7) and it would have been the check's entire content on day one. `Bot._num` was an unused base-class helper with no reference anywhere in the repository. The corner cluster's docstring was the only record of a measured-and-discarded design, so **the measurement moved into `_chase`'s docstring** — which already archives two other discarded designs — before the code went. Evidence lands somewhere first; then the code goes |

The census population **includes `eval/judge/fixtures/`, which `lint.py` excludes.** Deliberate:
#136's published figure of 121 methods at `9fc044a` counts them, and direction 1b asserts against
that figure, so a narrower population would make the two numbers incomparable for nothing. The
fixtures contribute 0 dead methods in all three trees measured (`9fc044a`, `03cdb90`, HEAD), both
modes.

**What it gets wrong is pinned, not hidden.** A name assembled at runtime reads dead — fail-closed
noise, and no such site exists in `eval/judge/`. A method named only in another method's docstring
reads live — a genuine miss, and the price of the rule that keeps `getattr(self, "_step_once")`
alive. Both are variant rows, so widening the string handling cannot lose either silently.

---

## What the judge is told about the pack is a function of the pack, and both wordings are kept — decided 2026-08-23

**The question (task 104): the brief told every code judge the pack "may not contain every file
the author wrote" and the size budget that made that true was removed on 2026-08-22 (#69).
Correct the sentence, or delete it?**

**Neither on its own. The claim is now selected by the pack's state** —
`field.COMPLETENESS_NOTE[knowingly_truncated]`, read by both judge-facing texts. Deleting it was
the obvious repair and is wrong in the same way the original was: an unstated completeness leaves
a judge to decide for itself how much of a submission it is holding, and discounting absences is
what it does by default. Hard-coding "this pack is complete" is wrong too — `--allow-truncated`
still exists for the capped-vs-uncapped control, and a field built that way *is* incomplete.

**The general form, and it is why this is a decision rather than a bug fix: a claim with only one
possible value is not a claim, it is a decoration, and nothing can check it.** The constant
survived a mechanism's deletion precisely because no input could ever have made it read
differently. The same property put the opposite error in the pack skill, which asserted
completeness unconditionally — so a deliberately truncated field would have carried a skill and a
brief that contradicted each other.

**A pack with no recorded state is refused, not assumed complete.** `run_field` returns
`usable: false` when `knowingly_truncated` is absent from the mapping. Reading a missing key as
falsy would state completeness about a pack nothing on disk describes, which is #62's direction
(rule 7).

**Scope:** this licenses new rounds and repairs none. The 10 stored code rounds that recorded a
brief hash demonstrably read the stale sentence and cannot be re-run for it; `eval/RUNS.md`
records that, and the other 26 code rounds stored no hash and are unassessable.

---

## A ticket's body is appended to by `tasks.py note`, and a control never imports its expectation — decided 2026-08-23

`.claude/skills/work/SKILL.md` has told every dispatched agent to *write back what the next one
would otherwise re-derive* since the skill existed, and until now no agent could. Measured from a
real agent worktree (task 113): `Write`/`Edit` aimed at the shared checkout is **refused** by
worktree isolation; the worktree's own copy of `tasks/NNN-*.md` is a tracked file whose
main-checkout twin `start`/`done` rewrite, so a committed edit offers the merge a conflict in a
file the merge is already rewriting; and `tasks.py` had no subcommand that touched a body. Tasks
105 and 106 each emptied a session's findings into `established_by` — one unbroken line of YAML
prose that cannot carry a backtick (#80) and is not where the next agent looks.

**The decision is the subcommand, not a relaxation of the isolation.** The queue resolving to the
main checkout is #94's decision and stays; `note` writes there by the mechanism `add`, `start` and
`done` already use, and resolves the file **by id** rather than by a filename anyone typed —
which is the difference between it and the `>>` an agent would otherwise reach for, nothing
having ever blocked one. It appends through `open(p, "a")` and rewrites nothing, so *the rest of
the ticket is unchanged* is true by construction rather than by a round-trip that happened to
hold, and `-` reads the section from stdin because a backtick in argv is command substitution
before the program runs.

**The general rule this bought, and it is a refinement of AGENTS.md rule 12 rather than an
instance of it.** The first version of the control built its expected suffix by calling
`tasks.py`'s own `_note_block` — one value at one address, which is what rule 12 asks for, and
here it made the rows structurally incapable of failing: the mutant that deletes the newline
separating a section from the body came back **SURVIVED with 0 red rows of 48**, because the
mutant had edited the check. Rule 12 is about one **fact** at one address. **An expectation is
not the fact; it is the second, independent statement of it**, and a control that imports its
expectation from its subject is not a control. Where the two must be kept in step, do it with a
row that compares them — never by making them the same object.

---

## `-` means stdin in every `tasks.py` subcommand that takes durable text — decided 2026-08-23

`note` was given `-` because of #80: a backtick in an argv string is command substitution before
the program runs, so stdin is the only channel that carries one verbatim. `done` and `testing`
write a durable record from an argv string too and were given no such reading, so the obvious
call — `done 112 - < account.md` — stored the **literal one character `-`**, at exit 0, with no
warning, having also flipped the ticket to `done`. Reproduced on a scratch queue against
`dce1172` over a 2280-character account (task 120), and it is #80's shape with a sentinel where
the backtick was: a durable record silently emptied by a command that reports success.

**Two sibling commands disagreeing about one sentinel is the enumeration failure the rule audit
keeps recording** — the safe path was added where the problem had been *seen* rather than where
the property lives. The property is *an argument that becomes a durable record*, so `-` is read
once, in `_stdin_arg`, and `note`, `testing` and `done` all go through it.

**`established_by` stays one line, by refusal rather than by convention.** Reading stdin without
that would have re-opened tasks 105 and 106's workaround with nicer syntax — a whole account
inside YAML frontmatter, where the next agent does not look. So `cmd_evidence` refuses an empty
evidence string, refuses a multi-line one **naming `tasks.py note <id> -`**, and in both cases
writes *neither* the field nor the status: the pre-fix code closed the ticket while destroying
the record, and "it refused" and "it refused without closing the task" are different claims.

**What is deliberately not guarded: a `-` typed at a terminal still blocks on a read.** That
failure is loud — the agent sees it — and the one being closed here is the silent one. A guard
that cannot be pinned in both directions without a pty is dead weight by this project's own
standard.

`.agents/skills/tasks/SKILL.md` and `.agents/skills/work/SKILL.md` state the sentinel; direction
8 of `eval/tools/tasks_control.py` pins it, with `dce1172` as the positive control that must
still store the one-character record on the same harness.

---

## A finding cited in a live document is a reference-style link, gated by `linkcheck.py` — decided 2026-08-23

A bare `(#68)` is honest and useless: a reader who cannot click it has been told nothing. Making
it a link is not free, because **`docstat.py --sweep` does not check file paths** — a phantom
`eval/RUBRIC.md` passed a green sweep — so a link is a stronger claim than a number with no gate
behind it. **A link that resolves to the wrong place is worse than a bare number, because it looks
checked.**

Three shapes were available and the choice was made on what each fails at, not on which reads best:

| shape | why not |
|---|---|
| bare `(#68)` | unclickable; the objection that opened task 115 |
| inline `[#68](eval/findings/...#68-the-subjective-layers-first-...)` | a ~150-character URL inside every sentence, in a file whose stated defect was that it was hard to read |
| link to `eval/FINDINGS.md` with no fragment | always resolves and never lands on the finding. The index is a **table**, and GitHub generates no anchors for table rows, so there is nothing to aim at |

**Shipped: reference-style.** `[#68]` in the prose, and one definition block at the foot of the
file carrying the group file and the GitHub heading anchor. Prose stays as short as the bare form
and the machinery is in one place a checker can read.

**The fragment is the risk and `eval/tools/linkcheck.py` is the answer to it.** A reworded heading
kills an anchor silently. The tool derives the anchors from the target file's own headings rather
than assuming the rule, so a rewording turns a gate red instead of turning a link into a lie. It
checks inline links, reference definitions and `[#NN]` shortcuts with no definition, skips fenced
blocks and external schemes by design, and `--selftest` plants a known-good and a known-bad of
each of the three shapes — rule 12's corollary, prove the extraction on a case whose answer you
can state in advance. Both directions were exercised on `README.md` itself before the count over it
was believed: a phantom `eval/RUBRIC.md`, a truncated anchor and a dangling `[#999]` each went red.

**To re-open:** GitHub changing its heading-anchor rule, or a second consumer of these documents
that does not render Markdown links.

## No run is bounded by a money figure; token counts and time are measured, not capped — decided 2026-08-23

The account is a subscription. `agent.cost_usd` is a list-price valuation of token counts that the
CLI computes whatever the billing arrangement, so no dollar figure here is an expenditure (#159).

**Tokens and wall clock are kept and are the point.** They are how output is weighed against
resource used, and they are the only per-trial resource numbers the harness has. Nothing about
#159 makes them less worth recording — it makes the *unit* wrong, not the measurement.

**Nothing is bounded by them.** A ceiling denominated in a unit that does not bind cannot protect
what is scarce, and it truncates real evidence when it fires. Where the figure reaches the subject
it is worse than inert: `--max-budget-usd` is visible to a building agent and instructs it, proven
by three-way discrimination, and usage rose 1.54x when a stated ceiling moved 25 to 48. A capped
agent was told to conserve something that is not scarce and produced less for nothing.

| | |
|---|---|
| builds | `MAX_BUDGET_USD = None`, `--max-turns 1000`. Turns are invisible to the agent and truncate rather than instruct |
| judge sweeps | `--max-rounds` and `--max-wall-min`, both optional because every mode is finite by construction, and both written into the summary beside `stopped_by`. `--max-cost` is **retained as a named refusal** — it exits 2 naming its replacement rather than being deleted into argparse's generic "unrecognized arguments" — and it never fired: 0 of 12 stored summaries are short of their configuration. `--per-call-budget` still reaches each judge as `--max-budget-usd 12.0` and bounds nothing here: it is held at its stored value so new rounds stay comparable with the 97 on disk, and changing what the judge is told needs a pre-registration of its own |
| what may bound a run | turns, wall clock, rate-limit capacity — the things that are actually finite |

**The unit has a name and a producer.** Every `$n` in this project is **`tokval`** —
`sum(modelUsage[*].costUSD)`, the list price the tokens would carry at published API rates.
This covers the figures **this project generates**; a price quoted from outside — W4 Games'
console licence fees in `research/03-rust-engines.md` — is real money and is not `tokval`.
`eval/tools/tokenvalue.py` is the single definition; every producer formats through it, prints
the definition beside its output, and `--selftest` reads all 11 producer sources to assert none
of them prints a money sigil in any of the 3 forms Python can interpolate one. `python3 eval/tools/docstat.py --money` asks the same question of
the live documents, and runs inside `--sweep`. **Its red control is history rather than a
fixture:** `--money --at f598726`, the commit before the repair, reports **21** blocks; at `HEAD`
it reports **0**. Ten in-memory pins run alongside it, because a trigger returning 0 on a clean
corpus reads exactly like one that cannot fire.

**The gate's trigger is the NOUN, not the sigil, and the candidates were chosen on live-corpus
counts.** Requiring every `$` figure to be respelled would be a find-and-replace over
`eval/RUNS.md`'s 132 per-run rows — the ledger a reader compares runs by — and a `$` is not
always ours: `research/03-rust-engines.md` quotes W4 Games' published console pricing, which is
real money. So `--money` fires on a live block that states one of these figures **and** asserts
money moved, exempt when the block cites `#159`. Measured over 55 live documents on 2026-08-23,
before any repair:

| candidate | blocks hit | false positives |
|---|---|---|
| `cost`/`costs` | 39 | many — `cost` is an open class and mostly not about money |
| `price`/`priced` | 15 | reddens W4 Games' real console pricing |
| adding `pay`/`pays`/`paid` | +3 | **2** — *"it paid for itself"*, *"the numbers it paid for"* |
| **shipped**: `spend`/`charged`/`billed`/`expenditure`, no `pay` | **21** | **0** |

Dropping `pay` cost no true positive: its one real hit also carries `spent`. The exemption is an
**id**, never a marker word, for the reason the withdrawal register gives — a vocabulary is an
enumeration, and one has already failed here on a single inflection of one verb.

**What re-opens this:** moving to per-token billing, at which point the figures become real and a
ceiling becomes a real protection. Then the build-side reasoning still applies — a cap the agent
can see is an instruction, so it belongs outside the agent's view or not at all.

## The cost route is adjudicated and does not resolve, and a group is `(run, game)` — decided 2026-08-23

`README.md` carried the cost result with **no producer** — the last quantity in the file with no
way to re-derive it. Writing one (`eval/tools/cost_census.py`, task 123) reproduced every
published figure to the cent and disagreed with the sentence around them.

**What was published:** *"on the one measure taken on all four stacks at once, the between-stack
range is 42% of its own noise floor"*. **What the producer prints:** there are **7** such measures
in the stored tree, 42% is the **lowest** of them, they run **42% to 254%**, and the between-stack
range **exceeds** the within-cell floor in **5 of 7**. `#63` never claimed exclusivity — it says
*first* matrix, which was true — so this is a scope that was introduced when the finding was
summarised, and it is the shape `AGENTS.md` warns about: **a figure quoted correctly, about a
population nobody had counted.**

**So the cost route was re-opened, and re-deciding it bought no trials.** What survives is that usage is dominated by a
per-agent choice: turns vary by up to **165** inside one stack's cell. The **r = 0.65 to 0.97**
correlation with turns is **not** the evidence for that — it is arithmetic, because the figure is
computed from token counts and token counts scale with turns (#159). The correlation was the
measurement reported twice and correlated with itself. What does not survive is *"the between-stack range is small
against its floor"*, which was the half that reached the null.

### The ordering: TypeScript leads 5 of 7 and the stored tree cannot say whether that is real

`python3 eval/tools/cost_census.py --ordering` is the producer. **No reading of the stored
records settles the ordering**, and the reason is structural rather than marginal.

**The statistic** is an exact permutation test on the usage ranks, all 331,776 assignments
enumerated, with the **stack labels** permuted *within a cluster* and held constant across every
group in that cluster. The null is that
which stack got which of a group's four cells is arbitrary; rejecting it is the only sense in which
"the stacks are ordered" is a claim rather than a reading of a table. The leading stack was chosen
**post hoc**, because it looked lowest, so the statistic is *the smallest rank sum any of the four
stacks reaches* — the version that carries its own multiplicity. TypeScript's rank sum is **10**
against a null expectation of 17.5.

**The dependence structure is the whole result, and the unit is not obvious.** 3 units are
defensible and they do not agree:

| independent unit | n | p, post-hoc-safe | smallest p the design could return |
|---|---|---|---|
| **run directory** — one launch, one harness, one day | 4 | **0.0156** | **0.0156** |
| **game** — because games recur across runs | 4 | 0.0469 | 0.0156 |
| **connected component of run *and* game** | **2** | **0.25** | **0.25** |

**Two things make this unresolved rather than significant.**

1. **At the run unit the observed p IS the design's floor.** 0.0156 is `4 × (1/4)⁴`: TypeScript
   holds the cheapest column in all four runs, which is the most extreme outcome available. Any
   less-than-perfect ordering returns the next attainable value, which is above 0.05. **A test
   with exactly one rejecting outcome has no margin**, and dropping any single run puts the floor
   at 0.0625 — no subset of three runs could reach α whatever it said.
2. **The runs are not independent of each other.** 3 of the 4 games recur across runs, so a stack
   that is cheap on one game contributes the same evidence twice. Merging both channels leaves
   **6 of the 7 groups in a single connected component**, and there the smallest attainable p is
   **0.25**. At the honest unit the question is **not answered no — it is unasked.**

**And the lead is inside the noise.** Where TypeScript leads at all, its margin over the
runner-up is **14.9% to 93.7% of that group's own within-cell floor — above it in 0 of 5**. A
consistent ordering and a lead that beats the noise are different claims, and only the first was
ever on the table.

**So: suggestive, not established, and not a finding about the stacks.** The count of instruments
reaching the null in `README.md` does **not** change — this route reaches no null either, which is
what its row already says. `cost_usd` is a list-price valuation of tokens on a subscription
account (#159), so none of this is about money.

**What would settle it is now priced, and it is not a re-reading.** 4 qualifying groups sharing
**neither a run nor a game** put the design floor back at 0.0156 with independent clusters behind
it. The stored tree cannot be rearranged into that; it needs new runs on games that do not recur.

**The unit of the measurement is a `(run directory, game)` group**, and that is the load-bearing
choice. A floor is a property of a population: pooling across runs mixes budget-cap regimes
(`eval/RUNS.md`, #33) and pooling across games mixes tasks of different sizes. A group qualifies
only when every stack ran in it, with at least 2 trials per cell, under **one** `terminal_reason`.
A cell holding a single trial has **no gap** and is refused rather than contributing $0.00 — that
would deflate the floor and inflate the ratio, which is fail-open in the direction that
manufactures a difference.

**The mutant count is `python3 eval/tools/cost_census_mutants.py`, and it did not start that way.**
The sweep was first run from a scratchpad and the count published here by hand; CodeRabbit then
read the selftest's own comments and reported **11** against a published **14**, and neither number
was checkable, because the mutants died with the session. That is this section's own subject —
*a count with no producer goes stale forever* — committed inside the section. The suite is now
shipped, the count is `len(MUTANTS)`, and running it immediately found what the hand sweep had
hidden: **2 of the mutants were exiting non-zero via a traceback rather than reddening a named
check**, which a by-hand pass scores as "caught". The 3 **variants** stay inside
`cost_census.selftest` because a variant must *pass*.

**To re-open:** a matrix that lands 4 qualifying groups sharing neither a run nor a game with the
7, or a fifth stack — both of which change the cluster structure the adjudication turned on.


## The repository is public, `main` is protected, and merges are squashed — decided 2026-08-24

**Public.** The project is MIT and its output is evidence meant to be read. Making it public also
removed the two constraints the CI design had been bending around: branch protection is free on a
public repository, and Linux Actions minutes are unlimited. Scanned before flipping — 496
revisions, no credential-shaped strings, no blob over 5MB, nothing sensitive tracked;
`eval/runs/` was already gitignored and has never been in the history.

**Squash-only.** `allow_merge_commit` and `allow_rebase_merge` are off. A task branch lands as one
commit; its review rounds stay on the pull request where they were reviewed. PR #13 carried six
round commits plus a merge into `main`'s history for one change. The squashed commit takes its
subject from the pull request **title** and its message from the **body**, so the composed record
of what was established lives inside the reviewed artefact instead of being written locally at
merge time.

**Protected.** Required `gates` and `controls`; `strict`, so a branch behind `main` cannot merge;
`required_linear_history`; no force-pushes, no deletions; conversation resolution required.

**Requiring `controls` is right, and it composes with the filter only because the filter moved.**
It was path-filtered when the requirement was set, and a filtered workflow that does not match
produces no check rather than a passing one — so a pull request touching only `tasks/` or a root
document could never satisfy it. Found by the control that proved `strict` works (PR #14, closed);
repaired by task 131, which moved the filter into a step so the check always reports. The
derivation is in the CI section above.

`strict` is the one that was bought. On 2026-08-23 `main` went red on a merge where **both**
contributing pull requests were green, each tested against a base containing neither (#162). A
gate asking only *are the checks green* passes that, and did.

**`enforce_admins` is deliberately OFF, and it is the known hole.** Turning it on would require a
pull request for every change to `main`, including the queue commit the dispatch procedure pushes
directly — agents write status into the main checkout, so that path has to stay open. The
consequence is that an admin can push to `main` and can merge with `gh pr merge --admin`, and the
account that made the #162 mistake is an admin. `eval/tools/mergeable.py` is what covers that
path, and it is advisory by construction: a step someone has to run.

**What would re-open it:** if the queue commit stops needing a direct push — or if an admin
bypass ever lands a red `main` again — `enforce_admins` becomes the cheaper answer and the
dispatch procedure should change to suit it.

## The `g1_pong` round-1 judge figure is $13.16, mean $4.39, and cents round half-up — decided 2026-08-24

The 3 `g1_pong` field calls of 2026-08-16 are the only judge rounds here with **no surviving
artifact**. `python3 eval/judge/judge_ledger.py --tree eval/runs/` reads 97 rounds over 12
directories and none of them is this field, so the figure **cannot be re-read from any
currently surviving artifact** — task 04 re-ran `idiomatic` alone into
`wg-funframes-crossgame/pong/` and recovered the ranking, not these calls or their scores. It
was published 2 ways: **$13.16 / mean $4.39** in `eval/RUNS.md` and `eval/AGENTS.md`,
**$13.15 / mean $4.38** in `eval/judge/JUDGING.md` — which also stated $13.16 some 50 lines
further down the same file. The second pair is now withdrawn, `WR-g1pong-round1-13-15`.

**It was filed as a rounding disagreement and it is not one** (`WR-g1pong-round1-13-15`).
13.16 / 3 = 4.386667 and 13.15 / 3 = 4.383333, and half-up rounding takes those to 4.39 and 4.38
respectively, so each document was internally consistent and the 2 disagreed about the **sum**.
That distinction is what makes this decidable: a rounding convention is a preference, and a sum
is a claim with evidence behind it.

**$13.16 wins on the arithmetic of the table that prints it.** The `g2_tetris3d` rows of that
ledger sum to $33.63, which `judge_ledger.py` still re-derives to the cent from
`wg-tetris-judge-2026-08-17/pre/`, and the published day total is $46.79: 46.79 - 33.63 = 13.16
exactly, where $13.15 would require a total of $46.78. **This is coherence with a published
total, not a re-reading** — $46.79 has no artifact either — but only 1 of the 2 candidates
contradicts the table it was printed beside. The recorded per-call range $2.82-$5.29
discriminates neither: the third call is $5.05 under one and $5.04 under the other.

**This is not the move `eval/RUNS.md` refuses for the $118.62/$118.63 pair.** That pair is 2
readings of 2 different sources — trial records at full precision against a build log rounded
per line — and adjusting either would destroy a reading. Here there is 1 quantity, 1 spelling
closes the arithmetic of its own table, and the other closes nothing.

**Cents round half-up, never truncate**, stated once beside the figure in `eval/RUNS.md`'s
specialist-judge ledger.

**$13.16 is a historical aggregate and is not a planning basis, and the 2 uses are kept
separate.** As a record it stands: it is what 3 calls of `architecture` and `idiomatic` on
`g1_pong` consumed on 2026-08-16. As a rate it is barred by rule 4 — a mean over 2 aspects,
where per-aspect rates on `g2_tetris3d` span $0.60 to $6.81 a call. `judge_ledger.py` prints no
per-call mean for that reason, and the 1 projection made from this one came out 1.84x low. So
every live document that used to project from it now prices per (game, aspect) from
`eval/RUNS.md`'s ledger rows instead, and `eval/judge/JUDGING.md`'s 96-round figure became a
range, $58 to $653 for 1 game, rather than a single **~$420** that matched no aspect.

**Withdrawing the figure outright was the alternative and was rejected.** $13.16 is load-bearing
for the #121 correction — it is the part of $46.79 that is *not* the tetris field — so retiring
it would take the correction with it.

**The losing spelling is declared, not merely corrected.** `$13.15 / $4.38` is register entry
`WR-g1pong-round1-13-15`, so `docstat.py --withdrawn` now turns red if either reappears in a live
document outside a block citing that id. Before the entry existed the check was green with
`JUDGING.md` stating the retired pair, which is the point of the register: a stale figure agrees
with every copy of itself and no consistency check can see it (#113, #119).

**To re-open:** a `g1_pong` round file from 2026-08-16 turning up, which would make the figure
readable and could contradict either candidate; or the $46.79 day total being shown wrong, which
is the only ground this choice rests on.

## Scene prompts live in their own module, and the rubric trigger is a curated list — decided 2026-08-24

`eval/suites/scene_prompts.py` renders `s1_parallax` and `s2_glass` for all four stacks.
`eval/SCENES.md` is the design authority; that module renders it and nothing else.

**A separate module from `wholegame_prompts.py`, not a 5th and 6th entry in `TASKS`.** 2 reasons,
both mechanical. `wholegame.py` defaults `--games` to every key of `TASKS`, so a scene
added there would be launched by the standing matrix command against a probe that does not exist
yet. And a scene needs preamble text a game does not — no player, no controls, no sound, a fixed
run length — so under 1 shared preamble every scene edit would reach 4 game prompts, which is #41
with a different subject. The isolation is **measured, not asserted**: editing the scene
preamble moves 8 rendered prompts and no game; editing the game preamble moves 16 and no scene
(`eval/tools/prompt_guard_control.py`). The vocabulary dicts are **imported** rather than copied,
so 1 concept is still said in 4 languages in 1 place.

**The rubric check is a curated list of measurement vocabulary, chosen over a derived property on
the live false-positive count.** `eval/SCENES.md` states each scene criterion, and a prompt
repeating one teaches to the test. The obvious trigger — every content word of the criterion
columns — was built first: 85 words, **31 hits over the 24 rendered prompts, 0 of them a real
leak**, because `water`, `glass`, `layers`, `seed` and `tick` are the scene's own subject and its
capture contract. That is the census-trigger failure below, in a new place: an open class of
English words is an enumeration in disguise. What is closed here is the vocabulary of
**measurement** — terms naming how a thing will be checked — plus English bound expressions,
which is what a threshold is. Shipped, both lists are at **0** false positives on the 8 scene
prompts; `probe` came off the first list for hitting all 8 with no true positive, because it is
the name of a starter recipe every prompt must state.

**The check is addressed at SCENE prompts, and that is an address rather than a convenience.**
The same lists over the 16 rendered game prompts hit all 4 games with no true positive: a game
legitimately says `score`, and `at least three kinds of enemy` is `g3_arena`'s own rule. The
criteria in `eval/SCENES.md` grade scenes, so scene prompts are where the question is asked.
`variant-game-prompt-untouched` is the row that says so in code.

**2 anti-drift guards, because a list is the thing that rots.** Every term on the criterion
list must appear in `eval/SCENES.md` itself, asserted at run time against a copy with markdown
emphasis and line wrapping removed — so the list cannot drift into words the authority never
used, and a term that is only ever wrapped or emphasised there is not silently dropped from the
guard. And the rendered prompts are **checked in** at `eval/suites/rendered/`, with `gates.yml`
running `--diff` against them: none of the three assertions can see a shared-preamble edit,
because it leaves every rule identical across stacks and names no engine. A deliberate prompt
edit re-records the snapshot in the same commit.

**The list holds each withheld claim in its plain-English wording as well as its measurement
wording**, and the same 2 lists govern the scene statement a tier-3 judge is handed. `distinct
rates`, `declared depth` and `world-horizontal` are the criterion tables' words; `ordered by
depth` and `stays level` are how `eval/SCENES.md` says the same 2 claims when it says they are
withheld. Without the second pair the check reads **0 hits on all 8** with either claim planted
into a rendered prompt — green on a corpus carrying the leak it most exists to prevent. Both are
at **0** false positives on the 8 shipped prompts and on the 2 packed scene statements, and both
are in `eval/SCENES.md`, so the anti-invention guard accepts them. **That pair is 2 spellings and
not a property**, which is the repair this project distrusts (#30, #83, #131): a third phrasing
walks past. It stands because the list's own definition is *the vocabulary `eval/SCENES.md` uses
to state a criterion* and these 2 phrases are exactly that; the derived alternative is measured
and rejected above.

**To re-open:** a scene prompt that cannot be written without a term on either list — which would
mean the term is functional spec and belongs off it, the way `probe` did; a false positive on a
correct prompt, which is how a gate gets switched off; or a real leak that ships past both lists,
which would say the closed class was drawn too narrow.

## The scene probe reads telemetry and pixels, and an absent half is not an excused one — decided 2026-08-24

`eval/judge/scene_probe.py` is tier 2 for scenes: 8 criteria for `s1_parallax`, 7 for `s2_glass`,
every one binary, equally weighted and always reported. `eval/SCENES.md` is the design authority
and holds the per-criterion table; the decisions the implementation had to make are here.

**The seed pair is 1 criterion, not 2.** *Different seeds differ* alone is satisfied by anything
random, including a scene seeded from the wall clock; *same seed matches* alone is satisfied by a
canned animation. Splitting them would award half a mark to each of the 2 implementations the
criterion exists to reject. `scene_mutants.py` carries one mutant for each half — a scene that
ignores its seed, and one seeded from `time.time_ns()` — plus a canned fracture that satisfies
*different seeds differ* perfectly while the fragments never change.

**An absent image half and an unestablished experiment are different, and are scored
differently.** A `just film` that produced no frames, the wrong number of frames, or frames of
2 different sizes is a fact about the SUBMISSION: an image-only criterion goes red. A criterion
that also has a telemetry half is scored on it, because one broken recipe must deduct once rather
than once per criterion, and the fallback is recorded in the evidence. A run in which no captured
MOMENT satisfies a precondition — no frame inside the light ramp, no layer wrapping between two
frames, the glass never leaving its opening box — is an experiment that could not be set up, and
comes back `scored=False`, counted in `unscored`. Both directions are pinned: 2 mutants break the
capture (half the frames, and the geometry changing mid-run) and a variant ramps the light over 30
ticks so the image half genuinely cannot be established.

**`shatter.pieces_rest` does not read `table.y` as the ground plane.** The contract calls it *"the
height of the surface everything stands on"* while the scene has 2 surfaces — the glass stands on
a table and its fragments rest on what is below it — so a submission may reasonably report either
and a floor test on that field would fail correct work. The criterion asks instead what needs no
plane: a settled fragment must not go on descending, and the settled fragments must lie in a band
rather than being scattered through the world. `table.y` is used only for the SCALE,
`max |glass.y − table.y|`, which is what makes every distance tolerance a share of the drop.

**The image-side shift estimator was chosen on a measured hit rate, and its robustness lives in
the criteria rather than in the estimator.** 5 candidates, all over the same 88 frame pairs — the
reference and its nearest-first variant, which are the same scene with the seeded textures dealt
to different bands, 44 pairs each:

| candidate | reference | nearest-first | total |
|---|---|---|---|
| **SAD over normalised horizontal gradients, growing overlap — SHIPPED** | 43/44 | 39/44 | **82/88** |
| the same, over a fixed central window | 43/44 | 39/44 | 82/88 |
| the same, with the profile clipped at 3x its own mean | 40/44 | 33/44 | 73/88 |
| normalised cross-correlation | 41/44 | 34/44 | 75/88 |
| SAD on the SIGN of the gradient | 37/44 | 20/44 | 57/88 |

**Clipping is the result worth keeping.** It is the textbook robustification for exactly the
failure being repaired — one very strong edge dominating a sum — and it is 9 pairs worse than
doing nothing. *Choose between candidates on the live-corpus count, never on which one sounds
more principled.*

So the estimator stands and 2 gates absorb its error: a band is measured only when what it drew
agrees with what it reported on 80% of its pairs, to within `max(15% of the predicted shift, 1.5
px)` — *A band the captured frames cannot resolve is unreadable* below holds why that floor is in
pixels, and which pairs it is not asked of — and a wrap crossing measured at zero displacement
while the band's own model predicts a
large one is counted as unreadable rather than as a jump. **The shipped estimator misses 8 of the
132 pairs in the 3 fixtures — 1 of 44 on
the reference, 5 of 44 on the nearest-first variant, 2 of 44 on the 1.5x variant — and every one
of the 8 is the same shape**, on the band holding a car the camera follows.

**No criterion has met a submission, and that is stated wherever a scene score is reported.** The
thresholds were chosen against fixtures written by the same hand as the criteria.
`scene_mutants.py --census` reports what each criterion separated and says in as many words that
the population is fixtures; `--runs-root` prints `NOT ASKED` on an empty tree rather than
`0 separated`, and `--census-selftest` proves the census can say NO.

**To re-open:** a real submission that any criterion fails for a reason that is not about the
submission — which is #46's shape and the honest prior here; an estimator miss that is not the
stationary-object shape, which would mean the 2 gates are aimed at the wrong property; or a
contract change adding `car.screen`, which is the one field that would let `front.occludes` be
measured twice instead of once.

**A declared band is not a region of the frame that belongs to one layer, so a layer is measured
only from rows no other declared band contains — decided 2026-08-27.** A layer left fewer than
`band_profile`'s own 10-row sample is UNATTRIBUTABLE: reported, excluded from the score, and never
given a neighbour's motion. `eval/SCENES.md` states the rule for a reader of the criteria;
`ParallaxScene.MIN_OWN_ROWS` is where it lives.

The 88 pairs above were all read from `ref_parallax`, whose 4 bands **tile the frame** — its
author's choice, not the contract's. `layers[].top`/`bottom` say where a layer is DRAWN, and a
layered background overlaps by construction, so a band holds the nearer layers' pixels where they
cover it and the farther ones' where they show through. `best_shift` then answers for whichever
content carries the gradient energy, and the 3 gates cannot see it: a band reading a neighbour's
motion agrees with itself as well as a band reading its own.

Three measurements decided it, and each could have come out the other way:

- **The subtraction is over every other band, not only the nearer ones.** The nearer-only rule is
  the painter's-algorithm reading and would be right if every layer painted its band opaquely. It
  leaves the first real submission's `range` and `grove` bands returning the identical 11-pair
  series 20, 17, 15, 19, 20, 15, 16, −4, 6, 5, 6 px, which is the rate of `clouds` — **farther**
  than both, and showing through them.
- **It is a refusal, not a recovery.** Where the old code erred is exactly where a band has
  nothing of its own, so there is nothing to fall back to. On the one stored scene trial tier 2 is
  unchanged at 6 of 6 and `layers.image_parallax` stays `scored=False`; what changes is that the
  recorded reason is now true (`eval/RUNS.md`).
- **What it buys is a false negative the fixtures could never fire.** A correct scene declaring
  its bands at the layers' full extents was read at 25px/frame for a band whose drawn shift is
  13.5px, and **failed**. It is now refused instead. That variant is in `scene_mutants.py`, and
  because it must `tolerate` the criterion it exercises, the mechanism is pinned offline by
  `--attribution-selftest`: 7 hand-written band tables with the row counts stated before it runs,
  and 3 mutants of the shipped file.

**To re-open this one:** a windowing that attributes a row of an overlapping band to one layer and
survives the `range`/`grove` measurement above; or a contract change declaring the bands disjoint,
which would be a prompt change and a regime boundary.

## The scene performance pass is an uncapped ramp on a spaced, exclusive machine — decided 2026-08-24

`eval/SCENES.md` proposes scoring a scene as a ramp, which reads the stack only if the machine
underneath holds still. **It cannot be held still by any mechanism tested on this host, and it
does not need to be.** `eval/PERF-HOST.md` is the report and the authority.
`eval/tools/host_perf_probe.py` is the producer for the host figures in it — capping, spread and
drift; the per-stack frame-timing rows come from the installed toolchains and each names its own
source.

**No tested mechanism gives a usable GPU, RAM or CPU-rate cap, and 1 candidate lies about doing
so.** `taskpolicy -b` cuts CPU throughput to 0.20x and moves GPU frame time by under 0.1 ms in
every interleaved round, so the CPU levers do not reach the GPU. That is a claim about the arms
`host_perf_probe.py --gpu` runs, not about every mechanism that could exist: a candidate nobody
has tried is a new row rather than a refutation. **The 1 exception is `RLIMIT_CPU`**, which is
genuinely enforced — it killed a hog with `SIGXCPU` at exit 152 where the unrestricted control
finished at exit 0 — but it bounds cumulative CPU seconds and kills on exceeding them, so it can
end a trial and cannot hold one to a rate or a core count.

`RLIMIT_AS`, `RLIMIT_DATA` and `RLIMIT_RSS` — the first and third being the same limit on Darwin —
return `EINVAL` from `setrlimit`, with `RLIMIT_STACK` set to its own hard limit as the control that
proves the refusal is about the limit rather than the value. `taskpolicy -m` documents a memory
limit in MiB and does not enforce one: a hog asked for 2048 MB got all of it at exit 0 under
`-m 512`, and again under `-m 64 -j 10 -a`. That is #61's shape — an accepted-but-ignored flag —
and it is written down so nobody builds a cap on it.

**The container route is rejected on the GPU, not on the caps.** A Linux guest with cgroups v2 was
started and measured: `--memory=512m` OOM-kills the same hog at exit 137 where the control writes
2 GB, and `--cpus=2` delivers 2.08 cores against 2.00 asked. Those are real caps and `taskpolicy`
has no number to ask for at all. But the guest has no `/dev/dri`, no DRM module and no Vulkan
loader — no GPU device of any kind — so a GPU-bound scene there is software rasterisation, on a
different machine from every existing result. **A stricter cap on the wrong hardware is not a
stricter experiment.**

**What replaces the cap is spacing and exclusivity, and both are measured.** The same fixed GPU
workload, launched in separate processes 25 s apart, holds its median to a 0.766–2.485% range
across 3 separate runs whose medians agree to 0.074% — 3 runs rather than 3 independent
replicates, since one began straight after the drift arm and inherited its machine state. Run back to back for 10 minutes it swings
**1.975x** best to worst, reaching 10% above its opening value at t+16 s. One competing GPU process
costs **2.13x**. Converted into ramp levels at a 1.25x step between levels, that is 0.11 levels
spaced against 3.05 back-to-back and 3.39 shared. **Spacing is free and it is the difference
between a ramp that can separate stacks and one that cannot.**

**The drift is not monotone** — it peaks at t+120 s and recovers — so these arms do not separate
thermal throttling from the shared CPU/GPU power budget or from a co-tenant, and a block design
cannot be corrected after the fact by assuming the machine only got slower. Interleaving is
therefore required rather than preferred.

**The ramp reads a harness-side wall clock.** Bevy 0.19's `RenderDiagnosticsPlugin` records CPU
time only on Metal by its own documentation, and the ts capture path runs on a software
rasteriser, while godot 4.7 and unity 6000.0.45f1 both expose a real GPU-side frame timer.
Reading each engine's best available clock would compare CPU frame time on 2 arms against GPU
frame time on the other 2. The engine timers stay useful per stack and as a cross-check.

**To re-open:** a GPU capping or biasing mechanism nobody has tried, which is a new
`host_perf_probe.py --gpu` arm and would settle the question the existing arms only bound; a
machine that is exclusive and not a laptop, where the spaced and back-to-back
arms would come back much closer together and spacing could be dropped; a macOS release that makes
`setrlimit` accept an address-space limit, or `taskpolicy -m` enforce one, either of which is a new
`--caps` row; GPU passthrough into a Linux guest on Apple silicon, which would make the container
route a real option rather than a different experiment; or the first real scene submission
measuring a run-to-run spread far above the floor reported here, which would mean the submission
rather than the machine is what stops a ramp.

## A scene pack carries a hand-written statement of the scene, written raw — decided 2026-08-25

`fidelity` asks whether a strip reads as the scene it was asked for, and that needs what was
asked for. `field.SCENE_STATEMENTS` holds one statement per scene and `field.build_pack` writes
it into a scene pack — and only a scene pack — as `SCENE.md`, one text for all 8 submissions.
Without it the aspect recovers the subject from the field, which finds a submission that omitted
what 7 others drew and cannot find one where all 8 missed the same requirement — the case a
fidelity aspect exists for.

**The rendered prompt is not a candidate, and the reason is measurable rather than a worry.** It
exists per stack: `anonymise.find_stack_names` returns a stack token in every one of the 8
rendered scene prompts, so handing a judge one names the arm in its own evidence — the leak
`neutralise` and `blind_extensions` exist to close. The statement is instead written by hand from
`eval/SCENES.md`.

**Written RAW, and that is the decision most easily got wrong.** Every other piece of pack text
goes through `neutralise`, because it comes from a submission and is not ours to write. This text
is ours. Passing it through would rewrite `Bevy` to `engine` and hand `verify_blind.py --packs` a
clean file — **the gate green over judge-facing text that named an arm until the harness edited
it**. `blurb_selftest.py` drives a leaking statement through the real `build_pack` and requires
the leak to survive and the gate to go red — a mutant that edits the built pack instead cannot
ask that question at all.

**A scene the module cannot state is refused, and both the packer and the spender ask.**
`build_pack` refuses to build such a pack; `run_field` refuses to judge one whose `SCENE.md` is
missing, undecodable, or not this scene's statement, because a pack is built once and judged later
from a directory anything may have touched (rule 13). **Existence is not the resource**: an empty
file and the other scene's statement both pass a presence test, and a field scored against the
wrong subject is worse than one scored against none, because it looks like an answer. There is no
escape flag — a pack whose `SCENE.md` differs from this checkout's statement of its scene is
refused, whatever produced the difference, and with 0 stored scene packs there is nothing to
grandfather, so an escape would be a fail-open channel with no measured need (rule 7).

**The statement it validated is recorded**, as `provenance.scene_statement_sha256`. The brief
names `SCENE.md` and does not contain it, so `brief_sha256` cannot say which subject a round was
scored against — the question #83 could not answer about what a judge had read.

**No game brief moved.** All 90 `(aspect, game, completeness)` briefs this checkout builds for
game task ids are byte-identical to the ones built before the statement existed, so no stored
round's `provenance.brief_sha256` is affected.

**To re-open:** a first real scene field whose judge cites the statement for something no
submission was asked for, which would mean the statement asks for more than the prompt did and is
the failure mode that matters most here; a scene added to `eval/suites/scene_prompts.py` whose
subject cannot be stated without naming a stack, which would say the technique does not
generalise; or a measured way to blind a rendered prompt, which would replace a hand-written text
with a derived one and remove the drift risk a hand-written text carries.

## The runner launches scenes behind `--scenes`, and every route to an instrument declares a class — decided 2026-08-25

`eval/wholegame.py` could not launch a scene until this. Task 133 kept scenes out of `TASKS`
because `--games` defaulted to every key of it, so registering one would have put it in the
standing matrix command against a probe that did not exist. The probe exists (`scene_probe.py`),
tier 3 exists (`fidelity`, `motion`, `framework_fluency`) and the judge's subject exists
(`SCENE.md`), so the reason has expired — but the trap has not, and the fix is not to widen the
default.

**`--scenes` is a second flag, not a wider `--games`.** It defaults to **none**, so a scene is
built only when it is named, and `--games` still defaults to every game. A default is a value
somebody can widen without noticing; a second flag is a selection nobody makes by accident. The
asymmetry is the decision: a scene trial is not a cheap addition to a game run — `eval/SCENES.md`
records that scenes and a second harness are two variables, and #172 measured the same fixed
workload swinging **1.975x** back to back, so a matrix that packs scene trials together forecloses
the performance question before it is asked. `wholegame.select_tasks()` is where both defaults are
written and where the reason is; an empty `--games` is now refused rather than read as *all*,
because a selection narrowed to nothing must not become the widest one there is.

**A CLASS IS DECLARED BY THE INSTRUMENT, NOT INFERRED AT THE CALL SITE.** `aspects.applicability`
was already the guard for the three paths that reach a judge FIELD, and none of them was the
runner. Wiring scenes in adds three more routes, and what stood in for a guard on the largest of
them was `evaluate.BOTS[task]` raising `KeyError` — a refusal that exists because a dict happens
to hold four keys, arrives after tier 1 has already run, and disappears the moment anyone adds a
fifth. `judge.py` had not even that: `GAME_BRIEF.get(game, "(unknown game)")` supplies a brief
rather than refusing, so a scene handed to the retired generalist judge is answered on all 13
game criteria.

So `aspects.INSTRUMENTS` declares the class of every non-aspect instrument — `playbot`,
`scene_probe`, `legacy_judge` — and `applicability()` answers for both registries. 1 function
rather than 2 that can drift apart, because the question is identical.

**`evaluate.TIER2_INSTRUMENT` is written out per task and NOT derived from the class.** Deriving
it would make the guard a comparison of a value with itself — every pairing correct by
construction, `applicability` structurally unable to disagree, which is rule 12's corollary and
what left a `tasks.py` mutant surviving 48 rows (task 113). Written out, it is a second statement
about each task, and `eval/tools/scene_runner_control.py` carries the variant that shows a
class-derived map is the weaker of the two.

**The routes are enumerated, because a guard is a property of a call site.** `scene_runner_control
--paths` prints six: task selection, the class resolution that gates the per-submission pack, the
tier-2 dispatch, the legacy judge, and the two argparse surfaces. `anonymise.build_pack` gets no
row of its own — it is class-agnostic, copies a submission's own files, and is reachable only
through the class resolution. A route with no row is a route nobody checked.

**The tier-2 SLOT keeps the name `playbot`, and so does `playbot.json`.** It is the weighted slot,
spelled that way in `WEIGHTS`, in the completeness gate, in `regrade_wholegame.py`, in
`paired_verdicts.py`, in `tier2_census.py` and in every stored grading. Renaming it to suit the
second task class rewrites what all of those read and changes nothing about the measurement. Which
instrument produced the record is inside it — `tier: "playbot"` or `tier: "scene_probe"`, written
by the instrument — and beside it as `tier2_instrument`, with `task_class` at the top of both the
trial record and the grading. Nothing downstream has to parse an id prefix, and `cmd_report`
computes every aggregate **per class**, because a per-stack mean over both describes neither.

**Two things about tier 1 are class-dependent, and both would otherwise measure the task rather
than the work.** A scene is filmed at its own contracted tick count rather than the game default
of 900 — the frames are what `fidelity` and `motion` read, and their brief says the last frame is
late in the run, which filming 240 ticks past the end makes false. And the five tier-1 audio
criteria are **not** asked of a scene: every rendered scene prompt says *"The scene has no sound.
Do not spend effort on audio"*, so scoring one against them deducts for compliance — the same
shape as the stale-cache defect, where the grader penalised an agent for doing what the task
asked.

**Nothing time-shaped enters the correctness pass.** The capture stays `just film SEED TICKS -
OUTDIR`, six argv elements and no seventh, and the control drives one submission twice and
requires every per-criterion verdict to be identical — with a variant that adds a clock reading to
one criterion's evidence and shows the row goes red. Performance is a second pass
(`eval/SCENES.md`, `eval/PERF-HOST.md`); the correctness pass is tick-indexed and that is what
makes the same-seed / different-seed pair a control rather than an opinion.

**To re-open:** a third task class, which would make a two-flag surface a three-flag one and argue
for a single `--tasks` with an explicit class filter; a measured reason to launch scenes by
default, which would mean the scene and game populations had become comparable enough to want in
one directory; or a tier-2 instrument that serves both classes, which would retire
`TIER2_INSTRUMENT` as a per-task table.

## A known play-bot false negative is declared as a red subject, not fixed in passing — decided 2026-08-25

`bot_mutants.py` carries a third kind of subject beside its mutants and its variants. A
`Pending` is a **correct game the suite fails today**, with the failing criterion ids written
down; every run asserts the measured set equals the declared one, and each entry names the
ticket that owns its repair. **0 are live**; `python3 eval/judge/bot_mutants.py` is the
producer for that count and prints it beside the variant count on its last line.

**`PENDING_VARIANTS` may be empty, and it is still pinned.** `--selftest` builds a synthetic
`Pending` rather than taking one from the list, so its 3 adjudication rows run whether or not
anything is declared. A self-test drawing its subject from the list would stop exercising
`adjudicate_pending` the moment the list emptied — silently, at exit 0.

**Why the defect is declared rather than repaired here.** Every one is a criterion change, and
a criterion change is a re-scoring event over 69 graded submissions, carrying its own
`tier2_census.py` before-and-after — whether or not any verdict turns out to move. Landing the
repair inside the ticket that *found* it would bundle a measurement change into a coverage
change, which is the multi-variable comparison rule 8 exists to prevent. So the finding lands
with the subject that reproduces it.

**A closed entry may re-score 0 stored verdicts. That does not weaken the declaration.**
The 2 `ref_tetris3d` opening-card subjects are in `VARIANTS`, and their promotion moved 0 stored
verdicts. `piece.spawns` and `piece.falls` each have 0 failures over the 19 stored `g2_tetris3d`
trials (`python3 eval/judge/tier2_census.py --runs-root <checkout>/eval/runs`). That game's only
2 tier-2 failures come from a Unity probe-session abort, not an opening card. Whether a repair
re-scores anything is knowable only once it lands, so the split is what keeps the coverage change
and the measurement change separable in both outcomes.

**A pending entry has a second way to close: the subject is not a correct game.**
`ref_pong/rally.counts` carries no pending entry, and `tasks/159` is where the decision is
written down. A trace line that raises `paddle_hit` must publish a `rally` that already counts
that hit, so a sim settling the counter a tick later fails the criterion correctly.

Three facts from the task decide that, in order.

1. The probe prints a tick-0 line before anything is stepped, then one line after each step.
   All four starter guides say so, so a line describes the state **after** its own tick.
2. The g1 prompt defines `rally` as *"the number of consecutive paddle hits since the last point
   was scored"* — a count of the events the line carries, not a free variable.
3. A line therefore cannot both raise `paddle_hit` and report a `rally` that excludes it.

Where the sim increments stays free; what the tick's line **publishes** does not.
`bot_pong._rally` holds the derivation and records the same-tick and following-tick observations
separately, so a failure says which one it saw.

**The criterion stays exact rather than accepting an increment within a window**, which would be
a reason not to count a failure (rule 7), would accept an increment caused by anything, and would
re-mean 25 stored `g1_pong` gradings
(`python3 eval/judge/tier2_census.py --runs-root <checkout>/eval/runs`) to buy a pass this
criterion has never once withheld.

**The same reading was declined for the arena and it went the other way** (`tasks/170`).
`ref_arena/multiplier.falls` reads the multiplier across the `player_hit` tick and looks
identical, but step 2 is missing there: the g3 contract gives `multiplier` no definition at all —
only that it *"falls when the player is hit"* — and the other half of that one sentence is read
by `multiplier.rises` over hundreds of ticks by any mechanism. Nothing licensed reading this half
to the tick, so the criterion now reads the damage tick **and the 8 ticks after it**, and passes
on the first of those 9 where the multiplier moves, if it moved down.

**The widening is not the half that mattered.** The old criterion compared the peak the killing
phase reached against the value on the hit tick, and on the reference those are **459 idle ticks**
apart — so anything that lowered the multiplier in between passed. A game whose multiplier lapses
on a combo timer and has **no damage link at all** passed it, with evidence byte-identical to the
reference's. The baseline is now the value on the tick **before** the damage, and that game is a
mutant. Both directions are pinned on `ref_arena`: a correct game that publishes the collapse one
tick late is a `VARIANTS` entry the old reading failed, and the combo-timer game a `MUTANTS` entry
it passed.

**A pending entry is not a tolerance, and the difference is the assertion.** `Variant.tolerates`
waives a criterion silently; a pending declares exactly which ids fail and goes red on **any**
other set. That includes the **empty** set: a landed repair turns the row red with *"promote it
into VARIANTS"*, which is the only mechanism that makes the entry stop being a waiver. Rule 7
says every reason not to count a failure is a channel a bug can widen — this one is a channel
exactly one criterion wide, and it closes itself.

**The registry is the other half.** `HAZARDS` holds one answer per criterion to *what
correct-but-unusual game would mis-score this?* — one per criterion instance the 4 bots
actually report, which is more than the set carrying a mutant. Some declared false negatives
sit on criteria with **no mutant at all**, so a registry scoped to the mutant set would miss
them. `python3 eval/judge/bot_mutants.py --hazards` is the producer for all three counts and
names the unmutated criteria. A criterion added without an entry fails the suite;
`no-construction` is a legitimate entry and says nobody could build a correct game that
fails it.

**Variant coverage is per fixture.** Each variant runs the whole bot on one fixture, so a
suite-wide variant count is not the number of observations any one criterion has. Read the
per-fixture counts out of `bot_mutants.py --hazards`; do not infer them from the suite
total. A fixture can have **0** variants while the suite total is non-zero.

**To re-open:** a pending entry that survives 3 tickets, which would mean the declaration is
being used to live with a defect rather than to schedule its repair. **An empty list is not a
reason to retire the mechanism** — the pending loop iterates it, so it costs nothing to carry,
and what it buys is the alternative to a silent `Variant.tolerates` on the next false negative
found.

**To re-open the `rally.counts` decline specifically:** a real submission whose counter settles
a tick late. It would be a submission that violates the state contract, so the question it
raises is whether tier 2 should fail it or whether the g1 prompt should say the ordering out
loud — and only a submission can raise it, because the decline rests on reading the contract
rather than on a measurement that could move.

## A scene layer's `offset` may accumulate or wrap, and the probe reads both — decided 2026-08-25

The `s1_parallax` trace contract calls `offset` *"how far that layer has been displaced sideways
so far"* and `span` *"the width after which the layer repeats itself"*, and it does not say
whether the number keeps growing or stays inside `[0, span)`. **A submission may report either.**

**The prompt does not change.** A layer declares its own `span`, so a wrapped series and a
cumulative one carry the same information. Naming an encoding would be a regime boundary across
every scene trial, and it would deduct marks for reporting `offset` the way a renderer wants it.

**The probe absorbs it, in 1 place.** `ParallaxScene._walk` rebuilds each layer's offset series
from the per-tick trace, mapping every step into `(-span/2, span/2]` before adding it;
`layers.depth_ordered`, `layers.image_parallax` and `loop.seamless` read that series. **`_walk` is
the only place that subtracts 2 reported offsets, and only ever consecutive ones** — a criterion
that differences 2 arbitrary offsets is reading a modular residue. Per tick, not per captured
frame: captures are 60 ticks apart, and a near layer can cross more than half its span in that
time.

**A layer earns a walk by carrying a finite `offset` and a positive `span` on every trace line,
and `layers.depth_ordered` fails one that does not.** `state.shape` reads tick 0 only, so all 3
ways of falling short are silent and all 3 read as a smaller, plausible travel: a hole between 2
reported ticks, a layer that stops reporting and never resumes, and a row declaring no usable
`span`.

`eval/SCENES.md` states this where a prompt author will look, and `scene_mutants.py` holds both
directions: a variant reporting `offset` inside its own span, and 3 mutants that break a layer's
reporting in each of those ways.

**To re-open:** a scene whose layers can move more than half a span in 1 tick, which is where
a per-tick unwrap stops being decidable and the contract would have to name an encoding after
all.

## The improvement loop is triggered by a change, not by a run — decided 2026-08-27

**The trigger is the change, not the occasion.** The loop fires when the **instrument** (graders,
judges, rubric, blinding, the tools that produce the numbers), the **product** (`eval/starters/*/`,
the task prompts) or the **guidance for either** is about to change and the effect can be measured
before and after. Those three name a resource rather than a list of components, so a part of the
instrument written tomorrow is covered. A matrix finishing is the occasion that supplies most such
changes and it is not the only one: a ticket, a sweep of stored artifacts, and a loose end handed
on by a previous iteration each supply them, and all land in the same file under the same standard.

**An iteration and a finding are different records and one piece of work commonly produces both.**
What was **observed** is a finding; what was **changed** is an iteration. Iteration 13 is the
change; [`#95`] is the defect it repaired. **Guidance files with the thing it governs**: a
document about the instrument is an iteration in `eval/IMPROVEMENTS.md`, one about the starters
or the task prompts an iteration in `IMPROVEMENTS.md` at root, so no change the trigger admits is
left without a destination.

**The run-only alternative was declined.** Sending every change that did not come from a run to
`eval/FINDINGS.md` makes the record worse rather than tidier: a finding has no pre-registration,
no falsifier and no keep-or-revert, so filing a measured change there drops exactly the parts that
make an iteration falsifiable — and it would still leave iterations 13-15 in a file whose trigger
excluded them. **Nothing is retro-filed either way**: the evaluator changes of 2026-08-24 and
08-25 that have the iteration shape stay where they were recorded, because rewriting them into the
loop would narrate a loop that did not produce them.

**What the skill said, and why it was wrong.** `.agents/skills/refine/SKILL.md` fired the loop on
*"a matrix has finished AND been evaluated"*, which excludes every iteration the file has gained
since. `grep -c '^## Iteration ' eval/IMPROVEMENTS.md` counts **17**; the last 3, read 2026-08-27:

| iteration | origin, by `git log -S'<heading>' -- eval/IMPROVEMENTS.md` | the before/after it records |
|---|---|---|
| 13, the pack-versus-manifest gate | `tasks/33` | `judge/pack_selftest.py`: 8 of 8 real submissions fail unfixed, 0 of 16 fixed |
| 14, blinding the extensions a file mentions | `tasks/87` | `judge/blind_ext_selftest.py`: 2,083 arm-naming tokens over 84 stored packs → 0 |
| 15, rebuilding a blind `CHANGED.txt` | the loose end iteration 14 handed on | `judge/blind_dir_selftest.py`: 1,275 → 0 segments over 43 stored submissions |

All 3 were committed 2026-08-23 and each measured a stored corpus offline. The last multi-cell
matrix is `wg-g4c-2026-08-21T02-26-46`, at **8** by
`ls eval/runs/wg-g4c-2026-08-21T02-26-46/artifacts | wc -l`; the 2 later run directories are at
**1** by the same command. The root loop is the same shape at `grep -c '^## Iteration '
IMPROVEMENTS.md` = **2**: *each template at its own stack's best* came from `tasks/26` and a
capability survey, with no run between.

`eval/IMPROVEMENTS.md`'s preamble holds the statement; `IMPROVEMENTS.md` at root points at it
rather than restating it, and the skill and the `AGENTS.md` index row follow it.

## A band the captured frames cannot resolve is unreadable, and the capture stays at 12 — decided 2026-08-27

A layer repeats every `span`, so a displacement of `d` and one of `d + span` draw the same picture.
At exactly half a span the two candidates are the same distance apart and neither is the answer;
beyond it the smaller one is the wrong one. **A pair moving half a span or more is declared
unreadable, and the capture contract does not change.**

**More frames is not the repair, because `span` is the submission's choice and no fixed capture
rate resolves every repeat length.** A band crossing 1.66 to 2.25 spans between captures needs
more than 50 frames where the contract gives 12; one repeating every 10 world units needs
thousands. Raising the frame count is also a regime boundary against every scene trial. So the
contract stays at 12 and the instrument says it did not measure.

**It has to be a PRECONDITION on the pair, not a tolerance**, and that is the part a test would
not have found. An aliased band can agree with itself perfectly: `scene_mutants.py`'s `the near
layer repeats twice between captures` variant is a correct scene whose nearest band crosses its
span exactly twice between captures, so `best_shift` answers 0px on 11 of 11 pairs at confidence
0.83–0.92. Nothing downstream of that number can tell it from a real background that never moved —
only the reported offset can — and a background reported as moving and drawn stationary is the one
thing `layers.image_parallax` exists to catch, so it must stay readable.

**In the same repair, the agreement slack moved from RATIO units into PIXELS**, which is the unit
the estimator answers in. The proportional term is unchanged — a ratio slack of `|median| * 0.15`
is exactly `|predicted| * 0.15` pixels — but the floor was a constant in ratio units, so in pixels
it was `0.15 * |d_offset|` and grew without bound as a submission reported its offsets in finer
units. On the road band that floor admitted ±60 to ±81 pixels of a ±89-pixel search window: every
answer the estimator could return agreed with every other, and the band was called readable on 8
of 8 pairs while its shifts ran −73px to +3px. The pixel floor is 1.5, which is the estimator's own
quantisation and not a number fitted to a population — `best_shift` answers in whole pixels, and
the worst pure-rounding residual measured over the 6 s1_parallax fixtures is exactly 1.00px.

**The two halves are pinned separately because no one input reaches both.** A fixture that aliases
is refused by the precondition whatever the slack does, and isolating the slack needs a scene
reporting offsets so large that the whole search window fits inside a ratio-unit slack — a property
of the reported units, not of any scene worth filming. So `scene_mutants.py
--reliability-selftest` drives `_reliable` over 7 hand-written layer records whose answers are
stated before it runs, against the shipped file and against 2 mutants of it; each mutant moves
exactly 2 records, in both directions.

**To re-open:** a submission whose bands are all inside half a span per capture and which is still
misread — that would mean aliasing was never the property that mattered; or a measured
pure-rounding residual above 1.5px, which would mean the floor is fitted rather than derived.

## Reversal conditions — what would re-open a decision

**Adopted 2026-08-23 from `game-research-gpt`, whose ADRs each end with one (task 11).
Labelled honestly: this is UNVERIFIED as an improvement.** No finding in `eval/FINDINGS.md` is
known to have been caused by a decision outliving its basis, so the case for it is an argument,
not a measurement. It is adopted narrowly — only where a decision rests on a measurement that
could plausibly move — rather than on every row, because a reversal condition attached to a
settled question is noise that makes the live ones harder to find.

| Decision | Re-open when |
|---|---|
| Tier 3 weight stays 0.00 | Repeats at a **fixed presentation order** clear gate 0. More aspects do not count — already tried, verdict unchanged |
| Separation figures reported under `rank`+`pool` | A field where the **ceiling gate passes on both orders**. The choice rests on scores saturating (6-7 of 8 on one modal value); on an unsaturated field a score-based figure loses its handicap and the comparison should be re-made. `field_ranks.py` prints all four either way |
| Code aspects are within-stack only | **Never on a better anonymiser.** The judge identifies the language from syntax, so only a change to what is being asked could re-open it |
| The code half of the directory leak stays unrepaired | A rewrite that **stops isolating an arm per field** — a strict threshold on one pack's redaction count naming a whole arm in fewer than a third of the stored fields. Currently 6 of 9 for the arm-exclusive vocabulary and 9 of 9 for all three alternatives, against 7.1% by chance. **This row asked for a uniform per-arm density until 2026-08-23, and that was the wrong quantity**: a vocabulary-free rewrite satisfies it at 2.1x with no arm at zero and is *worse* on the per-field figure, because per-arm density is an aggregate the judge never sees. `judge/blind_dir_selftest.py --runs-root` reports both and fails if any candidate stops partitioning |
| Deterministic tiers may not rank stacks | **`python3 eval/judge/discrimination.py <run_dir>` printing `CROSSES` for any one (run, game) group.** SIZE: the adjudicated between-stack range of tier 2 must exceed the mean within-cell difference by **at least one criterion, `1/N`** — today 0.0435 to 0.0769 depending on the game. SCOPE: **one run × one game**, never pooled (`eval/RUNS.md` bans both poolings), counting only stacks whose two trials are `completed` **and gate-green**, since tier 1 gates and a submission that does not build has no rank position. Read 2026-08-23 over the 9 stored groups: the test is **asked of 8** and **0 cross** — each of the 8 sits at range 0.0000 against a floor of 0.0000, stacks tied at the tier-2 ceiling. The 9th is **NOT ASKED**, a third value and not a pass: `wg-audio` `g2_tetris3d` has one gate-green stack, so there is nothing to compare. Only 5 of the 8 are four-way; the other 3 compare 2 or 3 stacks and say so. What would cross it is a game where the gate-green stacks are **not** all at that ceiling (tasks 65, 74). Set by task 70; the previous wording is adjudicated below the table |
| Tier 1 gates rather than scores | `tier1_census.py` reporting **DISCRIMINATES** on its **headline** verdict — a group where both tiers vary among the trials tier 2 could measure. Currently 0 of 11. Its *"if every grading were pooled"* line already reads DISCRIMINATES and is **not** a trigger: it counts 16 superseded re-gradings of 8 work trees `wg-g4c` already contributes (task 75). Adding a tier-1 criterion with real headroom is what would do it, and it would need a mutant *and* a variant before it counted |
| A saturated tier-2 group certifies rather than ranks | `tier2_census.py` reporting **SEPARATES** — no group flat. Currently 5 of 11 are. It will not be moved by promoting a withheld diagnostic (single-valued wherever recorded) or by another existence-of-mechanic criterion (four measured, 8/8 on `wg-g4c`); it moves on a harder task |
| The play-bot tier carries 1.00 | `weight_sensitivity.py` reporting **FLIPS on a group whose variance is not a confound** — it needs a second scored tier to be worth re-running for that, so this re-opens only alongside the row above |
| No budget cap, `--max-turns 1000` | A trial **reaching 1000 turns**. The 250 limit became binding without anyone noticing (#35); the same failure at 1000 would mean the backstop has become an instruction |
| 2 trials per cell | A stack difference landing inside the ~0.015 the design cannot separate — at which point n=2 is the constraint, not the evidence |
| The cost route is adjudicated and does not resolve | **4 qualifying groups that share neither a run nor a game.** The adjudication ran (`cost_census.py --ordering`) and came back unresolved for a structural reason, not a marginal one: 6 of the 7 stored groups are one cluster once game recurrence is counted, so the smallest p the design can return is **0.25** and no outcome could have reached α. Re-reading the stored tree cannot change that — only new runs on non-recurring games can. **A fifth stack also re-opens it**, by widening the label space the permutation draws from |
| Performance fields are captured, not scored | `capability.py` reporting **real variance in `capture.megapixels`** across a run. At that point capture geometry is a choice submissions actually exercise and it is worth asking whether the judges should see it. Currently 62 of 68 sit on the starter default |
| No frametime or fps field | The TypeScript capture path getting a **real GPU backend**. Nothing else changes it: the asymmetry is the renderer, not the stack (§3 of the capability matrix) |
| An unreachable private method is deleted, never exempted | A hit that is genuinely reachable and cannot be made visible to the census — in practice a `getattr(self, ...)` whose name is assembled at runtime, the known false positive, appearing in real `eval/judge/` code. There are **0** such sites today: all three `getattr(` calls there take a literal or a non-private attribute. If one appears, the repair is a marker the census reads that names *why*, never a bare name list — an exemption that does not state its reason is indistinguishable from a mistake |
| The git hooks run a named subset, not the whole of `gates.yml` | **2** pushes to `main` reddened by the **same** gate outside that subset. It is aimed at the failure that recurs locally — stale citations and a malformed queue — so a repeat from one uncovered gate is evidence the subset is drawn wrong, where **1** is a normal miss. `python3 eval/tools/ci_minutes.py --hooks` says what is in it today. Widening it is a re-timing, not a re-argument: read the new tier with `time .githooks/run-gates.sh pre-push` before adding, because the tier's value is that nobody reaches for `--no-verify` |
| Harness lint is a recipe, not a gate | `PLW1510` and `BLE001` **staying at 0 across a working week** without anyone tending them. At that point a gate costs nothing to add and would catch the next site before it is written; today it would fire on a backlog nobody has triaged and be disabled |
| The `template*/` trees and the spec-change suite are retired | A decision to **run spec-change trials again**. Then restore from git rather than re-forking: `git checkout <pre-retirement> -- template-ts/`. Note what re-opening costs — the trees are frozen at 2026-08-23 and every starter repair since then is missing from them, which is the drift that closed them in the first place |
| A harder task is priced, not bought | **A play-bot that reaches the goal.** The pre-test ran (task 83, #139) and came back spread — 0.274 to 0.803 — but 8 of 8 runs end on health exhaustion, and improving the bot reordered the field (ρ=0.405, p=0.163), so the spread is the instrument's. Nothing here justifies buying it: all-eight-at-1.000 would, and none of the eight reaches 1.000. **This row cited a $421-to-$698 *spend* until 2026-08-23. There is no such spend** — the account is a subscription and every dollar figure here is a list-price valuation of tokens (#159). The decline rests on the pre-test, not on a price. Re-opens when a bot clears a real submission's stage without dying — at which point the fraction is about the level and the question is live again |
| Compliance with the always-loaded rules is measured, not assumed, and the measurement stops at k=16 | A pool **larger than 32 live instructions** exists. `eval/instrfollow/RESULT.md` bounds the count effect at 3.3pp up to 16, and `python3 eval/tools/instruction_census.py` puts the always-loaded set at 112-155 (read 2026-08-23) — so the open question is the gap, and closing it needs instructions, not trials. Cost rises steeply with k ($0.056 at k1, $0.273 at k16), so price a k32 pilot before sizing anything. Conflict is the cheaper subject: arXiv:2510.14842 puts the mechanism there, and two contradictions already sit in the always-loaded set (tasks 77, 79) |
| Both completeness wordings are kept in `COMPLETENESS_NOTE` | `--allow-truncated` being **removed from `field_sweep.py`**. While a deliberately capped field can be built, the truncated wording is reachable and the claim is checkable; delete the escape and the note collapses back to a constant, at which point the honest move is to delete the claim from the brief too rather than leave an uncheckable sentence in it |
| `tasks/` is reviewed by CodeRabbit rather than excluded with the other archives | A review comment **correcting a figure, a number or the prose** in a `tasks/` file. The exclusion is then 1 line — move the pattern into the archive block in `.coderabbit.yaml`. Nothing else re-opens it: noise about a ticket's *content* is the cost being accepted for the reviewer having the brief |
| `skillspector` is disabled; every other analyser is left on | SkillSpector gaining **per-rule configuration** — the schema offers `enabled` and nothing else, so today it is all or nothing — or a skill arriving here from **outside the dispatch-and-merge loop**, which is what would make a scanner for malicious skill manifests worth 14 findings and 0 true positives. For the analysers still on, the trigger is unchanged: a tool naming itself on a comment nobody wanted. `languagetool` is at 1 finding and 1 false positive, which decides nothing; do not disable it on the argument that 173 markdown files must be noisy |
| One authoritative path per skill | A **maintained** non-Claude consumer — a sibling that actually reads a skills tree and edits it. The 2026-08-23 measurement was 0 readers and 0 content-bearing edits in 3 commits; a copy that anyone maintains is a different object from the one that was deleted. Even then the first question is whether a pointer serves it, since a copy reintroduces the drift, not the reader |

The rows with no entry here are not exempt; they are decisions where the owner's judgement is the
input and no measurement would overturn them.

### Why the ranking ban's re-open condition changed shape — task 70, 2026-08-23

It used to read *"any instrument change producing **non-zero** within-cell verdict variance —
currently 0 of 380"* (`WR-paired-verdict-tie`). Three things were wrong with it, and the third is
the one worth carrying:

1. **The number was withdrawn.** No coherent scope gives that denominator, and no scope gives
   zero. The scoped recount is 5 of 436 in `wg-matrix` and 0 of 232 in `wg-audio48`, so the
   condition was **met in letter** the moment it was scoped, by a quantity that had no reason to
   be exactly zero.
2. **It was a sign test on a rate, and its two figures were not the same measurement.** 156 of
   the 436 are LLM-judge criteria at weight 0.00; the 232 contains none. The section above has
   the per-(run, game) deterministic table that replaced them.
3. **A noise floor cannot re-open a ranking ban on its own, in either direction.** Within-cell
   variance enters the comparison as the thing a gap must *beat*: more of it makes ranking
   harder, not easier, and none of it means the instrument is silent, not that it is sharp. The
   condition now names the comparison — **`range - floor >= 1/N`** — which is the rule
   `eval/judge/JUDGING.md` pre-registered on 2026-08-16 for the aspects, applied one layer down,
   plus the smallest gap a pass-count over `N` criteria can represent.

**Adjudicating the old reading against the new condition: it does not cross in any group where
the question can be put.** Of the 9 stored (run, game) groups the test is **asked of 8** and
**0 cross** — not because 1.1% is small, but because the between-stack range it would have to
beat is **0.0000** in all 8, every gate-green cell sitting at the tier-2 ceiling. The 9th,
`wg-audio` `g2_tetris3d`, prints **NOT ASKED**: one gate-green stack, nothing to compare. That is
a third value and it must not be read as a pass, for the same reason `total=0 passed=0` is not
(rule 1). Five of the 8 are four-way; the other three compare 2 or 3 stacks and say which.

Two things that reading cost, both kept because the next agent would otherwise re-derive them:

- **`discrimination.py` read `wg-arena3d`'s arena as "between-stack exceeds within-cell"** on a
  0.0435 gap that was entirely one Rust submission **which does not compile** (`just check` exit
  101, a borrow-check error `E0502` on `velocity.0 += (target - velocity.0) * PLAYER_ACCEL` in
  the agent's own `crates/sim/src/lib.rs`, in both trials). It scored 0.957
  rather than 0.000 because `audit_criteria.is_harness_failure` excuses any criterion whose
  evidence says *"probe unusable"* — and the probe was unusable because the submission did not
  build. **22 of its 23 criteria were excused on that pattern; the 23rd, `audio.triggered`, has
  the identical cause and different wording, and that lone survivor WAS the whole 0.0435 gap.**
  A fail-open excuse (rule 7) that manufactured a between-stack signal out of a build failure.
  Gating on tier 1 removes it here; the excuse pattern itself is untouched and still live.
- **The ranking test said `DOES NOT CROSS` every time it was asked**, which is the shape of a
  check that cannot fail. `python3 eval/judge/discrimination.py --selftest` now proves it can, on
  the boundary case as well as the obvious one.

> **The boundary row was green against a value the tool could not produce, and that is the
> sharper lesson.** `ranking_test` compared floats against `1/N`, and every score reaches it
> through `evaluate.overall_score`, **which rounds to 4 decimals**. At `N=13` a one-criterion gap
> arrives as `1.0000 - 0.9231 = 0.0769` against a threshold of `0.076923…`, so on real data the
> documented boundary case read **`DOES NOT CROSS`** — while the selftest, which built `12/13`
> unrounded and never went through `load()`, read `CROSSES`. A tolerance could not fix it: the
> shipped `1e-9` is four orders of magnitude below the rounding error, and a tolerance wide
> enough to absorb it would swallow real gaps. **Tier 2 IS a pass count, so the test now does its
> arithmetic in integer counts** — `k·(max_s − min_s) − 2·Σd ≥ 2k` — and cannot round at all;
> `_row` builds every selftest row through `overall_score` so the control travels the subject's
> path. **No stored verdict changed**: 8 groups asked, 0 cross, before and after.
>
> 2 rules fired here and neither was mine to claim. **A control that does not travel the
> subject's path is a control over a different subject** (rule 12), and *a mutant asks whether a
> check can fail; only a variant asks whether it can still pass on an input it mishandles* (rule
> 15) — the input being an ordinary rounded score. Both were found by the reviewer on **pull
> request 8**, from this repository's own rules. (Written without a `#`: in a live document
> `#NN` is a finding citation, findings run #19-#157, and `[#8]` would be a reference-style link
> to a finding that does not exist.)

- **The denominator was taken from the whole game and the gating happened afterwards**, so `1/N`
  could come from a submission that had been removed from the comparison. It is now established
  over the selected stacks, and a group whose survivors disagree on `N` is `NOT ASKED` with the
  counts printed rather than silently reduced to one of them (rule 4).
- **Two selected stacks with 0 scored criteria raised `ZeroDivisionError`** — an aggregate over a
  population that does not exist. `NOT ASKED`, reported, never divided by.
- **The output header claimed `completed` and the function did not enforce it.** `main()` filters
  non-completed rows before calling, so nothing shipped was wrong; but a guarantee that lives only
  in the caller is one the next caller will not have, and `ranking_test` prints a claim about its
  own population. It filters now, and the variant row proves the identical gap still crosses when
  both trials completed — otherwise the repair would be a deletion.

## The agent harness is an arm dimension, and dollars never cross it — decided 2026-08-24

The `claude` CLI was spelled into the runner's argv, so *which agent built this* was a constant
and every result the project holds is a statement about one harness with nothing saying so.
`wholegame.py --harness` now chooses it; `eval/agent_harness.py` holds one object per CLI —
build argv, parse stdout, normalise, preflight — and the rest of the runner learns no second
vocabulary.

**The claude arm's argv did not move, and that is asserted rather than believed.** It was
compared against the argv the pre-change code built, in three configurations, by loading both
revisions and intercepting the subprocess call: identical, with a deliberately mutated argv as
the control. `eval/tools/agent_harness_control.py` keeps a literal copy and 12 mutants, and it
runs in `gates.yml` and in `precampaign_smoke.py`. A changed command line is a changed
experiment and appears in no stored artifact, so nothing else could ever notice.

**Tokens and wall clock normalise. Dollars do not.** `tokval` is Anthropic's list price for
Anthropic tokens (#159); prime-agent reports OpenAI's list price for OpenAI tokens. Adding them
produces a figure in no unit. So `cost_usd` is populated only where `tokenvalue.py`'s definition
covers it and is `None` — never `0` — elsewhere, the foreign figure is stored under
`vendor_cost_usd_not_comparable`, and both aggregating producers exclude a foreign record and
report how many they excluded. A mutant that removes the exclusion moves a stored floor from
10.5 to 130.5 on one foreign record, which is what makes the guard worth having.

**Turns do not normalise either, and the record says so per row.** The claude CLI counts every
turn of its loop; prime-agent has no counter, so the module counts assistant messages. Both are
recorded with a `turns_definition` beside the number rather than a convention nobody can see.

**A terminal reason is mapped, and an unmapped one stays unmapped.** The shared enumeration is
the claude vocabulary because 161 stored records are written in it. prime-agent's map has ONE
measured entry (`stop` -> `completed`); anything else becomes `unknown:<raw>`, and an ABSENT
reason stays absent — killed trials store `null` and that is a third value, not an unknown one.

**Isolation on the second arm is an assertion, not a flag.** prime-agent reads a context file
from every ancestor of its working directory to `/` and from its agent directory — measured: an
`AGENTS.md` one level above came back through the model verbatim. Its `-nc` flag stops that and
also removes the starter's own `AGENTS.md`, which is the product being measured, so it cannot be
used. `preflight()` refuses to launch when a context file sits above the trial tree or in the
agent directory, or when that directory holds discoverable skills, extensions, prompts or
themes; what it checked goes into the trial record. Model, provider and thinking level are
pinned on the argv because `~/.prime/agent/settings.json` otherwise supplies them and ordinary
interactive use rewrites it.

**What is NOT claimed:** that the arms are equalisable. They are not. The permission regime, the
Stop gate, the turn ceiling and the thinking level have no counterpart across the two, and
`eval/RUNS.md` lists each with what it costs the comparison. A harness change must never be
crossed with any other change in one run.

**`codex` was considered and declined.** The installed build is 0.46.0 against a current
0.149.1 — a version gap wide enough that anything measured on it would describe an obsolete
client rather than the vendor's agent. It becomes a candidate after an upgrade, not before.

**What re-opens this:** per-token billing on either account, which would make the dollar figures
real and comparable-in-principle (they would still be two vendors' prices for two vendors'
tokens); or a prime-agent release exposing a project-scoped context flag, which would replace
`preflight()`'s assertion with the isolation the claude arm has.

## Keeping this current

Update in the same session a decision is made or changed. Replace superseded entries rather than
annotating them — this file states what is true now, not how it got here.

[`#95`]: eval/findings/one-arm-bias.md#95-a-judge-pack-is-a-numbering-not-a-set-so-re-evaluating-a-run-left-nine-passes-stacked-on-disk
