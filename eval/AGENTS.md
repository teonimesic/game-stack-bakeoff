# eval/ — the measurement harness

Two harnesses share this directory:

| File | Runs |
|---|---|
| `wholegame.py` | The whole-game matrix — "build 3D Tetris" tasks, graded by `judge/`. **The only harness that can still launch anything** |
| `runner.py` | The spec-change suite. **Retired 2026-08-23**: the four `template*/` trees it copied are deleted, so `run` and `check-suite` exit 2 with the reason. `report` and `regrade.py` still read its 71 stored trials, and `judge/static.py` still imports its capture policy — which is why the file stays whole (`DECISIONS.md`, #122) |

The grading machine needs **`ffmpeg` and `ffprobe`** as well as the four stacks' toolchains —
the audio criteria decode every clip rather than trusting its extension.

`FINDINGS.md` is the findings log. `BAKEOFF.md` and `FINE-TUNING-BRIEF.md` document the retired
spec-change suite's design — history now, but the history 71 stored trials are read against.
Stored results live in `runs/<name>/`, one directory per run — that is data, not guidance.

**The producer for that 71, and for every count of the tree, is `python3 tools/census.py`.**
It is `71 over 12 run directories, 153.82 tokval`. Do not reach for a glob instead:
`runs/archive-run1-byte-identical-prompts/` is a **wrapper holding four run directories**, so a
`runs/*/trials/*.json` pattern misses 24 records and reports 47 — which is what the tool itself
did until 2026-08-23, agreeing to the digit with a `RUNS.md` figure produced the same wrong way
(#127). Search at any depth or use the producer.

> **A run directory is not always a child of `runs/`, and there is more than one wrapper.**
> Naming the archive alone is the enumeration failure this file's own meta-lesson describes:
> `runs/wg-g4c-capgate/` wraps `capped/` and `uncapped/`, and it holds no `trials/` at all, so
> the second wrapper is invisible to any check keyed on the first one's shape. The three tree
> walkers are now depth-independent and each prints what it skipped — `tools/census.py`,
> `tools/manifest.py audit` (19 run directories before, **23** after, no verdict changed) and
> `judge/tier1_census.py` (68 submissions before and after, over **84** gradings on disk).
> Any new walker over `runs/` gets the same treatment and a fixture with a nested run in it.

**`suites/*.toml`, `suites/prompts.py`, `holdout*/` and `variants/` are evidence, not a live
suite.** They are the ONLY record of what the 71 spec-change trials were asked to do and graded
on: the trial JSON stores `task: "t1_rally"` and no prompt (#122). Nothing launches from them and
nothing should be deleted from them.

**`starters/*/` is the product, not instructions to you.** It is what a building agent reads during
a trial. Any edit changes the thing being measured, must not happen mid-run, and requires
re-running `judge/verify_blind.py`. `judge/starter_parity.py` checks the four stay comparable.

**Run `judge/starter_parity.py` where the four toolchains are installed.** Its test axis is now
three-valued — a real count, `UNMEASURABLE`, or an explicit `--skip-tests` non-measurement — and
`UNMEASURABLE` fails the tool, because `0/0` printed as a test count for a stack whose runner
could not start and the gate still reported no drift (#108). An agent worktree has no
`node_modules`: that is untracked and lives only in the checkout it was installed in, so the TS
arm cannot run its tests there. `judge/parity_selftest.py` pins both directions and must stay
green.

**A near-miss AGENTS.md heading — one in every guide but one — is a QUESTION, not a finding, and
it is answered once in `starter_parity.ADJUDICATED_HEADINGS`.** The four guides are stack-native
by decision, so the same guidance legitimately appears under a different heading or inside
another section; both rows the axis produced when it was first wired to a report were that, not
forgotten copies (task 67). An adjudication records the *sentence* that carries the guidance and
the tool re-reads it out of all four guides every run, so an entry that stops being true goes red
rather than quiet. Unadjudicated rows stay notes: a heading rename must not turn a gate red.

**A HOOK WIRED IN EVERY STARTER MUST BE NAMED IN EVERY GUIDE, and that is a failure, not a
note.** The heading axis above cannot reach this shape in either dimension: it needs a *heading*,
and it needs *n-1 of n*. The Stop hook was a **sentence** in **one guide of four** while
`.claude/settings.json` wired it in all four, so three arms ran under a gate that refuses to let
the turn end while `just verify` is red and their guides never said so (task 78).
`starter_parity.mechanism_findings` keys on the wired event read out of `settings.json`, never on
the word "Stop", so the next hook is covered by the row that caught this one. Wording stays
stack-native; silence is what fails. An event wired on some stacks only is a stack choice and is
reported, never failed.

**WHAT THE STOP GATE DID IS NOW AN ARTIFACT, and its address is `runs/<run>/artifacts/<trial>/
hook_log.tsv`.** A Stop hook that exits 0 leaves no trace in the transcript or anywhere else, so
"no block" could never tell a green gate from a gate that never ran, and every trial before
2026-08-23 is permanently in that state (task 84, the eighteenth comparability break in
`RUNS.md`). Each hook now appends `invoked` plus one of `pass` / `block` / `skip` / `no_project_dir`,
and `wholegame.py` summarises it into `trials/<trial>.json` under **`stop_hook`**.

Three things about reading it:

- **`log: "absent"` is a third value.** It is not `invocations: 0` and it is certainly not "the
  gate passed" — it means the hook never ran, or the CLI never passed the variable, or the trial
  predates this. Anything testing for truthiness collapses the one distinction the log exists to
  make.
- **`skip` names the guard that fired.** Every hook short-circuits on a warm guard (`target/`,
  `node_modules/`, `Library/`, `just` on `PATH`), and a short-circuit was indistinguishable from a
  pass in every artifact the project stored.
- **The log MUST stay outside the trial tree**, which becomes the graded diff (#106).
  `wholegame.hook_log_path` refuses to launch if the address is inside it, and every trial record
  carries `stop_hook.leaked_into_tree` measured against `tree.txt` and `diff.stat` after the fact.

`tools/hook_audit_control.py` pins all of it offline in both directions — green, blocked and cold
arms with distinct logs, a mutant with the logging deleted, and variants for append-not-truncate
and for the unset-variable fallback. `--live` adds the one row a shim cannot fake: that the CLI
really hands `$STARTER_HOOK_LOG` to a hook it spawns (~0.05 tokval).

## Checking a run

**`python3 tools/runstat.py`** — the only correct status check. Do not hand-roll one at a
shell prompt; every ad-hoc version written here has been wrong at least once, and a wrong
status reading looks exactly like a right one. `--run-dir` targets a specific run,
`--watch N` re-reports every N seconds. See `PROTOCOL.md` for what it avoids and why.

**Arm a 30-minute heartbeat whenever a run is building**, calling `runstat.py` rather
than reimplementing it, reporting the tool's own non-zero exit loudly, and emitting every
tick so silence means "checked, nothing moved" instead of "monitor is dead". Re-arm it
when the run directory changes. Full recipe and rationale in `PROTOCOL.md`.

## Resource use per call

> **THE UNIT, and it is not money.** Every `$n` and every `*_usd` field in this directory is
> **`tokval`**: the list price the tokens a call used would carry at published API rates, which
> the CLI computes as `sum(modelUsage[*].costUSD)` from the token counts whatever the billing
> arrangement. This account is a subscription, so **nothing here is an expenditure** (FINDINGS
> #159). The token counts are real and every comparison built on them stands; the unit and the
> noun were what was wrong, and a research decision was once declined on one.
> `python3 tools/tokenvalue.py --definition` prints this, and every producer prints it beside
> its own output.

**Anything that consumes account capacity per call**, whatever runs it — an agent trial, a judge
field call, a calibration probe. Trials are ~$11-73 each; judge field calls are $2.82-$8.08.

**Nothing is bounded by a token valuation.** Builds are bounded by `--max-turns 1000`, which the
agent cannot see; judge sweeps by `--max-rounds` and `--max-wall-min`. A ceiling denominated in a
unit that does not bind cannot protect what is scarce, and it truncates real evidence when it
fires (`DECISIONS.md`, #159).

**Whether cost SEPARATES the stacks is a different question from what anything cost, and its
producer is `python3 tools/cost_census.py`.** It groups the stored trials by `(run directory,
game)`, computes each group's within-cell noise floor and its between-stack range, and prints
`r(cost, turns)` beside them. **Never quote a between-stack cost figure without its floor, and
never quote one group's floor as the floor** — a floor is a property of a population, not of the
cells you happened to sample. #63 measured a one-cell floor estimate wrong by **7.2x**; over all
7 stored groups the tool's `worst one-cell floor error` line reads **33.0x**, so #63's number was
the mild case. It compares gaps only **inside** a group, because gap sizes are bound to a
budget-cap regime (#33) and a cross-group ratio would be arithmetic on incomparable dollars. The
tool exits 2 on a missing tree rather than reporting 0, so run it against the main checkout.

**Whether one stack is systematically cheapest is a third question, and `--ordering` is its
producer** — an exact permutation of the stack labels *within a cluster*. Above its
enumeration limit it **refuses rather than sampling**, because every p here is read against
alpha and a sampled p needs a confidence bound before it can be compared with a threshold.
**A fifth stack or a fifth run crosses that limit**, and both are recorded re-open
conditions: widening the corpus means implementing the bound, not raising the limit. **Read the
`smallest p this design could return` line before reading the p.** At the honest unit — a
connected component of run *and* game, because the games recur — the stored tree's floor is
**0.25**, so the question is unasked there rather than answered. `DECISIONS.md` holds the
adjudication.

- **Report the measured token valuation and get authorisation before launching anything at
  scale.**
- **Prefer offline re-grading to any re-run.** `judge/regrade_wholegame.py` and `regrade.py`
  recompute scores from stored tier files.
- **Never extrapolate a projection across a boundary you have not measured across.** Not from
  the cheapest case, not from a pooled mean, and **not from one game to another** — the games
  differ, and so does the cost of judging them.

  This rule existed, was read, and did not fire on 2026-08-16. It was written under a heading
  about *agent trials* and in their vocabulary, so a **judge field call** — same resource,
  different mechanism — was projected from three `g1_pong` calls (mean $4.39) onto
  `g2_tetris3d`, where the first call measured **$8.08, 1.84x**. A `--max-runs 6` sweep projected
  at $131 was really $256, past the ceiling it was authorised under.

  That is this file's own meta-lesson biting: **a rule whose trigger is written as the
  instance that produced it must be re-derived by every reader who meets a different
  instance.** The trigger is now the RESOURCE — account capacity consumed per call — not the
  mechanism.

- **What ONE INVOCATION generated and what a FIELD is worth are 2 questions, and neither is
  an amount owed.** A round already on disk contributes 0 to the invocation that reuses it, so the
  invocation counter cannot double-count work already done. That counter is
  `charged_to_ceiling_usd`; the field's own figure is `field_cost_usd`, summed from the rounds
  themselves. `python3 judge/judge_ledger.py --tree runs/` reports both per directory and is
  the producer for every judge figure in `RUNS.md`. **Never quote a summary file's counter as
  the field's figure** — stored under one name, it put $21.05 into 3 live documents for 10
  calls worth $31.66, and **5 of 11** stored sweeps carry the same shape (#121).

- **A budget flag is visible to the callee, so it is an instruction, not just a ceiling**
  (#33). `--per-call-budget` is still passed to the judge as `--max-budget-usd 12.0`, and it is
  held there **only** so new rounds stay comparable with the 97 on disk. It bounds nothing in
  `field_sweep.py` any more — `--max-rounds` and `--max-wall-min` do, and both are written into
  the sweep summary beside `stopped_by`. Changing what the judge is told is a regime boundary
  and needs a pre-registration, not a relabelling.

## Running trials

- Drive the **`claude` CLI directly**, not the SDK.
- `--setting-sources project` is **mandatory** and empirically verified. Without it the operator's
  global `~/.claude/CLAUDE.md` leaks into every arm and confounds the comparison.
- The matrix runs with a targeted Bash allowlist (`just`, `cargo`, `pnpm`, `git`). Runs with and
  without it are **not comparable** — without one, ~30% of turns are lost to denials, including
  agents blocked from running their own verify gate.
- Cost and tokens come from `modelUsage`, not `usage` — `usage` covers the main loop only and
  excludes subagents.
- Each trial gets a fresh template copy with a baseline commit, so `git diff HEAD` isolates exactly
  what the agent did.

## What a trial record holds of the commands it ran

`sh()` returns an **`Sh`**, not a string: the exit code and **both streams, kept apart**.

- **`Sh.text` is what gets PARSED** — stdout then stderr, or the harness's note alone on a
  timeout, byte for byte the merged buffer `parse_test_counts`, `parse_skipped` and every
  diagnostic print were handed before #114. Nothing about the stored shape can move a score.
- **`Sh.record(**extra)` is what gets STORED** — `self_verify` and `holdout` in every
  `trials/*.json`. Each stream is sampled on its **own** budget (`STREAM_HEAD_CHARS` head,
  `STREAM_TAIL_CHARS` tail, the elided middle counted in the marker), each stream's full length
  is recorded as `stdout_chars` / `stderr_chars`, and the harness's own words go in `note` —
  never into a stream the command did not write.

It used to be one `tail` field: `self_verify` kept the last 4000 characters of `stdout + stderr`
and `holdout` the last 5000. **A truncation policy is a sampling policy**, and that one sampled
whichever stream the toolchain happened to write second. Over the 46 stored green `self_verify`
records, the 2 with no trace of the recipe's own `✅ verify passed` are exactly the 2 that hit the
cap, and both are the Rust template, because `cargo-nextest` fills stderr (#100, #114).
**Raising a cap is not a fix for that class of defect** — it moves the boundary and leaves the
rule that stdout is sacrificed first, still stack-correlated.

**The policy is defined once, here in `runner.py`, and `judge/static.py` imports it.** Both
harnesses store command output; giving them two similar policies is how #100 came back.
`runner_capture_selftest.py` pins both directions and asserts there is still only one copy;
`--submission STACK=PATH` is its positive control and runs the real `just verify`.

Reading the stored corpus: **`stored_stdout()` returns `None` for a pre-repair record**, because
a line missing from a merged buffer is not evidence the command never printed it — those records
are unmeasurable, not empty, and they cannot be repaired because the discarded stdout was never
written down. `stored_output()` reads either shape. Every sweep over `runs/**/trials/*.json` must
partition on which shape it is reading.

## Controls

Every task needs all three. A negative control alone is not enough — a task whose tests can never
pass looks identical to one that is correctly failing.

| Control | Proves |
|---|---|
| **Negative** | The held-out tests fail on the pristine starter |
| **Positive** (gold patch) | A correct implementation makes them pass — *the grader can go green* |
| **Adversarial** | A plausible-looking fake does **not** pass |

This is a rule about graders, not about one harness. `runner.py check-suite` was the negative
control for the retired spec-change suite and no longer has a tree to run against; every live
grader owns its own three, listed in `judge/AGENTS.md`.

## Concurrency and artifacts

- **One writer per artifact path, always.** Concurrent writers once produced a file that parsed
  cleanly while holding two spliced documents, and its in-range values were published as fact.
  Write atomically — temp file plus `os.replace`.

- **Any durable record of what a measurement was CONFIGURED to be, or of what it MEASURED, is
  append-only.** A second launch adds a record; it never replaces one. The resource, not a list
  of files: suite manifests, prompt snapshots, blinding mappings, control floors, regime notes,
  judge-sweep summaries, backup verification records. `cmd_build` guarded the prompt snapshot
  (#57) and overwrote `suite.json` eleven lines below it, so five stored run directories
  describe a launch that is not the one they are named for, and `wg-arena3d`'s manifest hides a
  two-wave build that #49 had to reconstruct by hand (#93, #120).

  **`tools/manifest.py` is the single writer, and it holds two shapes. Which one you want is
  decided by whether the directory has an identity the record is named for.**

  | | canonical name holds | writer | used by |
  |---|---|---|---|
  | **pinned** | the FIRST record; a re-launch goes to `<stem>-<stamp>` | `write_manifest()` | `runs/<run>/suite.json` — the directory is named for one launch, and a later one must not take the name |
  | **rolling** | the LATEST record; the one it replaces is kept as `<stem>-<stamp>` | `write_rolling_json()`, `write_rolling()` | judge-sweep `GATES/SEQUENTIAL/REPRODUCIBILITY.json`, and `MANIFEST.sha256`/`DEST_ONLY.txt`/`MEASURED.json` at the evidence destination — these directories accumulate and their record states the position as of the last invocation |

  Both reserve the sibling name atomically (`O_EXCL`, or `os.link` for the rolling one), so
  nothing can lose the race with itself. **Pinning where rolling belongs is not a safe default:**
  `PROTOCOL.md` tells a reader to take the evidence count from `MEASURED.json`, and pinning that
  name to the first sync would protect every record and hand the documented reader a stale
  number. `judge_ledger.read_counter` reads the canonical summary for the same reason — pin it
  and every resumed sweep comes back `UNEXPLAINED`.

  **`python3 tools/manifest.py audit` sweeps `runs/` offline** and asks two things of every
  manifest: does it describe the reports beside it, and does it belong to the directory it
  sits in. Neither question alone finds all five. Run it after any partial re-run.

  **The two questions are independent, and a manifest that cannot be asked one is still asked
  the other.** Until 2026-08-23 the code returned as soon as question 1 was unaskable, so all
  12 spec-change directories — every pre-wholegame manifest in the corpus, the four that task
  75 had just added included — printed `skip` without question 2 ever running. Placement now
  has three channels (`run_dir`, `started_at`, `suite`) and **every one a manifest's fields
  support runs**; the `skip` line names which of them acted, because *asked and clean* and
  *never asked* had been printing the same word. Result over the 12: placed and correct on
  all 12, corroborated by an independent channel that shares none of the same assumptions
  (`eval/tools/manifest.py`, task 85).

  Directory names are operator-chosen and this project has stamped them in **both** local time
  and UTC, so never compare a `started_at` against one by eye — that is how a 1-second delta
  was published as a defect (#120).
- **Judge calls compete with trials for account session capacity.** Run trials first, judge after.
  A concurrent judge fan-out during a matrix contributed to four trials dying on a session limit.
- **Give every judge invocation an explicit long timeout.** The default tool-call limit is shorter
  than a judge pass, and a killed pass looks like a silent crash because piped output never flushes.
- **Archive work trees, don't rely on patches.** A patch can fail to apply; an archive cannot.
  Verify an archive by opening it and counting entries, not by trusting the exit code.
- Trial ids repeat across runs and `prepare()` starts with `rmtree` — **namespace work trees by
  run**, or launching a new matrix will delete an earlier run's submissions.

## Reading results

- **Partition by `terminal_reason` before computing anything.** `completed`, `max_turns`,
  `budget_exhausted`, `api_error` and session-limit aborts are different populations. `runner.py`
  records it for exactly this reason. `python3 tools/census.py` does that partition over the
  whole stored tree offline, and is the producer for any count of it a document quotes — it also
  separates the whole-game records from the retired suite's, which share the `trials/*.json`
  glob and must never be pooled. It **exits 2 on a missing or empty tree** rather than reporting
  `0`, so run it against the main checkout: an agent worktree has no `eval/runs/`.
- Report `n` per group alongside any aggregate.
- Score per task first, then take the SE across tasks. Pooling across trials is inconsistent.
- Use paired per-task differences for arm comparisons, and Wilson intervals for pass rates.

**Reading the agent's own closing message — there is now a reader.** `wholegame.py report`
prints each trial's located passages beside its score, and
`python3 tools/disclosure.py --run-dir runs/<run>` gives them without waiting for evaluation;
`--trial <id>` prints one message whole. It is a **locator, not a classifier** — `quiet` means
no cue matched, not that a trial disclosed nothing — and it has three values, because a message
that was never written is not a message that said nothing. `tools/disclosure_mutants.py`
carries ten mutants and must stay green; six of them are caught only by a real stored message,
so run it in the main checkout.

**It reports TWO families and they must never be pooled.** *Unverified own work* is **25 of
the 75** messages an agent actually wrote, against a hand-classified **31** (`RUNS.md`).
*Starter arrived broken* is **15 of 75** against a hand-classified **18** (the module's own
docstring, which also names the 3 it misses and why). Both under-report; quote the hand figure
for a rate. Until 2026-08-23 the two shared one counter, so a row located only by the starter
family sat inside the number compared against a hand pass that never covered it — reported as
26, comparable number 25. **A locator that answers two questions needs two denominators**, and
the pooled figure was quoted in three documents.

**The address, and what is not one.** Four documents tell you to read this field before grading
(`PROTOCOL.md`, `DECISIONS.md`, root `AGENTS.md` rule 11, `G4-PLATFORMER.md`) and none said
where it is. It is in **two** places, in two shapes:

| where | what |
|---|---|
| `runs/*/artifacts/<trial>/agent_result.json` → **`.result`** | the whole message, untruncated |
| `runs/*/trials/<trial>.json` → **`agent.final_text`** | the **last** 3000 characters of it (`wholegame.py`); the retired `runner.py` kept the last **1500** |

A truncation policy is a sampling policy: **43 of the 90 stored whole-game messages exceed 3000
characters**, so `final_text` is a partial read of nearly half the corpus. It samples the tail,
which happens to be where a closing caveat usually sits — that is luck, not design, and the
luck has already run out once: `wg-arena3d`'s `g3_arena__rust__t1` states #49's whole mechanism
at character 0 of 3912, where `final_text` cannot see it. Read `.result` for any census; use
`final_text` only when the tail is what you want.

**`.result` is not always something the agent wrote.** On a session- or quota-limited trial it
holds the API's own error string — `"You've hit your weekly limit · resets …"`, 71 characters —
which anything that merely checks for non-empty will count as a closing report. **9 of 90**
stored trials are that shape and **6** more are `null`. Partition on it: a message that was
never written is not a message that said nothing.

**This suite resolves large gaps only.** With 2 trials per cell, stacks landing within ~0.015
cannot be separated — and the spec-change suite already failed to separate four stacks that all
scored 6/6. If the results do not separate, say so; do not present an ordering that is noise.

## Reading a stored submission: two traps, both measured

**A `submission.tar.gz` contains AppleDouble sidecars.** Alongside `./project.godot` sits
`./._project.godot` — a 3-line macOS metadata stub carrying none of the file's content. It
satisfies `name.endswith("project.godot")`, so a census written as

```python
next(n for n in tf.getnames() if n.endswith("project.godot"))     # WRONG
```

reads the stub and reports the file as clean. On 2026-08-23 that returned **"0 of 20 godot
submissions carry the defect"** against a true answer of 4, and the wrong answer was uniform
across every row, which is what made it look like a finding rather than a bug — rule 9's shape.
Filter on the basename:

```python
[n for n in tf.getnames()
 if n.endswith("project.godot") and not posixpath.basename(n).startswith("._")]
```

`anonymise.py` already filters these; nothing else did.

**Do not use `tar --wildcards` on this machine.** macOS ships bsdtar, which does not accept it.
The same census wrapped the failure as `grep -c ... || true` and every row became `0` — the
fallback `AGENTS.md` rule 3 forbids by name, producing a plausible in-range number from a
command that never ran. Let it fail, or use Python's `tarfile`.

> Both errors gave the *same* wrong answer for *every* submission. A census that returns one
> value across a population it was meant to discriminate is reporting the instrument, not the
> population — check the extraction before believing the result.
