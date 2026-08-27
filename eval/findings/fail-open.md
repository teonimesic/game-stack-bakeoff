# Guards, repairs, and the ones that failed open

Repairs that introduced new defects, and the first defects that would have
excused a genuine failure rather than inventing one.

> Index and the distilled rules: `../FINDINGS.md`


## 27. The fix for a measurement defect belongs in the thing that lied, not only in the metric

§26 established that `just film` omits the HUD on Unity (IMGUI is not part of
`camera.Render()`) and on TypeScript (a DOM node is not in the pixels of an offscreen
canvas), and that all seven `look.feedback` firings were false negatives because of it.

The obvious response — withdraw the criterion — fixes the *report*. It does not fix the
*instrument*, and the instrument is not only ours. `just film` is a template feature that
a building agent uses to look at its own work. An agent that builds a correct scoreboard,
films it, and sees no scoreboard is being lied to by its own tooling, and the cheapest
explanation available to it is "my HUD code is broken". The failure mode is an agent
deleting working code to chase a ghost, and no amount of adjusting the grading rubric
touches it.

So the repair was made in all four starters, and it is deliberately not a special case
for the two broken ones:

| stack | before | after |
|---|---|---|
| Rust / Bevy | no HUD at all | HUD drawn through the camera the capture reads |
| TypeScript / three.js | (agents reached for a `#hud` DOM node) | screen-space overlay scene composited by the one `renderFrame` both `main.ts` and `capture.ts` call |
| Unity | the starter itself demonstrated `OnGUI` | HUD rendered by the camera |
| Godot | worked by luck — agents happened to put labels under the captured node | HUD owned by the captured node by construction |

Three properties of the repair matter more than the repair:

1. **The starter demonstrates the working path.** Two of the four shipped no HUD example
   at all, and one shipped the broken idiom. An agent copies what it is shown.
2. **A rendering test asserts HUD pixels are in the captured frame.** A HUD that leaves
   the capture path now turns the gate red instead of going quiet. Each of these tests was
   validated by removing the HUD and watching the test fail before restoring it — a test
   that has only ever been seen to pass has not been shown to measure anything.
3. **`AGENTS.md` states the rule**, with the stack-specific trap named, because the trap
   is invisible from inside the idiom that triggers it.

### The general form

**A defect in an instrument that the subject also uses is two defects.** One corrupts the
measurement; the other corrupts the work being measured, and it does so *before* the
measurement, so no amount of care in the grader can recover it. When an instrument is
shared with the subject — a test harness, a preview command, a linter, a CI signal — ask
what the subject would conclude from the defective reading, not only what you would.

Here the subject would conclude that its own correct code was broken.

---


## 28. A capture that frames against a viewport which has not been realised yet

Found while fixing §27, in code nobody was looking at: the Godot starter's
`capture_frame` called `frame_arena(root.get_visible_rect().size)` **before the window
had been realised.** For the first captures of a run the root viewport still reports its
default 100x100 rect while the texture handed back is already 640x400, so the arena was
drawn as a 3x4 pixel miniature in the corner of a full-size frame. Measured in the
pixels: 12 marker-coloured pixels, bounding box x 48..50, y 48..51.

Two things make this worth recording rather than just fixing.

**It is a race, so it is invisible on a warm machine and fires on a cold one.** The
starter's own gate was red at baseline on this machine, today, with no edit to provoke
it. The 24-trial matrix scored every Godot submission 1.000, which means either the
window was realised in time on those runs or the frames it produced were graded before
anyone looked at them. Both readings are uncomfortable; neither is recoverable now.

**It would have presented as a submission defect.** A frame with a 3x4 pixel marker has
an ink coverage of about 0.00005 against a floor of 0.001, so `render.nonempty` fails —
on one stack, for a reason that has nothing to do with the submission. That is the same
shape as the Unity project lock (§25) and the HUD capture defect (§26): **a harness
assumption that holds on some stacks and fails on others, in a direction that looks like
a result.** Three of these are now known; this is the fourth.

The fix is the one the shape always implies: **establish the condition instead of
assuming it.** `capture_frame` now retries until the size it framed against agrees with
the size that came back.

### #27, continued — the fix made an already-inert criterion more inert, and that is worth saying

Every starter now draws a HUD showing the tick, so consecutive filmed frames of *any*
submission differ by construction. `render.animates` — "do consecutive frames of a played
run differ?" — can therefore no longer fail on a submission that has a working HUD, which
after this task change is all of them.

Measured before assuming: across the 24 stored submissions, `render.animates` fired
**0 times**, and so did **every other tier-1 criterion** (`judge/audit_criteria.py`, run
2026-08-14). The whole programmatic tier caught zero defects in 24 submissions. So the
HUD did not break a working discriminator; it removed the last theoretical way an inert
one could have fired.

The number worth keeping from that audit is larger than `render.animates`:

| | count |
|---|---|
| criteria that never fired in 24 submissions | 28 |
| criteria that fired ONLY wrongly | 15 |
| criteria that caught a genuine defect | **0** |

**The deterministic tiers carry 1.00 of the grade and have not caught a single real
defect.** That is not an argument for weighting them differently — they are the only
tiers that are reproducible — but it is the reason the task had to get harder rather than
the grading getting stricter. Stricter grading of work that is uniformly correct produces
false negatives, which is precisely what the 15 produced.

The six audio criteria are the first in this project that are *known* to be able to fail,
because each was built with a mutant that makes it go red before it was allowed to grade
anything.

---


## 29. Sixteen false negatives, repaired — and the repair found two latent bugs that would have made the harness fail OPEN

`audit_criteria.py` over the 24 stored submissions: **28 criteria never fired, 15 fired
only wrongly, 0 caught a genuine defect.** The 15 share one root cause — each **waits for
a condition instead of establishing one**, or samples ambient state instead of tracking
identity — so each measures incidental circumstance rather than the property it names.

Repaired 2026-08-14, each from observation to experiment:

| criterion | was | now |
|---|---|---|
| `ball.wall_bounce` | idled and hoped the ball reached a wall | both paddles chase with a deliberate vertical offset, so returns leave at an angle and the ball is *driven* into a wall; the offset is searched because paddle half-height is not in the state contract |
| `move.translates` | pushed one direction and failed if there was no room | derives the direction from the piece's own cells and the well; tries all four with clearance; returns NOT MEASURED if the piece spans the well |
| `enemies.chase` | compared distance to whichever enemy was nearest at two instants | follows one enemy by `id`, counts its disappearance as arrival, then makes the player walk away and requires the enemy to *turn* |
| `determinism.*`, `piece.stacks`, `gameover.triggers` | each opened a fresh session, which an engine holding a project lock refuses | one live session per repository, enforced across threads and processes |

**The repair is only half done when the false negatives stop.** Rewriting a criterion as
an experiment makes it easier to pass *by construction*, so eight criteria are now pinned
in both directions by `bot_mutants.py`: each passes the reference game and fails a mutant
with the behaviour removed (walls that do not reflect, a seed that is ignored, locked
cells that never settle, enemies on a fixed heading). Sixteen false negatives replaced by
criteria that can no longer fail would be a **worse** outcome and would look like success.

The lock control is itself checked for vacuity: with session serialisation removed, the
control goes red. **A control that cannot fail is not a control.**

Repairing these uncovered two defects that are not instances of this pattern and are
catalogued separately, because conflating them would bury both: **#30** — the guard added
for the project lock could never have fired — and **#31** — the first defects in this
project that would have failed *open*.

### A tier that measured nothing is not a score of zero

When every criterion comes back unscored the tier reports `usable: false`. Folding that
in as 0.0 against a 0.69 weight would deduct two thirds of the grade from a submission
that was never driven — and it can only happen on the stacks that take a project-wide
lock, which is bias, not noise.

It is **not** fixed by renormalising the way an unusable judge tier is. Tier 2 is
deliberately fail-closed: a game that cannot be driven has not demonstrated gameplay, and
renormalising would let an undriveable submission inherit tier 1's score — a far worse
failure, and the exact one this tier exists to prevent. So the score stays fail-closed and
the *condition* is made loud: `cmd_report` excludes these trials from every aggregate and
prints them for adjudication, the way it already does for a trial with a missing tier.

**Two defensible rules pointed in opposite directions here.** "Never fold an unmeasured
tier in as a zero" and "never let a submission that cannot be driven score well" are both
right, and only one can be satisfied by the number. Making the *population* visible
satisfies both, because it refuses to answer with a single number at all.

---


## 31. The first defects in this project that would have failed OPEN

Every entry in this catalogue up to now fails **closed**. A mechanism that measures
nothing reports `total=0 passed=0`. A corrupted artifact reports a wrong number. A
criterion that fires on one arm deducts from that arm. All of them are wrong, and all of
them are wrong in the direction of reporting *something* that costs a trial, a rerun, or
a retraction.

Two defects found while repairing #29 are the first that would have made the harness
**excuse a genuine failure**:

1. **A queue reused across probe start attempts.** `start()` retried on the same
   `queue.Queue`, so a stale EOF sentinel left by a refused attempt would be handed to
   the *next*, healthy session as "the probe exited". A working submission reported dead.

2. **Harness notes written into the buffer the lock-hint matcher reads.** Lock conflicts
   are now scored `NOT MEASURED` rather than FALSE — correctly, per #25. But the matcher
   scans the same stderr buffer the harness writes its own diagnostics into, and it
   matches the bare substring `lock`. **Any harness note containing the word "lock" would
   have converted a real, submission-caused failure into "not measured".** A criterion
   could have been excused by the grader's own logging.

### Why the asymmetry deserves naming

**A fail-closed defect costs you trials. A fail-open defect costs you the result.**

A fail-closed defect announces itself: a red gate, a zero, an implausible number, a stack
that mysteriously scores worse. Somebody investigates, and the catalogue above is what
investigating produced. The cost is rework.

A fail-open defect produces a **higher** score than the truth, on work that did not earn
it. Nothing looks wrong, because a passing criterion is what everyone expected. There is
no anomaly to chase, no arm that looks odd, no number out of range. It survives every
consistency check, every stability metric, and every reviewer — and it is *indistinguishable
from success at the moment you act on it*, which is the property #19 identified as the
worst one available.

Note the direction of travel. Defect 2 was introduced **by a correct fix**: scoring lock
conflicts as unmeasured rather than FALSE is right, and it is what #25 demands. Adding an
excuse path is exactly how a fail-closed system acquires a fail-open hole — every
legitimate reason to *not* count a failure is a channel that a bug can widen. So:

> **Whenever you add a reason not to count a failure, ask what else can reach that
> reason.** Here the channel was a shared buffer and a three-letter substring.

Both were found by exercising the mechanism rather than reading it, and neither would have
shown up in any aggregate. The harness now keeps harness notes in a separate buffer from
the engine's own output, and gives each start attempt its own queue.

### #31, continued — a third one, found by looking for the shape

Having named the class, I went looking for it and found a third instance within the hour.

`audit_criteria.py` carries sixteen hand adjudications keyed by `(trial_id, criterion)` —
verdicts reached by reading the failing submission's archived source. **Trial ids repeat
across runs.** `g1_pong__unity__t0` is the first Unity Pong trial of *every* run. Pointing
the tool at the new matrix would have applied the old matrix's "false_negative" verdicts
to same-named trials that share nothing but a name, silently converting this run's genuine
failures into harness defects.

It is the identical collision that once made a new matrix delete an earlier run's work
tree — the reason work trees are namespaced by run — reappearing in a different file
because only the directory layout had been fixed, not the assumption underneath it.

And it fails open in the worst available direction: it excuses failures **in the arm that
had the most of them**, since that is where the adjudications are concentrated. Unity
carried 14 of the 16. A rerun would have shown Unity's problems vanishing.

Now scoped: adjudications apply only to the run they were made against, and any other run
is told so in its first three lines and counts every failure as genuine until a human says
otherwise. Verified in both directions — the original run still reports 28 never fired /
15 fired only wrongly / 0 genuine, and the new run refuses to inherit any of it.

A fourth turned up in the next file. `discrimination.py` printed
`[all adjudicated harness defects]` next to every criterion that had ever fired, from

    adjudged = all(is_harness_failure(...) or True for r in rows if c in r["fails"])

`x or True` is `True`, so `all(...)` is `all(True)` — the label was **unconditional**. It
asserted, in the report that decides whether any criterion separates the stacks, that
every failure of every criterion was a harness defect, no matter what the evidence said.
It happened to be true of the run it was written against, which is why nobody noticed:
**a tautology and a correct answer are indistinguishable on the data that inspired both.**

Fixed and then proven falsifiable, because replacing one tautology with another that is
merely true here would have been no better: run against data the adjudications do not
cover, 12 of 15 criteria keep the label and `ball.wall_bounce` and `enemies.chase` lose
it. The label can now be false.

**The lesson is about search, not about these bugs.** Once a defect class is named, it is
worth spending an hour looking for more instances while the shape is fresh. Three of the
four fail-open defects here were found that way; none was found by a test.

---


## 36. The retry overwrote the record of the thing it was retrying, and the ledger lost the money

`RUNS.md` states its own rule: *a run's spend is the sum of `agent.cost_usd` over
`runs/<name>/trials/*.json`*. That is only true if every cell was attempted **once**.

`wg-audio48`'s eight arena cells were attempted twice — the first attempt died on an account
session limit. Measured from the two build logs, which are append-only:

| | records | spend |
|---|---|---|
| attempt 1 (all 24 cells) | 24 | $498.03 |
| — of which arena, all `api_error` | 8 | $11.76 |
| attempt 2 (arena only, 4 finished so far) | 4 | $118.63 |
| **money actually spent** | | **$616.66** |
| sum over `trials/*.json` right now | 24 | **$604.90** |

The $11.76 the first arena attempt cost is **not recoverable from the trial records**. Its eight
JSONs were overwritten in place by the retry.

### Mechanism, verified in the source rather than assumed

`cmd_build` builds its job list from `games × stacks × trials` and never looks at existing
records. `build_trial` calls `prepare()`, which begins with `rmtree`. The record is written with
`write_text` to a path derived from the trial id alone.

So the answer to the question `RUNS.md` and `PROTOCOL.md` both carried as open — *does the build
path treat an existing trial JSON as "done"?* — is **no, and the real hazard is the opposite one**:

- A retry always re-runs. Good; that is what was wanted.
- A retry whose selection includes already-completed cells **deletes their work trees and
  overwrites their records**. Re-running the full matrix to recover eight arena trials would have
  destroyed sixteen completed submissions worth $486.27. It was avoided only because the retry was
  scoped `--games g3_arena` — by judgement, not by anything in the harness.

### Two rules, and the second is the general one

**The ledger needs two numbers, not one.** The sum over records is the spend *represented by the
run's surviving results*; the sum over `[built]` lines across every build log is the money
actually spent. When they disagree, the difference is overwritten attempts, and the disagreement
is the only trace those attempts leave.

**An idempotent-looking retry is not idempotent when its output path is the artifact it is
retrying.** This catalogue's second rule is *never infer a process's state from its artifact's
state*. The sibling is: **an artifact overwritten by a retry no longer records that the first
attempt happened.** The state was not merely stale — it was erased, by the operation that was
supposed to repair it, and no error was produced because overwriting is what the code is for.

### And a ledger row for a live run is a moving number

The previously published figure for this run — *$571.15, 19 completed, 5 api_error* — was read
from disk correctly and described a state that lasted minutes: three fresh arena records had
landed, one stale `$2.00 api_error` had not yet been replaced, and four cells were still building.
It was never wrong; it was **transient**, and nothing in the row said so.

`RUNS.md` rows are now marked provisional while a run is in flight, and a run's spend is only
final once its terminal reasons are.

### It had already happened once, and the published figure for matrix #1 is low by $9.85

Having named the shape, I looked for it in the other runs — the same search that found three of
the four fail-open defects in #31. `wg-matrix-2026-08-13` has **28 `[built]` lines and 24
records**. The same four arena cells died on a session limit and were retried into the same run
directory:

| cell | attempt 1 | attempt 2 |
|---|---|---|
| `g3_arena__unity__t0` | $3.05 `api_error` | $11.23 `completed` |
| `g3_arena__unity__t1` | $3.04 `api_error` | $15.48 `completed` |
| `g3_arena__godot__t0` | $2.06 `api_error` | $17.70 `completed` |
| `g3_arena__godot__t1` | $1.69 `api_error` | $13.45 `completed` |

**Correction to a published number.** `$355.28` for matrix #1 appears in `README.md` and
`RUNS.md`. It is correct as the spend of the run's 24 surviving records and **wrong as the money
the run cost, which is $365.13.** The gap is the four overwritten attempts. Nothing was decided on
the missing $9.85, but it was the basis of the cumulative total, so every cumulative figure this
project has published is low by the same mechanism.

Two instances, in the only two runs that ever retried a cell, is not a coincidence — it is what
the code does every time. The ledger's rule was written from the runs that never retried anything.

---

---

## 44. The blinding scanner cried contamination on a clean $1,727 matrix

`verify_blind.py` exited 1 with **18 findings** across both matrices, immediately before the
evaluation that depends on it. A CONTAMINATED verdict means the run is discarded.

Every one of the 18 was the same string: `CRITERION ID audio.py`.

`audio.py` is not a criterion id. It is the **grader's own implementation file**, named in
backticks in `RUBRIC.md` — *"Implemented in `audio.py`"* — and `criterion_ids()` scrapes
backticked `word.word` tokens out of the rubric as vocabulary that must not leak. Six
filenames were in the list: `aspects.py`, `audio.py`, `checks.py`, `judge.py`, `static.py`,
`playbot.json`.

What it then matched, as a substring, in the agents' own work:

| file | why `audio.py` is in it |
|---|---|
| `tools/make_audio.py` | the agent's audio generator — the name **contains** `audio.py` |
| `justfile` | `@python3 tools/make_audio.py audio` |
| `AGENTS.md` (starter) | documents that recipe |
| `crates/game/Cargo.toml`, `tests/audio_test.gd` | reference the generator |

The canary was absent. The rubric was unreachable from every ancestor. **Not one real
criterion id had leaked.** The run was blind in fact and reported contaminated.

### Why this is worse than a nuisance

A guard that fires on clean input gets switched off, and then it protects nothing. This one
was about to be believed at the worst possible moment — the verdict was the last gate before
grading 24 submissions, and "18 findings" is exactly the shape that reads as a real problem.
The alternative failure is equally bad and quieter: a reader who dismisses 18 known-bogus hits
stops reading the list, and a genuine leak sits in it unnoticed. **Noise in a guard's output
destroys the guard either way.**

It is also the fourth appearance of one root cause: **a document that names its own
implementation gets read as data.** #38 was `RUBRIC.md` naming five judges that do not exist;
#20 was a criterion id reaching a starter through an incident write-up; #32 was an answer key
reaching a blinded judge through a mapping file. Here the rubric's own prose became the
scanner's vocabulary.

### The repair, and why it needed a control in BOTH directions

Filenames are now excluded by extension. That change makes a strict scanner more permissive,
which is the move that turns a fail-closed guard into a fail-open one (#31) — so it was pinned
before being trusted:

| control | expected | got |
|---|---|---|
| tree containing `tools/make_audio.py` and its justfile recipe | **exit 0, BLIND** | exit 0, BLIND |
| tree with a real criterion id (`invuln.window`) planted in a comment | **exit 1, named** | exit 1, `CRITERION ID invuln.window: .../notes.gd` |

Then re-run on the real trees: **exit 0, BLIND, 74 ids, 32 trial trees.**

> **When you loosen a guard to stop a false positive, plant the true positive it must still
> catch.** Otherwise "the false alarms stopped" and "it can no longer fire" are the same
> observation — the identical trap as removing an assertion that could not fail, and as the
> sixteen play-bot criteria that were rewritten into experiments and then had to be pinned by
> mutants.

---

## 47. A repair that named the right cause and ran after the measurement it was fixing

`evaluate()` calls `drop_stale_caches(submission)` — the fix for engine caches carried over
from a build being read as fresh state at grading time. The diagnosis was right and the
remedy was right.

It was called **after** `static.collect` and `probe.drive`: after every command whose result
it existed to correct.

It ran. It found the caches. It recorded `stale_caches_dropped: ["Library"]` in **all 24**
trial records. Every one of those lines is true. The four Unity cells scored exactly what they
had scored before, because nothing that read the caches ran again afterwards.

### Why it is worth its own entry

> **A repair applied after the measurement is indistinguishable in the record from one that
> did not work.** Both leave a truthful log line and an unchanged number.

The usual tell for a broken repair is that it reports failure, or reports nothing. This one
reported success, in twenty-four places, with an accurate list of what it had done. The only
way to see it was to ask *when* it ran relative to the thing it was correcting — a question no
log line answers, because a log line has an entry but no position.

Same family as #30: a guard addressed to the right failure, triggered on the right symptom,
structurally incapable of resolving it. #30's guard waited for a lock its own caller held;
this one cleaned a cache the measurement had already read. **In both, every observable
behaviour was that of a working repair.**

> **For any corrective step, state what it must run BEFORE and put that in the code, not in a
> comment.** "Drop stale caches" is a description; "drop stale caches before any command runs"
> is a specification, and only the second is checkable. The call now sits above tier 1 with
> that sentence beside it.

---

## 61. Two tasks were marked complete having guarded the path that was already safe

Tasks #14 (no focus steal) and #15 (audio off the default device) were reported done. Neither
was. Both guards landed on the **capture and test** recipes — `--audio-driver Dummy` on godot's
render tests, `-disable-audio` on unity's batchmode editor invocations — and those recipes were
already offscreen and already silent. The recipes that open a window on somebody's desk with
sound on their speakers, the `run` family, were never touched.

The result: a Unity player window appeared in the foreground of the operator's machine with
audio playing. Twice. **The second one was launched by the verification I was running to
confirm the fix.**

### It is a fail-open completion, and that is a different animal from a fail-open guard

Every other entry in this file is a mechanism that ran and reported success while measuring
nothing. This one never ran at all in the place that mattered — the *ledger* said the task was
finished. A wrong guard costs you the thing it was guarding; a wrong completion costs you the
knowledge that anything is unguarded, which is worse because nobody looks again.

Three separate errors made it, and they are worth keeping apart because they have different
fixes:

**1. The guard was written against a list of recipes, not against the resource.** The rule
should have been *anything that opens a window or an audio device*. Stated as an enumeration,
it covered the items someone had thought of. This is rule 6 in its general form and the third
time it has fired here (#30's `LOCK_HINTS`, #60's work-root spelling, now this).

**2. The exit code was read as evidence of an effect it cannot establish.** `-disable-audio` is
an EDITOR flag. The standalone player **accepts it without error and ignores it** — measured:
a player with the flag explicitly in its argv was audible, and the process was identified from
`ps` while it was making the sound. `just test-render` exiting 0 was read as "audio is off". It
only ever meant "the command ran".

> **An accepted-but-ignored flag is worse than an unsupported one.** An unsupported flag fails
> loudly. This one is indistinguishable from a working guard by every signal a script can see,
> and the only thing that separates them is observing the resource itself.

**3. The verification never touched the failing path.** I tested `just test-render` and
concluded focus-stealing "could not be reproduced on this machine" — while `just run`, which I
never executed, stole focus every time. A negative result from a probe pointed at the wrong
subject is not a negative result.

### What the repair looks like when it is done properly

| stack | mechanism | verified by |
|---|---|---|
| unity | runtime hook zeroing the AudioListener; `open -g -j` | harness log discriminates both ways; frontmost-ASN controlled both ways |
| godot | `--audio-driver Dummy`; autoload setting `WINDOW_FLAG_NO_FOCUS` | 0 audio devices; focus **prevented**, not corrected |
| rust | none exists — `just run` is refused under the harness | three escalating attempts measured to fail |
| ts | nothing to do — a dev server opens no window and no audio device | covered by construction |

The `ts` row is a **result**, not a gap: a guard there could never fire, which is #57.

The `rust` row is the honest end of an investigation rather than a fix: `Window { focused:
false }` still raises, `set_minimized(true)` hides the window and leaves the **application**
frontmost, and adding `visible = false` changes nothing — the frontmost app stayed `game` at
3s, 6s, 10s and 14s and returned only when the process was killed. **Bevy 0.19 on macOS cannot
be prevented from taking keyboard focus and cannot correct it from inside itself.** That is a
property of the engine, recorded as one.

### The instrument that made the difference

The first audio probe used `lsof` and returned the same value in both arms. **A probe that
cannot distinguish its two arms is not a weak probe, it is not a probe** — and it was run
against a live machine to produce nothing. The working one counts CoreAudio IO threads,
validated against `afplay` of a **silent** WAV (5) and `sleep` (0).

It also has a stated limit, which the `ux` and `audio` retirements needed and did not have: it
answers *"was a device opened"* and **not** *"is this silent"*. Unity's guard leaves the device
open at zero volume, so on that question it reads 5 either way. Silence is asserted from the
harness log instead.


## 105. Of 27 unread exit statuses, 24 were deliberate — and one of the three that were not was in the lint category itself, which had been reporting a clean bill of health for two of the three ways ruff can fail to run

Task 34 triaged the two rules the pinned lint set exists for: 27 `subprocess.run` calls with no
`check=` argument (an unread exit status, `AGENTS.md` rule 3) and 30 blind `except Exception`
(the fail-open shape, #31). The expectation going in was that most of the 27 were real. **They
were not.** 24 were deliberate best-effort probes whose non-zero exit is either read on the next
line or *is* the answer — `pkill` exiting 1 because it matched nothing, `just --summary` exiting
non-zero on an older `just` so the `--list` fallback fires, `cp -Rc` failing off APFS, `find`
exiting 1 on a permission-denied descent **while still listing everything it could read**, the
agent CLI exiting non-zero after writing a submission worth grading.

That is the finding, and it is not "the lint count was noise". It is that **an explicit
`check=False` and an accidental omission were indistinguishable to every reader for the entire
life of the harness**, so the 3 that mattered were sitting in a pile of 24 that did not, and no
count over the pile could ever have gone down in a way that meant anything.

### The one in the instrument: three ways for ruff not to run, one of them controlled

`prune_scan.cat_lint` was added on 2026-08-23 with a docstring that names the risk exactly —
*"a linter that is not installed must not read as a clean bill of health -- that is the
`-disable-audio` failure (#61)"* — and controls **one** of the three ways ruff can fail to run.
Measured, on the installed ruff:

| how ruff fails | exit | stdout | what `cat_lint` reported |
|---|---|---|---|
| not installed | — | — | `(ruff not installed)` — **controlled** |
| refuses the invocation (removed or unknown rule selector) | **2** | `''` | `lint (0)` — **green** |
| pointed at a path that does not exist | **0** | `'[]'` | `lint (0)` — **green** |

`json.loads(r.stdout or "[]")` turns an empty stdout into an empty findings list, and the
category prints its length. The third row is the worse one: ruff exits **zero** on a missing
path, printing only a warning to stderr, so a wrong `LINT_ROOT` would report a clean codebase
forever. That is #60's shape — a correct method pointed at the wrong place — inside the
instrument built to find that shape.

**The guard named the mechanism it had met (`shutil.which` returning None) rather than the
property it was protecting (ruff produced a verdict).** That is the rule-audit lesson in
`AGENTS.md`, one day after it was read: *write the trigger as the resource or the property,
never as an enumeration of the instances you happened to see.*

`run_ruff()` now checks the address before the command, treats any exit outside `{0, 1}` as a
refusal, and is the single entry point both `cat_lint` and the new `eval/tools/lint.py` call, so
the two cannot disagree about what was scanned.

### The one in the evidence capture: a failed `git add -A` is indistinguishable from an agent that changed nothing

`wholegame.build_trial` closes every trial with three commands whose exit codes it discarded:
`git add -A` (which is what makes untracked files appear in `diff.patch`), `tar -czf` (the
submission archive, described in the comment directly above it as *"what makes offline
re-judging actually possible"*), and `find` (for `tree.txt`).

Both failure modes are reachable — measured: `git add -A` outside a repository exits **128**,
`tar -czf` into a non-existent directory exits **1** and writes no archive. What they leave
behind is an empty `diff.patch` and a missing `submission.tar.gz`, and **every artifact stored
afterwards reads that as "the agent changed nothing"**. The comment above those lines exists
because a submission was once unrecoverable; the mechanism that was supposed to prevent it
could fail without saying so.

`check=True` would be the wrong repair — it would abandon the record of a build already paid
for, and `find` legitimately exits 1 on an unreadable subtree while listing the rest. The three
codes are now recorded in the trial record as `capture_exit_codes` and printed when any is
non-zero. **An audit trail of what the mechanism did, not the confidence that it worked.**

### And one in the judge pack: a file that could not be read was dropped and counted nowhere

`field.build_pack` wrapped its per-file copy into the judge pack in a blind `except: continue`.
A file the pack could not read was silently omitted from what a judge is shown, with nothing
recorded anywhere — an unequal amount of each submission reaching the judge, which is #62's
shape through a fourth mechanism. It is now `except OSError`, counted as `code_unreadable`, and
carried in the pack manifest beside `code`. The blind version also covered `neutralise` raising,
which would drop **every** file and still report a built pack; that now crashes.

### What the remaining blind excepts are, and why an explicit one is not the same object

16 blind `except Exception` sites are in the harness proper (14 more were in `judge/fixtures/`,
which are stand-in *submissions* and are now out of the lint scope for the same reason
`eval/starters/*/` always was — one of them is deliberately defective). Of the 16, **9 were
narrowed** to the exceptions actually expected, and **7 carry a `# noqa: BLE001` naming why the
exception set is open**: a bot is arbitrary per-game Python, a submission's frames were not
written by us, a verifier that enumerates the ways a backup can be corrupt only checks the ways
someone thought of. Every one of the 7 **records** the failure rather than swallowing it.

The nine narrowings are not cosmetic. `adjudicate._sees` caught everything and returned `"code"`,
so a renamed field on `Aspect` would have silently changed which evidence the adjudicator was
shown; `docstat`'s frontmatter check caught everything and would have reported a bug in the
sweep as *"your frontmatter is malformed"*, sending a reader to edit a file that was fine.

> **A blind `except` that is deliberate and one that is an oversight are the same three words.
> The linter can tell them apart only if you write the difference down.** That is the entire
> value of this triage, and it is why the count matters more as a *baseline* than as a total: a
> new PLW1510 or BLE001 hit is now a site nobody has considered.

---

## 109. Unity's batchmode editor runs an FMOD CoreAudio output whatever the manifest says and whatever `-disable-audio` says — so `-disable-audio`'s stated reason is not something it achieves

`tools/unity-tests.sh` puts `-disable-audio` on every invocation and gives a reason: *"an editor
that opens an audio device also contends for one."* Task 52 put `com.unity.modules.audio` into
the Unity starter, and the brief asked the obvious follow-up — Bevy's audio capability opened a
device on the capture path silently and needed a guard, so does Unity's?

The check was run **with the pristine manifest as a control**, and that is the whole reason the
answer is usable. A live batchmode editor was sampled with `sample`, counting
`FMOD::OutputCoreAudio` frames on a CoreAudio IO thread — the probe `starters/_shared/launch.just`
validated both ways against `afplay` of a silent WAV (5) and `sleep` (0):

| arm | frames |
|---|---|
| pristine manifest, **no audio module**, with `-disable-audio` | **2** |
| audio module, with `-disable-audio` | **1** |
| audio module, without `-disable-audio` | **1** |

**All three have one.** The editor's mixer is rendering into the device in the arm that has no
audio module at all — the arm believed to have nothing capable of opening one. So this was true
of every matrix already graded, and the module adds nothing.

Two conclusions, which must not be merged:

- **Task 52 introduced no new hazard on the capture path and needs no new guard.** That is the
  question that was asked, and only the control answers it: a measurement taken after the change
  alone could not separate *"the module did this"* from *"this was always true"* (AGENTS.md
  rule 14, with the pristine tree standing in for the mtime).
- **The flag does not do what the comment says.** `-disable-audio` may well silence the editor's
  output — nothing here contradicts that, and nothing was audible — but it does not stop a device
  being opened, so *"an editor that opens an audio device also contends for one"* is a rationale
  for an effect that is not in force. It is #61's shape again, on the editor this time instead of
  the player: a flag accepted without complaint, on a path where no exit code can report that
  half of it did nothing. **The flag is kept and the rationale is what was repaired**, because
  the flag is free and may still be doing the other half of its job.

The path where a human would actually hear something is the launch path, and it is guarded and
now measured for the first time. `StarterLaunchGuard` finds `AudioListener` by reflection
precisely so that it would work once an agent added the module; with no module it had always
taken the *"this project has no audio module — nothing can play"* branch. It now logs **"SILENT
LAUNCH ACTIVE — AudioListener.volume=0, pause=True"**, against a control launch without the flag
that logs *"silent launch NOT requested"*. The device is still open at zero volume, exactly as
`launch.just` says it will be.

> **A guard's comment is a claim about a mechanism, and it decays with nothing going red.**
> `-disable-audio` was right to add, has never been wrong in its effect, and acquired a reason
> nobody could check. When the reason is the only thing carrying the claim, the reason is the
> thing that has to be measured.

## 125. The guard was stated as a resource and implemented as a layout, so reusing it would have broken two readers

Task 30 established the right rule: **any durable record of what a measurement was configured to
be is append-only.** That is resource-shaped — it names the property, not the file — and it was
written that way deliberately, because #57 named *prompts* and #77 named *judge packs* and
neither trigger reached `suite.json` sitting eleven lines away.

Task 63 then found two more records with the same shape and applied that guard. **Applying it
verbatim would have been a defect wearing the shape of a fix.**

`write_manifest` pins the canonical name to the **first** record written. That is correct for
`runs/<run>/suite.json`, where the directory is named for one launch and a later launch is the
intruder. It is wrong for a destination that is *re-synced*, and it breaks two documented readers:

- `eval/PROTOCOL.md` tells a reader to take the evidence count from `MEASURED.json`. Pinned to
  the first sync ever, it returns a stale number **and nothing disagrees with it.**
- `judge_ledger.explain_gap` looks for carried-over rounds at the **head** of the mtime order,
  because the counter belongs to the last invocation. Against a first-invocation counter the gap
  becomes the **suffix**, so every resumed sweep returns `UNEXPLAINED` and exits 1.

> **A rule stated as a resource can still be implemented as a layout, and the implementation is
> what gets reused.** The next person applies the guard, not the sentence — so if the guard
> encodes one arrangement, the sentence's generality is decorative.

Repaired by carrying **both** shapes in `tools/manifest.py`, pinned and rolling, with the
criterion written between them: *does the directory have an identity the record is named for?*
Four call sites, each reverted to its pre-repair line in turn, each turning the suite red on the
expectation that names it.

The ticket named two records; the two writers hold **six**, all with the overwrite shape.
`MANIFEST.sha256` is arguably the most valuable of them — it is the only per-file record of what
a copy held, and #116's stale prefix was a file that *changed* at the destination under a
correctly green SHA-256 check.

**What is unmeasurable, and stated rather than estimated:** whether either record has actually
lost anything historically. The pre-repair writers left no trace of what they replaced, which is
the defect itself, so the loss is unbounded below and unmeasurable above.

## 138. The one entry point the module docstring tells a human to type built a completely unblinded pack, because it read half the object — and every test called the function underneath it

Found by aiming the finished repair for #137 at a real run instead of at its fixture.

`field.py pack --aspect architecture` is the command `field.py`'s own docstring gives a reader who
wants a pack. It constructed one with `build_pack(..., sees=aspect.sees)` and **never passed
`blind_language`**, so the argument fell to its default of `False`. The aspect knew it was blind;
the CLI asked it one of the two questions.

### Both directions, one variable, on a real field

`wg-g4c/g4_platformer`, aspect `architecture`, eight submissions, the same command run against a
copy of the module with that one keyword removed and against the shipped one:

| | pre-repair | repaired |
|---|---|---|
| files on disk | 208 | 208 |
| evidence files keeping their real suffix | **199 of 207** | 0 |
| filenames naming an arm (`field.BLIND_EXT`) | **191** | **0** |
| arm-naming extension tokens in content | **667** | **11** |

The 199 are `.gd` 50, `.cs` 50, `.ts` 43, `.rs` 43, `.py` 5, `.json` 3, `.mjs` 3, `.shader` 2 —
every one of them `.src` after the repair. The 207 denominator is the evidence: 199 code files
plus 8 `CHANGED.txt`. The 208th file on disk is the packer's own
`.claude/skills/sampling-code/SKILL.md`, which carries no extension token in either arm; **state
which denominator a ratio uses, because both are defensible and they differ.**

All **11** residual tokens are `import.meta` — the construct #137 declines deliberately — and
naming them is the difference between "0 by the pattern I chose" and "0 paths, 11 known
non-paths". Two consecutive builds of the pre-repair pack gave 667 both times, so the figure is
the packer's and not a sampling artifact.

The task-87 ticket recorded **663** for the same quantity. Under the pattern stated here — the
`field.BLIND_EXT` alternation with a `(?![A-Za-z0-9_])` tail, every file in the pack — it is 667,
and the earlier pattern was not recorded. The gap is 4 and unresolved; the split that carries the
argument (345 in `CHANGED.txt` against 322 in code) is unaffected either way.

### Why nothing noticed, which is the whole finding

`field_sweep.py` passes **both** properties at all **three** of its call sites, and every stored
judge round was packed through `field_sweep.py`. **No stored round is affected.** That is not a
mitigation — it is the mechanism: the defect sat on the only path with no output anyone checks,
so it could not go red, and it had been there for as long as the CLI had.

And every test called `build_pack` **directly**, where `blind_language` is written out in the
call. A test that constructs the arguments itself cannot discover a caller that constructs them
wrongly. The suite was green on the property and blind to the path.

> **When an object gains a property, grep for every reader of its siblings.** `Aspect.sees` had
> readers; `blind_language` was added beside it and the reader list was never re-derived. One
> call site holding half an object is invisible to every test that calls the function rather than
> the command.

This is rule 13 with the resource being *the blinding* and the unverified path being *the one the
documentation recommends* — #61's shape, where the guarded path was the one already safe.
`blind_ext_selftest.py` check 7 now drives `field.py pack` **as a subprocess**, for `architecture`
(must be 16/16 neutral names and 0 tokens) and for `idiomatic` (must be 0 neutral names and >0
tokens, so the check cannot pass by blinding everything).
## #189 — the agreement test's slack grew with the speed it was testing, until it covered the window

`ParallaxScene._reliable` kept a layer when 80% of its per-pair shift-to-offset ratios sat within
`max(abs(median) * 0.15, 0.15)` of the median. The second term is a **floor in ratio units**, and
what it is compared against is a ratio whose denominator is the layer's own reported offset. So the
slack scaled with how fast the layer said it was moving.

On the first stored scene's road band that floor is `0.15` against a median ratio of `0.053` —
**2.8x the median**, or **±60 to ±81 px inside a ±89 px search window**. Every answer the estimator
could physically return agreed with every other one. The layer was called readable on 8 of 8 pairs
while its usable shifts ran **-73px to +3px**, and that promotion is what let `layers.image_parallax`
establish itself on 3 bands and score the submission FALSE.

**A guard whose tolerance is a function of the value being guarded has no failing input.** That is
the fail-open shape with an extra step: nothing here excused a failure, it made failure
unreachable. The repair moves the comparison into **pixels** — the unit the estimator answers in
and the unit its error is bounded in — leaving the proportional term arithmetically unchanged.

**And the second defect, which no slack value could have fixed.** A band that moves half its own
repeat length or more between two captures draws a picture recoverable only modulo that span, so it
**agrees with itself perfectly**: the `near layer repeats exactly twice between captures` variant
reads 0px on 11 of 11 pairs at confidence 0.83-0.92. Tightening the tolerance makes such a band
*more* readable, not less. It is now refused as a **precondition**, before agreement is asked at all
(`NYQUIST_SHARE = 0.5`, the sampling limit rather than a tuned constant).

**Both constants are derived, and the evidence that they were not fitted is in the source.**
`K_PIXEL_FLOOR = 1.5` follows from `best_shift` answering in whole pixels: over 6 fixtures, 24
layer rows and 264 pairs the worst pure-rounding residual is 0.78px, and exactly 1.00px on the
constant-speed variant. It sits **60x below the 94px the road band would have needed to survive** —
which is the point of quoting it. The submission that exposed the defect still fails.
`eval/SCENES.md` records the decision that an aliased band is UNREADABLE rather than wrong, and
that the 12-frame capture does not move, because `span` is the submission's choice and no capture
rate is safe from it.

**Still open, and visible only because the filter stopped lying:** the estimator locks onto one
whole-frame feature rather than each band. At frame pair 4 all five lower bands answer -9px; at
pairs 1, 3, 5 and 10 four of them answer -46, -19, -66 and +8. Three bands now fail on
**confidence** rather than on aliasing, which is a different instrument defect and has its own
ticket.

---
## #190 — the repair a false-negative ticket suggests is fail-open, and this is the second time

`fire.rate_limited` asks whether there is a minimum interval between **shots** and counted **bullet
ids**. On the `ref_arena` spread fixture it read `90 bullets from 120 ticks of held fire (30 fire
events)` and returned `passed=False` — the right number printed beside a verdict computed from the
wrong one, failing a weapon that is correctly rate-limited and fires three bullets per shot.

**`tasks/160` told the agent how to fix it, and the instruction was wrong.** *"Count fire events
rather than bullet ids"* is fail-open taken literally: the verdict fails on a **high** count, so
whichever signal reads lower always excuses. The agent measured it instead of complying, and built
the mutant that proves it — `ref_arena` with `FIRE_INTERVAL` removed **and** `fire` emitted only on
the rising edge reads `120 shooting ticks out of 120 (1 carried a fire event, 120 put a new bullet
id in the world)`. An event-only criterion would have certified a gun with **no interval at all**
as rate-limited, on 1 shot in 120 ticks.

The shipped repair counts shooting ticks by both signals and takes the **maximum**, so neither can
excuse alone. The union was the other candidate and was rejected on a case rather than on taste: a
game whose spawn reaches the snapshot one tick late has two disjoint sets, so a legal 60-shot weapon
would read 120. `max` does not double-count.

> **A criterion that fails on a HIGH count must take the maximum of its candidate signals; one that
> fails on a LOW count must take the minimum. Picking the "better" signal is picking the one that
> excuses.**

**The part that generalises past this criterion is where the bad instruction came from.** It was
written by the orchestrator, and it is the second prescribed repair here to be fail-open —
`tasks/157` was the first, telling an agent to carry pong's *press nothing after the end* across to
`ref_arena`, where with the player dead nothing moves the score (#186). Two for two is not chance,
it is the situation:

> **A repair gets prescribed when the ticket is about a FALSE NEGATIVE — a check failing something
> correct — and the repair that comes to mind while looking at a wrongly-red check is, by
> construction, one that makes it pass.**

A wrong *cause* in a ticket is self-correcting: the agent measures, disagrees, and costs an hour. A
wrong *repair* gets implemented, and if it weakens a check nothing disagrees — the suite goes green
precisely because the check stopped being able to fail. `.agents/skills/dispatch/SKILL.md` had a
rule against stating unmeasured causes, listing the `tasks/157` case by name, and it did not fire,
because a repair is not a cause. It now asks for the **falsifier instead of the mechanism**: say
what must still FAIL after the repair. `tasks/160` should have said *"a weapon with no interval at
all must still fail"* — one clause, naming no mechanism, and it kills the repair the ticket
actually suggested.

---
## #195 — the baseline was 459 ticks from the event it was attributed to

`multiplier.falls` asks whether taking damage drops the multiplier back. It compared the **peak the
killing phase reached** against the value on the `player_hit` tick — and on `ref_arena` those two
readings are **459 idle ticks apart**: 188 ticks to raise the multiplier, then 459 more before the
first hit lands.

So the criterion attributed to *damage* any decline that happened anywhere in that gap. A game with
**no damage link at all** passed it, because a combo timer lowered the multiplier somewhere inside
those 459 ticks. The baseline is now the value on the tick **before** the damage, which makes the
repair a widening in time (the damage tick and the 8 after it) and a **tightening** in what is
compared.

> **A criterion that names two events and reads a value at each has a third thing it never states:
> the interval between them. Everything that happens in that interval is silently attributed to the
> second event.** The gap here was not a bug anyone introduced — it is how long a competent bot
> takes to get hit.

**Its evidence string was byte-identical to a correct submission's**, which is why no amount of
reading stored records finds it: the criterion printed a real drop and a real hit, and the sentence
does not contain the thing that was wrong. That is #83's shape again — the record was kept and
recorded something true and useless.

**`NO_MULT_FALL` could never have found it.** A mutant removes the mechanism the check names; this
defect needs an input the check **mishandles** — a correct-shaped game whose multiplier falls for
the wrong reason. Rule 15, and the fourth instance now.

**On the ordering question this ticket was told to answer for `tasks/166`:** `multiplier.falls`'
windows **are** truncated by end-detection, unlike `158`'s and `160`'s, which were fixed tick
counts. It does not re-open the ordering — both loops break on the **state flag alone**, never on a
`game_over` event, so adding the event branch could only make them exit earlier on a game whose
verdict is a fail either way. **That is a measured answer to a question the orchestrator had guessed
the other way**, and the guess was recorded as a guess.

The remaining hazard is left **open and bounded rather than closed**: a correct game carrying both a
combo timer and a damage collapse, whose timer lapses inside the window. The span it could land in
was 459 ticks; it is now 9.

---
## #196 - four pixels of 256,000 passed "did the frames contain anything"

`ink_coverage` counts pixels differing from a reference colour, and `analyse_frames` took that
reference from **frame 0's mode** and applied it to all twelve frames. #191 established that this
makes `mean_ink` departure-from-a-palette rather than a measure of what was drawn, and removed the
ceiling. It left the reference alone. The reference was the other half.

**The case that closes it**, measured on the pre-change code before anything was changed: 12 frames
where frame 0 is uniform black and the other 11 are uniform white carrying a single **2x2 speck** -
**4 pixels of 256,000 drawn** - read `mean_ink = 0.91665` and **PASSED**. Under each frame's own
background it reads `0.00001` and fails.

**Both halves of the criterion admitted it**, which is why the #191 repair did not catch this: a
frame carrying a speck is not flat, so `flat_frames` saw 1 of 12 and had nothing to say. Two
independent-looking guards, one blind spot, because both were reading the same wrong reference.

**The corroborating measurement is rule 12's signature.** 14 of 804 stored frames read *exactly*
`1.00000` under frame 0's mode, in 3 sets - `wg-matrix` `g3_arena__rust__t0` flashes its arena red at
frame 5,
and its last 7 frames saturate while drawing the same 4% of the frame they had drawn all along. Under
a per-frame reference: **0 of 804**. A value pinned at the top of its range across a population is
the instrument, not the subject.

> **The objection to the repair applied equally to the thing being defended, and that is what
> settled it.** The ticket worried that a per-frame mode moves when a subject grows past half the
> frame. True - and equally true of frame 0's mode, which is the same computation on one arbitrary
> frame. **A fixed reference does not avoid the error; it freezes one frame's version of it and
> applies it to eleven frames it was never measured on.** When an objection to a change is also an
> objection to the status quo, it is not an argument for the status quo.

Two practices from the repair worth copying. The now-redundant all-flat half was **kept** - it is
the fail-closed direction and still reports *how many* frames were blank - and its dead mutant was
replaced by an implication row rather than deleted quietly, so the redundancy is recorded instead of
hidden. And the control's advance values were **re-derived** rather than re-recorded when the
reference moved.

This is a **regime break** (`eval/RUNS.md`, twenty-fifth) and not a withdrawal: the stored `mean_ink`
values remain true of their records, computed under the rule in force when they were written, which
is #194's distinction. `WR-ink-arrangement-0-91667` retires the one figure that was never a property
of any render.

---
## #200 - the same evidence string read PASS under one verdict and FAIL under the other

`rally.counts` asks whether the rally counter rises on **each** paddle hit. Its verdict was
`rose_on_hit > 0`, which answers *"on at least one of them"*. A `ref_pong` whose counter takes only
the left paddle's returns **PASSED**, and the evidence it printed was
`rally rose on 3 of 6 paddle_hit ticks`.

> **The criterion printed the number that condemns the game beside a verdict that cleared it.** The
> measurement was right the whole time; only the comparison was wrong. Reverting the repair
> reproduces it exactly - *"expected FAIL rally rose on 3 of 6 paddle_hit ticks, got PASS rally rose
> on 3 of 6 paddle_hit ticks"*. Byte-identical evidence, opposite verdict.

That is the third instance of this shape in one week - `fire.rate_limited` printed the right bullet
count beside a verdict computed from the wrong one (#190), and `multiplier.falls` printed a real drop
and a real hit while attributing 459 ticks of decay to the wrong cause (#195). **A stored evidence
string is not a check on the verdict beside it, and reading one to audit the other is reading the
same half twice.**

`paddle.deflects` - computed in the **same loop over the same hits** - was already all-or-nothing. So
the defect was visible from ten lines away, in a file where the correct form sat adjacent, for as
long as the criterion has existed.

**The one-tick question was decided from the contract, and its two precedents point opposite ways.**
`tasks/159` declined a one-tick reading for this very criterion; `tasks/170` repaired one for
`multiplier.falls` a day later (#195). Neither is a house rule to inherit. g1 **defines** rally as the
number of consecutive paddle hits since the last point - a count of the very events the trace line
carries - so a skipped hit makes a line publish a rally its own event history contradicts. That is
159's case, and it is the contract that says so rather than the precedent.

**The floor was argued at one countable hit, not six.** A reviewer proposed requiring 6 hits; that
fails a correct game for a short rally, which is #46's shape, and it was declined with the
measurement. `countable > 0` is required so that excluding a hit tick which also carries the point
cannot swallow the criterion whole (rule 7).

**What could not be established, and is recorded rather than guessed:** whether any stored grading
would flip. All 50 stored evidence strings read `rally counter incremented on paddle hits (6 hits
seen)`, and `grep -rl "rally rose on" eval/runs/` returns 0 files - `rose_on_hit` was never recorded,
so only re-driving those submissions could answer it. Logged as a comparability break.

A smaller trap from the same work, worth carrying: **a mutant that degenerates into an existing
mutant's shape pins nothing.** The literal *"moves once and stops"* mutant reads `0 of 33` and is red
under *both* verdicts, because `_rally` shares its session with the wall-bounce drive. Only the
evidence string revealed that the mutant was not testing what its name claimed.

---
