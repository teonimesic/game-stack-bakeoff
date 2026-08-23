# Defects that fire on one arm and look like a result

A defect touching a single stack produces exactly the signature a real stack
difference would. Four for four here have been the harness.

> Index and the distilled rules: `../FINDINGS.md`


## #20 — I leaked rubric vocabulary into the starter myself, and the guard caught it

`verify_blind.py` over the 24-trial matrix's work trees returned CONTAMINATED:

```
[g1_pong__unity__t0] CRITERION ID determinism.replay: .../Assets/Sim/Sim.cs
[g1_pong__unity__t1] CRITERION ID determinism.replay: .../Assets/Sim/Sim.cs
```

Traced to `starters/unity/Assets/Sim/Sim.cs:93` — a comment **I wrote**, while
documenting why a cross-stack one-ULP divergence was being left alone:

> `// that holds (see the determinism tests and `determinism.replay`).`

That back-reference names a play-bot criterion id. Every Unity trial in this matrix
inherited it from the starter.

**Impact: low, and stated rather than assumed.** `determinism.replay` is measured
deterministically by the play-bot tier, not by a judge, and the task prompt already
requires that "the same seed and the same sequence of inputs reproduce the same run
exactly, tick for tick". An agent that reads the string learns a name for something it
was already told to do. It is not a scoring advantage.

**Not fixed mid-run, deliberately.** Editing the starter now would give the Unity
Tetris and arena trials a different starter from the Unity Pong trials, trading a
low-impact leak for a real within-run inconsistency. The comment is removed after the
matrix completes; all Unity trials in this run had it.

### The part worth generalising

The leak did not come from the task prompt, the template, or `AGENTS.md` — the three
places the blinding design worries about. It came from **an incident write-up**. I was
documenting one finding and quoted a rubric identifier into a file that gets copied
into every trial.

**Provenance guards have to cover the places you edit for unrelated reasons.** The
rubric was never at risk of being copied; a comment about floating-point rounding was.
Nothing in the design anticipated that, and only the mechanical canary-plus-vocabulary
scan caught it — a human reading that comment would see a sensible cross-reference.

Run `verify_blind.py` after *any* edit to a starter, not just before a run.

### A second, smaller error in the same command

I ran `python3 judge/verify_blind.py ... | tail -12; echo "blind_exit=$?"` and reported
`blind_exit=0`. `$?` was `tail`'s exit code, not the scanner's — the pipe discarded it.
The scanner had exited 1. I read "exit 0" off a command that could not have reported
otherwise.

Same family as #19: **a pipeline's exit status is the last stage's.** Capture the
status of the command you care about (`PIPESTATUS`, or don't pipe) before quoting it.

---


## #24 — a permission change created a measurement confound, and nothing connected them for two days

The Unity starter's `just run` recipe ends in `open build/Starter.app`: it builds the
game, launches it, and never terminates it. Reasonable behaviour for a "run the game"
command a human invokes.

Adding `Bash(just *)` to the agent allowlist — a change made to cut a **29.8% turn
denial rate** — gave agents a route to that recipe. Every Unity trial thereafter leaked
a running GUI process.

Six were found still running. Two had been burning CPU since the start of the matrix
and survived its entire remainder: **94 to 136 CPU-minutes each**, across two days.

### Why it matters more than untidiness

**Wall clock is a comparison metric in this project.** Every trial that ran after a
Unity trial ran on a progressively busier machine, and the contamination is *ordered by
build sequence* — precisely the shape that manufactures a spurious trend.

The measured correlation between live orphans and wall clock is +0.30, which looks like
a real effect and is not: orphan count is nearly collinear with build phase (the first
two appeared as Tetris began, so "2 orphans live" is a synonym for "this is a Tetris
trial"). Controlling for game, load never varies within Pong or within Tetris, and the
only within-game variation — arena, 3 vs 4 — is exactly the rust/ts vs unity/godot
split, so it is fully confounded with stack.

**Neither direction can be established: machine load cannot be shown to explain the
wall-clock differences, and cannot be ruled out.** Wall-clock comparisons between
stacks in this run are provisionally unsafe. API cost is unaffected.

### The generalisable question

Two facts sat in the record for two days without being connected: *"we allowlisted
`just`"* and *"something has been eating a CPU since Tuesday"*. Nothing linked a
configuration change to a resource anomaly, because nothing was watching for either.

**Ask of any harness: what does it start that it never accounts for?** Here: a GUI
application, launched by a recipe the harness never calls directly, reachable only
because a permission list was widened for an unrelated reason.

Fixed in the **harness**, not the starter — the starter is the artifact under
measurement, and `just run` leaving a window open is defensible. `build_trial` now reaps
any process rooted in the trial's work tree once the agent stops. The other three stacks
were swept for the same failure — Godot binaries, Chromium/Playwright, `cargo run`,
node dev servers, stray Unity editors — and none leaked.

---


## #25 — a harness defect that can only fire on one arm is bias, not noise

`g1_pong__unity__t0` scored 0.894 where Rust and TypeScript scored 1.000. The deduction
was two play-bot criteria, `determinism.replay` and `determinism.seed`, and neither
tested the submission at all:

```
probe exited (code 134) while waiting for the tick-0 header
"It looks like another Unity instance is running with this project open.
 Multiple Unity instances cannot open the same project."
```

Both criteria open a **fresh probe session** on the same project directory. On Unity
that means a second batchmode process against a project the previous one has not
released, which Unity refuses by design. The probe aborted before emitting tick 0, and
`drive()` - correctly fail-closed - scored both criteria FALSE.

**The constraint was already written down in this repo before the harness existed:**
*"two Unity processes on one project deadlock or corrupt the asset DB… parallel trials
need separate project copies."* Two criteria were then built that each spawn an
independent session, and nothing connected them.

### Why this is worse than every other defect in this catalogue

Every previous entry produced a number that was **wrong**. This one produces a number
that is wrong **in a specific direction**: it can only fire on Unity, so it can only
ever deduct from Unity. That is the difference between noise and bias.

Noise widens an interval and makes a comparison less sensitive. Bias moves one arm and
manufactures a difference that is not there. A 15% deduction applied to exactly one of
four stacks, silently, is precisely the shape that produces a confident and false
ranking - and it would have looked entirely plausible, because Unity being slower or
weaker is a story anyone would accept.

It was found only because a single score looked odd enough to adjudicate against
source. **The ones that produce plausible numbers are the ones nobody adjudicates.**

### Two consequences

**Aggregates hide it.** A criterion sound on three stacks and broken on the fourth
presents as a criterion with a 25% failure rate - which reads like a criterion that is
working. Any audit of criterion quality must have a **per-stack dimension** or this
class of defect is invisible by construction.

**Ask what else is stack-asymmetric.** The stacks are not symmetric in what they demand
of a harness, so assumptions written against the simplest one will silently break on
the others:

| stack | structural demand nothing else has |
|---|---|
| Unity | an editor, a project lock, batchmode startup, a 38.9 MB artifact footprint |
| Godot | a display server for anything that renders - `--headless` returns a null image |
| TypeScript | a browser binary and an installed `node_modules` |
| Rust | a warm target dir; cold builds are minutes |

Every one of those is a place a harness assumption can hold on three stacks and fail on
the fourth, in a direction that looks like a result.

### Corrected reading of the Pong data

Three separate readings were published before adjudication and all were wrong:

1. "Seven of eight scored 1.000" - wrong denominator; six were evaluated, not eight.
2. "Pong's spread is zero, the task is too easy" - stated before Unity was measured.
3. "Unity may genuinely be weaker" - stated from a raw verdict, before adjudication.

Adjudicated: **all three play-bot failures across the Pong game are harness defects,
none are submission defects.** `godot__t0` failed `ball.wall_bounce` because the
criterion waits for a wall bounce instead of causing one; `unity__t0` failed both
determinism criteria because of the project lock. The corrected spread across all four
stacks on Pong is **zero** - the original conclusion, reached for the wrong reason and
now supported by adjudicated evidence rather than raw scores.

**The tier carrying 0.69 of the grade has not caught a single genuine defect across
eight Pong submissions.**


## 30. A guard whose trigger names an EXTERNAL cause cannot fire on a failure with an INTERNAL one — and looks like a fix

This is a distinct failure mode from the fifteen observation-not-experiment criteria
(#29) and belongs beside them, not inside them. Those criteria measured the wrong thing.
This one measured nothing, while being addressed to the right problem.

### What happened

FINDINGS #25 established that Unity refuses a second batchmode process on an open
project, that this took out four criteria on one arm, and that a criterion which can only
fire on a subset of arms is bias rather than noise. The diagnosis was correct and the
evidence was unambiguous: the probe's own stderr carried Unity's exact wording.

The remedy was a retry in `ProbeSession.start()`, gated on a set of `LOCK_HINTS`
("another unity instance", "cannot open the same project", "lock", ...). It was endorsed
on that diagnosis. It could never have worked.

Every bot opened its sibling sessions from *inside* `with ProbeSession(...)`. **The lock
being waited for was held by the process doing the waiting.** The retry slept, retried,
slept, retried, and failed, because the only thing that could have released the lock was
the caller further up its own stack.

### Why it is worth separating

The guard's trigger condition was written in the vocabulary of the cause it was told
about — *another* instance, *another* process. That phrasing is not merely a comment; it
is the matcher. It encodes the assumption that the conflicting party is external, and it
is applied to a conflict whose other party is the guard's own caller.

So the guard was:

* **addressed to the right failure** — a project-lock conflict, correctly identified;
* **triggered on the right symptom** — the engine's actual refusal message;
* **and structurally incapable of resolving it**, because the remedy for an external
  holder (wait) is the opposite of the remedy for an internal one (release).

It ran, it matched, it retried, it reported. Every observable behaviour was that of a
working guard. Only reading who *held* the lock separated it from one.

### The general form

> **A guard whose trigger condition names an external cause, applied to a failure with an
> internal one, cannot fire — and looks like a fix.**

The tell is not in the failure rate; a self-inflicted deadlock fails at exactly the rate
the original defect did, so the guard's presence changes no number. The tell is that
nobody ever asked *which party* held the resource. The diagnosis stopped at "there is a
lock conflict", which was true, and the remedy was chosen from the space of remedies for
the kind of conflict the error message described.

Concretely, when adding a retry, a backoff, a wait or a lock: **name the party you are
waiting for, and check that it is not you.** If the answer is "the caller", the fix is
structural — here, one live session per repository, enforced across threads and
processes — and no amount of waiting substitutes for it.

The correction also does what the retry could not: `bot_mutants.py` removes the
serialisation and confirms the criteria go red, so the guard is now known to be load
bearing rather than assumed to be.

---


## 32. The blind judge's pack contained the answer key

Found 2026-08-14 by listing a judge pack instead of reading the code that builds it, and
before a single specialist judge had been run.

`field.py` builds a pack of eight anonymised submissions, `A/` through `H/`, hands it to a
judge whose working directory *is* that pack, and tells it:

> They were produced by different starting templates across four different technology
> stacks, two attempts each — **you are not told which is which, and you should not
> guess.**

It then wrote `MAPPING.json` into the same directory:

```json
"mapping": { "A": "g1_pong__godot__t0", "B": "g1_pong__ts__t1",
             "C": "g1_pong__unity__t1", "D": "g1_pong__rust__t0", ... }
```

Every label, every stack, sitting beside the briefing that says the judge does not know
them. Anonymisation ran, the labels were shuffled by a seed, the mapping was described in
the code as "recorded separately so the analyst reading the ranking cannot see the
stacks" — and it was written one directory too high.

### Why it survived review

The comment above the write is *correct about its purpose* and wrong about its effect,
which is the hardest kind of defect to see. Everything around it works: `anonymise.py`
strips identifying structure, file names are flattened to `sim/01.gd`, the order is
randomised per seed, the identity is deliberately attached only after the judgement
exists. The blinding design is real. It leaked through the bookkeeping.

This is the same shape as **#20**, where a criterion id reached the Unity starter not
through the prompt, the template or `AGENTS.md` — the three places the design watched —
but through a comment in an incident write-up. **Provenance guards have to cover the
places you write for unrelated reasons**, and a mapping file is exactly that kind of
place: nobody thinks of it as content.

### What it would have cost

Nothing yet, and that is the only lucky part. Had it run, every per-aspect ranking would
have been produced by a judge holding the answer key, and the output would have looked
completely normal — eight scores, evidence strings, a defensible ordering. There is no
statistic that detects it. Order-invariance would have passed, because the mapping moves
with the shuffle. Independence would have passed. Adjudication against cited files would
have passed, because the citations would still have been real.

**A judge with the answer key produces a ranking that survives every validation gate this
project has.** The gates check whether a judgement is stable, independent and evidenced.
None of them can ask what the judge knew.

### Fixed

The mapping is now written **beside** the pack (`<pack>.MAPPING.json`), `build_pack`
raises if any `MAPPING` file remains inside, and `run_field` refuses to judge a pack
containing one rather than producing a ranking. Verified non-vacuous: planting the file
back inside makes `run_field` return `usable: false` before any model call.

The general rule, and it is not about mappings:

> **Anything written into the directory a blinded evaluator reads is shown to it,
> whatever the writing code believes it is for.** List the directory. Do not read the
> code that fills it.

---


## 40. A stack-correlated pattern is the SHAPE a harness defect takes here

Five times now a defect in this project has landed cleanly on a subset of the four stacks.
Every time, the split was the most convincing thing about it.

| # | what was observed | which arms | mechanism, once found |
|---|---|---|---|
| 25 | two determinism criteria failed | Unity only | a second probe session on a project the first still held |
| 26 | `look.feedback` failed the submissions with the most HUD code | Unity, TypeScript | IMGUI and DOM nodes cannot reach an offscreen camera render |
| 28 | frames drawn as a 3×4 pixel miniature | Godot only | the viewport was framed against before it was realised |
| 31 | hand adjudications excused failures | Unity (14 of 16) | trial ids repeat across runs, and Unity had the most adjudications |
| **40** | **four of four arena trials wedged** | **Unity ×2, Godot ×2; zero of four headless** | **not established** |

The first four were each read, at first, as a property of the stack. Each was consistent
across every game. Each survived every stability metric — `instability` read 0.000 through
the whole of #26. And each turned out to be the harness.

### The lesson is not "we keep finding stack-specific defects"

That reading would suggest the defects are the exceptional thing and a genuine stack
difference is the default. The record says the opposite:

> **A stack-correlated pattern is the shape a harness defect takes in this project, and it
> is indistinguishable from a real stack difference until the mechanism is found.**

The stacks are not symmetric in what they demand of a harness — an editor and a project
lock, a display server, a browser and `node_modules`, a warm target directory — so every
assumption written against the simplest one has a way to fail on exactly one or two of the
others. There are far more ways for a harness to be stack-asymmetric than there are real
capability differences between four well-built templates that have tied on every task put
to them.

**The prior is therefore strongly against the interesting reading.** With four for four
behind us, a fifth split is evidence about the instrument until proven otherwise.

### What that means operationally

- **A stack-correlated result is not reportable without a mechanism.** Not "we checked and
  it looks real" — the actual causal chain, in the code, named. Consistency is not
  evidence: all four of the resolved cases were perfectly consistent.
- **Do not invent one to fill the gap.** #40's tidy story was that Unity and Godot launch
  real engines and the wedged agents' last tool calls were `just bless` and `just film`.
  It fits the split exactly. It is also wrong: the agents had **no children** and **no
  engine binary was running anywhere on the machine**. One check separated a mechanism
  from a coincidence, and without it the story would have been written down as fact.
- **Where a mechanism cannot be found, act on the asymmetry of the decision rather than on
  the hypothesis.** The remaining arena trials run at `--parallel 2` — not because
  saturation is established, but because being wrong costs wall clock and being right
  costs half the matrix.
- **An unresolved split must be recorded as unresolved**, with what was captured and what
  was not, so the next occurrence starts with evidence instead of a fresh guess.

### Why #40 is still open, and what would close it

Nothing distinguishes "the agent is stuck on an API response that never arrived" from "the
agent died in flight and the tool result was never written". Both fit every measurement:
zero CPU accumulation, no children, no engine running, no transcript append for an hour.
`PROTOCOL.md` now lists what to capture *before* terminating a wedged trial, because the
first four occurrences were killed before anyone thought to look.

---


### #40, closed on evidence — Unity measured mid-pack once the instrument worked

The 3D arena set completed 8 of 8 on a healthy machine with the Unity lock fix in place:

| stack | mean cost |
|---|---|
| ts | $37.97 |
| godot | $43.37 |
| **unity** | **$46.85** |
| rust | $58.85 (one 369-turn outlier) |

**Unity is mid-pack and statistically indistinguishable from Godot.** Two prior attempts to
measure this exact cell produced no usable data at all, both to harness defects, and on both
occasions the raw numbers would have read as a large Unity deficit — a deficit that does not
exist.

That is **four for four**: the project-lock bias, the frame-capture artifact, the audit-key
collision, and the shared-resource wedge. Every stack-correlated signal this project has
produced has turned out to be a property of the instrument. The prior is no longer merely
strong; on this evidence it is the default, and a fifth split should be treated as an
instrument defect until a mechanism is named.

## 41. A shared preamble edited for one game silently changed all four tasks

Found 2026-08-15 while checking that a cost experiment would have exactly one variable, by
diffing the **rendered** `g2_tetris3d` prompt against the one **stored** with the trials it
would be compared against.

```diff
- - `just run` opens a window and the game is actually playable with a keyboard.
+ - `just run` opens a window and the game is actually playable with a keyboard, and
+   with a mouse where the game calls for aiming.
```

Mouse support is a **3D arena** requirement, added when that task was rewritten. It was added
to `_preamble()`, which every game's prompt is built from, so it also went into Pong, 3D Tetris
and the platformer — three tasks where nothing calls for aiming.

| game | wanted the change | got it |
|---|---|---|
| `g3_arena` | yes | yes |
| `g1_pong` | no | **yes** |
| `g2_tetris3d` | no | **yes** |
| `g4_platformer` | no | **yes** |

### Why it matters more than one vacuous clause

For Tetris the clause is inert — nothing in Tetris aims. The damage is not to the game, it is
to **comparability**: every Pong and Tetris trial from now on is built from a prompt that
differs from the stored ones, and this project's first rule is that a task change is a
comparability break. A one-line, mostly-inapplicable difference is exactly the kind that gets
waved through, and #34 is the entry recording that a task change creates false negatives *in
criteria that had never fired*, through behaviour the old references could not produce.

Worse, it would have landed on the **one experiment designed to have a single variable**: the
no-cap Tetris trial that settles whether capped trials were paced or truncated. That experiment
exists because the previous comparison crossed three boundaries at once. It would have crossed
two.

### The general form

> **A shared template edited for one arm changes every arm.** The edit is correct where it was
> aimed and invisible everywhere else, because nobody re-reads the three prompts they were not
> working on.

Same shape as #20, where a rubric criterion id reached the Unity starter through a comment in
an incident write-up, and #32, where the answer key reached a blinded judge through a mapping
file nobody thought of as content. **Provenance guards have to cover the places you edit for
unrelated reasons** — and a shared function is the most ordinary such place there is.

### What actually caught it

Not review — the diff was one line in a file nobody had reason to re-read. It was caught by a
mechanical comparison of the artifact that would be *sent* against the artifact that *had been
sent*, run because the experiment's design required proving a single variable.

> **Before any comparison, diff the rendered inputs, not the source that renders them.** The
> prompt is what the agent sees; the function that builds it is not.

`wholegame.py` now supports `--prompt-file`, so a trial can be run against a byte-identical
stored prompt when reproducing an earlier condition is the point.

---

## 43. A resource that looks per-trial and is not — twice, on two stacks, invisibly

Four of eight `g3_arena` trials in `wg-arena3d` died without producing a record. Two Unity,
two Godot. **The Unity half is a real harness defect; the Godot half was environmental and
is retracted below.**

**Unity.** The building agent issued `just check`, `just warm` and `just coverage` as
*background* shell tasks. Unity holds a project-wide lock, so the first invocation took the
project and every later one blocked forever. Seeing no output, the agent launched another —
five stacked shells on one trial, ages 1h24m, 1h11m, 1h01m, 55m, 52m, all at 0:00.00 CPU.
Each attempt to escape the deadlock deepened it.

**Godot — RETRACTED 2026-08-16.** This entry originally claimed the two Godot trials died
because every work tree's `.venv/bin/gdformat` carries an absolute shebang back to the
shared starter, so all trials ran one interpreter. The shebang observation is true. It is
**not** why they hung.

A system daemon, `syspolicyd`, had been pegged at **102% CPU for ten days**. Restarting it
dropped machine load from 6.28 to 3.87 — and the exact command that hung for 69 minutes,
`gdformat sim view tests tools`, then completed in **0.33 s** through the same symlinked
interpreter it had used all along. The Godot wedge was environmental.

Two things were true at once, and the second hid the first:

| | with `syspolicyd` pegged | after restart |
|---|---|---|
| `gdformat` on the real dirs | **hung 69 min** | **0.33 s** |
| a *copied* interpreter (`copytree` follows symlinks) | hung >15 s | **fails in 0.55 s**, `Could not find platform independent libraries` |

The copied 17 MB interpreter is genuinely broken — but it is never executed, because the
shebangs point at the starter's working symlink. It is dead weight, not a defect.

**The fix written for this was worse than the bug.** `relocate_venv()` rewrote those
shebangs to point into the work tree — that is, at the broken copy — and
`assert_self_contained()` would have rejected the *working* configuration as a leak. Both
were reverted before any run used them. A note now sits at the point of temptation in
`prepare()`.

> **A saturated system resource turns a fast, legible failure into silence.** Every
> diagnostic habit here is tuned to "the check is wrong". This was the opposite: the check
> was fine and the machine swallowed it. Before attributing a hang to your own code,
> establish that the machine is healthy — `syspolicyd`, load average, and anything holding
> CPU for days.

Consequence for the record: **every wall-clock measurement in this project was taken on a
machine with a system daemon pegged for ten days**, alongside an unrelated 2.9 GB agent
process at ~96%. API cost is unaffected. Wall-clock comparisons across all runs are
suspect.

### Why it took four wrong diagnoses to find

1. *"Contending engines"* — both wedged agents' last tool call was an engine-invoking
   recipe, on exactly the two stacks that launch an engine. Tidy, and false: no engine
   process was running.
2. *"`unity-compile.sh` blocks without ever launching Unity"* — also false. Unity batchmode
   on a fresh copy compiled and exited cleanly in under 20 seconds while both trials sat
   blocked, and both trees held earlier logs reading `Exiting batchmode successfully`.
3. *"Concurrency across trials"* — bought with wall clock at `--parallel 2`, and
   disconfirmed: the stacking is *within* one trial.

What finally located it was `lsof` on the blocked shell, which showed its stdout going to a
background-task output file, and reading the shebang of the script that was hanging.

### The shape, and why it is the dangerous one

**Rust and TypeScript touch no shared resource, so they never wedge.** Every failure lands
on Unity and Godot, and looks exactly like a capability difference between stacks. It is
not. Both attempts at an arena comparison have now lost their Unity arm to a harness defect,
neither to anything about Unity.

This is #40 with a mechanism attached, and it sharpens it: the correlation was never with
*the stack*. It is with **whichever arms happen to touch a resource that is shared**. A
four-arm comparison cannot distinguish those from the scores alone.

### The rule

> **Isolation is a property you must verify, not one you get by copying a directory.** A
> lock, an absolute path, a daemon, a licence, a port — each survives a clone and turns
> per-trial work into shared work. Ask of every trial resource: *what does it name that
> lives outside the tree?*

And the failure was silent in both cases. Neither produced an error, a timeout or a log
line — three hours of frozen CPU and no output. **Any command that can block on a shared
resource needs a timeout**, or its failure mode is indistinguishable from slow work.

### The fix is viable, measured 2026-08-16

Concurrent Unity batchmode instances on **separate** project directories run in genuine
parallel. Two instances, two CoW clones of the starter:

| | measured |
|---|---|
| `cp -Rc` clone of the Unity project | **0.44 s, 36 MB** |
| two concurrent instances, separate projects | **both exit 0, 15 s total, `Exiting batchmode successfully` in each** |
| two invocations, same project | **deadlock, 3 h, no error, no log** |

So the constraint is exclusively the shared **project directory** — not the licence, not
the binary, not Unity Hub. Both instances connected to the same `LicenseClient-stefano`
channel; the `Code 10` signature-verification error in the log is non-fatal (Unity logs
it, ignores the client, handshakes, proceeds) and both runs succeeded with it present.

Controls run first: a single instance on one clone exits 0 with a clean log, so a failure
in the concurrent test could not have been blamed on the clone itself.

**The fix must be per-invocation, not per-trial.** The deadlock was five commands inside
*one* trial; cloning per trial is what the harness already did and it did not help.

**And it still needs a timeout.** A clone removes this cause. Only a timeout makes the
next one visible in minutes rather than hours — the failure here produced no error, no log
line and no output for three hours.

---

## 45. The artifact under measurement was stored somewhere with a lifetime shorter than the measurement

Work trees defaulted to a directory under `$TMPDIR`. That path was chosen for one good
reason — a tree inside the repository lets a building agent walk up its ancestors and read
`RUBRIC.md`, which `verify_blind.py` exists to prevent — and nobody asked the second
question.

macOS reaps `$TMPDIR`. **Measured 2026-08-16: six TypeScript submissions lost about 80% of
their installed toolchain between being built and being graded.**

| | at build | at grading |
|---|---|---|
| `node_modules`, files | 6,175 | **1,230** |
| `three`, files | 1,195 | **2** |

Every one of the six then scored **exactly 6/14**.

### The tell was the thing that made it convincing

Six independent agent runs, six identical scores. That is the signature of a property of
the stack — it is what "TypeScript is worse at this" would look like — and it is why the
number was not questioned. An identical score across independent submissions is evidence
that something *other than the submissions* is producing it, and this project has now been
taught that four other ways (#25, #26, #28, #43).

> **A repeated identical measurement across independent subjects is not corroboration. It
> is the signature of a shared cause, and the shared cause is usually the instrument.**

### The general form

> **The artifact under measurement must not live somewhere with a lifetime shorter than the
> measurement.** Ask of any storage location: what deletes things here, and on what
> schedule?

Two requirements, and most candidate paths satisfy only one:

1. **outside the repository**, for blinding;
2. **durable for longer than the measurement.**

`$TMPDIR` satisfies (1) and fails (2). The default is now `~/game-research-work`, and
`assert_work_root_sane()` refuses any path under `$TMPDIR`, `/tmp`, `/private/tmp` or
`/var/folders` with both reasons stated in the error, because a guard that gives one of two
reasons is one the next reader "simplifies" back into `/tmp`.

Removing the reaping also **unmasked** a second defect: `_targets/<tid>` collided across
runs, and `$TMPDIR` had been quietly cleaning it between matrices. A shared folder is only
safe if everything under it is namespaced, not just the part that was noticed first.

---

## 49. The arena matrix straddles a machine repair, and the split is exactly the stack split

**Five for five.** Every stack-correlated signal this project has produced has turned out to
be a property of the instrument, and this is the largest one yet: it is the entire spread of
the 3D arena matrix.

`wg-arena3d` reads as one run with eight completed trials. It is two populations, divided by
a system daemon:

| stack | built | `syspolicyd` | its own `just verify` | graded |
|---|---|---|---|---|
| rust t0, t1 | **15 Aug** | pegged ~100% CPU | **never ran** | **0.000, 0.000** |
| ts t0, t1 | **15 Aug** | pegged ~100% CPU | **never ran** | **0.956, 0.956** |
| unity t0, t1 | **16 Aug** | restarted | green, 0 skips | 1.000, 1.000 |
| godot t0, t1 | **16 Aug** | restarted | green, 0 skips | 1.000, 1.000 |

Trial timestamps, read from the records: the last 15-August trial finished at 22:11 UTC and
the first 16-August trial started at 13:47 UTC. `syspolicyd` was restarted between them
(#43), and every deduction in the matrix is on the 15-August side of that line.

### The mechanism, named in the code and in four independent agent reports

`syspolicyd` gates `execve` of *freshly created* binaries. All four agents built on 15 August
diagnosed it themselves, independently, in their own final reports:

> *"This host's `syspolicyd` is wedged at ~100% CPU (591 minutes and climbing), and it gates
> `execve` of freshly created binaries. Every newly linked executable hangs at exec with
> ~0.02s of CPU and never starts... a trivial dependency-free binary I built as a control."*
> — `g3_arena__rust__t0`

> *"Every executable under `node_modules/` hangs at 0% CPU on exec — `pnpm exec tsc`,
> `prettier`, `vitest`, esbuild's native binary. So does a shell script I created in `/tmp`
> as a control."* — `g3_arena__ts__t0`

Both rust agents shipped code that had **never been compiled**, and both said so:
*"expect ordinary compile errors on the first successful build"*. Both TS agents shipped
render tests that had **never been executed** and labelled them *"unproven code"*.

**Rust and TypeScript link or install new binaries on every build. Unity and Godot run
pre-existing ones.** That is the asymmetry, and it is #43's rule in a second costume: the
correlation is never with *the stack*, it is with **whichever arms happen to touch the thing
that is broken**.

### The TypeScript half, adjudicated against source and re-run on a healthy machine

Both `ts` trials fail exactly two tier-1 criteria, `verify.green` and `tests.green`. Re-run
2026-08-16 on the repaired machine, from the stored work trees:

| trial | own tests | the three that fail |
|---|---|---|
| `ts__t0` | **100 / 103** | `moving right moves the player right on screen`; `moving up moves the player up on screen`; `the HUD is drawn into the frame, and it follows the world` |
| `ts__t1` | **106 / 109** | `moving right moves the ship right, and moving up moves it up`; `enemies are drawn out in the arena, not only at the centre`; `destroying something leaves debris that outlives the tick it died on` |

All six are in `tests/render/`, all six are assertions the agents wrote themselves, and all six
**reproduce**. They are genuine failures of the submissions' own gate, and the grader is right
to report them.

They are **not** an artifact of the grading machine, and the evidence separates the two
readings:

- the two trials fail **different** tests. A shared environmental cause would tend to produce
  the same failures in both;
- the rest of each render suite **passes** — 7 of 10 and 6 of 9 render tests — so headless GL
  works, the browser is present, and frames are being captured;
- the failure text carries real measured numbers (*"idle x=251.1, moving x=263.1"*, *"an arena
  with a wave in it (20,961 lit pixels) is no busier than an empty one (220,160)"*), which is
  a harness that ran and disagreed, not one that could not run.

The causal chain is therefore: the daemon prevented the agents from **executing** their own
tests; both said so and labelled them *"unproven code"*; the tests were shipped untested and
three in each are wrong — about the view, the test, or both. That is a defect in the
submissions, produced by a defect in the machine, and it is why the deduction stands while the
comparison does not.

### What is and is not withdrawn

Two statements are both true and must not be merged:

- **The grading is correct.** `g3_arena__rust__*` does not compile (`E0502` in
  agent-written `crates/sim/src/lib.rs`); the grader reports 0.000 and must keep doing so.
  It has survived four harness repairs and a full offline re-grade. Do not "fix" it.
- **The comparison is void.** Two arms were measured on a machine that would not let their
  agents run a single command that could have told them the work was broken, and two were
  not. **No stack claim can be drawn from `wg-arena3d`**, in either direction, and the
  cost figures in `RUNS.md` inherit the same split.

### Why nobody saw it for a day

The run's own records say `8 completed`, `terminal_reason` homogeneous, wall clock
unremarkable. `runstat.py` partitions by terminal reason, which is the right partition for
every failure this project had met before and the wrong one here. The population boundary
was a **date**, and no aggregate in the harness has ever been partitioned by one.

> **Partition by terminal reason, and also by anything about the world that changed while
> the run was in flight.** A run is not a controlled experiment merely because it is one
> command.

The evidence was sitting in `agent.final_text` of all eight records the whole time — four
agents each writing a paragraph headed *"What I could not verify — and why"*. **Nothing in
the harness reads that field, and no gate looks at it.** A grader that never reads what the
subject said about its own work will keep re-deriving what the subject already told it.

---

## 53. The blinded judge can read the stack off the file extension, and `idiomatic` scores the stack rather than the submission

Every judge brief ends with:

> *"They were produced by different starting templates across four different technology
> stacks, two attempts each — **you are not told which is which, and you should not guess.**"*

It does not have to guess. `anonymise.py` flattens filenames to `sim/01.gd`, `view/03.rs`,
`view/06.cs`, `src/02.ts` — and **keeps the extension**. Measured across four code packs:

| submission | extensions present |
|---|---|
| `g2_tetris3d__godot__t1` | `gd`, `json` |
| `g2_tetris3d__rust__t1` | `rs` |
| `g2_tetris3d__ts__t0` | `ts` |
| `g2_tetris3d__unity__t0` | `cs`, `shader` |

One extension per stack, uniquely identifying, in every file the judge reads. **Blinding for
the two code aspects is nominal**, and the sentence promising it is false.

### This is #32 again, structurally rather than by accident

#32 found the answer key inside a blinded judge's working directory, in a `MAPPING.json`
nobody thought of as content, and concluded:

> **A judge with the answer key produces a ranking that survives every validation gate this
> project has.** Order-invariance passes, independence passes, adjudication passes. None of
> them can ask what the judge knew.

That was a bookkeeping slip and was fixed in an afternoon. This one is in the design: the
anonymiser was never asked to hide the language, and for `idiomatic` it **must not** — you
cannot judge whether Rust was written like Rust without knowing it is Rust. **The aspect
whose subject is the variable under test is the one aspect that cannot be blinded to it.**

### What the scores then look like

`idiomatic` per-stack means, three independent judgements across **two different games** and
sixteen different submissions:

| | godot | rust | ts | unity |
|---|---|---|---|---|
| `g1_pong` seed 0 | 3.0 | **4.0** | 3.5 | 3.0 |
| `g2_tetris3d` seed 0 | 3.0 | **4.0** | 3.5 | 3.0 |
| `g2_tetris3d` seed 1 | 3.0 | 3.5 | 3.5 | 3.0 |

> **The pong row is now backed by files on disk (task 04, 2026-08-22).** Re-run on the stored
> `wg-matrix-2026-08-13` field, **4 rounds**: godot **2.75**, rust **3.38**, ts **3.00**, unity
> **2.75**. **The ordering reproduces exactly — rust > ts > {unity, godot} — and the godot/unity
> tie reproduces too, but every value sits about 0.6 lower.** So the row's *ranking* is sound and
> its *levels* are not; the judge, its brief and its model have all moved since. Treat the
> original numbers as a ranking, never as scores, and never against a later round's absolutes.

Per-cell, pong against tetris: **6 of 8 identical**, and the two that differ are the two `ts`
trials *swapping with each other*, which leaves the stack mean unchanged. All four godot and
unity cells score 3 in both games; both rust cells score 4 in both.

So the **stack-level** signal is constant across games while the **submission-level** signal
is not stable at all. That is the wrong way round for an instrument that is supposed to be
measuring submissions, and it is this catalogue's rule #11 firing: *a repeated identical
measurement across independent subjects is the signature of a shared cause.* The shared cause
is nameable in the code rather than inferred — the extension.

The judge says so itself, unprompted, in its field note: the separation *"came from each
stack's own checklist in the brief"*.

### The pre-registered consequence, which has now fired

`RUBRIC.md` registered the conditional before any of this ran:

> *"If this proves incoherent in the evidence, the aspect is per-stack-only and cannot
> contribute to a cross-stack ranking — itself a reportable result."*

It has. **`idiomatic` may not contribute to a cross-stack ranking.** It is a per-stack
fluency score assigned by a judge that knows the stack, and its cross-stack ordering
(rust ≥ ts ≥ godot = unity) is stable across games precisely because it is not a property of
the games.

### What is fixable and what is not

- **`architecture` does not need the language and should not see it.** It asks "could a second
  enemy type be added"; that is answerable from structure. The leak there is gratuitous.
- **`idiomatic` cannot be blinded** without destroying the question. So it is a within-stack
  instrument only, and must be reported that way or not at all.
- **No statistical gate can detect either case**, which is #32's point and is why this was
  found by listing extensions rather than by reading a number.

> **Ask of any blinded evaluator: what does the evidence structurally reveal, independent of
> its content?** Filenames were anonymised and the alphabet they were written in was not.

### #53, PARTIALLY repaired 2026-08-16 — and the honest finding is that it cannot be closed

`Aspect.blind_language` is now set for `architecture`, and `build_pack` renames every source
file to a neutral `.src`. `idiomatic` keeps its extensions, deliberately and permanently.

**Measured immediately afterwards, and it is the point of the entry:**

| aspect | extensions in the pack | submissions whose language is still identifiable |
|---|---|---|
| `architecture` | `.src`, `.txt` | **8 of 8** |
| `idiomatic` | `.cs`, `.gd`, `.rs`, `.ts`, … | 8 of 8 |

`func`/`extends` is GDScript. `fn`/`impl`/`let mut` is Rust. `export const` is TypeScript.
`using UnityEngine` is C#. **The extension is a label; the syntax is evidence, and the evidence
is the thing the judge is there to read.**

> **Renaming the label does not blind a competent reader.** A leak you can only close by
> destroying the evidence is not a leak you can close — it is a constraint on what the
> instrument can be asked.

So the repair removes one channel of two and the remaining one is structural. `architecture`'s
cross-stack rankings are still produced by a judge that can tell the stacks apart; the change
makes that harder to do casually and does not make it impossible. The pack is otherwise
untouched — 126 files, 1,300,015 bytes, identical to the unblinded one — so the aspect can
still answer its question.

**`idiomatic` remains per-stack-only. That is a result, not an outstanding defect.**

---

## 59. The last surviving subjective aspect was ranking palette depth

After the 2026-08-17 repairs, exactly one aspect cleared every gate with a between-stack range
above its within-stack noise: **`ux`**, which reads 12 PNGs and nothing else. It was the only
candidate the layer had left.

Adjudicated offline, at zero cost, by correlating its scores against cheap measurable
properties of the pixels it was given:

| | seed 0 | seed 1 |
|---|---|---|
| score vs **distinct colours in the frames** | **+0.735** | **+0.823** |
| score vs mean ink coverage | +0.209 | +0.041 |

It replicates across both presentation orders — which almost nothing in this layer does — and
the thing it tracks is not a property of the game:

| submission | distinct colours, full frame |
|---|---|
| `ts__t0` | **28** |
| `unity__t0` | **26** |
| `godot__t0` | **607** |
| `rust__t0` | **1789** |

**A 60-fold split, and it is cleanly by stack.** TypeScript and Unity render flat-shaded;
Godot and Rust render with gradients, lighting and anti-aliasing. Rust also renders at
768x576 where the others are 640x400.

Checked before believing it: every frame is 4-channel RGBA of the same kind, so this is not a
palette-indexed PNG artifact, and the counts above are over **every pixel**, not a sample.

**Method, so a reader can reproduce it rather than take the numbers.** Colours are counted over
every pixel of a single frame per submission; the correlations are Spearman with **average
ranks** (a tie-blind rank manufactures a correlation with a constant field — see #52's
continuation). Which frame you sample shifts the individual counts and not the bands: an
independent recount from frame 0 gave ts 14/51, unity 30/17, godot 610/598, rust 1578/1181
against the frame-6 figures above. **Both trials of each stack land in the same band either
way**, which is the part the result rests on.

### THE FRAMES ARE NOT ALL THE SAME SIZE, and a reader will notice

`g2_tetris3d__rust__t0` **in `wg-audio48-2026-08-14`** filmed at **768x576**. The other 21
submissions across both runs filmed at **640x400**.

> ⚠️ **The run matters and was missing.** The SAME id in `wg-matrix-2026-08-13` filmed at
> **640x400**, and a trial id is not unique across runs - in those two runs it is not even the
> same work (#70). Citing it bare cost a round of confusion on 2026-08-22.

> **REFRAMED 2026-08-22, and the conclusion is unchanged.** This finding was read for a while as
> *"a field with divergent geometry is not comparable"*, which led to a gate that REFUSED such
> fields and a plan to force every `film` recipe to 640x400. Both were wrong. Only godot's recipe
> passes a resolution; the others capture at whatever their own render target defaults to, so
> **frame size is a presentation choice the task left open** - a portrait well for a
> falling-block game is a design decision, not a defect, and normalising it would have erased a
> real difference between submissions and called it a fix.
>
> The correct statement is narrower and survives: **raw-count measures are not comparable across
> geometries; density measures are.** `ux` tracking distinct-colour counts is unsound for that
> reason and the retirement stands. The response is not to reshape the submissions but to
> guarantee that nothing the harness measures depends on shape, and to TELL the judge the
> geometry rather than shield it from it. More pixels is more opportunity for distinct colours, so this has to be dealt
with before the colour result can be believed.

**It does not carry the result, and the reason is within-stack replication:**
`g2_tetris3d__rust__t1` films at **640x400** — the same size as ts and unity — and still counts
**1181** distinct colours against their **14–51**. The band is a rendering property at equal
resolution. Stated explicitly rather than left for a reader to trip over the 768x576 row and
doubt the whole finding.

**It is one trial in twenty-two, not a stack property.** Measured across every submission in
both runs: godot 6/6 at 640x400, ts 6/6, unity 6/6, rust 3/4 — with `g2_tetris3d__rust__t0` the
only exception, uniform within itself across all 12 of its frames. So it is not machine-
dependent and not #49's class; it is one agent changing the capture size in its own source.

**No guard covered it.** `starter_parity.py` compares the four STARTERS, and outside Godot the
capture size lives in each stack's own source (`film.rs`, `film.ts`, `Probe.Film`) where an
agent may change it — so a submission-level divergence is invisible to it by construction. That
is rule 6 once more: the parity guard names the axes someone thought of, and capture geometry
was not one of them.

`tools/frame_parity.py` now measures it per run and refuses to be quiet about a mixed field.
Pinned on real data in both directions: `wg-audio48` **exit 1**, naming
`g2_tetris3d__rust__t0`; `wg-arena3d` **exit 0**, *"every submission filmed at the same size"*.

Which measures this affects, stated so the next frame-derived criterion is written knowing:
ink coverage and fraction-of-pixels-changed are **densities and are safe**; raw counts are
**not**; and a judge handed the PNGs directly is handed the difference.

### Why this retires the aspect

`ux` asks about onboarding and legibility — whether a newcomer can tell what to do. Palette
depth is a fact about the rasteriser. The scores ranked `ts` lowest and `rust`/`godot` highest,
in the same order as colour count, across both orders.

Causation is not established and does not need to be. This project's standing rule is that **a
stack-correlated signal is an instrument defect until a mechanism is named in the code** — and
here the mechanism is named and measured. The confound cannot be excluded, so the aspect cannot
carry a cross-stack claim.

> **This is #26 arriving a second time at the end of a redesign built to prevent it.** The old
> rubric's only measured signal was a frame-capture artifact; the new layer's only surviving
> signal is a frame-rendering artifact. The redesign changed the question, the packing, the
> gates and the sampling, and the thing that survived to the end was still a property of how
> the four engines draw.

### The count is now six

| # | signal | mechanism |
|---|---|---|
| 25 | two determinism criteria failed on Unity | a second probe session on a locked project |
| 26 | `look.feedback` failed the most-HUD submissions | IMGUI and DOM cannot reach an offscreen render |
| 28 | 3x4 pixel frames on Godot | viewport framed before it was realised |
| 43/49 | rust and ts arms broken | `syspolicyd` gating `execve` of new binaries |
| 53 | `idiomatic` returns a per-stack constant | the file extension identifies the stack |
| **59** | **`ux` separates the stacks** | **palette depth differs 60x by renderer** |

**Every stack-correlated signal this project has produced has been a property of the
instrument. Six for six.**

### What survives

Nothing in tier 3 is usable for a cross-stack claim. `fun` is now honest — its confound is gone
by construction (#52) — and it does not separate the stacks. That is the layer's final state:
**repaired, and still measuring nothing about the variable under test.**

---

## 62. Every code pack was truncated, the amount varies by stack, and the record has said so since the first matrix

`anonymise.py` fills a judge's code pack by walking files in **sorted path order** and stopping
at `max_chars = 160_000`. Nothing is dropped by rule — `tools/` is not in `SKIP_DIRS`, `.mjs`
is in `CODE_EXT` — files are dropped because the budget ran out before the walk reached them.
**Which files survive therefore depends on where their paths sort**, and on how much
earlier-sorting code the agent happened to write.

Measured across all eight `g2_tetris3d` packs: every one sits at the cap (160,102-160,308
characters). The field was truncated in its entirety.

### The deficit is stack-correlated

`anonymise.py` has written `files_dropped_for_length` into every pack manifest since the first
matrix, and it lands in every `eval/report.json`. **60 submissions carry it. 32 dropped at
least one file. Nothing has ever read it.**

| stack | n | mean | median | max | any>0 |
|---|---|---|---|---|---|
| godot | 14 | 1.1 | 0.0 | 8 | 4 |
| rust | 16 | 2.1 | 1.0 | 7 | 10 |
| ts | 16 | 1.5 | 0.0 | 8 | 6 |
| **unity** | 14 | **6.1** | **4.5** | **21** | **12** |

Unity loses three to six times as many files as any other stack, and 12 of its 14 submissions
lost at least one. Worst case `g3_arena__unity__t0` at 21 files. The mechanism is obvious in
hindsight: more C# spread over more files exhausts a fixed budget sooner.

### What this does and does not establish

**It does not invalidate `idiomatic` or `architecture` by itself, and the data says so.** Godot
has the LOWEST drop rate and also scores low; the deficit does not map onto the ordering. The
temptation here is a second retraction and the evidence does not support one.

**It does mean the field was never a controlled comparison.** Evidence completeness varies per
submission and correlates with stack, so any cross-stack ordering from a code-reading aspect is
confounded by how much of each submission the judge was shown. That confound has to be ruled
out before either aspect's ordering is believed, and it never was — including in the
2026-08-17 round. It applies retroactively to every code-aspect round this project has run.

It also sharpens #53 rather than replacing it: `idiomatic`'s evidence strings cite `BoxPool`
with line ranges, `Mesh.MarkDynamic()` and the `Update`/`FixedUpdate` latching split with its
rationale, so the judge is demonstrably reading files. It can read carefully and still order by
prior. Both can be true; #53's strong form is weakened and neither is settled.

### Why this one is different from the other six

The six instrument artifacts before it (#25, #26, #28, #43/#49, #53, #59) were each caught by a
**suspicious result** — a score that looked wrong, a split that looked too clean. This one was
never visible in a score. It sat in a stored field, in every record, from the beginning.

> **Rule 11 one level out: the record already told us, and no gate looked.** The rule was
> written about `agent.final_text` — read what the subject said about its own work. The same
> failure applies to what the HARNESS said about its own evidence. A number nothing reads is a
> number that is not being collected, whatever the file contains.

And the first attempt to measure it repeated the pattern: probing a handful of guessed key
names (`judge_pack`, `pack`, `anonymise`) rather than searching for the key returned **35 of 60
records** and reported that subset as the population. A filter that silently drops 42% of its
input and produces a plausible table is the same shape as the defect it was measuring.

### Fixed

- `evaluate.py` gains a **completeness gate**: a field where any submission dropped files, or
  where drop counts differ materially across the field, is refused for code aspects rather than
  judged. The data already existed; the gate needs nothing recomputed and would have fired
  before any of the rounds already paid for.
- The **brief now states how much was withheld**, because a pack that silently omits files asks
  the judge to score completeness it cannot assess.
- The budget itself was left as an open design question in `eval/IMPROVEMENTS.md` — raising it,
  or budgeting per bucket so no directory is starved by sort order. **Not** tuned until the
  drop counts look acceptable, which would be fitting the instrument to its data.
  **RESOLVED 2026-08-22: the budget was removed entirely (#69), not tuned.** Neither option
  above was taken. The judge is agentic and already chooses what to read, so the cap was a
  pre-filter in front of a selector, deleting files by alphabetical accident before the judge
  could choose. The completeness gate was repurposed to assert the drop count stays zero.

---

## 66. Unity's `just verify` told the agent its work was clean; the same tree fails from a clean extract

`g4_platformer__unity__t1` (run `wg-g4c-2026-08-21`) failed `verify.green` and `lint.clean` — `just verify` exit 1, five
`CA1861` analyzer errors in `Assets/Editor/AssetGen.cs`, a **602-line, entirely agent-written
file** (`new file mode` in the diff). On the evidence that looks like the third genuine
submission defect in the project.

It is not. **The agent's own final `just verify` printed:**

```
✓ fmt: 0 file(s) rewritten
✓ lint: all assemblies compile clean
✓ test-sim: 85 passed, 0 failed, 0 skipped (of 85, 10.7s)
✓ test-render: 13 passed, 0 failed, 0 skipped (of 13, 0.2s)
✅ verify passed
```

Established mechanically, not inferred:

| check | result |
|---|---|
| `just lint` in the agent's warm work tree | **exit 0**, "all assemblies compile clean" |
| `just lint` on `submission.tar.gz` extracted to an empty directory | **exit 1**, CA1861 ×5 |
| tarball vs work tree, `cmp` on `AssetGen.cs` | **identical** |
| violations present in the shipped file | yes — lines 444, 581, 583, 584, 592 |

The agent *had* seen CA1861 earlier (record 287), fixed some of the sites, and been told by the
gate that the file was clean. It was not: the Editor assembly was not re-analysed after the
edit, so the surviving violations never reappeared.

> **The Unity template's `just lint` is not reproducible across build-cache state. It can report
> a tree clean that fails from cold.** The starter's own justfile calls `just verify` "ONE
> command to know whether the work is done" — and on this arm it is a command whose answer
> depends on what was compiled before it.

**Do not count this as a submission defect** — *as of the date of this finding*. The agent ran
the gate it was told to run and was told it passed; that is the task performed as specified.

> ⚠️ **SUPERSEDED IN PART, 2026-08-22.** The recipe is fixed (task 07): `just lint` now deletes
> `Library/` from its scratch copy when running strict, so it answers from the code. With the
> gate honest, `g4_platformer__unity__t1` **is** a genuine submission defect — the project's
> third — because the five CA1861 violations were always in the shipped file. **The code never
> changed; the gate stopped lying about it.** Everything above remains correct about what was
> true when the trial ran, and that is exactly why the reclassification is dated rather than
> retroactive. See `eval/RUNS.md`, eighth comparability break.

The count of genuine submission defects stood at
two. An agent that runs the gate it is told to run, and is told it passed, has done the task as
specified; a gate that answers differently on a clean checkout is measuring its own cache.

The scope is wider than one trial. This gate has been green on the Unity arm across four
matrices, and nothing has ever checked its answer against a cold build — so *"Unity passed
lint"* has never been the claim it appeared to be. **`starter_parity.py` compares recipe text,
not recipe reproducibility**, which is why it never fired.

The fix belongs in `starters/unity` — the product — so it is **not** applied here: editing a
starter changes the thing being measured and requires re-running `verify_blind.py` and
`starter_parity.py`. It is filed as a hypothesis in the root `IMPROVEMENTS.md`. The candidate is
forcing analyzer re-run (a clean, non-incremental build in `lint`), and the measurement
that could refute it is whether a cold `just lint` and a warm one agree on a tree known to have
violations.

## 67. `(0, 0)` is a plausible position, so an empty rectangle scored as one

`g4_platformer__unity__t0` (run `wg-g4c-2026-08-21`) failed `attack.faces` with:

> hitbox centre relative to the character: facing right **[-61.7, -61.7, -61.7]**, then after
> turning (facing=-1.0) **[-11.0, -11.0, -11.0]**

Read as written that is a hitbox on the wrong side, twice — a clear submission bug. Its source
says otherwise, and says it in one line:

```csharp
public Aabb Hitbox => AttackConnects ? Aabb.FromCentre(...) : Aabb.Empty;
```

`Aabb.Empty` centres at **(0, 0)**. The player was at x=61.7 and x=11.0. Both "measurements" are
the origin minus the player's position — the criterion sampled ticks on which no hitbox existed
and treated the sentinel as a location.

**The bot did gate its sampling** — on `attack.active` — which is why this survived review. The
conflation is one level down: `active` and `hitbox` answer different questions, and the
submission had written that down in its own probe:

> `active` means a swing is in progress. `hitbox` is only the rectangle that damages THIS TICK,
> so it is empty during the wind-up and the follow-through.

That is not merely legal, it is what `attack.active_frames` *demands* — the damaging window must
be shorter than the swing. **So the better a submission implements one criterion, the more ticks
it offers the other one to misread.** The two criteria were in tension and only one fixture
could ever reveal it.

### Why no mutant or variant caught it

`ref_platformer` sets `attack_active` to *exactly* the damaging window
(`STARTUP < attack_t <= STARTUP + ACTIVE`) and empties the hitbox outside it, so on the
reference `active` is true **iff** a hitbox exists. The two tick sets are identical and no
fixture in the suite could tell them apart. This is #65's asymmetry again with the reference
itself as the blind spot — the fifth instance.

**Fixed:** `_live_hitbox_x` skips degenerate boxes by width and height rather than reading their
centre, and a fourth variant (*`active` spans the whole swing, hitbox only the middle*) pins the
other legal reading of the contract. Both criteria pass on it.

> **A sentinel that is in range is not a sentinel.** `(0, 0)`, `-1`, `0.0` and `""` all pass a
> null check and all read as data. Where a field can be absent, test the ABSENCE — here, the
> width — never the value.

### A third defect, found while fixing the second

The first attempt to make the variant pass listed `stage.completes` in the variant's
`tolerates`. It went green. But `stage.completes` is `diagnostic_only` and reports
`scored=False` **by design**, so the variant harness was counting "not scored on purpose" as
"came back unscored", and would have failed *every* variant on a fixture that has one. Waiving
it would have buried a harness bug in the single field allowed to excuse failures — rule 7
exactly. The harness now reads `diagnostic_only` from the bot, and the waiver was removed.

---

## 69. The pack budget was a pre-filter in front of an agent that already chose what to read

`anonymise.py` capped each judge pack at 160,000 characters, writing files until the budget ran
out and dropping the rest. #62 established that the deficit was stack-correlated. What #62 did
not ask is **why there was a budget at all.**

The judge is agentic: `claude -p`, `--max-turns 120`, `cwd` set to the pack, prompted to read the
code in A/ through H/. **It was always going to browse selectively.** The cap did not protect it
from volume — it deleted files the judge might have chosen, by alphabetical accident, before it
could choose. A pre-filter in front of a selector, doing the selector's job worse and invisibly.

Measured by rebuilding one submission both ways, same starter, same filters:

| | files | chars | dropped for length |
|---|---|---|---|
| cap = 160,000 | 15 | 160,038 | 16 |
| **uncapped** | **32** | **388,968** | **0** |

**53% of `g4_platformer__unity__t0`'s packable code (run `wg-g4c-2026-08-21`) was invisible to
every code judgement this project has made.**

Removed. Every other filter stays — starter-identical drops, `DROP_NAMES`, `CODE_EXT`, empty
files, `neutralise()` — because those are blinding and noise control, not size.

### The gate had to be repurposed, not deleted

With no budget, drops are 0 by construction, so the completeness gate can never fire: #57's
"check that cannot fail". Deleting it was the obvious move and is wrong — a cap is *how this
defect arrived*, as a reasonable-looking guard on prompt size, and deletion leaves nothing to
notice the next one. It now asserts `files_dropped_for_length == 0` and refuses loudly if
truncation returns. **A gate that detected a defect became one that detects its return**, pinned
in both directions so its green is not vacuous. Argued in `eval/IMPROVEMENTS.md` 11a.

### A second defect, found only because the budget went

Rebuilding a pack from a macOS tarball extract produced **47 AppleDouble `._` sidecars** —
`._Probe.cs`, `._BuildScript.cs` — which inherit the real file's suffix, pass the `CODE_EXT`
test, and land in the pack as code files full of binary. They inflated a 32-file pack to 78.

No stored pack is affected: packs are built from the work tree, which has none. It is filtered
anyway, because **"no caller does that today" is not a property of the function**, and with the
budget gone every such file would reach the judge instead of being crowded out by the cap. The
cap had been hiding it.

**#62 is not retracted.** It describes what was true of every round already run: every stored
code judgement was made on a truncated, stack-correlated sample.

---

## 76. The Unity pattern was the field, not the stack — refuted by a $8.29 re-grade

`fun_frames` on `g2_tetris3d` at n=7 produced the first tier-3 result where between-stack spread
clearly exceeded within-stack: **1.857 against 0.286, a 6.5x ratio**, with Unity top and its two
trials returning *identical* means of 2.71. It was flagged rather than reported, on the standing
rule that a stack-correlated pattern is an instrument defect until a mechanism is named.

**It does not survive a change of game.** Same aspect, same four stacks, stored submissions,
$8.29:

| field | top stack | unity rank | between-stack range | mean within-stack gap | ratio |
|---|---|---|---|---|---|
| `g2_tetris3d` | **unity** | 1st | 1.857 | 0.286 | **6.50x** |
| `g3_arena` | ts | **3rd** | 0.750 | 0.750 | **1.00x** |
| `g4_platformer` | godot | **3rd** | 0.750 | 0.750 | **1.00x** |

A different stack tops each game — unity, ts, godot — and on the two new fields the between-stack
range **equals** the within-stack gap exactly, which is no separation at all.

### The n confound, checked rather than waved away

Tetris was judged at n=7 and the new fields at n=2, so the comparison changes two things. Holding
n constant by restricting tetris to every consecutive pair of rounds:

| tetris rounds | top | unity mean | ratio |
|---|---|---|---|
| 0,1 | unity | 2.25 | 3.00x |
| 1,2 | unity | 2.25 | 4.00x |
| 2,3 | unity | 2.75 | 4.50x |
| 3,4 | unity | 3.00 | 4.50x |
| 4,5 | unity | 3.00 | 2.80x |
| 5,6 | unity | 3.00 | 4.00x |

**Unity tops tetris in 6 of 6 windows at n=2.** So the arena and platformer results are not an
artifact of their lower n — at equal n, tetris shows the effect and the other two do not.

### What it was

Not a stack property, and not an instrument-wide prior of the kind #53 suspects for `idiomatic`.
The most defensible reading is the mundane one: **on that particular field, the two Unity
submissions were the ones this aspect liked** — which is what an aspect that reads submissions
rather than packaging is supposed to do, and is consistent with #68's positive result for the
telemetry channel.

The identical within-stack means (2.71, 2.71) that looked like rule 9's signature were the
strongest part of the case for an instrument defect, and they were a coincidence of two
submissions scoring alike on one field. On `g3_arena` the same stack's two trials scored **0.0 and
2.0** — the widest within-stack gap in the entire comparison.

> **A pattern with an identical-value tell, a 6.5x ratio and a plausible mechanism still
> evaporated on the first different game.** Flagging it rather than publishing it cost one
> paragraph; publishing it would have cost a retraction, and this project already has three.

### The null gains two more fields

Incidentally and more durably: `fun_frames` returns **no stack separation** on `g3_arena` and
`g4_platformer` (ratio 1.00x on both). Tier 3's frames aspect now agrees with the other
instruments on three of four games. n=2 on the new fields, so this is an observation and not a
measurement — but it points the same way as everything else.

---

## 77. Rebuilding an old pack against a moved starter reclassifies template code as authored work

Unblocking the code aspects on `g3_arena` (run `wg-matrix-2026-08-13`) meant rebuilding its judge
packs uncapped (#69). The work trees for that run are long gone, so the rebuild reads
`submission.tar.gz` — and filters against `starters/`, **as it is now**.

`starters/` changed on 2026-08-17 (the launch guards). So the starter-identical filter, which
exists to keep template code out of the judge's view, was comparing August-13 submissions against
August-17 templates:

| submission | files it stops recognising as template |
|---|---|
| `g3_arena__godot__t1` | `tests/frame.gd` |
| `g3_arena__ts__t0` | `src/view/capture.ts` |
| `g3_arena__ts__t1` | `src/view/capture.ts` |

Three of eight, and **stack-correlated** — godot and ts, never rust or unity — because those are
the stacks whose capture files the guard work touched. Left alone, `idiomatic` and `architecture`
would have been shown template capture code as the agent's own work, in two stacks only. That is
the shape this project treats as disqualifying.

### The distinction that made it fixable

A naive fix — "exclude anything that appears in the current starter" — is wrong, because agents
legitimately modify template files and those modifications *are* authored work. The correct
exclusion set is narrower and provable:

```
drift = (files in the rebuilt pack) - (files in the stored manifest)
                                    - (files the original build dropped FOR LENGTH)
```

The third term matters. Five submissions gained files, and only three were drift: `rust__t1`
gained `.codex/hooks.json` and both unity trials gained `Assets/Editor/Probe.cs`, each of which
the original build had dropped for **length**, not for being template code. Those are legitimately
returning and excluding them would re-create #69.

**Being dropped as starter-identical in the original build is proof the agent never touched that
file.** That evidence survives even though the starter it was compared against does not.

### Verified, not asserted

`anonymise.build_pack` gained an explicit `exclude_origins`, and the rebuild reproduces the
**original starter-identical count for all eight submissions exactly** (8, 9, 5, 5, 9, 9, 11, 11).
The only growth is the three submissions reclaiming length-dropped files. Zero AppleDouble
sidecars reached the packs, which is the filter from #69 doing its job on the first real tarball
rebuild.

> **A hash-based filter silently changes meaning when the thing it hashes against moves.** It does
> not fail; it reclassifies. The stored manifest of the original build is the only record of what
> the filter decided when it was still correct, which is a reason to keep manifests rather than
> just scores.

---

## 78. `ux` tracks distinct-colour count on all three games it has been run on

#59 measured `ux` scores correlating with the number of distinct colours in a submission's
frames — on `g2_tetris3d` alone, which #71 later established was the only game tier 3 had ever
judged. Task 03 asked whether that survives a change of game. It does.

Spearman on average ranks, n=8 submissions per game, colours counted over every pixel of one
frame per submission:

| game | rounds | `ux` ~ distinct colours |
|---|---|---|
| `g2_tetris3d` | 2 | **+0.528** |
| `g3_arena` | 2 | **+0.733** |
| `g4_platformer` | 2 | **+0.573** |

Three independent fields, three different games, sixteen different submissions each time, and
the sign and rough magnitude hold throughout. #59's original +0.735/+0.823 was on a different
frame sample of the same field; the effect is not an artifact of which frame was picked.

**Checked for a single-point artifact.** `g3_arena` in `wg-matrix-2026-08-13` contains one
extreme outlier — `g3_arena__godot__t1` at 512 distinct colours where the rest of that field
sits between 3 and 10.
Dropping it leaves **+0.596** at n=7, so the correlation is a property of the field and not of
that submission.

The colour ranges themselves differ wildly by game — arena spans 3-512, tetris 6-1254,
platformer 31-874 — which makes the consistency more telling rather than less: the aspect is not
keyed to an absolute colour count but to where a submission sits *relative to its own field*.

### What this settles

> **`ux` is measuring picture richness, and it does so wherever it is pointed.** #59's retirement
> of the aspect is confirmed rather than narrowed, and it is no longer conditional on one game.

It also completes the pair with #76. Both are frames-only aspects on the same fields:
`fun_frames` correlates **-0.120** with distinct colours while `ux` correlates **+0.53 to +0.73**.
That is the strongest form of the #68 comparison-2 result — the frames channel is not
intrinsically contaminated, because two aspects reading the *same pixels* diverge completely on
whether they track colour depth. **The defect is in `ux`, not in the evidence it is given.**

### What it does not settle

Whether "more colours" is *entirely* illegitimate. A richer render could genuinely be easier to
read, so the correlation alone does not prove the aspect is wrong — it proves the aspect is
dominated by a property of the renderer rather than of the authored work, which is disqualifying
for a **cross-stack** comparison and says nothing about a within-stack A/B.

---

## 79. `idiomatic` has a real stack-level component, but #53's contrast between stack and submission was backwards

#53 concluded that `idiomatic` *"scores the stack rather than the submission"*, resting on a
specific contrast measured at **n=1 per game**:

> the **stack-level** signal is constant across games while the **submission-level** signal is
> not stable at all. That is the wrong way round for an instrument supposed to be measuring
> submissions.

Task 02 re-ran it properly: three games, **n=4 rounds each**, every score joined on
`submissions[].submission` and never on pack label (#70), with pair resolution against the
judge's own SD rather than by eyeballing means.

### The stack-level component is real, and it never contradicts itself

| game | packs | resolved stack pairs (of 6) | which |
|---|---|---|---|
| `g2_tetris3d` | capped | **4** | rust>godot, rust>unity, ts>godot, ts>unity |
| `g4_platformer` | uncapped | **4** | **identical set** |
| `g3_arena` | uncapped | 2 | godot>unity, rust>unity |

- **Zero contradictions anywhere.** No pair resolves in opposite directions in any two games.
- **`rust > unity` resolves in all three games**, across 24 different submissions.
- tetris and platformer agree on all four pairs **despite different pack regimes** — one
  truncated, one complete — which strengthens the agreement rather than confounding it.

So a stack-level signal exists and survives a change of game. **#53's core claim stands.**

### But its supporting contrast does not

#53 said submission-level scores were *"not stable at all"*. They are stable. Counting
submissions whose four raw observations are identical:

| game | invariant submissions |
|---|---|
| `g2_tetris3d` | **6 of 8** |
| `g3_arena` | 3 of 8 |
| `g4_platformer` | 2 of 8 |

The `godot__t0` cell is invariant at exactly 3 across all four rounds in *each* of the three
fields — three different submissions (`wg-matrix-2026-08-13` for tetris and arena,
`wg-g4c-2026-08-21` for platformer), each stable within its own game. **Both levels are stable**,
so the asymmetry #53 built its argument on is an artifact of having had one round per game: at
n=1 every submission looks unstable because a single draw carries the judge's full ±0.5 SD.

> **A contrast between "stable" and "unstable" needs both terms measured at the same n.** #53
> compared a stack mean over eight submissions against a single submission's single score and
> read the difference in variance as a difference in kind. It is a difference in sample size.

### The methodological result, which outlives this finding

Full rank correlation between the three games gives tau **-0.333, +0.333, -0.333** — apparent
disagreement. Resolved-pair analysis on the same data gives **zero contradictions** and a shared
core. Both are correct; they answer different questions.

> **With ties and judge noise, rank correlation hides the reproducible subset.** A tau over four
> stacks weights unresolved pairs — pairs whose order is noise — exactly as heavily as resolved
> ones, so a single swap inside a statistically tied pair flips the coefficient's sign. **Only
> pairs individually resolved against `SEi + SEj` show what replicates.**

Reporting the tau alone would have refuted #53. Reporting the resolved pairs alone would have
overstated it. The pair of them is the result: a stable core with an unstable ordering on top.

> ⚠️ **COMPROMISED AS A BLIND RESULT, 2026-08-22 (#83).** Every `idiomatic` round behind the
> table below was later shown to have opened pack files naming the submissions outright — all
> four `g1_pong` rounds, three of four `g3_arena`, four of six `g4_platformer`. The judge knew
> which stack it was scoring. The ordering may still be a real reading of the code, but it is no
> longer defensible as *blind*, and the four-game `rust > unity` result must not be cited as
> evidence that the judge cannot have been applying a prior.

### The core holds on a fourth game

`g1_pong` (**4 rounds**, `wg-matrix-2026-08-13`) resolves **rust>godot and rust>unity** — two of
the four core pairs, the rest unresolved but **not contradicted**. Tallying across all four games:

| pair | tetris | arena | platformer | pong |
|---|---|---|---|---|
| **rust > unity** | ✓ | ✓ | ✓ | ✓ |
| rust > godot | ✓ | | ✓ | ✓ |
| ts > godot | ✓ | | ✓ | |
| ts > unity | ✓ | | ✓ | |
| godot > unity | | ✓ | | |

> **A result that gets weaker with more data is the one most likely to survive by neglect.**
> Nobody re-checks a pair that has already resolved: the incentive and the attention both run
> the other way. Twice now in this project a claim has weakened when evidence was added, and both
> times it was only caught because the extra evidence happened to arrive before the write-up
> hardened. **Re-run the analysis after every new round, including on the pairs that already
> passed.**
>
> ⚠️ **An earlier report of this table, at n=3, listed `ts>godot` as resolved on pong. The fourth
> round removed it** — godot rose from 2.50 to 2.75 and the gap fell inside the combined SE. It
> is corrected here rather than left standing, because **adding evidence weakened a claim**, and
> that is the direction a result is most easily lost in: nobody re-checks a pair that already
> resolved. It is also a live demonstration of the low-n warning in `separation()` — n=3 is
> exactly where an SD estimate flatters itself.

**`rust > unity` resolves in all four games, and nothing contradicts anything.** Arena remains
the least decisive field rather than a dissenting one. Four games, 32 submissions, four different
task specifications — the stack-level component is the most reproducible thing tier 3 has
produced.

### Which stacks are constant: a gradient, not a split

Testing each stack's cross-game variation against its own measurement error — counting game-pairs
whose means differ by more than `SEa + SEb`:

| stack | tetris | arena | platformer | game-pairs differing |
|---|---|---|---|---|
| unity | 3.00 ±0.00 | 3.00 ±0.00 | 3.00 ±0.19 | **0 of 3** |
| godot | 2.88 ±0.12 | 3.25 ±0.16 | 3.12 ±0.12 | 1 of 3 |
| rust | 3.62 ±0.18 | 3.25 ±0.16 | 3.62 ±0.18 | 2 of 3 |
| ts | 3.50 ±0.19 | 2.88 ±0.30 | 3.88 ±0.12 | **3 of 3** |

So *some* stacks behave like constants and others do not — but it is a **gradient from unity to
ts**, not two-and-two, and **rust varies more than godot**, not less. A first reading that paired
unity with rust as the constants had the second member wrong.

> ⚠️ **RESOLVED, and the alarm was mis-framed — see #81.** Four rounds of one submission are
> repeated measurements, so a small SD across them is *reliability*, not independent subjects
> agreeing. Rule 9 speaks only to the second. Truncated packs, caching and anchor-defaulting were
> each tested and eliminated; the residual pattern has p≈0.27 of arising by chance in some stack.
> The paragraph below stands as what was believed at the time.

**`unity` is the striking case and the one worth pursuing:** its SE is exactly 0.00 on two
different games, meaning the judge gave *literally the same score* to all eight unity submissions
in four rounds, twice, on unrelated work. That is rule 9's signature — independent subjects
agreeing exactly report the instrument — and it is a sharper, more testable claim than a uniform
language ranking: **a prior on SOME stacks**. It is stated here as a hypothesis to test, not a
result.

### The effect is small and the scale is barely used

Every score in 96 observations is **2, 3 or 4** on a 0-4 scale, and stack means span 2.88-3.88.
The resolved pairs are real but they are separations of a quarter-point against SDs of
0.35-0.83. This is #74's compressed-scale problem again, and it means the ordering is
**resolvable but not large**.

### Verdict on #53

**Narrowed and confirmed, with its argument replaced.** The conclusion — a stack-level signal
that a cross-stack ranking must not be built on — holds on better evidence than it originally
had. The reasoning that got there does not, and the mechanism it named remains the live one: the
file extension is still in every pack, still uniquely identifies the stack, and `idiomatic`
**cannot** be blinded to it, because you cannot judge whether Rust reads like Rust without
knowing it is Rust. That is unchanged and unfixable, and it is why the aspect stays barred from
cross-stack use regardless of how consistent it looks.

---

## 83. The answer key was in the judge's pack again: `.codex` hook scripts carried the trial id

Investigating how much the code-aspect blinding leaks turned up something categorically worse
than the leak being investigated.

Agents write `.codex/hooks/*.sh` — tooling configuration — and those scripts embed the **absolute
work-tree path**. `SKIP_DIRS` listed `.claude` and `.github`, but not `.codex`, so the files
reached the pack carrying:

```
/Users/…/game-research-work/wg-g4c-2026-08-21T02-26-46/g4_platformer__godot__t1/.codex/hooks/…
```

That names the **game, the stack and the attempt**. It is not a hint about the language, it is the
identity of the submission, in a directory the judge is told is anonymous.

**31 stored packs contain a trial id.** Across `wg-audio48` and `wg-g4c`, for `g1_pong`,
`g2_tetris3d` and `g4_platformer`.

### This is #32, and #32's own lesson said so

#32 found `MAPPING.json` inside a blinded judge's working directory and concluded:

> **A judge with the answer key produces a ranking that survives every validation gate this
> project has.** Order-invariance passes, independence passes, adjudication passes. None of them
> can ask what the judge knew.

That was fixed by asserting no `MAPPING` file is left in the pack — **a fix aimed at the file that
had failed**, not at the property. The property is *no text in the pack may name the submission*,
and the next violation arrived in a different file with a different name, exactly as a
list-shaped guard predicts.

### Fixed in three independent places, because one of them is a list

1. **`SKIP_DIRS` gains `.codex`, `.cursor`, `.aider`, `.vscode`, `.idea`** — agent tooling as a
   *class*. Still a list, and still therefore incomplete.
2. **`neutralise()` scrubs the identity pattern itself**: any `g<n>_<game>__<stack>__t<n>` becomes
   `SUBMISSION` and any work-root path becomes `/WORKTREE`, wherever they appear. This does not
   depend on knowing which file will carry it.
3. **`verify_blind --packs` now fails on a trial id or a work-tree path**, checked *before* stack
   tokens because it is worse, and **not** exempting `code/` — which is where these were, and
   which the stack-token scan skips because `neutralise()` has already run over it.

Pinned both directions: a freshly built pack is clean; a stored pre-fix pack reports
`TRIAL ID 'g4_platformer__godot__t1' … the judge is holding the answer key`.

### What it invalidates — ANSWERED, not unknown

The first version of this finding said "unknown". It is partly answerable, and cheaply: task 09
added a capture of **which files the judge actually opened**, so for any round with that log the
question is a set intersection rather than an inference. Intersecting opened paths against the
index of pack files containing a trial id:

| | |
|---|---|
| judge rounds on disk | 63 |
| rounds with file-open logs | **37** |
| of those, rounds that **opened a leaking file** | **14** |
| rounds that identified **all eight** submissions | **3** |

**The answer key was not merely present. It was read.** In three rounds —
`g1_pong__idiomatic__seed1`, `g4_platformer__architecture__seed0` (both in
`wg-funframes-crossgame`) and `wg-g4c-capgate/out/uncapped/g4_platformer__idiomatic__seed1` — the
judge opened a file naming the trial for **every submission in the field**. Verified by dumping
the eight paths and the eight ids they resolve to.

> **The "all eight" count was disputed at 3 against 0 and reconciled by reproducing the other
> method rather than re-deriving the answer.** Two independent defects, neither in the matching:
> a glob of `runs/*/[a-z]*/g*__*__seed*.json` missed four rounds sitting one directory deeper,
> and the label was extracted with `path.split("/")[0]` on an **absolute** path, which returns
> `''` for every file — so the label set was always `{''}`, size 1, and `len(labels) == 8` could
> never fire. Fixing only the label extraction turned 0 into 9 on the looser per-submission
> keying; the strict count is 3.
>
> The tell was stated before the cause was found: *a permissive matcher returning fewer hits than
> a strict one usually means the two are matching different things.* **True, and it needs a
> qualifier or it points at the wrong stage:** the two may be matching identically and diverging
> **downstream, in the grouping**. Here the match was fine and the attribution collapsed — every
> hit was filed under the same empty label, so a per-round count that depended on distinct labels
> read 1 where it should have read 8.
>
> **Check the grouping key before re-examining the matcher.** A count that aggregates by a derived
> key has two places to fail, and the one that produces a *plausible* number is the second: a
> broken matcher usually returns zero hits and announces itself, while a broken grouping returns
> the right hits filed wrongly.
>
> The defective test was `len(labels) >= 8` over labels that were always `{''}` — **a guarantee,
> not a measurement**, and the vacuous-check shape catalogued in #73, committed while auditing an
> audit.

Per game and aspect, counting only rounds with logs:

| field | compromised | clean |
|---|---|---|
| `g1_pong` / idiomatic | **4** | 0 |
| `g3_arena` / idiomatic | 3 | 1 |
| `g3_arena` / architecture | **2** | 0 |
| `g4_platformer` / idiomatic | 4 | 2 |
| `g4_platformer` / architecture | 1 | 1 |
| `g2_tetris3d` / both | — | — (no logs; rounds predate the capture) |

### Two traps worth naming, both general

**A mitigation that alters the artifact can defeat the check looking for the thing it mitigates.**
`blind_language` renames pack files to `.src`, so a full-name comparison could never match a
stored `other/01.json` — and `architecture`, the *more* blinded aspect, came back clean for that
reason alone. The defence hid the evidence of its own failure.

**A repair can enlarge a defect that is not known to exist.** Removing the pack budget (#69) was
correct on its own terms — a judge shown half a submission has not read it — and it strictly
increased exposure of the answer key, because the dropped files were the leaking ones. Not an
argument against the fix; an argument for bounding what a fix touches, and for asking what a
change makes newly *visible* as well as what it makes newly *correct*.

### A correction inside the correction

The first pass reported `architecture` as entirely clean. **That was a matching artifact**:
`blind_language=True` renames pack files to `.src`, so `other/01.json` becomes `other/01.src` and
a full-name comparison could never fire. Re-run on stems, `architecture` is compromised in 3 of
its 4 logged rounds — including the 8-of-8 round. **The aspect that looked exonerated was the one
whose defence hid the evidence.**

### The truncation had been protecting the blinding

The only clean `g4_platformer__idiomatic` rounds are the two **capped** arm rounds from task 09.
Measured directly: the capped packs contain **0** files bearing a trial id across 118 files; the
uncapped packs contain **8** across 207.

**The 160,000-character budget removed in #69 had been dropping the leaking files for length.**
Removing it was correct on its own terms — a judge shown half a submission has not read it — but
it strictly increased exposure of the answer key, and nobody could have predicted that because
nobody knew the answer key was there. A fix in one place enlarged a defect in another that was
not known to exist.

### What this costs

**Every cross-game `idiomatic` conclusion in #79 rests on compromised rounds.** All four `g1_pong`
rounds, three of four `g3_arena` rounds, and four of six `g4_platformer` rounds opened a file
naming the submissions. The `{rust, ts} > {godot, unity}` core and the four-game `rust > unity`
result are **not defensible as blind judgements** and are marked accordingly in #79.

They are not thereby *wrong* — a judge that knows the stack may still be reading the code — but
that is precisely the distinction `DECISIONS.md` now records as permanently unavailable as a
defence. The blinding argument is gone for these rounds specifically, on evidence rather than on
principle.

> **#32 said no gate can ask what the judge knew. That was true when it was written and is no
> longer true**: the file-open log answers it directly for any round that has one. The capture
> was added for an unrelated question — did a bigger pack make the judge read more? — and it is
> the only reason this defect could be bounded at all rather than left as a class-wide suspicion.
> **Capture what the instrument did, not only what it concluded.**

## 95. A judge pack is a numbering, not a set, so re-evaluating a run left nine passes stacked on disk

`anonymise.build_pack` did `dest.mkdir(parents=True, exist_ok=True)` and never removed what was
already there. That reads as harmless — the same submission produces the same files, so the
second pass overwrites the first. It is not, because **a label is a position, not an identity**:
files are written as `bucket/NN.ext` with `NN` counted within the bucket, so the moment the
*picked set* changes between two passes the numbering shifts underneath and the earlier pass's
files survive under labels the new manifest does not list.

The picked set changes for ordinary reasons: a starter edit (#77), a new `exclude_origins`, an
extension added to `CODE_EXT`, `.codex` moving into `SKIP_DIRS` (#83), the character budget being
removed (#69).

Measured 2026-08-23. Six runs hold judge packs on disk, 68 submissions between them. **43 carry a
manifest and can be checked at all**; the other 25 (`wg-matrix-2026-08-13` 24, `wg-calib` 1)
predate the manifest and are *unmeasurable, not clean* — they already refuse for a different
reason. Of the 43, **35 are clean** (`wg-arena3d` 8, `wg-audio` 11, `wg-audio48` 16) and 8 are
not, all of them `wg-g4c-2026-08-21`, which was evaluated nine times straddling both the #69 cap
removal and the #83 leak repair and carries **23 stale files in 222 — 10.4%**, stack-correlated:

| stack | stale files |
|---|---|
| unity | 10 |
| godot | 8 |
| ts | 3 |
| rust | 2 |

Twelve are byte-identical to a live file, so the judge sees the same code twice under two names.
Eleven carry content no manifest lists, and **seven of the eight submissions hold a `.codex`
hooks config naming their own trial id verbatim** — `g4_platformer__rust__t0` and the rest, the
#83 answer key, sitting in the stored pack six days after #83 was closed. No file the manifest
lists carries either pattern.

**Blinding survives, by a mechanism that is not the repair.** `field.build_pack` runs
`neutralise()` on every file as it copies, and both `_TRIAL_ID_RE` and `_WORK_PATH_RE` rewrite
these to `SUBMISSION` and `/WORKTREE`; grepping a freshly built `architecture` and `idiomatic`
pack for either pattern returns nothing inside the pack directory. #83's own fix — adding
`.codex` to `SKIP_DIRS` — did not hold, because it only governs what the *next* pass picks and
nothing removed what earlier passes had already written.

### The `.src` collisions are the symptom, and they are worse than duplication

`architecture` is `blind_language`, so `field.build_pack` rewrites every pack file to `.src`.
Across the 43 checkable submissions, rebuilding the labels from the **manifests** collides
**0 times**; rebuilding them from **disk** collides **15** — all 15 in `wg-g4c` — and every
colliding pair is one live file and one stale one. Files are copied in
`sorted(rglob)` order and last write wins, so in **7 of the 15** the stale file overwrites the
live one — `Assets/Editor/Probe.cs`, `Assets/Editor/Json.cs` and `tools/audio-manifest.mjs`
among them. The `architecture` pack for that field holds 215 files where `idiomatic`'s holds
230: unity loses 8, godot 6, ts 1, rust 0.

That is #62's shape through a third mechanism — the amount of itself each submission is shown is
unequal and stack-correlated — so **no cross-stack `idiomatic` or `architecture` ordering on
`wg-g4c` is defensible.** Reliability measurements are unaffected and the reason is worth
stating precisely rather than assuming: the pack is a deterministic function of a static input,
so every repeat of one round reads the identical field.

### Why every gate the project owns was blind to it

`pack_completeness` reads `files_dropped_for_length`, a number `anonymise` computes about **its
own input**, and #69 made that 0 by construction. Nothing read the destination. Nine passes
returned normally; `build_pack` has no failure mode here at all.

> **A gate that reads a component's input cannot see what its output accumulated.** The
> completeness gate was repurposed in #69 to assert an invariant about the input and was
> reasonable on its own terms; what was missing is that the pack on disk is a *different object*
> from the manifest describing it, and only one of them was ever opened.

`field.pack_matches_manifest` now opens the directory and asserts set equality per submission,
`field.py packcheck --run R` runs it standalone, and `field.build_pack` refuses a field whose
packs do not match — including a pack with no manifest at all, which is **unmeasurable, not
clean** (25 stored submissions predate the manifest and already refuse for a different reason).
`--allow-truncated` does not excuse it: that escape exists for the capped-vs-uncapped control,
where truncation is the experiment, and a stale file is not an experimental condition.

**The fixture had to be a variant, not a mutant** (rule 15). Deleting the clearing code cannot
manufacture the input that produces this; only running the real function twice over one
destination with a *changed exclusion set* can. `judge/pack_selftest.py` does that, and against
the unfixed function it fails 4 of 7 expectations; the same three-pass check run over the 16 real
submissions of two runs fails **8 of 8** before the fix and **0 of 16** after.

## 98. The Godot template's own gate was red before any agent touched it, and only that arm paid

`build.compiles` and `verify.green` are two of the fourteen tier-1 criteria and both are nothing
more than the exit code of a recipe in the submission's own justfile (`judge/static.py:380`). So a
starter whose gate is red on an untouched tree hands **every submission in that arm** two
automatic failures in the tier weighted 0.31, and no other arm pays it.

`eval/starters/godot/tools/check.gd:51` called `script.reload()` on every `.gd` file it scanned.
`tools/no_raise.gd` is declared `NoRaise="*res://tools/no_raise.gd"` under `[autoload]` in
`project.godot:79`, so the engine has already instantiated it by the time a `SceneTree` script
runs. Godot refuses to reload a script with a live instance, returns an error, and the loop cannot
tell that error apart from a parse error. Measured 2026-08-23 on a fresh copy with the harness
uninvolved, twice:

```
ERROR: Cannot reload script while instances exist.
   at: reload (modules/gdscript/gdscript.cpp:754)
COMPILE res://tools/no_raise.gd — see the SCRIPT ERROR lines above
CHECK scripts=18 failures=1
```

`just check` exit 1, `just verify` exit 1, on a file that compiles perfectly. The other three
starters were measured the same day, two ways — an `rsync` reproducing `wholegame.prepare()`'s
ignore list, and `tools/starter_gate_control.py` importing that list — and **rust, ts and unity
are all exit 0 on `just check` and on `just verify` from a pristine copy.** The red baseline is
one arm.

### How much stored evidence paid for it: none, and the reason is luck

20 stored Godot whole-game submissions exist across seven runs. The autoload arrived with the
2026-08-17 no-raise starter edit — RUNS.md's seventh comparability break — so **only 4 carry the
defect at all**: `wg-g4b-2026-08-17` t0/t1 and `wg-g4c-2026-08-21` t0/t1. The 16 earlier ones have
neither `tools/no_raise.gd` nor a `NoRaise=` line in their stored `project.godot`.

Of those 4, **0 were graded with the defect unrepaired**:

| trial | terminal | graded? | what happened |
|---|---|---|---|
| `wg-g4b` t0, t1 | `api_error` | **no** — the run holds 0 `report.json` | both aborted with a 71-character final text |
| `wg-g4c` t0 | completed | yes, 14/14 | repaired it itself: `reload(true)` |
| `wg-g4c` t1 | completed | yes, 13/14 | repaired it itself: a skip list |

Both graded trials scored `build.compiles` **True** (`just check` exit 0) and `verify.green`
**True**. `wg-g4c-capgate` re-grades those same two work trees, so it adds no submissions. **No
published tier-1 Godot figure needs marking.** What the defect cost was turns and money inside
two trials, not a score — and that is a distinction the stored record cannot make, because
nothing counts a turn spent repairing the harness.

### The under-report, which is the transferable part

The defect was first written up as *"both godot agents patched `tools/check.gd` to call
`script.reload(true)`"*. A grep for `reload(true)` across the two diffs finds it in **one**. `t1`
added a `const INSTANCED` skip list instead. Same defect, same baseline, two mechanisms — and a
search keyed to either one under-reports by half.

> **Search for the DEFECT, not for the repair somebody happened to apply.** The trigger written as
> one instance of a fix is AGENTS.md's own most-repeated failure, pointed at evidence instead of
> at rules. The reliable signals were whether the submission's `check.gd` differs from pristine at
> all, and what the agent said in `agent.final_text`.

Both agents documented it unprompted, in the paragraph rule 11 exists for and nothing reads:

- `t0`: *"The starter baseline was already red here, before I touched anything … the loop reported
  it as a COMPILE failure. I changed it to `reload(true)`"*
- `t1`: *"The baseline was already red. `tools/check.gd` called `reload()` on the `NoRaise`
  autoload, which has a live instance; that's fixed with a skip list"*

Scanning all 20 stored Godot `agent_result.json` for the vocabulary of the defect returns exactly
these two and nothing else, which is also how the blast radius was bounded.

### The obvious repair is worse than the defect, and it shipped

`t1`'s skip list makes `just check` green by no longer re-parsing the file the engine loads first.
Measured as an adversarial variant of the repaired starter: plant an unparseable function in
`tools/no_raise.gd`, and with the skip list `just check` **exits 0** while the engine prints
`Failed to instantiate an autoload`. `ResourceLoader.load` returns the cached resource, so the
`script == null` arm never fires. A gate that stopped failing is indistinguishable from a passing
submission — this project's rule 7, arriving as a fix.

The repair taken instead is `script.reload(true)` — `keep_state` — which re-parses for real.

### Why nothing caught it, and what now does

The grader runs a starter's gate **only on submissions**, where a red result is the answer it is
looking for. Nothing had ever run one on a pristine copy, so a template could ship red
indefinitely; `starter_parity.py` compares the four starters to each other and would have to see
all four go red to notice, and `verify_blind.py` asks a different question entirely.

`eval/tools/starter_gate_control.py` runs both directions on a pristine copy of all four starters
and is registered in `tools/precampaign_smoke.py` (~160s, once per campaign). It imports
`wholegame.IGNORE` rather than restating it, so the copy it measures cannot drift from the copy a
trial gets. Pinned three ways on 2026-08-23:

| input | GREEN direction | RED direction |
|---|---|---|
| repaired starter | exit 0 ✅ | planted parse error in the autoload → exit 1 ✅ |
| the original defect restored | **exit 1, tool reports FAILED** | exit 1 |
| `t1`'s skip-list repair | exit 0 | **exit 0, tool reports FAILED** |

The third row is the one that earns the second direction. A mutant — deleting the reload call —
cannot produce it; only a variant that manufactures the input the gate mishandles can (rule 15).

## 100. The stored evidence for `verify.green` drops the gate's own "passed" line on 15 of 16 Rust submissions, because stdout is truncated before stderr

`verify.green` is decided by an exit code (#98), and the exit code is right. This is about the
**record of it**. Every command tier 1 runs is stored as a `Cmd` whose `tail` is
`self.tail[-4000:]` (`judge/static.py:64`) over a buffer assembled as `bufs["out"] + bufs["err"]`
(`judge/static.py:163`) — **stdout first, stderr second, then the last 4000 characters kept.** So
when a command is chatty on stderr, its stdout is what gets thrown away, whole.

All four starters end `verify` with the same line — `@echo "✅ verify passed"`
(`starters/godot/justfile:35`, `rust/justfile:36`, `ts/justfile:38`, `unity/justfile:30`) — and
`just` sends it to stdout. Measured 2026-08-23 over the 68 stored `programmatic.json` records:

| | godot | rust | ts | unity |
|---|---|---|---|---|
| `just verify` exit 0 | 15 | 16 | 16 | 15 |
| stored tail contains `verify passed` | 13 | **1** | 16 | 15 |

**17 records are missing it, and 17 of 17 are exactly the records whose tail hit the 4000-character
cap.** Eighteen hit the cap; the eighteenth holds the token at offset 3986, i.e. the boundary is
the cap and nothing else. `cargo-nextest` writes its per-test progress and its `Summary` line to
stderr, which is why the Rust arm loses stdout in 15 of 16 and the other three arms almost never do.

The visible consequence is `verify.green`'s own evidence string, `tail[-300:]`
(`judge/static.py:384`). Read from the stored records:

- godot — `…TESTS total=8 passed=8 failed=0 skipped=0\n✅ verify passed`
- unity — `…✓ test-render: 17 passed, 0 failed, 0 skipped (of 17, 1.0s)\n✅ verify passed`
- rust — `…he_captured_frame\n────────────\n     Summary [   2.451s] 12 tests run: 12 passed, 0 skipped`
- ts — `… eslint . --cache\npnpm exec vitest run --project sim\npnpm exec vitest run --project render`

Two arms justify the criterion with the gate's own verdict; two do not, and one of those cannot,
by construction of the capture.

### Why it matters, given no score is wrong

Nothing published needs marking. What is lost is the ability to ask the question later, and the
loss is stack-correlated by a property nobody chose — how loudly a test runner writes to stderr.

The concrete case: `game-research-gpt`'s verify manifest attaches `expected_stdout_contains` to
each command (`template/config/verify/fast.json` — `ARCHITECTURE_OK`, `E2E_SCENARIO_OK`,
`REPLAY_SMOKE_OK`), on the stated principle that *"a bare exit code is not sufficient diagnostic
evidence"* (`template/docs/TESTING.md:26`). That check is the natural strengthening of #98, and
against this project's stored evidence **it would be unable to fire on the Rust arm** — not
because the Rust starter fails to print the token, but because the harness throws it away. A
guard installed on one arm and inert on another is this file's whole subject.

> **A truncation policy is a sampling policy.** `[-4000:]` over a concatenation is not "keep the
> end of the output"; it is "keep whichever stream was written second", and which stream that is
> belongs to the tool, not to the harness. Truncate each stream separately, or keep both ends.

### What not to conclude

Not that the 17 Rust and Godot submissions failed `verify`, and not that #98 has recurred: all 62
of these exited 0 and the exit code is read from the process, never from the text. And not that
the Godot 2 share the Rust cause — they are the two whose engine printed resource-leak lines at
exit, a different chatty-stderr instance of the same mechanism.
---

## 101. The TypeScript capture page never ran its own determinism script, and the defect that was filed instead was the opposite of the truth

Task 31 filed two measured one-arm defects in the TS capture harness. **One is real, one is
false, and reproducing the false one found a third that is worse than either.**

| filed | verdict, measured on the harness's exact page |
|---|---|
| D1 — `page.setContent` leaves origin `null`, so loader-based assets render nothing into any filmed PNG | **TRUE.** `location.origin` is the string `"null"`, `document.baseURI` is `about:blank`, a relative `fetch` **throws at URL parsing** (`Failed to parse URL from ./sprites/hero.png`) before any request, and `TextureLoader` reports a bare `error` with no cause |
| D2 — `performance.now` is frozen to 0, so a clock-driven `AnimationMixer` shows the bind pose in every frame | **FALSE.** `performance.now()` measured 231.6 then 293.7 ms across a 60 ms sleep. `Clock.getDelta()` returned real deltas. Nothing was frozen |

D2 is false because **`DETERMINISM_SCRIPT` never ran at all.** `addInitScript` executes on
document creation, and `harnessPage()` registered it and then called `page.setContent` — which
does not navigate. The script was registered against an `about:blank` document that was never
created afresh, so it was dead. A three-arm control settles it:

| page setup | `__determinismApplied` | `Math.random()` | `Date.now()` |
|---|---|---|---|
| (a) the harness's own order, `addInitScript` → `setContent` | **false** | 0.2508 (unseeded) | 1787465478119 |
| (b) `addInitScript` → `goto` → `setContent` | true | 0.0000078 (seeded) | 0 |
| (c) no init script registered at all | **false** | 0.8130 | 1787465478195 |

**(a) is indistinguishable from (c).** The harness whose entire purpose is reproducibility was
running with an unseeded `Math.random` and both clocks on wall time, in every TS trial, since the
capture path was written.

> **A defect report is evidence about the reporter's page, not about yours.** D2 was filed as
> "measured live through Playwright with the harness's exact page setup". It reproduces only if
> the probe navigates — and a probe that calls `goto` has, without meaning to, repaired the very
> defect it is standing on. Rule 14 with the axis rotated: a control that *sets up* differently
> tests a different machine. Re-establish the state on the real path before trusting the
> mechanism named in a report, including your own.

### The radius: zero, on all 26 stored TypeScript submissions

The part that decides whether anything published needs marking. Established four ways, and every
one of them says the same thing.

| probe | result |
|---|---|
| three loaders constructed anywhere in `src/view` (comments and string literals stripped; stripper positive-controlled) | **0 of 26**. The only two `TextureLoader` mentions in the corpus are both inside doc comments explaining why the loader is *avoided* |
| `AnimationMixer` or a three `Clock` constructed in capture-reachable view code (import graph walked from `capture.ts`) | **0 of 26** |
| entropy or wall-clock reads in capture-reachable view code — the radius of the *real* defect | **0 of 26** |
| the filmed frames themselves, measured rather than inferred | **206 of 216 TS frames are distinct**; mean adjacent-frame diff 0.0370 and non-background fraction 0.229, both second-highest of the four arms |

**No published number rests on a TS submission's frames being static or empty, because no TS
submission's frames are static or empty.** Nothing needs retracting.

The frame measurement is the one that matters, because it is the only one that reads the
consequence instead of the cause. Its one TS-specific outlier — mean distinct colours 174 against
rust 713 and godot 616 — is **not** attributable to either defect: Unity is lower still at 50, and
`research/10-stack-capability-matrix.md` §9 already attributes the colour spread to SwiftShader.
Filming on a CPU rasteriser is a standing confound on this arm and it must be ruled out before any
TS rendering difference is read as a harness defect.

### Why the radius is zero is not luck, and is the useful part

`capture()` is **synchronous** — it steps, renders and reads back inside one call — and it builds
a fresh view each time. Both properties are visible to an agent through its own render tests, and
the two agents who came nearest an asset pipeline diagnosed the constraint unprompted and designed
around it, in `agent.final_text` and in source comments that nothing reads:

- `wg-g4/g4_platformer__ts__t1`: *"the art is generated in-process rather than loaded — because
  `capture()` renders one frame synchronously with no history, so a view-side timer would have
  nothing to count and an `<img>` would still be decoding"*
- `wg-g4c/g4_platformer__ts__t0`, in `src/view/hero-sheet.ts`: *"An `<img>` or a `TextureLoader`
  resolves on a later task, so every captured frame would show an untextured quad"*

That is rule 11 twice more. **A defect whose radius is zero because every subject worked around it
is still a defect — it is a tax paid in turns, and nothing counts a turn spent designing around
the harness.**

### The repair, and why the two fixes could not be shipped separately

All three defects are one edit apart, and **fixing the origin ACTIVATES the frozen clock.** Going
to a real origin makes `addInitScript` fire, at which point `performance.now = () => 0` stops
being dead code and starts freezing time for real — introducing the filed defect D2 as a genuine
regression. Sequencing:

1. `page.route` serves a real origin from `public/`; `addInitScript` is registered **before**
   `page.goto`. One change fixes D1 and the dead script.
2. The clocks become **virtual, not frozen**: `Date.now`/`performance.now` read `__nowMs`, which
   `captureFrame` sets to `(ticks / TICK_HZ) * 1000`. A pure function of the request, so still
   deterministic, but it *advances* from one filmed frame to the next.
3. `window.__capturePreload` — optional, awaited once per capture — is where an asset-loading view
   resolves loaders into a cache that the synchronous `createView` can read. A failing preload
   throws rather than filming a frame with its assets missing (rule 7).

All three are **harness-side**, per task 25: a mechanism in the harness cannot go missing in a
stack-correlated way, whereas a rule in `AGENTS.md` that the agent must remember can.

### Both directions, pinned

`tests/render/capture-environment.test.ts` — 8 tests asking what the *page* can do, as opposed to
what the renderer drew. They run inside the real capture page via `evaluateInCapturePage`,
because **a replica page built "the same way" shares whatever assumption is wrong and agrees with
the harness** (#37). Three mutants, each restoring one repaired defect:

| mutant | result |
|---|---|
| M1 `setContent` instead of `goto` (restores D1 *and* the dead script) | **RED** on 7 tests |
| M2 `performance.now = () => 0` (restores D2 as filed) | **RED** on the clock test |
| M3 preload hook not awaited | **RED** on 2 tests |

The regression direction holds too: `just verify` is green at 53 sim + 14 render, **the golden
frame still matches**, `just film` writes its 12 PNGs, and `starter_gate_control.py --stack ts` is
green-and-still-red-on-a-plant.

One test in the first draft was **vacuous** and the mutants caught it: "the determinism script
actually ran" compared the seeded sequence against a fallback that was never set, so it stayed
green under M1. It now asserts the injected LCG's own recurrence,
`seed = (seed * 16807) % 2147483647`, which the platform generator cannot satisfy. *The mutant
sweep's value here was not finding the defect — it was finding the test that could not see it.*

### The accepted limitation, stated rather than fixed

`capture()` remains synchronous, and that is deliberate: a fresh view rendering one frame with no
history is what makes a captured frame a pure function of `(seed, ticks, inputs)`. So a loader
still cannot complete *inside* a capture — it must resolve in `__capturePreload` first. Recorded
in the TS starter's `AGENTS.md` with the reason, because it is now a documented capability with a
documented shape rather than a silent failure.

---

## 103. #100 was repaired in the file it named, and the same merged buffer is still in the runner that stores the agent's own gate

The tier-1 capture is fixed. `judge/static.Cmd.to_dict` no longer truncates a concatenation: it
stores **`stdout` and `stderr` as separate fields**, each sampled on its own budget — first 1000
characters, last 3000, the middle replaced by a marker naming the characters and lines dropped —
with `stdout_chars` / `stderr_chars` recording the full length of each, and a `note` field for the
harness's own words (a timeout, a binary that could not be spawned) so nothing the harness says is
attributed to a stream the command did not write. A timeout no longer erases what the command had
already printed. `Cmd.tail` survives in memory, byte for byte, because the test-count and coverage
parsers read it — so no criterion moved.

### The variant, run against the unfixed function first

A mutant that deletes the truncation cannot produce this defect; only an input where one stream is
arbitrarily larger than the other can (rule 15). A child writing ~10 KB to one stream and one short
line to the other, through the real `static.run`, against the code as it stood:

| variant | stored record, before the repair | after |
|---|---|---|
| 10 KB on stderr, `✅ verify passed` on stdout | **token absent** — 4000 chars kept, all of them stderr | present |
| 10 KB on stdout, one line on stderr | line present | present |

**The asymmetry is the whole defect** — the survivor is whichever stream the tool wrote second, and
that belongs to the tool. `judge/capture_selftest.py` was written before the repair and run against
it: 9 of 17 expectations held and 7 of its 9 tests could not run at all against an API that did not
exist yet. After: **39/39**, including two mutants — deleting the truncation, and reinstating the
pre-#100 merge, which loses the stdout line on demand.

### The positive control: the real gate, one execution, two renderings

`just verify` in one `wg-g4c` submission per stack, in a scratch clone, each run **once** and the
captured streams rendered under both policies — so the comparison cannot be confounded by a
rebuild:

| stack | exit | stdout chars | stderr chars | token under `[-4000:]` of `out+err` | token now |
|---|---|---|---|---|---|
| godot | 0 | 3263 | 0 | yes | yes |
| rust | 0 | **16** | **8638** | **NO** | **yes** |
| ts | 0 | 670 | 213 | yes | yes |
| unity | 0 | 201 | 0 | yes | yes |

The Rust arm's green gate writes **16 characters to stdout and 8638 to stderr** — the completion
line is the entire stdout, and the old policy discarded it whole. This control does not reproduce
the *godot* half of #100: that submission printed nothing to stderr, so the two godot misses in the
stored corpus (engine resource-leak lines at exit) are not exercised here. Four positive controls,
one of which is the arm that carried the defect; the godot failure mode is covered by the variant,
not by this table.

### The instance the finding did not name

`#100` located the defect at `judge/static.py:64` and `:163`. The same shape is still in
`eval/runner.py`, the spec-change harness: `sh()` returns `(p.stdout + p.stderr)` as one string
(`runner.py:177`), and that buffer is stored as `self_verify.tail[-4000:]` (`:592`) and
`holdout.tail[-5000:]` (`:622`). Swept over the stored `trials/*.json` on 2026-08-23:

| | records | `self_verify` exit 0 | contain `verify passed` | at the 4000 cap |
|---|---|---|---|---|
| all arms | 47 | 26 | 24 | 2 |

The two misses are exactly the two at the cap, and both are the Rust template — one on the
`rust_bevy` arm, one on `baseline`. Same mechanism, same arm, a lower rate only because the
spec-change tasks are smaller. `self_verify` is the record of *the agent's own gate*, which is the
one place a future check could ask whether the agent ran it to completion. Filed as task 50 rather
than fixed here: `sh()`'s two-tuple is read in ten places and the stored field shape has its own
reader audit to do.

> **A finding names the instance it was found at; the defect is a shape.** Repairing the file the
> finding cites leaves the mechanism wherever nobody looked. The grep that finds this class is for
> the shape — a stream concatenation followed by a slice — not for the file, and it takes one
> command: two hits in this repository, one of them repaired today.

### What this does not settle

The stored corpus cannot be backfilled — the discarded stdout was never written down — so it stays
mixed, and `static.stored_stdout()` returns **None** for a pre-repair record rather than `""`,
because a line missing from a merged buffer is not evidence the command never printed it. And the
`expected_stdout_contains` check this unblocks (`eval/IMPROVEMENTS.md` axis 2 candidate 1) is still
a separate decision: it can only ever be asked of runs graded after today.

---

## 106. Two of the four pristine starters are not format-clean, so `just verify` rewrites a file the agent never touched — and that hunk is in every stored trial diff

`eval/AGENTS.md`: *"Each trial gets a fresh template copy with a baseline commit, so
`git diff HEAD` isolates exactly what the agent did."* That sentence is the mechanism by which
authored work is separated from template code, and #77 is what happens when the separation slips.

All four starters run **`fmt`, not `fmt-check`, inside `verify`** — deliberately, and the
justfiles say why: *"a stray blank line should never be able to mask whether the real work is
done."* The consequence nobody had looked for is that `verify` is only idempotent on a tree that
is already formatted, and two of the four are not. Measured 2026-08-23 against `main`, with each
file taken out of git rather than from a working tree:

| arm | file | what the formatter changes |
|---|---|---|
| rust | `crates/game/src/main.rs` | `rustfmt --check --edition 2024` exit **1**: `fn no_raise_correction(...)` is exploded across four lines and rustfmt joins it |
| godot | `tools/no_raise.gd` | `gdformat --check` — *"1 file would be reformatted, 19 files would be left unchanged"*: one missing blank line before `func _ready` |

ts and unity were **not** checked, because both formatters need dependencies installed
(`prettier` via pnpm, `tools/fmt.mjs`). The ratio is 2 of 2 checkable, not 2 of 4 established.

### Why it is not cosmetic

The agent's first `just verify` — and the Stop hook's, which runs whether the agent asks or not —
commits a change to a file it has never opened. Three things read that diff:

* `judge/static.py`'s authored-lines accounting, which is what #77 is about;
* every human or judge reading a stored `submission.tar.gz` to see what was built;
* `just ci`, which runs `fmt-check` and is therefore **red on the pristine tree in both arms** —
  the #98 shape exactly, one arm's gate failing before any agent touches it, except that here it
  is two arms and the recipe is not the graded one.

### The rule that should have caught it, and why it did not fire

`tools/starter_gate_control.py` exists precisely to ask *"is this starter's own gate green on a
pristine copy, and can it still go red"*. It runs `just check`. Rust's `check` is `cargo check`
and Godot's is a compile pass; **neither touches formatting**, so the control was green in both
arms while the defect sat next to it.

That is rule 12 with a different address: the method was right and pointed at one recipe out of
five. The generalisation is not "also check `fmt`" — it is:

> **A gate that repairs what it inspects has to be checked for idempotence, not only for its exit
> code.** Run it twice on a pristine tree and diff. Anything it changed on the first pass is a
> change every submission will be credited with.

Repaired in both arms as part of task 26 (RUNS.md's eleventh comparability break), which is the
only reason it surfaced: `just verify` rewrote `main.rs` under a change to `Cargo.toml`, and the
hunk had nothing to do with the change. **A control for it is filed, not written.**

---

## 107. Godot's capture path cannot show presentation state that accumulates across ticks, and Bevy's can — the two arms differ in what a filmed frame is able to contain

Task 26 went looking for a way to expose Godot's particle system and found that *"can a burst
appear in a judged frame at all"* has a different answer per arm, for a reason that has nothing to
do with the engines.

| arm | what `capture_frame(seed, ticks)` does | consequence |
|---|---|---|
| **godot** | `for tick in range(ticks): Sim.step(world, ...)` — a bare loop with **no view attached** — then `_view.sync(world)` **once**, then three `process_frame`s | the view never observes ticks `1..N-1`. Anything it would have accumulated — an emitter started when an event fired, a tween, a shake, a trail — is **structurally absent** from every filmed frame and every rendering test |
| **rust** | `for tick in 0..ticks { *world.resource_mut::<Intents>() = ...; app.update(); }` — the **whole App**, view systems included, once per tick | the view sees every tick. Accumulated state is visible, and `TimeUpdateStrategy::FixedTimesteps(1)` makes the clock a pure function of the tick, so it is deterministic as well |

Both are defensible designs and neither is a bug. But they are not the same instrument, and the
difference bites exactly where the survey says the largest capability asymmetry is:
`Sim.TickEvents` in the Godot starter holds **only the current tick's** events, so an effect
triggered by an event reaches a filmed frame only if the film happens to sample the very tick the
event occurred on — 12 samples out of a run of hundreds.

**What was done about it.** Not equalising the harnesses; that is a larger change than this task
should make on the way to something else. `view/fx.gd` is built around the constraint instead: a
burst is a **pure function of simulation state**, taking an age the caller derives from a tick the
simulation still holds, so it reconstructs correctly at whatever tick is sampled. The AGENTS.md
section states it as the one rule, beside the tree-shaped version of the same trap ("everything
the player sees goes under the view") that the template already carried.

**Why it is worth a number rather than a paragraph in a template.** It is a candidate explanation
for any future cross-arm difference on effects, feedback, or "the game tells the player what just
happened" — and it would look exactly like a stack property.

> **Two harnesses can agree on every field they record and still differ in what an artifact is
> able to contain.** Before attributing a difference in what submissions DID to the stacks, check
> what the capture path in each arm makes possible.

ts and unity were not audited on this axis. The TS capture builds a **fresh view per frame**
(established in #101's wake), which is the same constraint arrived at by a third route; Unity's
`RenderHarness` was not read.
