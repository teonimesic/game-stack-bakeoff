# Run protocol

How to launch, watch and stop a matrix. **These are instructions, not notes.** Follow them; do not
re-derive them from a conversation.

Every rule here was written after the failure it prevents. The cost of each is recorded so nobody
relaxes one on the grounds that it looks paranoid.

## Before launching

**Run `python3 tools/precampaign_smoke.py` first.** It exercises every command that is run
once per campaign — `plan` for each game, `prompt_guard --snapshot`, `starter_parity`,
`starter_gate_control`, `verify_blind`, `audio_selftest`, `capture_selftest`,
`runner_capture_selftest`, `parity_selftest`, `sequential_selftest`, `docstat --sweep` —
**unpiped, reading each exit
code**, and it exists because two of them were
silently broken:

- `plan` had crashed with a `TypeError` since the no-cap regime made `MAX_BUDGET_USD` `None`.
  It is the one command this file tells you to run before authorising a matrix, and it is run
  once per campaign, so nobody found out (#56).
- `starter_parity` had been exiting 1 on a condition `DECISIONS.md` formally accepts, making it
  permanently red and therefore unread (#57).

**Run it from a checkout whose toolchains are installed**, not from an agent worktree.
`starter_parity` now goes RED when a stack's `just test` cannot run at all, because `0/0` used to
print as a test count and read as agreement (#108); `node_modules` is untracked, so in a worktree
the TS arm genuinely cannot run its tests. If you mean to skip that axis, pass `--skip-tests` —
it stays green and puts the non-measurement in the report.

> **A command run once per campaign can be broken by an unrelated change and stay broken for
> months. The interval between the break and the next use is the whole exposure.** A green row
> means the gate is ALIVE, never that it PASSED.

Then run every check below. Each has cost trials at least once.

| Check | Why | Cost of skipping |
|---|---|---|
| **Probe session capacity.** Make a real call and confirm it succeeds. | A session limit mid-run kills trials that were fine. | 4 trials in matrix #1, 1 calibration, the entire first arena set |
| **Verify the cap in the live driver's process list**, not in a config file. | `--max-budget-usd` is read at import; editing a file changes nothing for a running process. | one full relaunch |
| **A running driver holds the PROMPTS it imported, not the ones on disk.** Check a live trial's own `artifacts/<tid>/prompt.txt`. | Same mechanism as the cap. Verified 2026-08-15: the arena prompt was rewritten mid-run and a trial launched 67 minutes later still received the superseded text — which is what makes the archive boundary clean, and would silently split a run into two task definitions if it were not noticed. | would have mixed two specs in one run |
| **Run `verify_blind.py` unpiped** and read its own exit code. | A piped exit status is `tail`'s. | reported BLIND when it was not |
| **Run `audio_selftest.py` and `bot_mutants`** and read both exit codes. | A criterion that cannot fail is worse than absent. | 15 criteria across 3 matrices |
| **Confirm starters are untouched since the last blind check.** | Editing a starter changes the thing being measured. | the `determinism.replay` leak |
| **Snapshot rendered prompts** — `python3 tools/prompt_guard.py --snapshot runs/<run>/prompts` | What the agents actually received, for diffing later. A shared `_preamble()` changes every game at once. | one experiment nearly run with two variables (#41) |
| **Establish the MACHINE is healthy, per stack, and read the exit codes unpiped.** `syspolicyd` CPU-vs-elapsed, load average, and — the two that matter — **compile and exec a trivial NEW binary in each toolchain**, and run `just verify` in each of the four starters — `starter_gate_control.py`, which `precampaign_smoke.py` already runs, now does that part for you and additionally fails if `verify` **rewrote** the pristine tree (#106). | A daemon pegged for ten days gated `execve` of freshly created binaries. Rust and TS link new binaries every build; Unity and Godot run pre-existing ones, so it is invisible on half the arms and looks like a stack difference on the other half. | **half of `wg-arena3d`** — two arms shipped work that had never been compiled or run (#49) |
| **Sweep for orphaned engine processes**, including `runs/_control/` and any tree no reaper covers. **Check each hit's cwd and ancestry before believing it is yours** — a `jq` that had been running 17 minutes looked like a hung trial and belonged to a different project on the same machine. | A Godot process orphaned to launchd ran 2d 21h through two matrices. | wall-clock validity of two runs |

## Concurrency for engine stacks

**Run a godot/unity-heavy selection at `--parallel 2`, not 4.**

Measured 2026-08-15: an arena-only retry put all four heavy-stack trials in flight at once —
which `BUILD_CAP` (godot 2, unity 2, overall 4) permits and which a single-game selection
saturates in a way a mixed 24-trial schedule rarely does for long. **All four wedged; all four
headless trials in the same selection finished.** No mechanism was established, so saturation
is a hypothesis and not a diagnosis.

The decision does not rest on the hypothesis being right, and that is the point:

- if it is wrong, `--parallel 2` costs wall clock and nothing else;
- if it is right and the run goes at 4, roughly half the set is lost at ~$30 a trial plus
  hours, on the last piece of a four-figure measurement.

**Buying validity with wall clock is the correct trade when the thing being bought is the
measurement itself.** Treat a recurrence at parallelism 2 as *data*: it would rule the
saturation explanation out rather than merely surviving it, which is more than the current
evidence can do.

## Before terminating any wedged trial, capture

In this order, and all of it, because the previous occurrence left none of it:

1. the agent's **last transcript entry** — specifically whether the last `tool_use` had a
   result written after it;
2. `pgrep -P <agent-pid>` — the **child list**;
3. a machine-wide **engine scan by process name** (`ps -Ao comm=`), not by argv;
4. `ps -o pid,time,etime` twice, so the frozen-CPU reading has two samples.

Then kill. The evidence is unrecoverable afterwards, and a wedge with no captured state is
an incident that teaches nothing.

## Choosing a budget cap

**`--max-budget-usd` is visible to the agent. `--max-turns` is not.** Verified three ways
(7.31 → `EXACT=7.31`; 41.77 → `EXACT=41.77`; absent → `NONE`).

Consequences:

- A cap is an **instruction**, and there is no neutral value. "You have $48" instructs as surely as
  "You have $25". Only *absent* carries none.
- **Spend responds to it**: Tetris cost $23.20 at $25 and $35.66 at $48 — 1.54×. See FINDINGS #33.
- Therefore **a cap change is a task change**, and runs under different caps are not poolable.
- At ~$0.13/turn the invisible `--max-turns 250` already bounds a trial near $33–40, so a visible
  cap above that buys little and instructs anyway.

Do not test a cap effect on the cheapest game. Pong costs ~$21 whether the ceiling is $25 or $48 —
it has no headroom, so it cannot show the effect *whatever the truth is*. **A null measured on a
saturated instrument is not a null.**

### The two limits interact — set them together

`--max-turns` and `--max-budget-usd` are both ceilings, and **whichever binds first is the one that
governs the run.** They must be set as a pair, not independently.

> ### MEASURED 2026-08-15 — the table below is superseded by one real datum.
>
> `g3_arena__rust__t0`, uncapped, `--max-turns 1000`: **$72.83 over 369 turns = $0.1974 per
> turn**, half as much again as the $0.13 assumed below. At the measured rate:
>
> | turn limit | cost equivalent at $0.1974/turn |
> |---|---|
> | 250 | ~$49 |
> | 500 | ~$99 |
> | **1000** | **~$197** |
>
> So `--max-turns 1000` is a **~$197** backstop, not the ~$130 claimed when it was chosen. It is
> still a backstop rather than a ceiling — the most expensive trial ever measured is $72.83 —
> but the headroom is smaller than it looked, and a stack more expensive than rust could get
> closer to it than expected.
>
> **One datum, one stack, one game.** The other three stacks have no uncapped measurement at
> all, and rust is the cell with the most headroom, so $72.83 may be the expensive end rather
> than the middle. Re-read this table against the full set when it lands.
>
> ### The original table, UNVERIFIED, kept because a deleted table is one somebody re-derives.
>
> It converts turns to dollars at ~$0.13 per turn, where "turns" means the `num_turns` field in
> the trial record. **The data contradicts that conversion.** Under the same `--max-turns 250`,
> `g2_tetris3d__godot__t0` **completed at 265 turns** while `g3_arena__rust__t1` was **cut off at
> 251** (FINDINGS #35). A trial finished normally with *more* turns than the limit, so `num_turns`
> is not the counter the flag applies to, and every figure below inherits the discrepancy —
> including the ~$130 that justifies `--max-turns 1000`.
>
> Kept rather than deleted because the *shape* of the argument still holds — two ceilings,
> whichever binds first governs, only one visible to the agent — and because a deleted table is
> one somebody re-derives. **The no-cap calibration trial measures the real number. Replace these
> figures with it.**

At a nominal **~$0.13/turn**:

| turn limit | cost equivalent | binds first against a $48 cap |
|---|---|---|
| 250 | ~$33 | turns |
| 370 | ~$48 | either — they meet here |
| 500 | ~$65 | **budget** |
| 1000 | ~$130 | **budget, by a wide margin** |

This matters because the two are not equivalent in kind: **the budget cap is visible to the agent
and instructs it; the turn limit is invisible and merely truncates.**

So raising the turn limit alone does not make turns the binding constraint — it hands the binding
role back to the visible flag, and the 1.54× spend response returns with it.

## Standing configuration: `--max-turns 1000`, no budget cap

**Do not pass `--max-budget-usd`.** The only limit is the turn count, which is invisible to the
agent and therefore instructs nothing.

Rationale: any stated budget is an instruction, and spend responds to it — 1.54× on a task with
headroom. A large cap is still an instruction; only an absent one is neutral. 1000 turns is four
times the limit that was actually observed to bind, and the most expensive trial ever measured is
$46.40 — but **what it bounds in dollars is not known**, because the turns-to-dollars conversion
is unverified (see the warning above).

Do not raise the turn limit and leave a low budget cap in place expecting turns to govern. That
combination governs by the visible flag while looking as though it governs by the invisible one.

**Cost under this configuration is genuinely unknown.** Every measurement so far was taken with a
budget instruction in force; removing it is a fourth regime and the first with no budget
communicated at all. Whether agents work to completion at ~$25 or expand toward the turn limit has
not been measured. **Calibrate with one trial before committing a matrix**, and report the measured
figure rather than extrapolating from a capped run — those numbers are measurements of their caps.

Record which limit bound each trial. `max_turns` and `budget_exhausted` are different populations
and both are different from `completed`.

## While it runs

- **Never infer the run's state from an artifact read taken earlier.** Re-read before reporting.
  A "0/24" report was stale by 16 trials and $498.
- **A one-shot liveness check confirms a spawn, not a run.** Check again later.
- **Nothing that consumes account session capacity may run during the build phase.** Not the
  judge, not `field_sweep.py`, not a subagent, not a "quick" side task in another window. A
  concurrent fan-out starved four trials into a limit.
  **The rule names the RESOURCE, not the mechanism, and that rewrite was needed:** it used to say
  "judge or LLM calls", and on 2026-08-15 the useful thing to spawn during a build was a
  *subagent* — which is neither of those words and is the same resource. A rule whose trigger
  lists mechanisms has to be re-derived by every reader who meets a new one (#30's shape, applied
  to prose).
- **Do not run engine work during the build phase.** Renders contend and produce flaky captures,
  and load contaminates wall clock in build order.
- Report cumulative spend every ~$100.

## When something stops

**Diagnose before restarting.** A restart that clears a symptom without the cause has already lost
trials three times.

Specifically check, in this order:

1. Is the driver blocked, or finished? A driver at 0% CPU with no children may have nothing left to
   launch rather than being stuck.
2. **`cmd_build` does not consult existing trial records at all** — verified in the source
   2026-08-15. It builds the job list from `games × stacks × trials` and `build_trial` calls
   `prepare()`, which starts with `rmtree`. So a retry always re-runs, and **the hazard is the
   opposite of the one to worry about: re-running a selection that includes already-completed
   trials destroys their work trees and overwrites their records.** Scope every retry to the
   failed cells (`--games g3_arena`), never re-run the whole matrix to recover part of it. See
   FINDINGS #36.
3. Did a trial die without writing a record?
4. Is it a session limit that blocked *before* a record was written? The `session_limit` split only
   fires when a record is written.

## Checking a run: use the script, not a shell prompt

```
cd eval && python3 tools/runstat.py                  # newest run
             python3 tools/runstat.py --run-dir runs/X
             python3 tools/runstat.py --watch 300    # re-report every N seconds
```

**Do not hand-roll a status check.** Every ad-hoc one written in this project has been
wrong at least once, and each wrong answer looked like a real reading. `runstat.py` is
the single correct implementation and its docstring lists the seven traps it avoids.

It reports, in one pass: per-trial cost/turns/wall/terminal read from `agent.cost_usd`;
aggregates **partitioned by terminal reason**; the real driver and its children with CPU
and descendant counts; work-tree writes in the last 10 minutes via `-mmin`; and engine
processes matched by **process name**, flagged for ancestry.

Its control, run 2026-08-15 against a live matrix: naive `pgrep -f "wholegame.py"`
returned **2** matches — one `/bin/zsh` monitor and one real driver. `find_drivers()`
returned **1**. That single filter is the defect behind four wrong diagnoses in one day.

**Arm a 30-minute heartbeat for the duration of any run**, and have it call the script
rather than reimplementing it:

```
Monitor, persistent, every 1800s:
  OUT=$(python3 tools/runstat.py 2>&1); RC=$?
  if [ $RC -ne 0 ]; then echo "RUNSTAT FAILED rc=$RC"; echo "$OUT" | tail -5
  else echo "$OUT" | grep -E "^===|^  [a-zA-Z_]+ +n=|^  driver|^    child|^  work trees"
  fi
```

Three properties that matter, each of which a hand-written heartbeat got wrong here:

- **It must report the tool's own failure loudly.** A monitor that swallows a non-zero
  exit prints an empty summary, and an empty summary reads as "nothing to report" — the
  same shape as the thing being watched for.
- **It must emit on every tick, not only on change.** A quiet heartbeat should mean
  "checked, nothing moved", which is different from a dead monitor, and the two are
  indistinguishable if silence is the normal case.
- **Match aggregate lines by SHAPE, not by an enumeration of terminal reasons.** The
  first version of this recipe listed
  `completed|max_turns|budget_exhausted|session_limit|api_error|None` and silently
  dropped `harness_timeout` the first time one occurred — an entire population invisible
  in every heartbeat, while the monitor looked healthy. `^  [a-zA-Z_]+ +n=` matches any
  of them, including reasons not invented yet.
- **It must not duplicate `runstat.py`'s logic.** Four earlier heartbeats reimplemented
  the checks and three carried a defect the script already fixed. A monitor that
  contradicts the mandated tool is worse than no monitor.

Retarget or re-arm it when the run directory changes. A heartbeat pointed at a finished
run reports a frozen number forever and looks healthy doing it.

Two readings it deliberately does not simplify:

- **Frozen CPU is only half a wedge.** An agent waiting on a running tool consumes no
  CPU and is perfectly healthy. The script prints descendant counts and flags a child
  with *zero* descendants — that plus frozen CPU across two samples is the signature.
- **Engine processes are listed, never judged.** A `Unity.app` on this machine may be
  the operator's editor. Check ancestry against the driver before assuming it is ours.

## Non-signals — readings that look like evidence and are not

Each of these produced a confident wrong diagnosis in this project. They are listed as
commands and readings rather than principles because a rule you have to remember is a rule
that will fail: the `-newermt` trap below was diagnosed, written down in a message, and
walked into again within hours by the same agent.

**`find -newermt '-70 minutes'` silently matches nothing on macOS.** BSD `find` does not
accept a relative time string there, and it reports no error — it returns zero files.
**Use `-mmin -70`.** Verified: on four trial trees that were actively being written,
`-newermt` returned 0 and `-mmin` returned 18, 12, 7 and 10 files.

> **A check returning zero because it is broken is indistinguishable from one returning
> zero because nothing happened.** Before concluding "nothing is happening", run the check
> against something you know IS happening and confirm it reports non-zero. A negative
> result from an unvalidated probe is not a measurement.

**`find /tmp/... -mmin -5` silently matches nothing, because `/tmp` is a symlink.**
On macOS `/tmp` -> `/private/tmp`, and `find` does not follow a symlink given as its
starting point. Verified 2026-08-15: a file created one second earlier was not matched
via `/tmp`, and was matched via `/private/tmp`. This is the `-newermt` trap wearing a
different hat — **a check that returns zero because it is broken.** Use the real path,
and always run the positive control: touch a file in the tree you are about to check
and confirm the check reports it.

**`%cpu` in `ps` is a snapshot, and ~0% is normal for a healthy agent.** An agent waiting
on an API response consumes no CPU. A driver waiting in `subprocess.run` consumes none
either. **0.0% CPU is not evidence of a stall.**

**`pgrep -f` matches the agent's own prompt, so it matches almost everything.** Every
trial's command line contains the entire task description, and the task names its
engine. `pgrep -fl "Unity|godot|Starter.app"` therefore matches four `claude -p`
processes that are not running any engine at all. The same trap in the other direction:
`pgrep -f "wholegame.py"` matches the monitoring shell that has `wholegame.py` in its
own loop text.

> **On this workload argv matching is nearly useless.** Match on the process NAME —
> `pgrep -x`, or `ps -Ao comm=` — when the question is "is this program running", and
> keep `-f` for when you genuinely need to distinguish two invocations of the same
> binary. A name match and an argv match answer different questions.

Two independent routes agreeing is only worth something when they are independent: the
2026-08-15 engine sweep was believed because a `comm=` scan and an inspection of each
agent's children both said "no engine anywhere", and those two do not share a failure
mode. The argv scan agreed with neither and was simply wrong.

**`pgrep -c` does not exist on macOS — and the failure looks like a zero.** BSD `pgrep`
accepts `[-Lfilnoqvx]`; there is no `-c`. `pgrep -cf claude` is a usage error: it exits
non-zero, writes usage to *stderr*, and prints nothing to stdout. Wrapped as
`pgrep -cf ... || echo 0` it reports **0 agents while four are running**. Diagnosed
2026-08-15 after it produced two wrong reports; `pgrep -l claude` listed all four the
whole time.

> **BANNED: `pgrep -c` anywhere in this project, and `cmd || echo 0` as a fallback on any
> counting command.** The fallback converts an error into a plausible measurement — the
> most dangerous shape a broken check can take, because the number is in range.

**Enforced, not merely documented.** `.claude/settings.json` at the repo root denies
`pgrep -c`, `pgrep -cf` and `pgrep -fc`. A written rule is advisory — this one was
written down and then violated by its own author within the hour, which is why it needed
a mechanism. Same reasoning as the Stop hook: an instruction is a request, a deny rule is
not.

⚠️ **The deny rule is written but UNVERIFIED.** Settings load at session start, so it
could not be tested in the session that created it — `pgrep -cf claude` still executed.
The first session to attempt a banned command is the test. **If it is not denied there,
the pattern syntax is wrong and must be fixed, not trusted.** Do not treat this guard as
working until something has been observed to bounce off it.

Count with `wc -l` on the pid list instead, and let a failure be visible:

```
pgrep -f claude | wc -l          # agents by pattern
pgrep -P "$DRIVER_PID" | wc -l   # children of the driver — the ground truth
```

Long argv is *not* the problem — these agents carry a 7,000-character prompt and
`pgrep -f` matches them fine.

**Two bad signals corroborate each other.** The stall diagnosis above was believed because
0.0% CPU and "no files written" agreed — and both were artifacts. Agreement between two
readings is only evidence if each is independently sound; two broken instruments agree
more often than two working ones.

### What to do instead, in order

1. `pgrep -P <driver-pid>` — list the driver's actual children. Necessary, not
   sufficient: it shows the `claude` processes, **not what they are running.**
2. **`ps -Ao pid,ppid,etime,command | grep -Ei 'unity|godot|cargo|node|gdformat'` — the
   DESCENDANTS.** This is the check that actually settles it, and it was missing from
   this list until 2026-08-15. Four agents with no file writes for 30 minutes and 0%
   CPU looked stalled; the descendant list showed a `unity-compile.sh` 12 minutes in
   and a `gdformat` 5 minutes in. **An agent blocked on a long build writes nothing and
   burns no CPU, and is indistinguishable from a dead one by every check above.**
3. `find <tree> -type f -mmin -5` on each live trial's work tree — **and validate it by
   touching a file in that same tree first.** A long compile produces no new files for
   many minutes, so a zero here is weak evidence at best.
4. **Transcript age per trial — the check that actually diagnoses a wedged agent.** Each
   trial appends to `~/.claude/projects/<mangled-work-tree-path>/*.jsonl` on every turn.
   No append for an hour while the process is alive is the strongest available evidence
   that the agent is stuck rather than thinking.

   ```
   python3 -c "import glob,os,time; now=time.time(); \
   [print(d.split('--')[-1], int((now-max(os.path.getmtime(f) for f in \
   glob.glob(d+'/*.jsonl')))/60), 'min since last turn') \
   for d in glob.glob(os.path.expanduser('~/.claude/projects/*<run-name>*'))]"
   ```

   **Compare epoch seconds, never formatted times.** Sorting `%H:%M:%S` strings picked a
   file from the previous evening as "newest" because `23:12` sorts above `12:38`.
5. **The elapsed-to-CPU ratio — the cleanest single signal, and it needs no baseline.**
   `ps -o pid,time,etime`. A wedged agent shows **2h10m elapsed against 5.13s of CPU**;
   a healthy one that is merely waiting on the API still accumulates CPU as it parses
   responses and runs tools. Unlike transcript age this needs no second reading and no
   comparison trial, so it is the first thing to look at.

   Sampling `ps -o time` twice five minutes apart is the confirmation: byte-identical
   means the process did nothing at all in between. **`%cpu` cannot substitute** — it is
   an instantaneous snapshot and reads ~0 for a healthy agent too.
6. **A process that ignores `SIGTERM` is itself evidence.** Both wedged agents had to be
   `SIGKILL`ed; a process handling its own shutdown path would have gone on TERM.
   Corroboration, not a first check — but free, since you are killing it anyway.
7. A capacity probe: one `claude -p "Reply READY."` on haiku. Distinguishes a session
   limit from everything else for a fraction of a cent.

**Always run all of these against a trial you know is LIVE as well as the suspect one.** On
2026-08-15 two of four arena agents were wedged and two were working; the same six checks
separated them cleanly, and the live pair is what proved the checks could still say "yes".

Only after all of these point the same way is a restart justified. **A restart that clears
the symptom without the cause is how this run has already lost trials three times.**

## Stopping a run

`pkill -f wholegame.py` stops the driver but **not** the trial agents — they keep building and
writing results. Kill both, then verify zero of each, then sweep for engine orphans.

## After a run: copy the evidence out, before reclaiming anything

Two things live here and they have opposite needs.

**The product** — templates, harness, docs, findings, tasks, skills — is in git and pushed to
`github.com/teonimesic/game-stack-bakeoff` (private). Committing is cheap. **Commit and push
after any batch of work lands**, not at the end of a session that may not have one.

**The evidence** is `eval/runs/`, it is gitignored, and it is the part that cannot be rebuilt: a
matrix costs ~$420 and several days, and the judge rounds cannot be reproduced at all because the
model and the harness have both moved since they ran.

### What is evidence and what is build output — the rule

> **A file under `eval/runs/` is evidence until something in the tree itself proves it can be
> regenerated. The proof must name a producer that declared the file its own output.**

Stated as a rule, deliberately, and not as a list of directories: an enumeration misses the next
stack, the next cache and the next harness, and it fails in the direction that loses evidence
silently. This one fails closed — an unproven file gets copied.

Two proofs are discharged, both of them the producer's own declaration, read out of the tree:

| proof | what it covers |
|---|---|
| `CACHEDIR.TAG` at a directory root, signature checked | cargo target dirs. The Cache Directory Tagging Spec — the tool that filled the directory saying a backup may skip it |
| the work tree's own `.gitignore` | `node_modules`, `/Library/`, `/target`, `.godot/`, `.venv/`. Each template ships the file naming what its toolchain regenerates, so a fifth stack updates the classifier for free |

`python3 tools/evidence_set.py` applies it and prints what it dropped and why.
`tools/evidence_set_control.py` adjudicates its `.gitignore` matcher against **real git** on the
real trees plus a synthetic fixture, and carries four mutants. Three of the four were **inert
against real data** — no shipped `.gitignore` uses anchoring, directory-only matching or a
negation — so the synthetic fixture is what makes the suite mean anything. Run the mutants after
touching the matcher; a green suite with an inert mutant is the "passes and measures nothing"
shape.

**Measured 2026-08-22/23. The evidence count moves — see the drift note below — so these are a
snapshot, and `MEASURED.json` at the destination is what any particular copy actually contains:**

| | files | size |
|---|---|---|
| total | 369,410 | 138.164 GB |
| **evidence** | 13,431 → 14,192 → 14,196 → **14,270** | ~**1.118 GB** |
| regenerable | 355,140 | 137.046 GB |

**Never quote the evidence count from this table.** Read it from `MEASURED.json`, which is written
only by a verification that passed.

99.20% of `eval/runs/` is build output — 133.344 GB of it cargo target dirs from old
`t1_rally`/`t2_net`/`t3_powerup` spec-change trials. **The often-quoted "129 GB" and "138 GB" are
the same measurement**: 128.66 GiB = 138.15 GB. Neither was ever the size of the evidence.

**Do not infer from that table that `work/` is disposable.** The older `runner.py` wrote its work
trees *inside* `eval/runs/<run>/work/<tid>/` and stores **no tarball and no `diff.patch`** — only a
3,000-character `diff_stat` tail in the trial JSON. For every spec-change trial the work tree is
the only copy of what the agent wrote, and the rule above keeps its source while dropping its
caches. `wholegame.py` does not have this problem: its work trees live under `--work-root`, outside
the repo, and each submission is archived as `artifacts/<tid>/submission.tar.gz`.

### Re-sync whenever the evidence set has grown or changed — whatever made it move

    python3 tools/backup_evidence.py --dest /Users/stefano/game-research-evidence

> **The trigger is the RESOURCE — files `evidence_set.py` classifies as evidence — not any
> activity that happens to produce them.** If what you just did changed which bytes are in that
> set, re-sync. You do not need to decide whether it counts as a run.

This section read *"re-sync after any run completes"* until 2026-08-23, and that is an
enumeration of one occasion (#115). The most irreplaceable class this project holds was created
by a **repair**, not a run: `starter-baselines/` was written at 04:24 on 2026-08-23 to preserve
the root commits before the work roots were reclaimed, 7.5 MB that exist nowhere else (#104), and
the copy verified at 00:08 that morning did not contain a single byte of it. Nothing was broken;
the rule was read and could not fire, because a repair is not a run.

The cheap, mechanical version of the trigger, which needs no judgement at all:

    python3 tools/backup_evidence.py --dest /Users/stefano/game-research-evidence --verify-only

**`--verify-only` answers the trigger rather than assuming it.** It re-classifies and reports what
is missing at the destination; a non-zero count *is* the signal to re-sync. Run it whenever you
are unsure, and after anything that wrote, rewrote, quarantined or archived under `eval/runs/`.

It classifies, rsyncs, and then **verifies by reading the destination back** in four tiers —
inventory, SHA-256 of every file on both sides, opening the harness's own JSON records and
extracting tarballs, and re-deriving every starter baseline's provenance. It never deletes from
the source.

**rsync's exit code is not the check.** A copy that reports success and wrote nothing is the same
defect class as a gate that passes and measures nothing, and it is discovered on the day the
original is gone. Pinned both ways 2026-08-22: a clean run verified 14,192 files; with one file
deleted, one tarball truncated and 100 bytes flipped inside a JSON, tiers 1, 2 and 3 each caught
their own and the tool exited 1.

**Tier 4 asks whether a baseline is still the commit it claims to be**, not whether its bytes
arrived. For every `<tid>.starter-baseline.tar.gz` it recomputes the git blob id of each member
*from the destination's bytes* and matches it against the `ls-tree` in the companion
`.blobs.txt`, whose first line carries the root commit id. It is **not sampled** — the class is
7.5 MB and cannot be reconstructed, and a sample of an irreplaceable class tells you about the
sample. `tools/backup_evidence_control.py` pins it: nine fixture cases built from a real git repo
(a flipped byte inside a member, a dropped member, an added member, a rewritten ls-tree oid, a
garbled commit header, an empty ls-tree, a truncated gzip, a missing companion — and the genuine
pair, which must come back clean), plus `--runs-root`, under which all 22 real baselines verify.
Five mutants each survive nothing: every one is caught by exactly the case that names its
mechanism.

That 2026-08-22 sweep also found a **false positive worth keeping in mind**: `tsconfig.json` is
JSONC, so a blanket `json.load` over every `.json` reported 26 corrupt files on a byte-perfect
copy. The semantic tier now checks only JSON the *harness* wrote — derived from the work-tree set,
not listed. A verifier that cries wolf on a good copy gets ignored on a bad one.

### The copy is additive, so it becomes a superset — and that has to be visible

rsync runs without `--delete` and nothing here removes from the destination, which is the right
default: this copy exists to survive an `rm -rf`, and a mirror that faithfully reproduces a
deletion protects against nothing. The cost is that when a file leaves the source, the copy keeps
it, and a stale file at the destination is indistinguishable from a current one.

`backup_evidence.py` therefore reports **destination-only files** every run and writes the full
list to `DEST_ONLY.txt` at the destination. It is an inventory, not a defect, and it does not fail
the tool. As of 2026-08-23 it holds **23** paths: the stale judge-pack files `judge/repack.py`
removed from `wg-g4c` that morning, which the source keeps under
`wg-g4c-*/repack-2026-08-23-stale-files-removed/`. Anyone re-packing from the second copy rather
than the source would resurrect exactly what was removed, so read `DEST_ONLY.txt` before treating
the copy as equivalent to the original. **Decide per path, at the source. Never reconcile by
deleting at the destination** — that turns an inventory question into lost evidence.

### The current copy is NOT a backup, and must not be reported as one

`/Users/stefano/game-research-evidence/` is on **the same physical disk** as the original — the
only writable volume on this machine. There is no external disk (the sole `/Volumes` entry is a
460 MB image with 44 MB free), no `rclone`, `restic` or `borg`, and no configured object-storage
remote. iCloud Drive exists but is the operator's personal document store; project evidence does
not belong in it and the quota is not ours to spend.

It protects against `rm -rf`, a bad `git clean`, and the reclamation below. It protects against
**nothing** a backup is for: disk failure, filesystem corruption, theft, loss of the machine.

**What would make it a backup** — any one of these:

- an external disk, then `backup_evidence.py --dest /Volumes/<disk>/game-research-evidence`. The
  whole set is 1.118 GB, so any USB stick does it;
- a private GitHub repo. Every evidence file is **under 50 MB** (largest 44.21 MB, a Unity
  `submission.tar.gz`), so no LFS — measured, not assumed. This is the one thing the original task
  forbade, on the strength of the 129 GB figure that turned out to describe the build output;
- `rclone`/`restic` to object storage, once a remote is configured.

### `eval/runs/` is written concurrently, so a copy is a snapshot of a moving target

While this was being measured the set grew from 13,431 files to 14,192 — another agent's session
wrote 761 files into `wg-aspect-reliability/packcheck/` at 23:59. Nothing in the harness marks a
run directory quiescent. `backup_evidence.py` classifies once and verifies against that same list,
so each run is internally consistent; what it cannot promise is that no *later* write is missing.
Treat `MEASURED.json` at the destination as the statement of what the copy actually contains.

**A concurrent write is not only a missing file — it can be a file that verifies and is a
prefix.** The 00:08 copy caught `wg-aspect-reliability/REPRODUCIBILITY.json` at **220 bytes** and
`sweep.log` at **88**, while the sweep still had 3 hours 39 minutes to run; both sides hashed
equal and tier 2 was correctly green. They are 49,666 and 8,070 bytes now. A SHA-256 match proves
the copy equals the source *at classification time* and says nothing about whether the source was
finished. So **check for recent writes before spending on a copy**, and re-sync afterwards
regardless:

    find eval/runs -type f -newermt '<15 minutes ago, as an ISO timestamp>' \
      -not -path '*/targets/*' -not -path '*/node_modules/*' | wc -l

Spell the timestamp out. `find` on this machine is **bfs**, which rejects GNU's `-newermt '-15
minutes'` — and piped into `wc -l` that rejection prints a confident `0`, which is rule 3's
fallback shape reached without anyone writing `|| echo 0`.

## After a run: reclaiming disk, without deleting evidence

Work trees are large and they accumulate: measured 2026-08-22, three g4 runs held **55G**
(`wg-g4` 16G, `wg-g4b` 14G, `wg-g4c` 24G) on a volume at **87%**. A build that dies part-way
because the disk filled presents as a harness bug, and this project has already spent days
tracing failures whose real cause was environmental.

**NEVER delete anything under `eval/runs/`.** That is the evidence, including
`submission.tar.gz`, the frames, the reports and the packs. Nothing in this section applies to it.

**Safe to delete, once verified:**

- `~/game-research-work/<run>/_targets/` — build output, always reproducible.
- `~/game-research-work/<run>/<trial>/` — **only if that trial's `submission.tar.gz` exists AND
  the tree's `starter baseline` commit has been preserved.** Both, not either.

> ⚠️ **The tarball is the submission. It is not the trial.** `submission.tar.gz` carries **no
> `.git/`** — verified by listing one — and the work tree's root commit, `starter baseline`, is
> the only record anywhere of *the starter the agent was actually given*. Without it a stored
> judge pack can never be honestly re-packed: the exclusion set for starter drift (#77) can be
> computed by subtraction and never checked, and `judge/repack.py` refuses on exactly that
> ground. Of 68 stored judge packs, the baseline survives for **8** (#104).
>
> **The three surviving work roots were preserved on 2026-08-23**, so this rule is now
> satisfiable rather than merely stated: `eval/runs/<run>/starter-baselines/` holds
> `<trial>.starter-baseline.tar.gz` (`git archive` of the root commit) and
> `<trial>.starter-baseline.blobs.txt` (its `ls-tree -r`, with the commit id) for all 22 trees of
> `wg-g4`, `wg-g4b` and `wg-g4c` — **7.5 MB against 55 GB of work trees**. Produce the same pair
> before deleting any future tree. `git bundle` does not work here: a bare commit id is not a
> ref, and it exits `Refusing to create empty bundle`.

### Verify per TREE, never per run

A per-run count is not sufficient and would have destroyed evidence here. `wg-g4` has **6 work
trees but only 4 archived tarballs** — it was stopped mid-build, so `unity__t0` (177M) and
`unity__t1` (40M) were never archived. A rule phrased *"delete work trees of runs that finished"*
deletes them; a rule phrased *"delete a tree whose own tarball exists"* does not.

```
for t in ~/game-research-work/<run>/*/; do
  n=$(basename "$t"); [ "$n" = "_targets" ] && continue
  if [ -f "eval/runs/<run>/artifacts/$n/submission.tar.gz" ]; then
    echo "ARCHIVED   $n"      # safe to rm -rf
  else
    echo "NO ARCHIVE $n"      # keep, or archive it first
  fi
done
```

Read the whole listing before deleting anything. An unarchived tree is either a stopped trial
worth archiving or a trial that never produced work — and those look identical from the size.

Re-measured 2026-08-22 across all three work roots, mechanically rather than from the note above:

| run | work trees | tarballs | unarchived |
|---|---|---|---|
| `wg-g4-2026-08-17T09-38-32` | 6 | 4 | `g4_platformer__unity__t0`, `__t1` |
| `wg-g4b-2026-08-17T19-50-43` | 8 | 8 | — |
| `wg-g4c-2026-08-21T02-26-46` | 8 | 8 | — |

Those two trials died before `build_trial` reached its archiving step: `eval/runs/wg-g4/artifacts/
g4_platformer__unity__t{0,1}/` holds **`prompt.txt` and nothing else**, and neither has a trial
record in `trials/`. They contribute to no published number and they are irreplaceable.

Their source is now copied to
`/Users/stefano/game-research-evidence/work-root/wg-g4-2026-08-17T09-38-32/` — 1,343 files,
0.020 GB of the 17.843 GB that root holds, SHA-256-verified on both sides. **Tier 3 of the
verifier checked nothing there**, because a raw work tree contains no harness records and no
tarballs; only inventory and hashes cover that copy, and the tool now says so instead of printing
a `0/0` that reads as a pass.

**Run `backup_evidence.py` against a work root before reclaiming it**, not only against
`eval/runs/`. The assumption that "every submission is archived as `submission.tar.gz`" is false
for exactly these two trials, and it is false in the direction that loses work.

### Keep a warm tree that is a finding's only reproduction

`wg-g4c`'s unity trees are the evidence for **#66**: `just lint` answers differently on a warm
tree than on a clean extract, which is *why* that finding is provable at all. Deleting them
destroys the ability to reproduce it, and **the repair does not restore it** — a fixed starter
answers cold by construction, so once the warm trees are gone #66 has no reproduction at any
price. Keep at least one warm tree per stack when reclaiming any run.

> This rule used to read *"do not reclaim `wg-g4c` until task 07 is closed"*. Task 07 closed on
> 2026-08-23 and the permission opened silently, which is the defect: **a trigger written as a
> task id expires the moment someone finishes the task, and finishing it is not the same
> decision as destroying the evidence it was measured on.** Reclaiming these trees deletes the
> only reproduction of a published finding, which `AGENTS.md` puts in the ask-the-operator
> column. Ask; do not infer it from a queue state.

> **A warm build cache is evidence, not waste.** It is the only copy of a state that cannot be
> reconstructed from the archive, because the archive stores sources and a cache is a *history*.


## After

- **Diff the rendered prompts against the run's own snapshot BEFORE grading:**
  `python3 tools/prompt_guard.py --diff runs/<run>/prompts`, unpiped. The snapshot exists for
  exactly this moment; taking it and never diffing it is the same as not taking it.

  Pinned in both directions 2026-08-17, because a diff that cannot go red certifies nothing:

  | control | expected | got |
  |---|---|---|
  | diff immediately after snapshotting | exit 0, all 16 match | **exit 0**, `all 16 rendered prompts match the snapshot` |
  | one line changed in the shared `_preamble()` | exit 1, naming the games | **exit 1**, `16 rendered prompt(s) differ` — every game, both stacks |
  | change reverted | exit 0 again | **exit 0** |

  The middle row is #41 reproducing on demand: **a single line in `_preamble()` moves all
  sixteen prompts**, which is why the guard is a diff of the RENDERED output and not a review
  of the source that renders it.

  **The snapshot must live at `runs/<run>/prompts`** — durable, inside the run. A snapshot in
  `$TMPDIR` is the artifact-lifetime defect of #45: it can be gone before the diff that needs
  it, and its absence looks identical to "no drift". `tools/precampaign_smoke.py` writes one
  to scratch as a liveness exercise and labels it `[LIVENESS ONLY - NOT the launch artifact]`,
  because on 2026-08-17 its green row was read as the launch snapshot having been taken when
  no snapshot existed (#57).

- **Check capture geometry before reading any frame-derived number:**
  `python3 tools/frame_parity.py --run runs/<run>`, unpiped. One submission in twenty-two
  filmed at 768x576 while the rest filmed at 640x400, and nothing reported it (#59). More
  pixels is more opportunity for distinct colours, more ink and more change — densities are
  safe, raw counts are not, and a judge shown the PNGs is shown the difference. Pinned both
  ways: `wg-audio48` exit 1 naming the divergent trial, `wg-arena3d` exit 0.

- **Read `agent.final_text` for every trial before grading anything.** Agents write a paragraph
  headed *"What I could not verify — and why"*, and on `wg-arena3d` four of them named the exact
  mechanism that produced the whole run's spread. **Nothing in the harness reads that field and
  no gate looks at it** — it sat unread for a day while the numbers were treated as stack
  results (#49). A grader that never reads what the subject said about its own work will keep
  re-deriving what the subject already told it.
- **Record what changed about the MACHINE while the run was in flight, not only what changed
  about the configuration.** `wg-arena3d` straddles a system-daemon repair; its records say
  `8 completed` with one terminal reason and nothing marks the boundary. The population split
  was a **date**, and no aggregate in this harness has ever been partitioned by one.
- Partition by `terminal_reason` before computing anything. `completed`, `budget_exhausted`,
  `session_limit`, `api_error` are different populations. Report `n` per group.
- Read spend from `agent.cost_usd`. **Not `total_cost_usd`** — it is absent and reads as zero.
- Record the run in `RUNS.md` with its cap regime and what it may be compared with.
- Update `README.md`, `DECISIONS.md` and `FINDINGS.md` in the same session.
