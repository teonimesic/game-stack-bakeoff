---
name: tasks
description: Read, claim, complete and create items in this project's open-work queue at tasks/. Use at the start of a session to find what to do, when finishing a piece of work, and whenever the heartbeat fires.
when_to_use: Starting a session and needing the next piece of work; finishing something and recording what established it; discovering work that must outlive this session; the hourly heartbeat asking whether the queue is accurate.
argument-hint: "[next|list|show ID|start ID|done ID \"evidence\"|add \"title\" --done-when \"...\"]"
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
grep -l "^status: open" tasks/*.md                          # which files are open
grep -h "^title:" $(grep -l "^status: open" tasks/*.md)     # their titles
grep -l "^priority: 1" tasks/*.md                           # the urgent ones
grep -rl "FINDINGS.md #66" tasks/                           # what refers to a finding
```

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

**Task subagents run on Opus.** The queue is the project's own reasoning about its instrument,
and a cheaper model here buys nothing worth the risk of a wrong number.

> **This does NOT extend to the judges or the building agents.** The judge model is a live
> research question with a cost argument attached, and the building agents' model is the
> *subject* of the measurement — changing either from a queue-side default would silently
> alter what is being measured. Model choice there is set by `eval/PROTOCOL.md` and
> `eval/judge/JUDGING.md`, never inherited from how a task happened to be run.


```bash
python3 eval/tools/tasks.py start 07
python3 eval/tools/tasks.py done 07 "lint now identical warm and cold, pinned both ways; RUNS.md regime note added"
```

`done` requires evidence, and the evidence must be **what established it** — a measurement, a
pinned control, a file — never "completed". A task closed without evidence is indistinguishable
from one abandoned.

## Creating one

```bash
python3 eval/tools/tasks.py add "Title in the imperative" \
  --done-when "the observable condition that ends it" \
  --refs "eval/FINDINGS.md #62" --priority 2 --why "why it matters"
```

`add` gives you a stub. **The stub is not the task — write the body.**

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

1. **Verify** — is anything `in_flight` actually still in flight? Is anything `open` already
   done? Mark it, with what established it. A stale queue is worse than none, because it is
   believed. Do not infer an agent's state from its files: an artifact mid-write is
   indistinguishable from one never written.
2. **Merge** — any task branch whose agent has reported. `git branch --list 'task-*'`. Verify
   the result against the artifacts, **not against the agent's report of them**, then merge.
   An unmerged branch is finished work that no one else can build on.
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
pattern is checkable even though reachability is not, so `check` now warns when a
`done_when` makes a universal claim (`all`, `every`, `each`) or a threshold comparison
(`below`, `exceeds`, `at least`, …) **with no alternative branch**.

Pinned in both directions against the real wordings: it warns on 08-original and
01-original, stays quiet on both repairs and on a plain artifact condition.

> **It is a smell, not a verdict.** Plenty of universals are perfectly reachable, and a
> warning here means *go and check whether the data can reach this*, not *this is wrong*.
> It is a warning rather than a failure because it will have false positives, and a gate
> that fails on correct input gets disabled.

**When you write a `done_when`, ask what you would report if the measurement comes back
negative.** If there is no honest way to close the task in that case, the condition is
unreachable and the task is a permanent excuse. Non-termination is a result: *"no pair
resolves, here is the measured gap"* closes a task; *"the experiment did not finish"* does
not.
