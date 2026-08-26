---
id: 163
title: render.nonempty is a GAME criterion and it fails a scene for drawing what it was asked to draw
status: in_review
priority: 2
refs: eval/judge/static.py,eval/judge/evaluate.py,eval/SCENES.md,eval/RUNS.md,tasks/156
done_when: the tier-1 ink window is decided per task class rather than once - a scene's ceiling stated with the measurement behind it, not a number picked to admit the one submission that exists - and static.collect takes it from the caller the way audio_game and film_ticks already do; a control pins both directions per class, including that a BLANK scene frame still fails; eval/runs/wg-scene-s1ts-2026-08-25 is re-graded and its gate verdict recorded either way; and eval/judge/RUBRIC.md says what the window is per class
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/42
---

static.collect scores render.nonempty on mean ink coverage inside a 0.001-0.85 window calibrated on games, which draw a subject against a background. A scene fills the frame by design. The first scene ever graded failed it at 0.966 - sky, road and scenery covering the frame - so the criterion deducted for compliance, the same shape as the stale-cache defect and as the audio criteria that task 156 already stopped asking of a scene. The floor still has work to do (a blank frame must fail); the CEILING is what does not transfer.

## note 2026-08-26

## note 2026-08-26 (orchestrator) — tier 1 is a GATE, which is what makes this urgent

`render.nonempty` is tier 1, and tier 1 is not a weighted term — it is a **gate**. So a false
negative here does not cost a fraction of a score; it can stop a correct submission being scored at
all. That is a different severity from the tier-2 scene defects (`tasks/162`, `tasks/164`) and is
why this sits above them despite the same p2.

**The scene it failed drew what it was asked to draw**, at 0.966 mean ink against a window
calibrated on games. A gate tuned on one task class refusing a correct member of another is the
shape #123 already found once, when tier 1's 7 failures in 68 trials turned out to be 5 lint
findings on a game that played perfectly.

## Calibrate on the population, and say which population

The window exists to catch a submission that renders nothing. **A scene that fills the frame is not
that**, and the fix is not to widen the window until this one passes — that is the tolerance error
`tasks/162` was told to avoid, one criterion over.

State which population each bound was calibrated on, and where a scene bound differs from a game
bound, say so **in the criterion** rather than in a comment. `aspects.applicability()` is the
existing precedent for a check that knows the task class it is being asked about.

## What NOT to do

Do not assume the only affected criterion is this one. The scene run exercised **5 tier-1 audio
criteria that are already not asked of scenes** — someone decided that correctly. Ask the same
question of every tier-1 criterion: is its bound a property of the artifact, or of games? A census
answering that for all of them is worth more than one repaired window, and is a complete answer
even if it finds this is the only one.

## note 2026-08-26

## note 2026-08-26 — the agent was KILLED by an account limit, not by the work

Terminated mid-task: *"You've hit your weekly limit · resets 6pm (America/Sao_Paulo)"*. Its last
line was **"Now verify the three new guards in both directions"**, so the guards exist and are
**unverified**. Nothing about the work had failed.

State left behind, read from the artifacts:

- **PR #42 is open**, branch `task-163-ink-window-per-task-class`.
- `controls` **SUCCESS**, `gates` **FAILURE** on one named step:
  `tokenvalue --selftest (no producer prints a money sigil)`.

That failure is diagnosable without re-running anything: a `$` next to a digit has entered a file
in `PRODUCERS`. It is the same gate that reddened `main` at the start of 2026-08-24 (#162's
origin), and the repair is the unit rather than the number — `tokval`, not `$` (`#159`).

**Do not treat the three guards as verified because CI later goes green.** Green would only mean
the sigil is gone. The guards still need both directions, and the ticket's own instruction stands:
do not widen the window until the stored scene passes.

## note 2026-08-26

## The CI red was NOT a money sigil — the note above misdiagnosed it

The ticket's previous note said *"a `$` next to a digit has entered a file in `PRODUCERS`"* and
pointed at the `no producer prints a money sigil` pin. **That pin was green.** `tokenvalue.py
--selftest` failed on a different one:

    FAIL  every module formatting a *_usd value is in PRODUCERS
        unlisted producer: judge/ink_window_control.py

There is no `$` anywhere in this branch. The cause is `tokenvalue._VALUE`:

    _VALUE = re.compile(r"cost_usd|costUSD|_usd\b|\bspent\b")

`judge/ink_window_control.py` interpolated a local named `spent` — the list of commands
`static.collect` ran before refusing — into an f-string. **The name alone made the module a
discovered money producer**, and `PRODUCERS` does not list it.

**The gate is right and the name was wrong.** Three repairs were available and two are traps:

| | why not |
|---|---|
| add the module to `PRODUCERS` | it produces no money figure. `PRODUCERS` would then name a file with nothing to check, and `discovery finds all N known producers` would be asserting a fiction |
| widen or except `_VALUE` | rule 7 — every reason not to count a failure is a channel a bug can widen. `spent` is in the vocabulary because #159 reserved it |
| **rename the variable** | what is spent here is a *toolchain*, not a token valuation. `ran_commands`. 78/78 pins green |

**The general shape, worth carrying:** this gate's trigger is a *name*, so it fires on
vocabulary rather than on behaviour, and a false positive from it is a signal that the
vocabulary was used for something the project reserves. The lesson is the one `AGENTS.md`
already states about triggers written as properties — the correct response to this class of
red is almost always to change the subject, not the check.

## The guards, verified in both directions at the merged head

Six guards were added across review rounds 1-2. Each was driven to red by a specific input, and
the check that must catch it named in advance:

| guard | forced red by | it said |
|---|---|---|
| every phase must contribute its declared count | every test function replaced by a no-op | `PHASES SHORT: fixtures: 0 of 5; window: 0 of 12; collect propagation: 0 of 3; bound census: 0 of 6; mutants: 0 of 10` |
| the same, per phase | only `mutants` removed | `PHASES SHORT: mutants: 0 of 10` — the 26 remaining checks used to print as a clean pass |
| the exact bound tally | `tests.exist` reclassified `starter` → `no_bound` | only `the tally is exactly {...}` goes red; `registry clean`, `all 14 declared`, `tally partitions` and `exactly one class-dependent` all stay green, which is precisely the hole |
| a per-class range over a missing `mean_ink` | a stored record whose frames block carries no `mean_ink` | `game: 0 of 1 record(s) carry frames.mean_ink - NO RANGE, which is not a range of 0` |
| a re-grade over a missing `mean_ink` | the same record, with `render.nonempty` FAILING | `mean_ink=absent ... NOT REGRADABLE`, and never `hit=floor`. Pre-fix, `nonempty_verdict({'mean_ink': None})` raises `TypeError: float() argument must be ... not 'NoneType'` and takes the whole report with it |
| `NOT ASKED` is not `0 firings` | an empty `--runs-root` | the `NOT ASKED` sentence, and no count |

**And the change itself, from the other side.** Restoring the single `0.001–0.85` window in
`static.INK_WINDOW` — literally the pre-change code — turns exactly 2 of the 36 rows red at
exit 1: `filled on a scene: PASS` and `collect(scene) passes the first stored scene's 0.96561`.
The blank-scene floor row and both game rows stay green. **The window was not widened to admit
the submission**: the scene ceiling is 1.00 because a scene has no ceiling, and the stored
scene at 0.966 is not what chose it — 0.87 and 0.999 pass equally.

## The census answers all 14, and 1 of them was affected

`static.TIER1_BOUND_POPULATION` maps every tier-1 criterion to the population its bound was
calibrated on, over a closed 5-value list, gated by `static.assert_tier1_bounds_declared()` and
tallied by the control: **`no_bound=8, starter=1, capture_contract=1, audio_signal=3,
task_class=1`**. So the complete answer to *"is its bound a property of the artifact, or of
games?"* is: 8 criteria carry no number to calibrate, 5 carry one that transfers, and
`render.nonempty` alone carries one that does not. That is a complete answer, and it did turn
out to be the only affected criterion — but it is now checked rather than asserted, and a
criterion added without an answer fails the gate.
