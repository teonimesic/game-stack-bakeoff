---
name: tasks
description: Read, claim, complete and create items in this project's open-work queue at tasks/. Use at the start of a session to find what to do, when finishing a piece of work, and whenever the heartbeat fires.
when_to_use: Starting a session and needing the next piece of work; finishing something and recording what established it; discovering work that must outlive this session; the hourly heartbeat asking whether the queue is accurate.
argument-hint: "[next|list|show ID|start ID|note ID -|done ID \"evidence\"|add \"title\" --done-when \"...\"]"
---

# The open-work queue

**Authoritative file: `tasks/` — one Markdown file per task.** `eval/tools/tasks.py` is a
convenience over it; if the two ever disagree, the files win and the tool is the bug.

There is deliberately no single backlog document. The first version was one `TASKS.md`, and
every agent had to read all of it to find one item — the same failure this project already
recorded for documentation: *a document nobody finishes reading protects nothing.*

## Reading it

```bash
python3 eval/tools/tasks.py            # one line per open task, priority order
python3 eval/tools/tasks.py next       # the single item to work on, in full
python3 eval/tools/tasks.py show 07    # one task, in full
```

The format is grep-first, so no tool is required:

```bash
grep -l "^status: todo" tasks/*.md                          # which files nobody has
grep -h "^title:" $(grep -l "^status: todo" tasks/*.md)     # their titles
grep -l "^status: in_testing" tasks/*.md                    # waiting on the orchestrator
grep -l "^priority: 1" tasks/*.md                           # the urgent ones
grep -rl "FINDINGS.md #66" tasks/                           # what refers to a finding
```

### The statuses, and where they are defined

**`STATUSES` in `eval/tools/tasks.py` is the definition, and it wins.** If this skill and that
constant disagree, the constant is right and this skill is the bug — the same rule every skill
here carries about its authoritative file. `python3 eval/tools/tasks.py check` is what enforces
it. The table below is the procedure, not the definition:

| status | which command moves a task into it |
|---|---|
| `todo` | `tasks.py add` |
| `in_progress` | `tasks.py start <id>` |
| `in_review` | `tasks.py review <id> "<pr url>"` |
| `in_testing` | `tasks.py testing <id> "<evidence>"` |
| `done` | `tasks.py done <id> "<evidence>"` |

Why each state exists, why the legacy names are accepted forever, and what would re-open any of
it: `DECISIONS.md`, *"An agent hands back a pull request, and the queue has 5 statuses"*. The
procedures that drive the transitions are `.claude/skills/work/SKILL.md` (the agent's half) and
`.claude/skills/dispatch/SKILL.md` (the orchestrator's).

**Do not hand-write `status:` in a task file.** `open` and `in_flight` still parse, but the
commands above are what keep the field and the tool in agreement.

**Read one task, not the queue.** `show ID` or the file itself. Reading all of them to pick one
is the cost this layout exists to remove.

### The frontmatter is YAML, and `tasks.py` needs PyYAML

`yaml.safe_load` parses every task file's frontmatter, and `tasks.py` writes it with
`yaml.safe_dump`. **Edit a task file by hand and you may quote a value; do not hand-write one
unquoted that contains `: ` or ` #`.** `tasks.py check` now reports an unparseable file by name
instead of tolerating it.

This is worth one paragraph because the failure was silent, not loud. Until 2026-08-23 the
reader split each line on its first colon, so 44 of 58 files raised `ScannerError` — and, worse,
9 more parsed *without error* and came back truncated: `refs: eval/FINDINGS.md #53, blocked by
task 01` loaded as `eval/FINDINGS.md`, because ` #` starts a YAML comment. An external reader
got a plausible wrong answer rather than a failure.

The id is deliberately left as bare digits (`id: 07`, not `id: '07'`), so a worktree still
running an older `tasks.py` can find tasks by id. Everything else the serialiser quotes as
needed, and long values stay on one line — the grep idioms above are unaffected.

### The queue is shared, and lives in the main checkout

`tasks.py` resolves `tasks/` to the **main worktree** wherever you run it from, including from
inside an agent worktree. There is one queue and every agent reads and writes it.

**So filing or closing a task appears as an uncommitted change in the MAIN checkout, not on
your branch.** That is deliberate: the queue's state is a fact about the project, not about one
branch's work, and it is why you can see what a peer filed a minute ago.

It was not always so, and the failure is worth knowing. When `tasks/` was per-worktree, three
agents each filed a "task 27" in one hour and every exclusive-create guard succeeded, because
each was guarding its own copy (#94). If you ever find yourself renumbering ids at merge time,
something has forked the queue again.

## Working it

**A task in this queue is authorised. Filing it was the decision.** Start it, do it, close it.
Do not wait for confirmation to begin planned work — if a task raises a question nobody
anticipated, ask that question and continue with the rest of the queue rather than stalling.

**One task, one agent, one worktree.** A single agent holding the whole queue serialises work
that is independent and makes a bad result hard to isolate. Spawn one subagent per task with
`isolation: "worktree"`, let it commit on a `task-NN-slug` branch, and merge each branch after
verifying the result against the artifacts — not against the agent's report of them. Respect the
dependency order stated in each ticket's `refs`; run everything else concurrently.

### The dispatch is one line, and the ticket carries everything

```
/work 56
```

That is the whole brief. Two skills, one on each side of it:

| | |
|---|---|
| `dispatch` | **the orchestrator's.** Make the ticket current, check it is safe to run now, launch, then verify and merge what comes back |
| `work` | **the agent's.** Read the ticket, do it to the standard, hand back a branch |

Neither restates the other, and neither restates the ticket.

> **Anything task-specific goes in the TICKET, before dispatch. Never in the message.**
> On 2026-08-23 every agent was launched with a paragraph of constraints in its prompt:
> established measurements, hazards, a dependency created hours earlier. All of it correct, all
> of it invisible to the next reader, and all of it re-derivable only by someone who happened to
> read that message. That is the failure `AGENTS.md` names in its own words — *a protocol
> delivered in a chat message dies with the session.*

So the orchestrator's job before dispatch is **updating the ticket**:

| When | Put it in the ticket |
|---|---|
| Something the ticket assumes has since changed | The correction, dated, and what it now implies |
| A dependency has appeared since it was filed | Which file, and what it forbids |
| A peer's result bears on it | The measurement, not a pointer to a conversation |
| The ticket's `done_when` is now unreachable or wrong | Rewrite it — and say why it moved |
| An agent hands back knowledge the next one would re-derive | It should have appended it itself with `tasks.py note <id> -`; if it did not, do it |

**A ticket that needed a message to be workable was not ready to dispatch.** If you find
yourself typing the constraint, stop and write it in the file instead — then dispatch.

**Task subagents run on Opus.** The queue is the project's own reasoning about its instrument,
and a cheaper model here buys nothing worth the risk of a wrong number.

> **This does NOT extend to the judges or the building agents.** The judge model is a live
> research question with a cost argument attached, and the building agents' model is the
> *subject* of the measurement — changing either from a queue-side default would silently
> alter what is being measured. Model choice there is set by `eval/PROTOCOL.md` and
> `eval/judge/JUDGING.md`, never inherited from how a task happened to be run.


```bash
python3 eval/tools/tasks.py start 07
python3 eval/tools/tasks.py review 07 "https://github.com/teonimesic/game-stack-bakeoff/pull/7"
python3 eval/tools/tasks.py testing 07 "lint now identical warm and cold, pinned both ways; RUNS.md regime note added"
python3 eval/tools/tasks.py done 07 "verified against the artifacts and merged as PR 7"
```

`testing` and `done` both require evidence, and the evidence must be **what established it** — a
measurement, a pinned control, a file — never "completed". A task closed without evidence is
indistinguishable from one abandoned, so an empty or whitespace-only evidence string is
**refused** rather than written.

**`-` reads the evidence from stdin here too**, exactly as in `note` — one sentinel, one
meaning, in every subcommand that takes durable text. Use it for the one case argv cannot
carry: a one-line evidence string containing a backtick (#80).

```bash
python3 eval/tools/tasks.py done 07 - <<'EV'
lint identical warm and cold; pinned by `tasks_control.py` in both directions
EV
```

**A MULTI-LINE account is refused, naming `note`.** `established_by` is one unbroken line of
prose inside YAML frontmatter and is not where the next agent looks. Until 2026-08-23 `done`
took `-` as a *literal*, so `done <id> - < account.md` stored the one character `-` over
whatever was redirected in, at exit 0, with the ticket closed and the record gone (task 120).
Put the account in the body with `note`, then pass a one-line summary here.

### `note` — writing what you learned back into the BODY

```bash
python3 eval/tools/tasks.py note 07 - <<'NOTE'
The recipe in the starter is wrong: `just build` passes `--offline`.
Measured on 4 of 12 trials. The next agent must not re-derive this.
NOTE
```

It appends a dated `## note <date>` section to the ticket in the **main checkout's** queue and
rewrites **no other byte** of the file — the append goes out through `open(p, "a")`, so "the
rest of the ticket is unchanged" is true by construction rather than by a round-trip that
happened to hold. `--heading` replaces the default heading; an empty note is refused rather than
written as a bare heading.

**`-` is not a convenience.** A backtick in an argv string is command substitution before
`tasks.py` runs (#80) and a newline cannot survive an argument at all. A **quoted** heredoc
(`<<'NOTE'`, never `<<NOTE`) carries both in unexpanded.

Why it exists: `.claude/skills/work/SKILL.md` tells every dispatched agent to write back what the
next one would otherwise re-derive, and until 2026-08-23 there was no way to obey it from a
worktree — `Edit`/`Write` aimed at the shared checkout are refused by isolation, and committing
an edit to your own copy of `tasks/NNN-*.md` offers the merge a conflict in a file `start`/`done`
are already rewriting. Tasks 105 and 106 both emptied their findings into `established_by`
instead, which is one line of YAML prose that cannot hold a backtick and is not where the next
agent looks (task 113).

**Aim it by id, never by filename.** That is the whole difference between this and the `>>` you
would otherwise reach for: a shell append to a filename guessed from a queue listing title is
AGENTS.md rule 12's worked example, and it created a second, malformed task.

## Creating one

```bash
python3 eval/tools/tasks.py add "Title in the imperative" \
  --done-when "the observable condition that ends it" \
  --refs "eval/FINDINGS.md #62" --priority 2 --why "why it matters"
```

`--why` and `--done-when` are both required. `--why` becomes the body, and `check` fails on an
empty one.

`add` gives you a stub. **The stub is not the task — write the body.** And write it into *this*
file: appending to a filename you guessed from a queue listing title is how task 71's brief ended
up in task 70's ticket. `check` catches that now — see [the body](#the-body-check-fails-when-a-ticket-is-not-its-own-ticket).

### Write it as a ticket for a stranger

**The reader is an agent in a fresh session with no memory of why this exists.** It has never
seen the conversation that produced the task, does not know what `ux` measures or what #59 said,
and cannot ask. If it has to guess what the task is about, the task has failed and you will get
back work that solves the wrong problem.

A task body must answer four questions, in this order, without assuming any of them:

| | |
|---|---|
| **What is this thing?** | One or two lines defining the component before naming its problem. "`idiomatic` is the aspect that asks whether code is written the way its language expects" — not "idiomatic's ordering". |
| **What is wrong, and how do we know?** | The defect with its evidence: the measurement, the number, the finding. Not "this is broken". |
| **Why does it matter?** | What conclusion is unsafe, or what is blocked, while it stands. If nothing is, lower the priority. |
| **What should be done?** | Concrete first move. Name the files. Include cost if it spends money, and any regime boundary the change would cross. |

Also state, where they apply:

- **Dependencies** — "depends on task 01", and put it in `refs` so grep finds it.
- **Outcomes that count as success.** For an experiment, pre-register what each result would
  mean, so a null result is a finding rather than a failure.
- **What NOT to conclude.** The cheapest way to prevent a wrong inference is to write it down
  next to the right one.

**Spell out every acronym, id and shorthand the first time.** `#66` means nothing cold; "#66 —
Unity's lint answers from its build cache" means something. Expand rather than cross-reference
when it costs a line.

**Cite by path**, never "the improvements doc": two files are named `IMPROVEMENTS.md`, and a
trial id is not unique across runs (#70), so a reference to a submission needs its run.

**Every task states how you would know it is done.** `tasks.py check` exits 1 when one does not,
and that check exists for a reason: a task that cannot be completed is a permanent excuse —
the task-list form of a criterion that cannot fail.

The test before you save: **could someone who has never worked on this project start it, and
know when to stop?** If not, it is a note to yourself, and notes to yourself do not survive the
session that wrote them.

## When the heartbeat fires

The heartbeat's measurement is `eval/tools/heartbeat.py` — a file, so it can be corrected when
it is wrong, which it has been. It counts **outputs** (`judge_rounds`, `graded_submissions`) as
well as source, because work lands inside existing run directories and moved no source-line
count on three separate occasions.

Four things, in order:

1. **Verify** — is anything `in_progress` actually still in flight? Is anything `todo` already
   done? Is anything stuck in `in_review` with a PR that was reviewed an hour ago? Mark it, with
   what established it. A stale queue is worse than none, because it is believed. Do not infer an
   agent's state from its files: an artifact mid-write is indistinguishable from one never
   written.
2. **Merge** — everything in `in_testing`. `python3 eval/tools/tasks.py list --status in_testing`
   is the list, and each ticket's `pr` field is the pull request. Verify the result against the
   artifacts, **not against the agent's report of them and not against its review**, then merge.
   An unmerged pull request is finished work that no one else can build on.
3. **Pick**, if there is open work. Highest priority, not newest.
4. **Add**, if fewer than three are open. Running out has never yet been true of this project —
   re-read `eval/FINDINGS.md` for anything filed and never acted on, and check `IMPROVEMENTS.md`
   (root, and `eval/`) for hypotheses left open.

**"Nothing moved" is a claim about the snapshot, not about the world.** Three times the counters
sat still through real work — once because the file list went by extension, once because it went
by directory, once because it counted source and the work produced JSON. Check the artifacts
before concluding the hour was idle.

## Priorities

`1` blocks a conclusion someone would otherwise publish · `2` a known defect with a known fix ·
`3` worth doing, nothing waits on it · `4` housekeeping · `5` large, needs a plan first.

Raise a priority when evidence arrives, not when it has been sitting a while.

## Reachability: `check` warns, it cannot decide

`tasks.py check` catches a **missing** `done_when`. It cannot in general catch an
**unreachable** one, because reachability depends on data the task file does not contain.
Two got written anyway:

- **08** wanted *"SE below the smallest non-zero gap"*. Unsatisfiable: means over n rounds
  live on k/n so the gap shrinks as 1/n, while SE shrinks as 1/sqrt(n). The target recedes
  faster than the estimate closes on it, so it passes only at n=2-3 where SE is least
  trustworthy (FINDINGS #75).
- **01** wanted *"all six aspects"* on a field that structurally cannot supply two of them —
  `g3_arena` has no audio evidence and one submission with no telemetry.

**Both were repaired the same way: an escape branch naming the negative outcome.** That
pattern is checkable even though reachability is not, so `check` warns when a `done_when`
makes a universal claim (`all`, `every`, `each`) or a threshold comparison (`below`,
`exceeds`, `at least`, …) **with no alternative branch**.

**An escape branch is recognised by the closed class of English function words that mark a
clause conditional or alternative** — `if`, `unless`, `when`, `where`, `or`, `either`,
`otherwise`, `any`, … — not by a list of the phrasings earlier tasks happened to use. That
distinction is the point. Until 2026-08-23 four of the nine entries were sentences copied
off tasks 01 and 08, and the check warned on tasks **32, 35 and 58**, every one of which
has an escape branch. Task 32's opens *"If no tool is worth adopting…"* — `if`, the
commonest conditional in the language, was not on the list; `naming`, one letter off
`named`, was.

Addresses come out of the text before the heuristic reads it, because `under
eval/findings/` is a path and not a comparison — that false positive was the *only*
warning `check` printed that day. So does the idiom `at all`, which quantifies nothing.

**Its limit, and why it stays a warning:** an escape branch carrying no marker at all
(*"the file records the negative result with its evidence"*) is invisible to it and always
will be, and a marker used non-hypothetically will silence a warning that should have
fired.

Pinned in both directions by **`eval/tools/tasks_control.py`**, which also pins the queue
round-trip, `add` from an agent worktree, and the three things `check` must still fail on.
Run it after touching `eval/tools/tasks.py`:

```bash
python3 eval/tools/tasks_control.py    # 0 green · 1 a direction FAILED · 3 NOT CHECKED
```

Never read exit 3 as a pass.

**And ask whether those rows can still go red**, which is a separate command because a
control that has quietly stopped measuring passes:

```bash
python3 eval/tools/tasks_mutants.py --selftest   # every mutant, killed by the row naming it
```

It writes a mutated **copy** of `tasks.py` into a tempdir and runs `tasks_control.py`
against it with `--tasks-py`; the repository's own file is never written to, and the run
asserts it is byte-identical afterwards. `--selftest` adds this runner's own positive
control: an **inert** mutation — a trailing comment on `MISFILED_MARGIN`'s line — that must
leave **every** row green, since a harness that can only print `CAUGHT` proves nothing by
printing it. It is inert *by construction* rather than by being an open coverage gap: the
gap it used to stand on was closed by direction 4c, and that broke `--selftest` (`tasks/106`).

The warning is pinned **twice, in different ways**, and the second is not redundant:
`reachability_warning` in process over the wordings, and `check` run end to end on a scratch
queue asserting the warning text reaches stdout. Without the second, `if warn:` → `if False:`
in `cmd_check` computes every warning, prints none, and every row stays green.

> **It is a smell, not a verdict.** Plenty of universals are perfectly reachable, and a
> warning here means *go and check whether the data can reach this*, not *this is wrong*.
> It is a warning rather than a failure because it will have false positives, and a gate
> that fails on correct input gets disabled.

**When you write a `done_when`, ask what you would report if the measurement comes back
negative.** If there is no honest way to close the task in that case, the condition is
unreachable and the task is a permanent excuse. Non-termination is a result: *"no pair
resolves, here is the measured gap"* closes a task; *"the experiment did not finish"* does
not.

## The body: `check` fails when a ticket is not its own ticket

The frontmatter was gated from the start. The **body** — the only part an agent is actually
briefed from — was not, and on 2026-08-23 commit `436bf64` appended task 71's entire 59-line
brief to `tasks/70-set-a-size-...md`, a filename guessed from a queue listing title, and created
`tasks/71-...md` with no body at all. `check` exited **0** on both for the **25m48s** they stood
on main — `436bf64` 09:12:56 to `28f6598` 09:38:44 (#141) — while `show 70` rendered a brief
about trial disclosures. Duration is the wrong measure anyway: the dispatched agent forked
*after* the misfile, so **all** of task 71's execution ran against an empty ticket.

Two failures now, one per half:

| `check` says | when |
|---|---|
| `body is empty` | exact, no heuristic. `add` writes a stub and **the stub is not the task** |
| `body restates task N's title/done_when (46%) far more than its own (9%)` | the body reads as a different ticket's brief |

**It is not keyed on the body naming another task's id**, which is how the repair was first
asked for and is not implementable: **58 of 85 live bodies name another task id** — tickets cite
their neighbours, which is the queue working — and the 59 misfiled lines never say *"task 71"*
once. What it compares is **containment**: what fraction of some other task's `title` +
`done_when` this body restates, against what fraction of its own. The misfiled brief restates
**45.6%** of task 71's and **9.4%** of task 70's.

`MISFILED_MARGIN = 0.25` is measured, not chosen. Scored over **every version of every task file
git has ever tracked** — 3175 file-versions across 81 snapshots — the margin separates cleanly:
the defect at **0.3615**, and the highest of the other 3174 at **0.1399** (task 62, whose subject
genuinely is task 70's). Both sides are pinned in `tasks_control.py`, so raising the threshold
and lowering it each go red — `tasks_mutants.py` is what re-runs that claim rather than
restating it: `margin_up` (0.50) turns 2 rows red, `margin_down` (0.13) turns 1 red, and the
one it turns red is the row asking whether the check can still stay **quiet**.

**Because of this, `add` now requires `--why`.** It is what goes into the body, and a tool that
creates a file its own lint rejects pushes the failure onto whoever runs the gate next.

> **What it cannot catch**, and why the empty-body check is separate rather than folded in: a
> body misfiled into a task with a *vague* brief scores low against it; a body misfiled between
> two *similar* tickets raises its own score too and stays under the margin — and adjacent
> tickets are exactly where a misfiling is likeliest. A body that is simply off-topic, matching
> nothing in the queue, is invisible to it.

Unlike the reachability warning, both of these run on `done` tasks too. The archive is what the
next agent reads to find out what was established.
