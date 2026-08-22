# Measurements that ran and certified nothing

A mechanism that ran, reported success, and measured nothing — plus the worse
variants: one that produced a number that was wrong, and one that passed for the
wrong reason.

> Index and the distilled rules: `../FINDINGS.md`


## #19 — the failure mode that is worse than measuring nothing

Eighteen entries in this catalogue share a shape: a mechanism ran, reported success,
and measured nothing. A shared build cache serving another trial's binary. A Stop hook
no-oping because the target directory moved. A test runner exiting 0 over zero tests.
An assertion comparing `null == null`. Every one of them cost a run.

**#19 is a different and worse shape, and it is the one most likely to generalise
beyond this project: a mechanism that measures *something*, hands you a number, and
the number is wrong.**

### What happened

The whole-game evaluator's LLM-judge tier writes its result to `judge.json`. Two judge
processes were pointed at that same path — one a retry launched after the first
appeared to have died. Both wrote it. `write_text` truncates, so the file ended up
holding two complete JSON documents spliced together.

For a window, **that file parsed cleanly.** It was read, and it reported:

> judge score 0.769, forward/reverse instability 0.231

That figure was published upward as the answer to a direct question — *is judge
instability near zero on real agent-built code?* — with the emphatic gloss "0.231, not
near zero". A weighting decision was then reasoned about on top of it.

The next read of the same file failed with `Extra data: line 229 column 1`. Recovering
the surviving document gave:

> judge score **0.846**, instability **0.077**

Both numbers came from complete, legitimate runs of the same judge on the same
unchanged submission. Which one the clean parse had returned is unrecoverable. So the
published figure was not merely uncertain — it was **one of two contradictory results,
selected by a race.**

### Why this is worse than measuring nothing

A mechanism that measures nothing eventually announces itself: `total=0 passed=0`, a
skipped test, an empty report. It wastes a run and then you find it.

A mechanism that measures something and hands you a number is **indistinguishable from
a real result at the moment you act on it.** There is no tell. It has the right shape,
the right magnitude, and it answers the question you asked. The corruption here was
caught one message *after* the number had already been reported as fact — and only
because a completeness gate added for an unrelated reason happened to re-parse the file.

Note the ordering carefully: the gate that caught it had been built minutes earlier, to
guard a different failure (a trial reporting two tiers as though it had three). It was
not looking for this. **The guard that catches a #19 is usually not the guard you wrote
for it.**

### The three defects, separated

1. **Truncating writes to a shared artifact path are not safe even when you believe
   there is only one writer.** Fixed: every tier artifact now goes through a temp file
   and `os.replace`.
2. **A retry that cannot prove the original is dead will double-write.** The four
   "silent deaths" that motivated the retry were not deaths at all — they were the
   harness's 120 s tool-call timeout killing a judge that needs 3–5 minutes, with the
   log empty because `| tail` buffers until exit. Diagnosing the *actual* cause would
   have prevented the retry, and therefore the corruption.
3. **A single reading of a stochastic instrument was reported as its value.** Two runs
   of the same judge on the same artifact differ by 0.077 in score and by 3× in
   instability. n=1 was never enough, and the corruption merely made that visible.

### The rule worth keeping

**Re-read and re-parse an artifact immediately before you quote a number from it, and
quote the spread rather than the reading when the instrument is stochastic.** A number
that arrives once, parses once, and is never checked again has no defence against this
class of error — and unlike every other entry in this catalogue, it will not announce
itself. It will simply be wrong, confidently, in a report someone acts on.

### #19, continued — the rule did not stop its own author

Within an hour of writing the entry above, I committed the same error three more times.

| # | what I did | what was true |
|---|---|---|
| 1 | read `ls -la \| awk '{print $5}'`, saw `Aug`, declared a judging dead | it had completed at 11453 bytes; two redundant re-runs followed |
| 2 | checked a variance file mid-write, saw 0 bytes, declared the loop killed | the loop was alive; I launched a duplicate pipeline alongside it |
| 3 | hardcoded two tier scores **from memory** for a ranking analysis | both were stale: `adversarial` play-bot was 0.538 not 0.4615, `starter` programmatic 0.889 not 1.000 |

The first two are the same mistake as #19 itself. The third is worse and generalises
further: **I treated my own recall as a source.** No file was corrupted; I simply
remembered numbers that later evaluator changes had invalidated, and would have
published a ranking built on them.

So the rule is wider than "re-read the artifact before quoting it":

> **Never quote a value you did not just read from its source, and never infer a
> process's state from its artifact's state.** Check the exit code the process
> reported. An artifact mid-write is indistinguishable from an artifact never written,
> and a remembered number is indistinguishable from a current one.

Both checks were available every time. The exit codes were sitting in the task logs
(`ref_pong exit=0`, `v1 exit=0`) while I was inspecting byte counts, and the stored
records were on disk while I was recalling their contents.

### The variance study #19 forced, and what it found

Six clean single-writer judgings of one unchanged submission, same model, same inputs:

| | min | median | max | spread |
|---|---|---|---|---|
| score | 0.769 | 0.846 | 0.923 | **0.154** |
| instability | 0.077 | 0.115 | 0.231 | 0.154 |

**Both figures previously published from the corrupted file — 0.769/0.231 and
0.846/0.077 — are genuine observed values.** The poisoned artifact was undetectable by
inspection precisely because its readings were in range. No sanity check on magnitude
would have caught it.

Per-criterion, the noise is not diffuse. **Ten of thirteen criteria are stable across
all six runs; three carry the entire spread** — `code.duplication` (1/6),
`code.navigable` (1/6), `look.feedback` (4/6). Those three questions are
underspecified, not the model. That is a fixable defect in the rubric rather than an
argument about LLM judges in general.

Two independent noise sources exist, and `instability` only ever measured one of them:
forward-vs-reverse disagreement *within* a run. The run-to-run spread is a second,
equally large effect the metric never saw. **Reporting instability alone understated
the tier's variability by about half.**


## #22 — a summary statistic that was arithmetically correct and referentially empty

Every other entry in this catalogue is a mechanism that ran, reported success, and
measured nothing. This one is different in mechanism and worth naming separately: the
arithmetic was right, the number was meaningless, and it manufactured a plausible
finding that survived two rounds of scrutiny.

### What happened

The 24-trial matrix reported per-game means:

| game | n | mean cost | mean turns |
|---|---|---|---|
| g1_pong | 8 | $11.30 | 109 |
| g2_tetris3d | 8 | $19.49 | 139 |
| **g3_arena** | 8 | **$7.61** | **66** |

A twin-stick arena shooter — the most mechanically complex of the three tasks —
apparently cost less than Pong and ran in 60% of the turns. The natural reading, which
both I and the reviewer reached independently, was that **the arena prompt was too easy
or admitted a trivially satisfiable reading**, which would have invalidated all eight
arena trials across four stacks.

It was wrong. Four of the eight arena trials had died at 25–27 turns on an account
session limit. Splitting the population:

| group | n | cost | turns | insertions |
|---|---|---|---|---|
| g3_arena, **all** | 8 | $7.61 | 66 | 1040 |
| g3_arena, **completed only** | 4 | **$12.76** | **107** | **1590** |

The completed arena trials sit cleanly between Pong and Tetris on cost, turns, files
and insertions — exactly where a mid-complexity task belongs. There was never anything
wrong with the task.

### Why this is its own failure mode

**$7.61 described no trial that ever ran.** It was not a cheap success and not an
expensive failure; it was the average of four real runs and four non-events. The mean
was computed correctly and referred to nothing.

That is what makes it more dangerous than a broken measurement. A broken measurement
tends to produce an implausible number, or none. This produced a *plausible* number
that fit a story anyone would find credible — "the third task was easier than we
thought" — and it took splitting the population to dislodge it. Two people looked at it
and neither questioned the denominator.

### The rule

**Never compute a mean over a population you have not established is homogeneous.**

Concretely, before any aggregate:

* Partition by terminal status first. `completed`, `max_turns`, `budget_exhausted`,
  `api_error` are four different populations and averaging across them is meaningless.
* Report `n` for each group alongside every mean, and report the groups separately when
  they differ.
* Treat an aggregate that shifts a conclusion as a prompt to check the denominator
  before believing it — the more a number changes your mind, the more it deserves that
  check.

Our own harness already partly enforced this: `runner.py` records `terminal_reason`
precisely because "agent finished" and "we cut it off" are different outcomes, and
`FINDINGS` notes that a naive pass/fail harness "merges four distinct outcomes into
'fail' and turns the A/B into noise". The lesson was written down and the cost mean was
computed across all of them anyway.

---


## #23 — I check other people's work and assert my own

The sharpest statement of the pattern behind several entries above.

Across one session I verified external state carefully — process tables, exit codes,
stored JSON — and repeatedly asserted **my own** actions without any check at all:

| claim | reality |
|---|---|
| "now running evaluation across all 24" | no process was ever spawned |
| "the variance loop failed to start" | it was alive and mid-run |
| "`ref_pong` died, twice" | it had completed; I misread a column |
| "instability is 0.231, not near zero" | read from a file two processes were writing |
| "`_atomic` is in place" (implied by a passing `ast.parse`) | the function had been deleted by a later patch |

The asymmetry is the finding. When the subject was somebody else's process I asked for
evidence. When the subject was my own action I treated the intention as the outcome.

**The rule: confirm your own actions with the same evidence you would demand of
someone else's.** It applies to anything you did, not just processes you started:

- a file you believe you wrote → read it back
- a fix you believe took effect → exercise the code path, not the parser
- a number you believe you computed → recompute it from source before quoting it
- a process you believe you launched → check the process table, past the point where
  it previously failed

The last one has a subtlety worth keeping. A one-shot liveness check confirms a
**spawn**, not a **run**. An earlier evaluation was checked at 20 seconds, was genuinely
alive, and died later on a `NameError`. If a failure mode is known, verify past it.

### Why `ast.parse` was not enough

Two text-surgery patches were applied to the same file. The second replaced a range
that contained a function the first had inserted, silently deleting it. The file still
parsed — an undefined name is not a syntax error — and the crash arrived only when that
code path executed, in a detached background process, an hour later.

**After patching, exercise the path. Import the module and call the function.** A
syntax check verifies the file is Python, not that it works.

---


## 26. The judge's only measured signal was a screenshot artifact

The subjective tier produced a clean per-stack ordering across 24 submissions --
Godot 1.000, Rust 0.974, TypeScript 0.974, Unity 0.910. Adjudicating every firing
against the frames and the source shows **none of it is a property of the games**.

Only 2 of 13 criteria ever fired. `look.feedback` (7 firings) failed submissions for
having no on-screen HUD. The submissions it failed are the ones that **render the most
HUD code**:

| stack | HUD mechanism | appears in `just film`? | `look.feedback` firings |
|---|---|---|---|
| Unity | `OnGUI` / `GUI.Label` (IMGUI) | **no** | 5 |
| TypeScript | `#hud` DOM element, `innerHTML` | **no** | 2 |
| Rust | text drawn through the camera | yes | 0 |
| Godot | `Label` nodes in the scene tree | yes | 0 |

Both exclusions are structural, not incidental. Unity's `RenderHarness.CaptureFrame`
builds a camera and calls `camera.Render()` into an offscreen `RenderTexture`; IMGUI is
emitted in the GUI phase of the player loop and is never part of a camera render.
TypeScript's `capture.ts` calls `document.createElement('canvas')` and reads back its own
offscreen target, so a sibling DOM node cannot be in the pixels. **A correct HUD on those
two stacks is invisible to the instrument by construction.** All 7 firings are false
negatives.

`look.legible` (4 firings) does not survive either. Measured distinct colours in the
arena frames:

| stack | trial | distinct colours | verdict |
|---|---|---|---|
| Rust | t0 / t1 | 13 / 14 | **failed** |
| TypeScript | t0 / t1 | 15 / 9 | passed |
| Unity | t0 / t1 | 4 / 3 | **failed** |
| Godot | t0 / t1 | 12 / 189 | passed |

Rust fails with more colours than TypeScript passes with. The criterion is not tracking
the property it names. Only Unity's two firings have any measurable support.

**The entire subjective ordering is withdrawn.** It reproduces the same shape the
project-lock defect manufactured -- Unity last, across every game -- for the same reason:
a harness assumption that holds on some stacks and fails on others, in a direction that
looks like a result.

### The general form

This is the third stack-specific instrument defect in one project, after the Rust 1-ULP
oscillation and the Unity project lock. All three share a signature worth naming: **the
defect fires on a strict subset of arms, consistently, and therefore looks like a finding
rather than noise.** Consistency was the reason each was believed. A defect that fires on
one arm every time is indistinguishable from a real effect by any stability metric --
`instability` read 0.000 on 22 of 24 submissions while this was happening.

The only thing that separated artifact from effect in all three cases was reading the
mechanism, not the numbers.

### Consequence for the templates, not just the eval

`just film` is a template feature agents use to see their own work. On two of four stacks
it silently omits the HUD. An agent that builds a correct scoreboard and films it sees no
scoreboard. That is a defect in the starters independent of any eval, and it is the kind
that teaches an agent to delete working code.

---


## 34. Making the task harder created a false negative in a criterion that had never fired

`ball.moves` — "does the ball move on its own?" — had fired **zero times across 24
submissions** in the previous matrix. On the first evaluation under the new task it fired
against **5 of the 8** Pong submissions — `godot__t1`, `rust__t1`, `ts__t0`, `ts__t1`,
`unity__t0` — every one with the evidence *"ball travelled 0.0 units over 60 ticks"*.

(I first reported that as "all eight", having read a set of *stack names* as a count of
*submissions*. It is five. The distribution matters: two of two on `ts` and one of two on
each other stack is uneven, so the defect could have manufactured a ranking rather than
merely depressing everything equally. Corrected before it was acted on, but it is the same
"never quote a value you did not just read from its source" failure this catalogue opens
with.)

The submission is not broken. Its source says why:

```gdscript
const SERVE_DELAY: int = 46
## Longer for the very first serve of a match, so the title card is readable.
const OPENING_DELAY: int = 104
```

The ball is held for 104 ticks so an opening title card can be read. The bot idled a fixed
60 ticks from tick 0 and concluded the ball was dead.

**The criterion failed a submission for doing the presentation work the new task
explicitly asks for.** The prompt now requires that "a player who has never seen it can
tell what to do"; the submission built a title card; the grader called it a defect.

### Why three matrices missed it

`ref_pong`, the reference implementation the criterion was validated against, **serves
immediately.** There is no serve delay anywhere in it. So the assertion and its control
shared the same unstated precondition — the ball is live at tick 0 — and no amount of
running them together could surface it. This is `IMPROVEMENTS.md` (root) iteration 1b in a new place:
*a control suite written by the same author as the assertions shares the author's
assumptions.*

It is also the sixteenth instance of the one pattern behind every play-bot false negative
here: **the criterion waited for a condition instead of establishing one.**

### The repair, pinned in both directions

The bot now steps until the ball reports a non-zero velocity — up to 512 ticks, eight
seconds, enough for a title card, a countdown and a pause — and only then measures
movement. Validated three ways, all observed:

| case | verdict |
|---|---|
| reference game (serves immediately) | PASS |
| **variant with a 104-tick opening title card** — the case that motivated the repair | **PASS** — "ball travelled 243.8 units over the 60 ticks after it went live (waited 104 ticks for the serve)" |
| the same variant under the OLD criterion | **FAIL** — "moved 0.0 units" |
| mutant: the ball never moves, though it still reports a velocity | **FAIL** |

The last row is the one that matters. A repair that only had to stop producing false
negatives could have been "assert True"; the frozen-ball mutant is what distinguishes a
fixed criterion from a disabled one — and it is deliberately a ball that still *reports* a
velocity, so detecting that the ball went live is not enough to pass.

### The general form

> **When you make a task harder, the graders written for the easier task acquire new false
> negatives — in criteria that had never fired, because the new behaviour was previously
> impossible.** Adding a requirement does not only test the subject; it moves the subject
> into regions of behaviour space the instrument was never exercised on.

Every criterion validated only against pre-change references is suspect after a task
change, whether or not it has ever failed anything. "Never fired" is not evidence of
correctness; here it was evidence that the reference could not produce the input that
breaks it.

### #34, continued — the same shape twice more, both punishing the new requirements

Two further criteria failed correct submissions in the first evaluation under the harder
task, and both fail for the same reason as `ball.moves`: they were written against a
reference that could not produce the behaviour the new task asks for.

**`gameover.triggers`** failed two Tetris submissions with evidence that contradicted its
own verdict: *"stacked into one corner for 179 ticks without the game ending;
**game_over=True**"*. The loop breaks out when no piece is falling — and `piece: null` is
exactly what a stacked-out game reports — without checking `game_over` first. It exited
through the success condition and reported failure. (The adjacent `if over_at:` was also a
truthiness test, so a game ending at tick 0 would have been missed; now `is not None`.)

**`match.ends`** failed a Rust submission: *"reached 11-0 at tick 3666; after 600 more
ticks of play the score is 2-0"*. The submission holds a game-over card for
`GAME_OVER_LOCKOUT_TICKS = 96` and then lets a control start a new match. The bot kept
holding paddle controls for 600 ticks after the win, pressed the reset, and failed the
submission **for implementing the reset the task's own wording contemplates** — "the game
then stops accepting play *until it is reset*". It now presses nothing after the win, which
tests that play stopped rather than that reset is impossible, and is strictly stronger
against the failure it exists to catch: a game still playing changes the score with no
input at all.

### The first repair of `ball.moves` was itself wrong — a proxy is not the property

The repair waited for the ball to report a **non-zero velocity**, then measured movement
over the next 60 ticks. It passed the reference, passed the title-card variant, failed the
frozen-ball mutant — all three checks green — and then failed a real Unity submission:

> *"ball travelled 0.0 units over the 60 ticks after it went live (waited 1 ticks for the
> serve)"*

That submission sets the serve velocity at tick 1 and holds the ball's position during its
countdown. Velocity was chosen as a **proxy for liveness**, and different submissions make
velocity live at different moments relative to movement. The criterion is named
`ball.moves`; the repair measured something adjacent to moving.

Now it watches the ball's position directly — step until displacement exceeds 1.0 unit,
up to 512 ticks — which is the named property and is indifferent to how any submission
sequences velocity, position and countdowns. Re-pinned: reference PASS, 104-tick title-card
variant PASS, frozen-ball mutant FAIL.

> **When repairing an assertion, assert the property in its own name.** A proxy passes
> every control built from the same assumption as the proxy, and fails on the first
> submission that separates the two. Mutants do not catch this: the mutant removed
> movement *and* velocity together, so it went red for the wrong reason and looked like
> validation.

### What these have in common is not carelessness

Each was correct against `ref_pong` / `ref_tetris3d`, which serve immediately, never report
a null piece while ending, and have no reset control. **The references cannot exhibit the
behaviours the new task rewards** — an opening title card, a clear end state, a way to play
again — so no amount of running the criteria against them could have surfaced any of it.

That sharpens the rule. It is not only that a task change creates new false negatives; it
is that **the controls change meaning at the same moment the task does, and they change
silently.** A reference implementation is a frozen answer to the old question. After a task
change every criterion is unvalidated until its reference exhibits the new behaviour, and
"the controls still pass" is evidence about the controls, not about the criteria.

---


## 37. Two agreeing readings said "stalled"; the descendants said "compiling"

Four arena agents, 2026-08-15. Every check in `PROTOCOL.md`'s own diagnostic list agreed:

| check | reading |
|---|---|
| `pgrep -P <driver>` | 4 children alive |
| `find <tree> -type f -mmin -20` | **0 files, on all four trees** |
| `ps %cpu` | **0.0%, on all four** |
| capacity probe on haiku | `READY` — the account was fine |

Last write across the four trees was 23 to 33 minutes earlier, and they had gone quiet within a
ten-minute window of each other. That is the signature of a session limit, and the capacity probe
had just ruled one out, which made it look like something worse.

The fifth check settled it in one line:

```
43256  13:48  /usr/bin/env bash tools/unity-compile.sh check errors
45383   6:37  .../gdformat sim view
48703   2:24  /usr/bin/env bash tools/unity-compile.sh warm errors
```

**All four were mid-build.** A Unity batchmode compile fourteen minutes in writes nothing new into
the work tree and consumes no CPU in the agent's own process — so the agent is, by every check in
the list, indistinguishable from a dead one.

### Why the list failed

`pgrep -P <driver-pid>` lists the driver's **children**. The compilers are its
**grandchildren**, launched by the agent's own Bash calls. The list contained a check that
looks like "is work in flight" and is really "did the process I spawned survive".

Fixed in `PROTOCOL.md`: the descendant scan is now step 2, ahead of the file-write check, and the
file-write check is labelled weak evidence because a long build legitimately produces none.

### And the probe I used to validate the probe was itself broken

Following the rule that a zero from an unvalidated check is not a measurement, I ran a positive
control: `touch /tmp/probecheck`, then `find /tmp -maxdepth 1 -name probecheck -mmin -5`. **It
returned 0** — for a file created one second earlier.

`/tmp` is a symlink to `/private/tmp` on macOS, and `find` does not follow a symlink given as its
starting path. The same check against `/private/var/folders/...` — the real path the work trees
live under — returned 1.

So the control I ran to check whether my instrument worked was measured with a *second* broken
instrument, and had I run it only on `/tmp` I would have concluded my activity check was broken
when it was not. This is the `-newermt` trap in different clothing, and the third time in this
project that a `find` invocation has returned a confident zero for a reason that has nothing to do
with the question. Both are now in `PROTOCOL.md` as commands rather than as principles.

### The rule, and it is the deepest version of this project's central pattern

> **A control shares the assumptions of the thing it controls, unless you deliberately make it
> not.**

The standing rule in `PROTOCOL.md` — *before concluding "nothing is happening", run the check
against something you know IS happening* — is sound and it did not save me, because the thing I
ran it against was reached by a path with the same defect. The control and the check failed
together, silently, for one shared reason.

That is the same shape as three earlier findings here, and naming the family is the point:

| # | the control | the assumption it shared |
|---|---|---|
| #21 | judge validated on `ref_pong` and `broken` | both artifacts were unambiguous, which is where agreement is cheap |
| #33 | cap effect tested on Pong | Pong has no budget headroom, so it cannot show the effect *whatever the truth is* |
| #34 | criteria validated against `ref_pong` | the reference serves immediately, so no criterion could see a title card |
| **#37** | `find` against a path I had just written | the path was a symlink, exactly as the checked path might have been |

In every case the control was run, passed or returned the expected value, and certified nothing —
because it could not have come out any other way. **Ask of any control: what would make it fail?
If the answer is "the same thing that would make the check fail", it is not a control, it is a
second copy of the check.**

Concretely, for this class: run the control against the *same* path, filesystem and flags as the
check it validates, and prefer a control that exercises a *different* mechanism from the one under
test — a second instrument, not a second reading.

### The part worth carrying

The project's standing warning is that **two bad signals corroborate each other**. This is the
sharper version: *four* signals agreed, one of them was a genuine positive result (the capacity
probe worked), and the diagnosis was still wrong — because all four measured properties of the
agent process and none measured what the agent had asked the operating system to do.

Ask what the subject is *blocked on*, not merely whether it is alive.

---


## 39. The mutant caught what the reference, the fixture's own tests and the bot's own run all missed

Building the g4 platformer grader produced a clean natural experiment, because the whole
apparatus was written fresh and every part of it was green before the mutants ran:

| check | verdict with the defect present |
|---|---|
| reference fixture `just verify` | **exit 0** |
| the fixture's own 19 behavioural tests | **19/19** |
| the play-bot against the reference | **19/19 scored criteria pass** |
| the mutant | **escaped — `player.falls` passed a game with gravity set to zero** |

`player.falls` asked whether the character falls when it walks off a ledge, and accepted
either *a loss of height* **or** *`grounded` becoming false*. With gravity zero the
character walks off the ledge and **hangs in the air**: it is not standing on anything, so
`grounded` is false, so the criterion fired. It is not falling. It never falls.

The criterion now asserts a loss of height and nothing else.

### This is #34 reproducing in a system built by someone who had just read #34

The first repair of `ball.moves` measured *velocity* as a proxy for *movement*, passed
every control built from the same assumption, and failed on the first submission that
separated the two. The rule written down from it was: **assert the property in its own
name.** I then wrote `player.falls` — a criterion whose name is a change in height — with
a flag as an alternative condition, in a file whose own docstring cites #34.

That is the third time in this catalogue a rule has been violated by the person who had
just written it, and it is evidence about the rules rather than the author: **a rule that
is a slogan is a rule you can satisfy in your head while breaking it in the code.** The
mechanical form is the one that works. "Assert the property in its own name" did not fire;
`bot_mutants.py` did.

### The mutant suite is necessary and NOT sufficient, and the same build proves it

Two of the three defects found here were **not** caught by a mutant, and they could not
have been, because they are a different failure. `player.falls` **could not fail** — a
mutant that breaks falling makes it fail to fire, and the suite sees that. The other two
**passed for the wrong reason**:

| defect | what the mutant sees |
|---|---|
| `player.falls` accepted a flag instead of a height | **caught** — the zero-gravity mutant escaped, and the escape is the report |
| `knockback.applied` asked whether `vx` *decreased* | a mutant deleting the impulse leaves `vx` at 0, which IS a decrease. It would have gone green |
| `anim.states` read `jump` for the "walk" activity | it still saw three distinct labels, which is a pass. Nothing to escape |

A mutant asks *does this criterion notice when I break the thing it names?* It cannot ask
*is the criterion noticing for the reason it claims?* A criterion that passes on the wrong
evidence passes the mutant too, because the mutant breaks the right mechanism and the
criterion was never reading it.

> **Mutants catch criteria that cannot fail. Only reading the evidence string catches
> criteria that pass for the wrong reason.** The second class is invisible to every
> aggregate, every stability metric and the mutant suite itself — and it is the class that
> produced this project's withdrawn stack ranking (#26).

The operational consequence: `knockback.applied` and `anim.states` were both found by
reading the evidence text of a **passing** criterion. That is the argument for criteria
that report what they saw rather than a verdict, and for reading the passes rather than
only the failures.

### Two smaller escapes in the same build, both instructive

**`knockback.applied`** asked whether `vx` *decreased* when the enemy was on the right.
Deleting the impulse entirely leaves `vx` at 0 — which is a decrease. The mutant would have
passed. It now asserts the sign: knocked *away*. **A criterion phrased as a comparison
against the previous value admits "became nothing" as a pass.**

**`anim.states`** sampled the walking label while the character was airborne after being
knocked back, and read `jump` for both the "walk" and the "air" activity. It still passed —
three distinct labels out of four is a pass — so this is the shape that never announces
itself: **a criterion that passes for the wrong reason.** It now waits until the character
is grounded before sampling, and reads four distinct labels. Nothing but reading the
evidence string would have found it, which is the argument for criteria that report what
they saw rather than a verdict.

### The general form

> **A control suite written by the author of the assertions shares the author's blind
> spots; a mutant does not, because it is written against the CODE rather than against the
> intent.** Green from the reference, the tests and the bot is three readings of one
> assumption. The mutant is the only member of the set that can disagree.

Cost of finding it this way: minutes. Cost of finding it in a $250-300 matrix: the matrix.

---


## 42. The calibration trial was an outlier, and one trial cannot calibrate a 1.6x-variance process

`g3_arena__rust__t0` was run alone to price the no-cap regime, and its $72.83 was used to
project the remaining seven at ~$510 and to re-cost the platformer matrix at $1,000-1,700.
Three more trials of the same task under the identical configuration have now landed:

| trial | cost | turns |
|---|---|---|
| `rust__t0` *(the calibration)* | **$72.83** | **369** |
| `rust__t1` | $44.86 | 240 |
| `ts__t0` | $34.27 | 239 |
| `ts__t1` | $41.66 | 231 |

**Within one cell — same stack, same game, same prompt, same flags, same starter —
rust cost $72.83 and $44.86. That is 1.62x.** Across the four it is 2.13x.

The calibration was the most expensive of the four, by a wide margin, and it was chosen
*because* rust was expected to be the expensive end. That expectation was right and it did not
help: the number it produced was 1.8x the mean of the other three.

### The methodological result

`PROTOCOL.md` and `cmd_plan` have both told every reader since before the first matrix to
**"run one trial and re-run `plan` with the measured number"**. That advice is sound about
*order* — measure before committing — and wrong about *sufficiency*:

> **A single trial cannot calibrate a process whose within-cell spread is 1.6x.** The
> projection it supports is a point estimate drawn from a distribution nobody has measured the
> width of, and a 60% error in either direction is inside the noise.

The same trap as #21 and #33 in a third costume: an instrument that reports a confident value
where the underlying quantity is variable. There, judge stability was a property of the
artifact and cap effects needed headroom to show; here, cost is a random variable and n=1
estimates its mean with no interval at all.

**What to do instead:** calibrate with **two trials in different cells**, report the spread,
and project from the range rather than the point. Two trials cost roughly what one wrong
projection costs in either direction, and they are the difference between "$510" and
"somewhere between $280 and $510".

### The consequence for the numbers already published

| projection | made from | revised |
|---|---|---|
| the seven arena trials | $72.83 x 7 = **~$510** | ~$48 x 7 = **~$285-340** |
| a 24-trial g4 platformer matrix | **$1,000-1,700** | ~$1,160 at the mean, but with 2.13x observed spread the honest range is **~$800-1,900** |

Both were stated with the caveat that they rested on one trial and that rust might be the
expensive end. **The caveat was correct and it did not stop the number being used.** A figure
with a stated uncertainty still gets acted on as a figure — so where the uncertainty is this
wide, report the range as the headline and the point estimate not at all.

### And it bears on the paced-vs-truncated question

Turn counts, uncapped: **369, 240, 239, 231.** Three of the four stop between 231 and 240 —
*below* the 250-turn ceiling every earlier trial ran under. If 250 had been broadly truncating
this task, uncapped trials should cluster above it, not beneath it. Only the calibration ran
past, and it is the outlier in cost as well as turns.

That is evidence against "the ceiling was cutting most trials short", and it arrives from
trials run for a different purpose entirely. The pre-registered Tetris experiment still settles
the question for its own cell; this weakens the general version of the claim before it runs.

---


## 46. Two criteria failed six submissions for four kinds of enemy the bot never lived long enough to meet

`enemy.kinds` and `enemies.chase` failed **6 of 6** driveable `g3_arena` submissions, with
evidence identical to the character across all six:

```
enemy.kinds    distinct kinds observed: ['drifter']
enemies.chase  ... over 90 stationary ticks its distance went 0.4 -> 0.4,
               heading alignment None; the player died before the target could be moved
```

Six for six, same string. By this catalogue's own rule that should have been read as an
instrument defect on sight; instead it sat in a table as a 0.94 arena score for two stacks.

Adjudicated against source. Every one of the six defines **four** kinds and gates them by
wave:

| submission | gating |
|---|---|
| ts | `['drifter', 10], ['weaver', wave>=2 ? 7:0], ['charger', wave>=3 ? 5:0], ['splitter', wave>=4 ? 4:0]` |
| unity | `weaver = wave >= 2 ? ... : 0; lance = wave >= 3 ? ... : 0; splitter = wave >= 4 ? ... : 0` |
| godot | `KIND_NAMES = ["drifter", "weaver", "charger", "splitter"]`, each with "the first wave this kind can appear in" |

All three did the thing the task rewards — introduce one new behaviour per wave — and the
grader called it one kind of enemy.

### Why the bot never saw wave 2

`_kinds` sampled whatever wandered past while sending **empty inputs**, then "gave later
waves a chance" by idling up to 600 more. **Standing still is fatal in this game.** Measured
across the reference and all six submissions, an idle player dies between tick 362 and tick
844. The bot never killed anything, so no wave ever ended, so no new kind ever arrived — and
it was dead before its own budget ran out.

`enemies.chase` then ran in the same session, on the corpse. Its evidence claimed "90
stationary ticks"; the loop had in fact broken after **one**, because `game_over` was already
true, and the string printed the requested tick count rather than the elapsed one. A false
negative and a false evidence string, from the same line.

### The reference could not have found this, and neither could a mutant

`ref_arena` spawned all three kinds in **every** wave, with a comment saying so: *"a single
wave is enough to exhibit the variety the task requires."* The criterion was therefore
satisfied on the first tick of wave 1, by construction, on the only artifact it was ever
validated against.

> **A mutant removes the mechanism a criterion names. It cannot manufacture an input the
> criterion mishandles.** `ONE_KIND` collapses three kinds to one and the criterion goes red,
> exactly as designed — and that tells you nothing about whether the criterion can find three
> kinds that arrive late. The reference is a frozen answer to the task as its author read it,
> so **every criterion is unvalidated on any behaviour the reference does not exhibit.**

The repair therefore began by changing the *reference*: kinds now unlock at waves 1, 2 and 3,
matching the shape all six submissions chose. The old criteria then failed the reference with
byte-identical evidence to the six real failures — which is the pin that matters, because it
is a known-correct implementation being failed.

### The repair, and what each half establishes

**`enemy.kinds`** gets its own session and plays: aim at the nearest live enemy, fire, and
hold a standoff. Meeting three kinds now requires clearing waves, which requires killing,
which requires surviving. Reference: three kinds, wave 3, 9 kills, 525 ticks, player alive.

The evidence string now separates the two ways it can fail, which the old one could not:
*"reached wave 12 from wave 1 over 4,537 ticks with 102 kills"* and still one kind is a
submission defect; *"reached wave 1"* is the bot failing to establish its condition.

**`enemies.chase`** gets its own session and the player **circles** the enemy at a fixed
radius. Two things must hold, and each defeats a different impostor: every step the enemy
takes points at the player *now* (measured per tick, so a fixed heading cannot average above
the floor), and the enemy **turns** when the player goes somewhere else.

Two earlier designs were measured and discarded, and both looked right:

| design | why it failed |
|---|---|
| stand still, watch the distance shrink | standing still is fatal — this is the original defect |
| run to one far corner, then the opposite one | the player outruns the enemy, the gap blows out to 730 units, and the direction from enemy to player then swings **0.36 of a possible 2.00**. The turn test had nothing to read |
| aim the orbit at a fixed goal direction | with the goal set to the antipode the tangential term is **identically zero** — a saddle point. A perfect chaser scored a heading swing of 0.00 |

The player being three times an enemy's speed is what makes the circle work, and it is the
only way found to demand a large turn without either outrunning the enemy or walking into it.
A collision the *player* caused would otherwise read as a chase, so contact counts only when
the enemy was already closing.

### The defect my own repair introduced, and what found it

Every exit from a chase leg returned a dict. One exit — the enemy reaching the player —
returned a **short** dict, and the caller read `align` off it before testing `gone`. On
`g3_arena__godot__t1` the bot raised `KeyError: 'align'` and the fail-closed path scored
**all 23 criteria FALSE**. A 0.000, on one stack, from a submission whose enemies chase
correctly.

The reference never takes that branch. So: the reference was green, all 36 mutants were
green, the three session-lock controls were green, and the defect was found by **a real
submission**, on the first re-grade after the repair. It is the same shape as the 0.000 in
#49 and would have read the same way.

Two things came out of it, and the second matters more:

- every leg now goes through **one constructor**, so no exit can carry a different shape;
- `bot_mutants.py` gains a **variants** suite: correct games the reference does not resemble,
  where *every* criterion must still pass. Two entries, both paid for — a 104-tick opening
  title card (copied from a real Godot submission, and the constant had been sitting in that
  file for a day, correctly labelled *"a VARIANT that must still PASS"*, wired into nothing),
  and enemies faster than the player, which is the only way to reach the contact branch.

> **A mutant suite asks whether a criterion can fail. A variant suite asks whether it can
> still pass.** Every false negative this project has adjudicated — sixteen in one sweep, then
> `ball.moves`, then these two — was of the second kind, and until now nothing ran that
> question automatically.

### Re-graded

Offline, tier 1 untouched, so the change measured is the bot and nothing else.

| cell | before | after |
|---|---|---|
| godot t0, t1 | 0.940 | **1.000** |
| unity t0, t1 | 0.940 | **1.000** |
| ts t0, t1 | 0.8957 | **0.9557** |
| rust t0, t1 | 0.000 | **0.000** (unchanged, and required — see #49) |


## 48. Two findings were reintroduced by the agent that had both of them open in front of it

The criteria repaired in #46 were **written after** #29 (fifteen criteria that observed
instead of establishing) and #34 (a criterion validated against a reference that could not
exhibit the new behaviour). They were written into a file whose own module docstring says, in
capitals:

> `EVERY CRITERION HERE ESTABLISHES ITS CONDITION AND THEN MEASURES. None waits for a
> condition to arrive.`

`_kinds` waited for a condition to arrive. `_chase` waited for one and measured a corpse. The
reference they were validated against could not produce the behaviour that breaks them, which
is #34 exactly.

This is the fourth time in this catalogue a rule has been broken by the person who had just
written it (#19, #23, #37, #39). At four instances it is no longer an anecdote about
attention.

> **A rule that is a slogan is a rule you can satisfy in your head while breaking it in the
> code.** "Establishes its condition" felt true while writing `_kinds`, because the code steps
> the simulation forward 600 ticks — it *does something*. What it does not do is cause the
> thing being asserted about.

The operative distinction, which the slogan does not carry:

> **Ask what the criterion would need the SUBJECT to do, and then make the bot do the thing
> that forces it.** Not "does my code act" — "is the condition under test a consequence of my
> action, or of luck?"

And the mechanical form, which is the only one that has ever fired:

> **A mutant suite is necessary and not sufficient, and a variants suite is the missing
> half.** #39 said mutants catch criteria that cannot fail and miss criteria that pass for the
> wrong reason. #46 adds the third class they cannot see: criteria that fail correct work the
> reference does not resemble. Both halves now run in `bot_mutants.py`; neither is a habit
> anyone has to remember.


## 50. Two independent agent runs produce identical grades in every cell — the instrument has no resolution below the cell

Twelve cells: 3 games x 4 stacks, two independent trials each. After the #46 repair and a
full offline re-grade, comparing `t0` against `t1` **criterion by criterion**, not by total:

| | |
|---|---|
| criteria compared | **380** |
| cells where a total differs | **0 of 12** |
| **criteria where a verdict differs** | **0 of 380** |
| evidence strings that differ | **219 of 380 (58%)** |

The last row is the control, and without it the result is unreadable. Identical totals are
consistent with two hypotheses — *the instrument cannot separate them*, and *the two
submissions are the same thing* — and a per-criterion comparison of verdicts alone does not
separate those either. **The evidence strings do:** the majority differ, and they differ in
substance, because the two submissions in a cell were built by independent agent runs and
behave differently in measurable detail. Different artifacts; different measurements; the same
380 verdicts.

> **Two independent agent runs produce identical per-criterion grades in every cell. The
> deterministic tiers have no resolution below the cell.**

That is a statement about the instrument, not about the agents. It also bounds every stack
claim this project could make from these tiers: an instrument whose within-cell resolution is
zero cannot report a between-cell difference smaller than the gap it has never resolved.

Twenty of the twenty-four cells now sit at exactly **1.000**. The remaining four are two
stacks measured on a broken machine (#49), which is the finding, not the difference.

**This does not mean the tiers measured nothing.** They are load-bearing in the other
direction: they caught a submission that does not compile, they caught two whose own gate is
red, and every criterion in them is pinned by a mutant. What they cannot do is discriminate
between four well-built templates on tasks these agents complete. That has now been the
outcome of the spec-change suite, three whole-game matrices and a cost metric nobody designed
as a discriminator — four independent routes to the same null.


## 51. The adjudication gate counted a judge's honest citations as fabrications, and doubled its own number

Gate 4 exists to remove claims nobody could have verified — the population the withdrawn
stack ranking (#26) turned out to live in entirely. On its first run against a real field it
reported:

> `citing a path the submission does not have: 15 of 16`

Fifteen of sixteen claims apparently unfalsifiable. That is the shape of a finding, and the
finding would have been *"the specialist judges fabricate their evidence"*.

### It is two populations, and only one of them is a problem

`anonymise.py` renames files to `sim/01.gd`, `view/03.rs`, `view/06.cs`. **It does not rewrite
the filenames the authors wrote INSIDE those files**, and agent-written code is full of them:

```
sim/04.gd:8   ## This file depends on NOTHING (not even [Sim]), which is what lets `sim/sim.gd`
other/05.gd:67 + "it inside a tick drops and duplicates input. Read sim/intents.gd instead; "
```

A judge that reads `sim/04.gd` and cites `sim/sim.gd` is quoting a string it really read. It
is not a path in the pack, and it is not a fabrication either. Splitting the two:

| | |
|---|---|
| citations naming something present in the pack's **text** | **9** |
| citations naming something found **nowhere** in the pack | **11** |
| single "paths not found" count the gate had reported | **15 of 16 claims** |

### And the second population is not what it looks like either

The claims in the "nowhere" bucket were spot-checked against source rather than counted. One
reads:

> *"Piece color is a direct `match kind { PieceKind::I => ..., ... }` over the enum in
> **`game/src/lib.rs:75-85`** with no wildcard arm"*

The pack contains exactly that construct — at **`view/03.rs:76-77`**. The construct is real,
the line range is nearly right, and the filename is invented. The judge read an anonymised
file and **reconstructed a plausible original path** for it. Across the field, 15 of 23
quoted code tokens (65%) locate verbatim in the pack.

> **On an anonymised pack, a path check measures PATH RECONSTRUCTION, not claim validity.**
> The flag means *the citation cannot be followed*. It does not mean *the claim is false*, and
> the gate's summary line said the second while measuring the first.

### Why this is the catalogue's own pattern again

A gate ran, produced a number in range, and the number answered a different question from the
one its label asked. It is #19's shape — *a mechanism that measures something and hands you a
number that is wrong* — arriving in the tool built to catch exactly that, which is the part
worth keeping:

> **The adjudicator is an instrument too, and nothing adjudicates the adjudicator.** It was
> caught only by opening one flagged file and finding the cited construct sitting in it under
> a different name. That is the same move that resolved #25, #26 and #46 — read the mechanism,
> not the count.

Fixed: `adjudicate.py` reports the two populations separately, names why the middle one is not
a defect, and its summary no longer asserts that an unfollowable citation is an uncheckable
claim.

### #51, continued — it took FOUR fixes, and every one of them was inflating the number

Run over the full five-aspect field, the headline moved every time it was corrected:

| reading | cause of the excess |
|---|---|
| **15 of 16 claims** (first run, one aspect) | filenames the authors wrote *inside* the files were counted as phantom paths |
| **54 of 80** | the adjudicator resolved **every** aspect against `judge_pack/code`, so a `ux` judge citing `frame_0000.png` — a real file in `eval/frames/` — was flagged |
| **31 of 80** | `PATH_RE` alternated `js` before `json` with no trailing boundary, so every honest citation of `telemetry.json` or `audio.json` was captured as `telemetry.js` |
| **15 of 80** *(current)* | pack artifacts the packer itself writes (`telemetry.json`, `audio.json`, `CHANGED.txt`) live in a temp directory that is deleted, so a judge quoting its own evidence by name could never resolve |

**Four independent mechanisms, all in the same direction.** None of them was a judge defect;
all of them looked like one. A gate whose errors are one-sided will always tell you the
subject is worse than it is, and this gate's output is the input to a decision about
withdrawing an aspect.

> **When a check's failures are one-sided, its headline is a bound, not a measurement.** Ask
> what the check does when the subject is innocent — here, four different innocent behaviours
> each produced a flag.

### The number that survives, split properly, is 1 of 80

The coordinator's question — *is this path reconstruction or invented claims?* — is answerable
mechanically, and they are different defects with different fixes. A citation whose **stem** is
a symbol in the pack (`GameView`, `palette`, `pieces`) is a renamed real file; one whose stem
appears nowhere and whose quoted code is absent is a claim nobody can check.

| | |
|---|---|
| `architecture` citations flagged "found nowhere" | 11 |
| of those, **path reconstruction** | **11** |
| of those, **claims not locatable at all** | **0** |

Across all five aspects and 80 claims: **11** name something in the pack's text, **15** are
reconstructions, and **1** is unlocatable. The reading that started as *"the judges fabricate
their evidence, 15 of 16"* ends at **1 of 80**.

So the fix is not to the judge. It is to the pack and the brief: the code briefs now say
*"cite files by the path they have HERE — `sim/03.src` — and never by a name you infer from
their contents"*, and `adjudicate.py` reports `paths_reconstructed` and `paths_unlocatable`
separately so the two defects can never again be summed.

### And the number that survives is informative

| aspect | reads | claims citing a name found nowhere |
|---|---|---|
| `architecture` | code | **11 of 16** |
| `idiomatic` | code | **4 of 16** (all naming `three.js`, a library rather than a file) |
| `audio` | audio | **0 of 16** |
| `fun` | frames + telemetry | **0 of 16** |
| `ux` | frames | **0 of 16** |

**Only the two code aspects invent citations, and they are the only two that read anonymised
filenames.** A judge shown `frame_0000.png` cites `frame_0000.png`; a judge shown `sim/04.gd`
cites `sim/sim.gd`, because the anonymised name is not what the file calls itself. The
behaviour is a property of the anonymisation, not of the judge's honesty — which is the same
conclusion the first fix reached, now supported by a clean contrast across five aspects
instead of one.


## 52. The best-behaved subjective judge was ranking how long the play-bot happened to run

`fun` was the one aspect that passed its gates. Across two presentation orders on
`g2_tetris3d` it separated the field on both (modal fraction 0.375 and 0.500 — the widest
spread any aspect produced), and its order-invariance was the only clean one measured:
**Kendall tau 1.0 over 19 comparable pairs**, with 2 of 8 submissions moving. Every other
aspect either ceilinged on one order or produced a tau on too few comparable pairs to read.

So it looked like the layer's one success. It is the layer's #26.

### The mechanism, in the data

`fun` reads 12 frames and `telemetry.json`. The telemetry is measured from the play-bot's own
driven session — by design, so that "the tiers cannot disagree about what happened in the
run". That session exists to satisfy criteria, not to be a representative play, and for
`g2_tetris3d` it is **6 to 9 events over 6 to 9 seconds**.

Its headline pacing number is `longest_quiet_stretch_seconds`. Measured across all eight
submissions:

| | secs of play | longest quiet stretch | ratio | events |
|---|---|---|---|---|
| godot t0 | 8.6 | 8.23 | **0.96** | 7 |
| godot t1 | 5.8 | 5.67 | **0.98** | 6 |
| rust t0 | 7.2 | 7.17 | **1.00** | 7 |
| rust t1 | 7.2 | 6.92 | **0.96** | 9 |
| ts t0 | 6.2 | 5.77 | **0.93** | 9 |
| ts t1 | 7.8 | 7.48 | **0.96** | 8 |
| unity t0 | 7.9 | 7.86 | **0.99** | 7 |
| unity t1 | 7.4 | 7.28 | **0.98** | 7 |

**The longest gap between events is 93–100% of the entire run, for every submission.** With
seven events in eight seconds it cannot be anything else. The metric is degenerate by
construction: it is run length wearing a pacing label.

And that is what the scores track. Spearman correlation between `fun`'s score and the
telemetry fields, both orders:

| field | seed 0 | seed 1 |
|---|---|---|
| `seconds_of_play` | **−0.60** | **−0.45** |
| `ticks` | **−0.60** | **−0.45** |
| `longest_quiet_stretch_seconds` | −0.52 | −0.45 |
| `events_per_second` | +0.29 | +0.43 |

The shorter the play-bot's run, the higher the fun score. **Run length is a property of the
harness's driving, not of the game.**

### What is and is not established

n=8, so ρ≈−0.5 is suggestive rather than significant, and the frames are a second input this
does not account for. The *degeneracy* needs no statistics: the ratio table is arithmetic, and
a quantity that is 0.93–1.00 of the run in every arm carries no information whatever the
judge does with it.

**So the claim is not "`fun` is measuring run length". It is: `fun`'s single most legible
piece of evidence is meaningless, and its scores move with the one harness quantity that
varies.** That is enough to withhold the aspect, and withholding it is the whole point of the
gates.

### Why the gates passed it

Ceiling, order-invariance and independence are all statistical, and **an artifact is more
order-invariant than a judgement, not less**. A judge latching onto a stable harness number
will reproduce its ranking perfectly across reshuffles — which is exactly what tau 1.0 over 19
pairs means here. `instability` read 0.000 through the whole of #26 for the same reason.

> **A gate that measures stability rewards artifacts.** The more mechanical the thing a judge
> has latched onto, the better it scores on every reliability metric this layer has. Only
> reading the evidence separates them, and gate 4 is the only gate that does.

### Fixed, and what is not fixed

`_telemetry_evidence` now reports `quiet_fraction_of_run` and, above 0.9, an explicit
`pacing_evidence_warning` naming the event count and the run length. That stops the number
being read as pacing; it does not make the evidence good.

**The real repair is a representative play session**, separate from the criteria drive — and
that is a change to what `fun` is fed, not to how it is judged.

### #52, REPAIRED 2026-08-16 — and the first repair was wrong in the opposite direction

`Bot.play_ticks` / `Bot.play_inputs` now drive a **dedicated 3000-tick session** whose only
job is to be a representative play. It scores nothing, and a bot without one gets
`representative: false` rather than a plausible number derived from the criteria drive.

**The first version of that fix traded one degeneracy for another and would have shipped.**
Pacing was computed over *every* event name, so a bot pressing keys on a steady cadence
manufactured a steady cadence of `move`/`rotate` events. Pinned against a deliberately dead
3D Tetris — nothing falls, hard drop removed — it emitted **200 `move` and 100 `rotate` events
and nothing else**, and scored a quiet fraction of **0.005**: indistinguishable from a healthy
game. The pin caught it; nothing else would have.

Two further corrections came out of that:

- **World events are separated from input echoes by a PROPERTY, not a list of names**: an
  event that never once fires on a tick where nothing was pressed is an echo. To make that
  reliable the play session is **idle on every other tick** by construction — without
  guaranteed idle ticks the classifier called `lock` an echo, because a lock caused by a hard
  drop genuinely does fire on the tick the drop was pressed.
- **The tetris policy stopped hard-dropping.** A lock the player causes is evidence about the
  bot's cadence, not the game's. Letting gravity land the pieces is the honest pacing question.
- **Zero world events now means quiet for the WHOLE RUN**, not `0.0`. Returning zero read a
  game in which literally nothing happened as the liveliest possible result.

Pinned in both directions, which is what the first attempt failed:

| fixture | world events | quiet / run | verdict |
|---|---|---|---|
| healthy `ref_tetris3d` | 12 | **0.192** | alive — correctly passed |
| deliberately dead variant | **0** | **1.000** | dead — correctly flagged |

Across the eight real `g2_tetris3d` submissions the metric went from **0.93–1.00 for all
eight** to **0.145–0.194, and it now varies between submissions** (spread 0.05) instead of
being pinned at the ceiling. Events per run went from 6–9 to 83–115. All four references still
pass every criterion: pong 13/13, tetris 13/13, arena 22/22, platformer 19/19.

**What this does not do is make `fun` usable.** The evidence is now non-degenerate; whether
the judge reads it is a question only adjudication can answer, and per #55 the statistical
gates will pass it either way.

### #52, ADJUDICATED 2026-08-17 — the repair holds, and the confound is gone by construction

The judge was re-run on the repaired evidence and its scores correlated against the telemetry
it was given. The result is not a weaker correlation with run length; **run length is no longer
a variable at all**:

| telemetry field | distinct values across the 8 submissions |
|---|---|
| `seconds_of_play` | **1** — 46.9 for every submission |
| `ticks` | **1** — 3001 for every submission |
| `longest_quiet_stretch_seconds` | **8** |
| `events_per_second` | 5 |

Every submission now gets the same 3000-tick representative session, so the quantity that
`fun`'s scores used to track (rho -0.45 to -0.60) is constant. **A constant cannot be a
confound.**

What the scores track instead, consistently across both presentation orders:

| | seed 0 | seed 1 |
|---|---|---|
| `longest_quiet_stretch_seconds` | **-0.639** | **-0.630** |
| `events_per_second` | +0.511 | +0.770 |
| `seconds_of_play` / `ticks` | **undefined — constant** | **undefined — constant** |

A game that goes quiet for longer scores lower; a game with more happening per second scores
higher. That is what the aspect claims to measure. Ceiling passes on both orders (modal 0.500,
0.375) and order-invariance is a genuine pass — **tau 0.857 on 14 comparable pairs**.

**`fun` is the first aspect in this project whose measured signal survives adjudication.**

Two things it still does not establish, stated because the temptation is to bank more than the
evidence gives:

- the correlation shows the score moves with the pacing evidence, **not that the judge read the
  telemetry rather than the frames** — a livelier game also looks livelier in 12 PNGs;
- it is **n=1 per seed**, and gate 0 (#58) measured ceiling verdicts flipping on unchanged
  input, so a single run's numbers are a sample.

### And the analysis that adjudicated it was wrong on its first pass

The first correlation run reported `score vs seconds_of_play = -0.429` **for a field whose every
value is 46.9**. The ranking function broke ties by index order, so a constant vector was ranked
0..7 and correlated against position in the list.

> **A tie-blind rank manufactures a correlation with nothing.** It is the same defect as
> `order_invariance`'s tie-blind tau (#51's neighbourhood), in the throwaway analysis written to
> check the repair rather than in the shipped code — which is exactly where it is least likely
> to be reviewed and most likely to be believed.

Fixed to average ranks, which makes a zero-variance field return `None` and say so. The
corrected numbers are the ones above.


## 54. Two judges with no evidence in common produced the same ranking, twice

`architecture` reads **source code**. `ux` reads **12 PNG frames**. `build_pack` gives each of
them exactly one of those and nothing else — the packs are built per aspect and `run_field`
refuses a mismatch. They share no input whatsoever.

Kendall tau between their rankings of the same eight `g2_tetris3d` submissions:

| | seed 0 | seed 1 |
|---|---|---|
| `architecture ~ ux` | **1.00** (13 comparable pairs) | **1.00** (6 comparable pairs) |

The independence gate reports it as designed: *"REDUNDANT: `architecture~ux` rank the field the
same way — each of those pairs is one judge with two names."* It is the only pair that
replicates across both presentation orders; the other two redundancies (`audio~idiomatic`,
`fun~idiomatic`) appear on one order each and are noise.

### Two readings, and the evidence favours the unwelcome one

Two judges agreeing perfectly is what you would want **if** they were both detecting a real
quality ordering. That reading requires the ordering to be visible in code *and* in frames,
independently, to the same precision.

Against it: the deterministic tiers score all eight of these submissions **identically** —
1.000 each, 0 of 380 criteria differing within a cell (#50). Whatever `architecture` and `ux`
are agreeing about is invisible to every mechanical check the project has. And `architecture`
**ceilings on seed 1** (7 of 8 at one score) and has no usable tau of its own, so it is not
behaving like an instrument that has found something.

**The likelier reading is a shared prior**, and #53 names a channel for one: the code packs
carry the stack in every file extension, so a code judge always knows which stack it is
looking at. `ux` cannot see extensions — but it can see a rendering style, and four templates
render distinctively.

> **Independence between judges is not evidence that either is measuring the submission. Two
> instruments sharing a prior agree exactly as well as two instruments sharing a truth.** The
> gate can tell you they are redundant. Only the evidence tells you what they are redundant
> *about*.

### WITHDRAWN 2026-08-17 — it did not replicate, and "twice" was one observation

The claim rested on tau 1.00 across two presentation orders. A second round, with `ux`'s
evidence provably unchanged (it reads only frames, which neither repair touched):

| `architecture ~ ux` | seed 0 | seed 1 |
|---|---|---|
| first round | **1.00** (13 comparable) | **1.00** (6 comparable) |
| second round | **0.385** (13) | **0.667** (12) |

The redundancy is gone. Worse for the original reading, the redundant pairs the second round
*does* find are different ones and disagree with each other: seed 0 gives
`architecture~idiomatic` and `audio~ux`; seed 1 gives `architecture~fun`. **No redundant pair
replicates across two orders, let alone two rounds.**

> **Two presentation orders of the same field are not two independent observations of a
> judge's behaviour.** I treated "tau 1.00 on both orders" as replication. It is one round,
> reported twice — and the thing that varies most between rounds is the call itself (#58).

The finding is withdrawn. What survives it is the method: **giving two judges disjoint
evidence and checking they disagree is still the cheapest available detector for a shared
prior** — it simply needs repeats at a fixed order before a positive reading means anything,
which is the instrument this project did not have when #54 was written.


## 58. The ceiling gate's threshold sits in a gap the field cannot land in, and half the field sits on its edge

Three of the subjective layer's four gates are statistical. This is a mechanical defect in the
first one, and it explains most of the instability attributed to the judges.

### The measurement

Six comparisons where the evidence is provably unchanged — `audio` reads `audio.json`, `ux`
reads frames, `idiomatic` reads code with `blind_language` deliberately left off, and no repair
touched any of them. Same pack, same verified label->submission mapping, same seed, same model.
**Nothing differs but the call:**

| aspect | seed | scores changed | modal fraction | ceiling verdict |
|---|---|---|---|---|
| `audio` | 0 | 2/8 | 0.625 -> 0.625 | stable |
| `audio` | 1 | 4/8 | 0.750 -> 0.375 | **FLIPPED** |
| `ux` | 0 | 5/8 | 0.375 -> 0.500 | stable |
| `ux` | 1 | 3/8 | 0.375 -> 0.625 | stable |
| `idiomatic` | 0 | **1/8** | 0.625 -> 0.750 | **FLIPPED** |
| `idiomatic` | 1 | **1/8** | 0.750 -> 0.625 | **FLIPPED** |

**Three of six ceiling verdicts flip on unchanged input.**

### The mechanism, and it is arithmetic rather than a property of the model

`modal_fraction` over eight submissions can only take the values `k/8`:

```
0.125  0.25  0.375  0.5  0.625  |  0.75  0.875  1.0
                        MODAL_CEILING = 0.7
```

**The threshold falls between 0.625 (5 of 8) and 0.75 (6 of 8) — adjacent achievable values
with nothing between them.** So the verdict changes when a single submission joins or leaves
the modal score. The two `idiomatic` rows are that exact case: **one score of eight moved, and
the gate flipped.**

And the field lives there. Of **21** judgements measured across two games and every sweep,
**11 (52%) have a modal fraction of exactly 5/8 or 6/8.**

> **A threshold on a coarsely quantised statistic is not a test, it is a coin weighted by where
> the threshold happens to fall.** At n=8 the ceiling gate has no margin by construction, and
> the "judge instability" it appeared to reveal is mostly the discretisation amplifying ordinary
> variation.

### What this does and does not excuse

It does **not** rescue the layer. `audio` moved 4 of 8 scores and `ux` moved 5 of 8 with the
evidence constant — that is real judge variation, well beyond a threshold artifact, and it is
why gate 0 (`field.reproducibility`) now runs first and why `field_sweep --repeats` exists to
produce the repeats it needs.

It does mean **every ceiling verdict this project has published rests on n=1 at a knife edge**,
including the ones reported as findings hours earlier in the same session.

### The repair the gate needs, stated but NOT applied

Three options, none of which should be chosen from an armchair:

1. **Report the count, not the fraction** — "6 of 8 at one score" and let the reader judge;
2. **Widen the field** — at n=16 the achievable values are twice as dense and a single
   submission moves the fraction by 0.0625 rather than 0.125;
3. **Require the verdict to hold across repeats** rather than tightening the threshold, which
   only moves the knife edge somewhere else.

(3) is the one this catalogue's own history recommends: the failure is not the threshold's
value, it is that a single sample was ever allowed to decide. Left unapplied deliberately —
changing a gate's definition after seeing which aspects it fails is how a rubric gets fitted to
its data.

### The gate did its job, and its job turned out to be the opposite of what was expected

`JUDGING.md` built this gate to answer *"are there five judges here, or one judge with five
names?"* — expecting redundancy to mean wasted money. What it actually surfaced is stronger:
a redundant pair with **disjoint inputs** is evidence that neither is reading its input. That
is a use nobody designed it for and it is the most informative thing the subjective layer has
produced.


## 55. Statistical validation of a judge cannot tell a judge that reads its evidence from one that does not

This is the transferable result of the whole subjective layer, and it is stated separately
because it is buried inside two entries that each look like a local bug.

The layer has four gates. **Three of them are statistical** — ceiling (is the field
separated?), order-invariance (does the ranking survive a reshuffle?), independence (do the
specialists disagree with each other?). The fourth, adjudication, is the only one that opens
the evidence.

Measured over five aspects x two presentation orders on one eight-submission field:

| judge | ceiling | order-invariance | what reading the evidence showed |
|---|---|---|---|
| `fun` | **pass**, both orders | **pass** — tau 1.00 on 19 comparable pairs, the cleanest in the layer | its pacing number is 93-100% of the run in every arm; scores track how long the play-bot happened to run (#52) |
| `architecture` + `ux` | ux passes both | both pass | they rank the field **identically on both orders** while sharing **no input at all** — one reads source, the other frames (#54) |

**`fun` scored better on every statistical gate than any aspect that was not withdrawn.** It
was the layer's apparent success and it is measuring a harness artifact.

### Why the statistics cannot help, stated as a mechanism rather than a caution

> **An artifact is MORE order-invariant than a judgement, not less.**

A judge that has latched onto a stable mechanical quantity — run length, a file extension, a
render style — reproduces its ranking exactly across reshuffles, because the quantity does not
move when the pack is shuffled. A judge genuinely weighing eight competent submissions against
each other produces *less* stable output, because the question is genuinely close. **The
reliability metrics are therefore anti-correlated with the thing they are trusted to
establish**, over the range that matters.

The same inversion has now appeared three times in this project:

| | the reassuring statistic | what was actually happening |
|---|---|---|
| #26 | `instability` read 0.000 on 22 of 24 | the only measured signal was a screenshot artifact |
| #52 | tau 1.00 on 19 comparable pairs | the score tracked play-bot run length |
| #54 | perfect agreement between two judges | the two judges shared no evidence |

#32 reached the same conclusion from the other direction and it is worth quoting, because it
was written before any of this ran: *"A judge with the answer key produces a ranking that
survives every validation gate this project has. The gates check whether a judgement is
stable, independent and evidenced. None of them can ask what the judge knew."*

### What follows for anyone validating an LLM judge

1. **Never promote a judge on stability.** Stability is necessary and is evidence of
   *mechanism*, not of *validity*. Rank the gates so the evidence check is the one that can
   veto, and run it on the passes, not only on the failures (#39).
2. **Ask what a judge would score if it ignored its evidence entirely** and could see only the
   packaging. If that hypothetical ranking is stable, your gates cannot distinguish it from
   the real one.
3. **Give two judges disjoint evidence deliberately and check they DISAGREE.** Perfect
   agreement between disjoint inputs is the cheapest available detector for a shared prior,
   and this project found it by accident rather than by design.
4. **The only gate that ever caught anything here was reading the evidence string.** It caught
   #26, #39, #52, #53 and #54. Every statistical gate has, at some point, certified an
   artifact.


## 56. The pre-launch gate had not run since the configuration changed under it

`PROTOCOL.md` tells every reader to run `wholegame.py plan` and get authorisation before
committing a matrix. On 2026-08-17, asked to price the g4 matrix, it did this:

```
TypeError: unsupported operand type(s) for +: 'NoneType' and 'float'
  f"${n * (MAX_BUDGET_USD + JUDGE_COST_PER_TRIAL):.0f}."
```

`MAX_BUDGET_USD` has been `None` since the no-cap regime was adopted — the deliberate
decision that a stated budget is an instruction and only an absent flag is neutral (#33).
`cmd_plan` adds it to a float. **The command has been dead for every reader since, and nobody
found out, because the way you find out is by running it.**

### Worse than the catalogue's usual shape, in a specific way

The pattern this project keeps meeting is *a mechanism that runs, reports success, and
measures nothing*. This one is a rung below: it **did not run at all**, and its absence was
invisible because it sits at a step people perform once per matrix and had not performed since
the config changed.

A mechanism that reports a false success is at least exercised. A gate that crashes is
detected the instant anyone uses it — so the danger is not the crash, it is the **interval
between the change that broke it and the next use.** Here that interval spanned the entire
arena matrix and the whole subjective-layer programme.

### What it cost, which is not nothing

The unpriced matrix was priced from memory instead, and the memory was wrong: **"a 24-trial g4
matrix"** was carried into `G4-PLATFORMER.md` and `README.md` and into an authorisation
request. `plan` prints `1 games x 4 stacks x 2 trials = 8 trials`. The g4 matrix is **eight**
trials; the figure was a 3x overstatement, inherited from the three-GAME matrices, sitting in
the document whose only job is to price the launch.

> **A number you did not read off the tool is a number from the last time the tool was
> different.** The rule "never quote a value you did not just read from its source" already
> covered this. What it did not cover is that the source can be *broken*, in which case the
> honest move is to fix the source, not to quote around it.

### The class, and the check that finds the rest of it

Any command that is run **once per campaign** rather than once per run is a candidate: it can
be broken by an unrelated config change and stay broken for months. `plan` is one. The others
in this repo are `check-suite`, `concurrency-check`, `starter_parity.py` and
`prompt_guard --snapshot`.

**A config value that is legal in one branch and illegal in another must be exercised in
both.** `MAX_BUDGET_USD = None` is now a supported value of `plan`, and the no-cap branch
prints a measured per-turn range instead of a flag-derived worst case — because with no cap
there is no dollar worst case, and inventing one would have been the more familiar failure.


## 57. A guard that had been red for months, on a condition the project had formally decided was acceptable

Written minutes after #56, by the smoke test #56 motivated, which is the point of the entry.

`judge/starter_parity.py` keeps the four templates comparable. It exits **1**. It has been
exiting 1 for a long time, and on this:

```
DRIFT - 5 finding(s):
  recipes differ in rust: only-here=['coverage','quick'] missing-here=[...]
  recipes differ in ts / unity / godot: ...
  unity diverges from godot at tick 53 - the two starters are NOT the same simulation
```

`DECISIONS.md`, on the divergence:

> *"The requirement is **within-stack** determinism only — cross-stack hash equality is not
> achievable and is not a goal. Unity's 1-ULP divergence is a Mono/ARM64 property (FMA
> contraction) not reachable from source."*

**The gate was failing on a condition the project had formally decided was correct**, and on
four more that are the whole reason there are four templates rather than one: `analyzers` is a
Unity recipe, `api-notes` is a TypeScript recipe, `quick` is a Rust recipe. Set equality across
deliberately tuned templates can never hold.

So it was **structurally incapable of going green**, on every run, forever.

### This is #44's lesson, and #44 did not prevent it

#44 recorded a blinding scanner crying contamination on a clean matrix and drew the rule:
*"A guard that fires on clean input gets switched off, and then it protects nothing."* That was
written about `verify_blind.py`. Nobody asked the same question of the guard sitting next to
it — the same failure as `order_invariance` inheriting a tie-blind tau that `independence` had
already been fixed for.

> **When you fix a guard for crying wolf, audit its siblings the same day.** The defect is
> rarely in one tool; it is in the standard being applied to that class of tool.

### How it stayed invisible

By being read through a pipe. Twice in this session I ran
`python3 judge/starter_parity.py 2>&1 | tail -5; echo "EXIT=$?"` and reported **exit 0** — that
is `tail`'s status, and the rule against it is AGENTS.md rule 3, in this repository, written
after the same mistake. The real exit was 1 both times.

It surfaced only because `tools/precampaign_smoke.py` runs every once-per-campaign command
**unpiped and reads its own return code**, which is the one thing the human reading could not
be trusted to do.

### Repaired, and pinned in both directions

- **Cross-stack hash divergence is now a NOTE**, quoting `DECISIONS.md` at the point of the
  finding, not a failure.
- **Recipe drift is checked against `CORE_RECIPES`** — `verify, test, lint, fmt, probe, film,
  run`, the ones a building agent is told to use and the harness calls by name. Stack-specific
  extras are reported as notes.

| control | expected | got |
|---|---|---|
| the real starters | exit 0, "No drift detected" | **exit 0** |
| a starter with a CORE recipe removed | exit 1, naming it | **exit 1**, `godot is missing CORE recipes [...]` |

The second row is the one that matters: loosening a guard to stop false alarms is how a
fail-closed check becomes fail-open (#31), so the true positive it must still catch was
planted before the change was believed.

### #57, continued — the smoke suite's own footer fired on its author within the hour

The suite prints, deliberately: *"A green row means the gate is ALIVE, never that it PASSED."*
Then this row went by:

```
prompt_guard --snapshot   0   0.0   snapshot: 16 rendered prompts -> /var/folders/9h/spk2...
```

and was reported upward as **"prompt snapshot taken (16 rendered prompts)"** in a pre-launch
readiness summary. `find runs -maxdepth 3 -name 'prompt*'` returns nothing. No launch snapshot
existed. `PROTOCOL.md` requires it at `runs/<run>/prompts` — durable, inside the run — because
its entire purpose is to be diffed **after** the run to prove the regime did not move (#41).

Two failures, and the second is the transferable one:

1. the green row meant the gate was alive, and it was read as the artifact being taken — the
   exact confusion the footer names;
2. **the liveness exercise and the real thing printed the same success string**, so nothing
   in the output distinguished them. The scratch snapshot also went to `$TMPDIR`, which is the
   artifact-lifetime defect of #45: it can be gone before the diff that needs it, and its
   absence is indistinguishable from "no drift".

> **A tool that EXERCISES a command and the command DOING REAL WORK must not be confusable in
> their output.** If both print "snapshot: 16 rendered prompts", a reader will bank the second
> meaning from the first. Label the exercise, in the line itself, not in a docstring nobody
> re-reads while scanning a table of green rows.

Fixed: the smoke suite's row now reads
`prompt_guard --snapshot [LIVENESS ONLY - scratch, deleted; NOT the launch artifact]`, writes
to a path named `prompts-liveness-check-not-the-launch-artifact`, and the footer ends with
*"NOTHING HERE IS A LAUNCH ARTIFACT. Every path above is scratch and is now deleted."*


## 60. The tool that measures whether measurement is happening was pointed at the old location

`AGENTS.md` designates `tools/runstat.py` as **the only correct status check** and forbids
hand-rolling one, because every ad-hoc version written here has been wrong at least once. For
the whole of the g4 build it printed:

```
work trees: no writes in last 10 min
```

Measured at the same moment, directly:

```
find ~/game-research-work/wg-g4-.../ -type f -mmin -10 | wc -l   ->   2555
```

### The mechanism

```python
WORK_ROOT = "/private/var/folders"                       # line 42
glob(WORK_ROOT/*/*/T/wholegame-work/<run>/*)  ->  0 directories   # line 181
```

The work root had moved to `~/game-research-work`. `runstat.py` kept the `$TMPDIR` spelling,
so its glob matched **nothing**, and "found no trees" and "found trees, nothing moved" printed
**the same sentence** — a statement about the glob, read as a statement about the agents.

### Three things make this the sharpest instance of the catalogue's pattern

**It is fail-open in the diagnostic direction.** A false "no writes" is one of the four signals
that produced the wrong stall diagnosis in #37, where four agents mid-compile looked dead. A
permanently-false quiet reading is a standing invitation to kill healthy trials.

**The change that broke it was the change that made the project safer.** The work root moved
*because* `$TMPDIR` was deleting the artifact under measurement (#45). Making measurements
durable broke the tool that measures whether measurement is happening. **A constant in one file
had to track a value in another, and nothing enforced it.**

**And the method was right.** `runstat.py` carries `-mmin, never -newermt` at line 107 and
obeys it — the rule bought with three separate `find` failures. It was applied faultlessly to a
path that did not exist.

> **A correct method pointed at the wrong place produces a confident answer.** Every rule in
> this project about HOW to check — unpiped exit codes, `-mmin` not `-newermt`, process names
> not argv, partition before averaging — is silent on WHERE. The address is an input to the
> check and needs the same discipline as the method.

### Fixed, and pinned by mechanism rather than by comment

`wholegame.DEFAULT_WORK_ROOT` is now the single spelling, and
`tools/precampaign_smoke.py` asserts `runstat.WORK_ROOT == wholegame.DEFAULT_WORK_ROOT` in
process — no subprocess can express "two modules agree on a value". `runstat` also now prints
**NONE FOUND** as a distinct line from **no writes**, so the merged sentence cannot recur.

| control | expected | got |
|---|---|---|
| the repaired spelling | smoke exit 0 | **exit 0**, 12 exercised / 0 failed |
| one spelling reverted to `/private/var/folders` | smoke exit 1, naming it | **exit 1** — `WORK ROOT MISMATCH: runstat.WORK_ROOT=/private/var/folders but wholegame.DEFAULT_WORK_ROOT=/Users/stefano/game-research-work` |
| restored | exit 0 again | **exit 0** |

### And I verified it wrong, in a way worth recording

Told the tool was broken, I ran it, compared its output against an independent `find`, got
**8 and 6 against 8 and 6**, and concluded the report was mistaken and the tool sound. I was
two minutes late: the file's mtime was **2.1 minutes** before my check, and the g4 build had
started **an hour** earlier.

> **A control run after the fix tests the fix, not the claim.** "Compare the tool against an
> independent measurement" is the right control and it was vacuous against a repaired binary,
> which can only agree.

This is the shared-assumption failure of #37 with a **time axis** instead of a code path. The
defence is the same shape: **establish the state you are testing before testing it** — mtime,
`git diff`, or reproduce the broken behaviour — when verifying a defect someone else reported.

The near-miss is worth keeping for the opposite reason too. I had assembled a tidy story from a
single grep line and was drafting it as a finding; running the tool stopped that. **The instinct
to distrust a story built from one reading was right. It simply fired on the wrong side, and
being right about the method did not make the conclusion right.**

---

## 65. The docstring said every criterion establishes its condition, so nobody checked the one that did not

`bot_platformer.py` opens with, in capitals:

> EVERY CRITERION HERE ESTABLISHES ITS CONDITION AND THEN MEASURES. The bot walks to a ledge it
> located in `platforms` rather than waiting to fall; it walks to an enemy it located in
> `enemies` rather than waiting to be hit. Sixteen false negatives in this project came from
> criteria that idled and hoped.

Three lines below it, `platform.lands` walked off the ledge and hoped a floor was underneath.

`player.falls` genuinely does locate its ledge, and sharing a session with it is what made the
landing look established: the fall was constructed, so the landing appeared to be. But "the
character fell" and "the character fell **onto a platform**" are different conditions, and only
the first was ever brought about. Whether anything is underneath is level layout the bot has no
knowledge of — and in a designed platformer the far side of the opening ledge is usually a pit,
because that is what an opening ledge is *for*.

**Measured on `wg-g4c`: 5 of 6 submissions failed it.** All five fell to y = −68…−136, straight
past the stage floor, and were recorded as having no landing collision. The sixth passed because
its gap happened to have a floor eight units down. Rule 9 exactly — near-identical evidence
across independent subjects, reporting the instrument.

### The reason it survived a mutant suite

`platform.lands` had a mutant (*"nothing ever lands on a platform"*) and it was green in both
directions. A mutant asks whether a criterion can **fail**; only a variant asks whether it can
still **pass** on correct work the reference does not resemble. There was no platformer variant.
This is the fourth instance of the mutant/variant asymmetry (#46), now with the reference itself
as the blind spot: `ref_platformer`'s ground platform spans the entire level, so no fixture in
the suite had a pit in it.

### The repair, and the alternative that is wrong

The landing is now **constructed**: jump from the platform underfoot and assert the descent ends
on it. That is a fall onto a platform in the criterion's own words and is constructible on every
correct game without knowing anything about the level.

The obvious alternative is wrong and worth recording: *locate a lower platform in `platforms` and
walk off aiming at it*. A lower platform that is ahead can still be on the far side of the gap, so
walking off lands in the pit and a correct game fails exactly as before — **the same hope, wearing
the vocabulary of establishment.** A condition is established only when the bot can bring it about
unilaterally.

Pinned both ways: the mutant still fails it, and a new variant — *the opening ledge overlooks a
bottomless pit*, the layout the real submissions had — passes. Cost of the repair, declared as
collateral rather than left as a surprise: `platform.lands` now depends on jump working, and says
so in its own evidence (*"this is a jump failure, not a landing failure"*).

### The larger defect the variant exposed, which is not fixed

Building that variant knocked out six *other* criteria — `attack.damages`, `score.on_kill`,
`enemy.damages_player`, `invuln.window`, `knockback.applied`, `gameover.triggers` — because the
reference spawns enemies on the ground the pit removed and **the bot reaches every enemy by
walking right**. Put a gap in the floor and combat stops being measurable.

That is the same six-criterion cluster `g4_platformer__ts__t0` failed on `wg-g4c`, and its source
confirms the mechanism: its ground is four segments with pits at x 520–600, 1080–1180 and
1700–1790, and the bot's own evidence says it "reached x=588.8" — **inside the first pit.**

> **ts__t0 scored the lowest in the field (0.758) for building the most sophisticated level.**
> The bot's unstated assumption is a continuous walkable floor, so a submission that builds real
> platforming — gaps that must be jumped — is punished for it, and the punishment is indexed to
> how good the level is.

The tolerances are declared on the variant with reasons rather than silently narrowing the check,
and the suite now reports which of them actually fired, so a dead tolerance cannot hide. **The bot
still cannot cross a gap; until it can, no submission with one can be graded on combat.** That is
open, and it is a ceiling on this task, not a property of any stack.

---

## 68. The subjective layer's first positive result, and the control that made it readable

Every previous reading of tier 3 failed on the same question: *is this disagreement real, or is
the instrument just noisy?* Nothing had measured the noise. Gate 0 finally did — four judgings
of the same field in the same presentation order — and the answer reframes the layer:

| | |
|---|---|
| absolute scores | **unstable**: 5 of 8 submissions moved, mean change 0.75, one by 2 |
| **rank order** | **stable**: mean self-tau **+0.853** (range +0.714 .. +1.000) |

**The instrument is far more reliable about order than about magnitude.** That distinction had
never been drawn here, and it is why earlier rounds looked noisier than they are: they were read
through scores, which move, rather than order, which largely does not.

With a floor in hand the pre-registered comparisons become readable, and one of them is positive
(2026-08-21, `g2_tetris3d`, $10.20):

| comparison | tau | pairs | floor |
|---|---|---|---|
| `fun` ~ `fun_frames` | **+0.043** | 23 | +0.853 |
| `fun_frames` ~ `ux` | **-0.364** | 22 | +0.853 |

Both sit far below the instrument's disagreement with itself, so both are real disagreements
rather than noise.

**`fun` and `fun_frames` are the same question, the same anchors and the same scale, differing
only in whether the telemetry is shown. They rank the field differently. The telemetry is doing
work** — the first evidence in this project that a judge read the evidence it was given rather
than the packaging.

Adjudicated to submissions, not left as a coefficient: `godot__t1` is `fun`'s best (3, 3), cited
on *"lock median 5.48s, fastest of 8; quiet_fraction 0.145, lowest of 8"*, and `fun_frames`'s
worst (1, 1), which sees only a HUD that never changes. `unity__t0` moves the opposite way for
the mirror reason. **The submissions that move are exactly the ones whose telemetry was
extreme**, which is what a real effect looks like and what noise does not.

The second comparison bounds #59 rather than extending it. Two different questions over the
*same* frames produce opposed rankings, and the mechanism check agrees with the tau: against
distinct-colour counts, `ux` correlates **+0.528** (replicating #59's +0.735/+0.823) while
`fun_frames` correlates **-0.120**. **#59 retires `ux`, not the frames channel.**

### What did not happen, and it was pre-registered as the thing to fear

The interaction — `fun` ≈ `fun_frames` **and** `fun_frames` ≈ `ux`, which would have shown
`fun`'s pacing signal to be palette depth arriving through the frames and **closed tier 3
entirely** — **did not land.** Naming it in advance is what makes reporting its absence worth
anything, and it is reported here as plainly as it would have been had it occurred.

### What it still does not license

**No cross-stack ranking, and the pre-registration said so before the numbers existed.**
`fun_frames`'s between-stack range is 1.50 against a within-stack floor of 0.75 — but that is
unity at 2.25 with godot, rust and ts on *exactly* 0.75, n=2 per stack, on a four-point scale.
Three independent stacks landing on an identical value is rule 9's signature, not a result.
**Tier 3 stays at weight 0.00.** What moved is whether an aspect reads its evidence, not whether
it can rank stacks.

### The control that was skipped

`frame_parity.py` — which exists precisely because #59 turned on frame size — was run **after**
the spend, not before, though its own docstring says to run it first. It found
`g2_tetris3d__unity__t1` **in `wg-matrix-2026-08-13`** captured at **420x640** against that field's 640x400, a portrait flip
shown directly to both frames-only aspects.

It does not carry the result: all three aspects saw identical frames, so a shared anomaly
cancels in any comparison *between* them. **But that is luck, not method.** The completeness
gate was run explicitly because the instruction was explicit; the parity gate was not, because
nobody thought to ask.

> **A gate that fires only when someone remembers it has a person-shaped hole in it.** The
> completeness gate fired on this same round without being asked, and the only difference
> between the two is that one was code on the path and the other was prose in a docstring.

### Closed, not recorded

The lesson would have failed the way this project's remembered rules always fail, so it was
wired into the path instead:

- `judge/field.py::pack_parity` calls `frame_parity.geometry()`, and **`build_pack` refuses any
  frames-reading aspect** (`sees` containing `frames`) on a field whose submissions were not all
  filmed at one geometry. It sits directly beside the completeness gate.
- Pinned **both ways**, plus scope: `g2_tetris3d` (divergent) refuses for `frames` and
  `frames+telemetry`; `g3_arena` (uniform) builds; a `code` aspect is refused by the
  *completeness* gate and never consults parity.
- "Not measured" is a distinct refusal from "measured and divergent", so an absent frames
  directory cannot read as parity.

**It refuses rather than annotating, and that choice is #62.** The obvious alternative — record
the divergence in the manifest and let the reader decide — is precisely what
`files_dropped_for_length` already did: written into every manifest since the first matrix, and
nothing ever read it. **A caveat nobody reads is a caveat that does not exist.** Fail-closed
costs a round; fail-open costs the result (rule 7).

**The gate is retroactively stricter than the round that produced it: the $10.20 judged here
would now be refused.** That is the correct outcome and not an argument against the gate — the
right response to the divergence is to re-film `unity__t1` at 640x400, which was always the
right response and which nobody had been prompted to do. Checked across the archive, the
divergence is narrow: `g4_platformer`, `g1_pong` and `g3_arena` are all uniform at 640x400 and
proceed untouched.

---

## 71. The subjective layer has only ever judged one game out of four

Every stored aspect result in `runs/` is `g2_tetris3d`. `g1_pong` had `architecture` and
`idiomatic` run once — they are cited in #53's table and in `JUDGING.md` — but **the output
files are not in the archive**. `g3_arena` and `g4_platformer` have never been judged by any
aspect at all.

**So every tier-3 conclusion this project has drawn rests on one game**, including #53's stable
per-stack ordering, #59's palette-depth retirement of `ux`, and #68's positive result for the
telemetry channel.

The reason nobody noticed is worth more than the fact. The layer sits at **weight 0.00**, so it
is described everywhere as "carrying no information" — and a component known to contribute
nothing is a component nobody audits for coverage. **Its irrelevance protected it from scrutiny.**

> **A quantity excluded from the result still gets cited in the reasoning.** Weight 0.00 governs
> the arithmetic, not the prose, and every finding above was written from a single game's worth
> of evidence without that being stated.

### It hands two open findings a sharper test than any statistical gate

Both are re-grades of stored evidence. No new trials, no new builds.

- **#53** — `idiomatic` produces a stable per-stack ordering, suspected to be a language prior
  rather than a reading of the work. **The clean test of a prior is whether the same ordering
  appears on a different game.** Three unused games are sitting in the archive.
- **#59** — `ux` tracked distinct-colour counts on tetris. Does it on arena and platformer,
  where the renderers differ the same way?

This is a **validity** test, where every gate the layer has been given so far — ceiling,
independence, order-invariance, reproducibility — tests only **precision**. An instrument can be
perfectly reproducible about the wrong quantity, which is exactly what #59 found. Filed in
`eval/IMPROVEMENTS.md` as the next experiment.

## 72. A 1.000 on pong clears 13 hurdles; a 1.000 on arena clears 22

Play-bot criterion counts are not constant across games:

| game | scored criteria |
|---|---|
| `g1_pong` | 13 |
| `g2_tetris3d` | 15 |
| `g4_platformer` | 20 |
| `g3_arena` | 22 |

Only `determinism`, `score` and `state` are universal; the rest are game-specific, which is
correct — a platformer has no layer-clear and pong has no invulnerability window. **But it means
the tier-2 score is a different measurement per game, and "1.000" denotes a different achievement
in each column.** Nowhere in the documentation did it say so.

`RUNS.md` already bars pooling across games, for **regime** reasons — different tasks, limits and
allowlists. This is an **independent** reason with the same conclusion, and it must be stated
separately: even two games run in an identical regime, on the same day, with the same limits, are
not poolable on tier 2, because the denominators differ in kind and not merely in size.

> **Two rules that forbid the same thing for different reasons are not one rule.** Fix the regime
> problem and the pooling ban would look obsolete, and it would not be.

### The tier nobody worried about is clean

Checked at the same time and recorded because a negative result is a result: **all 14 programmatic
criteria apply to all four games**, audio family included. No per-game gaps. Tier 1 is the only
tier whose denominator is genuinely constant across the suite, and it is the one nobody had
audited.

### A naming trap for the next cross-game sweep

`gameover.triggers` exists for tetris, arena and platformer; pong names the same idea
`match.ends`. Substantively equivalent, but a sweep asking *"does every game check its end
condition?"* would report a false gap for pong — a phantom finding produced by vocabulary rather
than by evidence, which is #38's shape pointed at criteria instead of docs.

---

## 73. A tally: eleven vacuous checks, and what they have in common

Individually each of these is a small mistake with a rule already written against it. The reason
to count them in one place is that **the recurrence rate is the finding**, not any instance:
every one was authored by someone who knew the rule, and most were caught by something other than
the check itself.

| # | the check | why its green meant nothing | caught by |
|---|---|---|---|
| 1 | `pgrep -c ... \|\| echo 0` | flag does not exist on macOS; the fallback made an error look like "0 agents" while four ran | a second look, twice |
| 2 | `--only` negative control read through `\| head` | pipeline exit status is `head`'s | re-running unpiped |
| 3 | g4 grader on a criterion that could not fail (#39) | green on reference, 19 fixtures and its own run | the mutant |
| 4 | `total=0 passed=0` read as success (rule 1) | indistinguishable from correctly failing | a positive control |
| 5 | `runstat` work-tree glob (#60) | "no writes" and "no trees found" were one sentence | 2555 files written during a "quiet" build |
| 6 | guard red for months on an accepted condition (#57) | nobody read a check that always failed | a sweep |
| 7 | completeness gate on an unbuilt field (2026-08-21) | "0 of 0 submissions dropped files" — a reading of an empty set | it refused for the wrong reason |
| 8 | `frame_parity` as a docstring instruction (#68) | fires only when a human remembers | ran it after $10.20 |
| 9 | **the bare-id ratchet set to 20 against an actual 18** | two units of headroom absorbed a planted violation | the both-ways pin |
| 10 | **a blind-safety pin on a file that did not exist** | "0 stack tokens found" in a pack whose skill was never written | a *later* pin in the same script failing |
| 11 | **an exit code read through `grep`** | reported `exit=1` for a command that succeeded | the number was implausible |

### The three shapes

- **Absence read as a measurement** (1, 5, 7, 10): the thing being measured was not there, and the
  checker reported a value instead of refusing. Every fix is the same — make "not measured" a
  distinct outcome from "measured and fine".
- **The status of the wrong thing** (2, 11): a pipeline reports its last stage. Both instances are
  rule 3, which is written down, and both were committed by someone who had cited it.
- **A guard with slack, or with a human in the loop** (3, 4, 6, 8, 9): the check could not fail, or
  could only fail if someone remembered to run it.

> **A check is not verified by passing. It is verified by being made to fail on purpose.** Nine of
> the eleven above were only ever run in the passing direction until something else went wrong.

### What actually catches them

Not review, and not care — the authors were being careful. The two that caught the most here are
mechanical:

1. **Pin both directions in the same script.** #10 was found because the *next* assertion in the
   same block failed; had the script stopped at the green pin it would have shipped.
2. **Set thresholds to the exact measured value, never a round number.** #9 was a ratchet with
   headroom, which is not a ratchet.

And the structural one, from the same week: **a check that reads a registry sees only what someone
remembered to register; a check that reads the source sees what exists.** That is why
`assert_frame_criteria_geometry_safe()` discovers criteria from the module source and treats an
unregistered one as a failure.

---

## 74. The capped-vs-uncapped test could not answer its question, and the reason was the ceiling

Task 09 asked whether removing the pack character budget (#69) changed what a code judge
concludes. `idiomatic` on `g4_platformer`, two presentation orders per arm, $27.30, with the
reading pre-registered in `JUDGING.md` before any call was made.

**The answer is that the experiment cannot tell**, and saying so is the whole value of having
pre-registered a third outcome alongside "changed" and "unchanged".

| | tau | comparable pairs |
|---|---|---|
| between arms, seed-averaged | -0.231 | 13 |
| **capped arm against itself**, across orders | **+0.333** | 6 |
| uncapped arm against itself | +1.000 | 4 |
| floor from #68 (`fun_frames`, tetris) | +0.853 | 14-18 |

A -0.231 between arms looks like a result. It is not, because **the capped arm disagrees with
itself almost as much as the two arms disagree with each other.** An effect the size of the
instrument's own noise is not an effect, and the +0.853 floor cannot be borrowed: it was measured
on a different aspect and a different game.

### The mechanism: near-total ties

Every one of the four rounds produced **2 distinct scores across 8 submissions**, and **2 of the 4
fail the ceiling gate outright** (7 of 8 at score 3; 6 of 8 at score 3). Ties are exactly what
Kendall tau discards, so the comparable-pair counts collapse to 13, 8, 6, 4 and 3 — two of them
below this project's own "fewer than 6 pairs is arithmetic, not evidence" bar.

> **A saturated field cannot be made informative by more rounds of the same size.** Repeating
> narrows the interval around a mean; it does not create ordering information that the scale never
> captured. This is #63's precision-is-not-validity with the axes swapped: there, repeats would
> have measured a confounded quantity precisely; here, they would measure a tie precisely.

The two rounds that **passed** the ceiling gate had the same 2 distinct scores as the two that
failed — they differed only in modal fraction. `eval/IMPROVEMENTS.md` 11b predicted this: the gate
measures bunching, not separation, and it passes and fails fields that are equally unrankable.

### What the round did establish, and it is new

The first audit trail of **what a judge actually read**, captured by switching the judge to
`stream-json` and recording its tool calls:

| arm | files opened | subagents | tool calls | cost |
|---|---|---|---|---|
| capped | 79, 98 | 8, 4 | 134, 171 | $12.06 |
| uncapped | **115, 178** | 4, 8 | 185, 246 | $15.24 |

**1.74x the content produced 1.5-1.8x the file opens.** The judge does not read a fixed number of
files and stop — it scales with what it is given, so the removed cap was constraining what it
could read and not merely what it was offered. That is the strongest available support for #69,
and it is independent of any score.

### Two process notes

- The capped arm was **refused by the completeness gate** and needed an explicit
  `--allow-truncated`. The gate built the day before did its job on the first field that genuinely
  was truncated. The escape is deliberately loud: it must be named on the command line and it
  **stamps `knowingly_truncated` into the pack's mapping record**, so no later reader can mistake
  that field for a complete one.
- The flag reached only one of three `build_pack` call sites on the first attempt, and one of
  those sites referenced a nonexistent global (`args.allow_truncated`) that would have raised
  `NameError` in sequential mode. Both were found by the arm silently skipping rather than
  running — visible only because the log said `[SKIP]` and the spend said `$0.00`. **A flag that
  is accepted and ignored is worse than one that is rejected**, which is a rule this project
  already had.

---

## 75. A threshold placed where the data cannot land — #58's shape, one level up

**#58 found a threshold sitting in a gap the statistic could never occupy**: `modal_fraction <=
0.7` over eight submissions, where the statistic can only take k/8, so 0.7 lives between 0.625 and
0.75 with nothing in between. This is the same defect one level up — in a *stopping rule* rather
than a *pass/fail gate*, and against a target that moves rather than one that is merely
unreachable.

The rule: repeat until **the SE of the mean is below the smallest non-zero between-submission
gap**. It is dimensionally correct, references the right quantities, and matches the standard form
*"repeat until the error bar is smaller than the effect"*. It still cannot be met. Measured on one
dataset — seven repeats of `fun_frames`/`g2_tetris3d` — by truncating it to each n:

| n | pooled SD | SE | smallest gap | SE < gap? | pairs resolved |
|---|---|---|---|---|---|
| 2 | 0.500 | 0.354 | 0.500 | YES | 9/28 |
| 3 | 0.577 | 0.333 | 0.334 | YES | 17/28 |
| 4 | 0.577 | 0.288 | 0.250 | no | 17/28 |
| 5 | 0.570 | 0.255 | 0.200 | no | 17/28 |
| 6 | 0.581 | 0.237 | 0.166 | no | 18/28 |
| 7 | 0.577 | 0.218 | **0.143** | no | 18/28 |

> **A mean over n rounds lives on k/n, so the smallest gap between two means shrinks as 1/n. SE
> shrinks as 1/sqrt(n). The target moves away faster than the estimate approaches it.**

So the criterion is satisfiable only at **n=2 and n=3** — where SE is estimated from too few points
to trust, and where the gate now raises a low-n warning — and becomes permanently unreachable
exactly as the measurement becomes trustworthy. **A criterion that only the least reliable
measurements can pass is inverted.**

At n=7 the smallest gap would need n=66. At n=66 a new smaller gap appears, because the
discretisation is finer. There is no n.

### The distinction it was missing

"Resolve the smallest gap in the field" is not a question anyone has. **"Does this aspect resolve
ANY pair?"** is, and it plateaus at 17-18 of 28 from n=3 onward — stable, informative, and reached
cheaply. The smallest gap is an artifact of how many rounds were run; the resolved-pair count is a
property of the field.

### The tool corrected its author on first use

`separation()` was written to replace #58's gate, and its first real run corrected the person who
specified it: the target had been stated as `SE < gap` for a single submission, where the correct
two-sample test compares a gap against **SEi + SEj**. Under the strict test the smallest gap needs
n=66 rather than n=7. **A tool that contradicts its own author the first time it runs is the
strongest evidence available that it is measuring something** — the opposite of the pattern in
this file, where instruments agreeably confirm whatever was expected.

It also surfaced a convention nobody had written down. Pooled SD is 0.577 as RMS of sample
stdevs, 0.565 as their mean, 0.534 using population stdevs — and exactly one pair
(`godot__t0` vs `ts__t1`, gap 0.4286 against a combined SE of 0.4452 or 0.4122) **straddles the
line**, so the count is 18 or 19 depending on which is chosen. The gate now fixes the conservative
convention *and* reports `marginal_pairs`, because fixing a convention silently would leave an
exact-looking integer hiding a boundary case.

### Why it survived being written down

The criterion is dimensionally correct, references the right quantities, and matches the standard
form *"repeat until the error bar is smaller than the effect"*. What it omits is that **the effect
here is not fixed** — it is computed from the same rounds as the error bar, so both move with n,
and it was never checked which moves faster. That check is three lines of arithmetic on data that
already existed.

**Same shape as #63.** There, a noise floor estimated from one cell was wrong by 7x because nobody
asked what the floor was a property of. Here, a stopping target was estimated from the same sample
as the estimator without asking how it scales. In both cases the quantity was treated as fixed
while the design made it vary.
