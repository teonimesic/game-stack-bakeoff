# Working in this repository

A research project measuring how well coding agents build games in four different stacks. The
output is **evidence**, so the standard for a claim here is higher than the standard for working
code: **a number that is wrong is worse than no number, because it gets acted on.**

## Read before changing anything

| File | Why |
|---|---|
| `README.md` | Current status and where things live |
| `tasks/` | **What is not done yet** — one file per task, grep-first. `python3 eval/tools/tasks.py next` gives the item to work on; read one task, never the queue. Every task states how you would know it is done. See the `tasks` skill |
| `DECISIONS.md` | What is decided and why |
| `eval/FINDINGS.md` | Findings #19-#116, including marked retractions and withdrawals. **Check whether a number has been retracted before trusting it** |
| `IMPROVEMENTS.md` (root) | the improvement loop for the **templates** — each iteration a hypothesis, a change, and a measurement that could have come out against it |
| `eval/IMPROVEMENTS.md` | the same loop for the **evaluator**. Two files share a name; cite the path, never "IMPROVEMENTS iteration 1b" |

## Folder-scoped guidance

This file covers what applies everywhere. Each area has its own `AGENTS.md` with the rules that
only apply there — read the one for the directory you are working in.

| Directory | Covers |
|---|---|
| `eval/` | Running trials, cost, controls, offline re-grading, concurrency |
| `eval/judge/` | The three grading tiers, blinding, rubric changes |
| `research/` | The briefs, and how claims in them must be sourced |
| `template*/`, `eval/starters/*/` | **Not for you.** Those `AGENTS.md` files are the product — what a building agent reads during a trial. Editing one changes the thing being measured, and requires re-running `eval/judge/verify_blind.py` |

`eval/runs/**` holds stored results, including per-trial copies of the starters. Nothing in there
is guidance; it is data.

## Everything belonging to this project lives inside this project

**Never write project skills, memories, or configuration to `~/.claude`.** Anything this
project knows or does must be inside the repository, where it is versioned with the work
it describes and travels with it.

| Thing | Where |
|---|---|
| Skills | `.claude/skills/<name>/SKILL.md` — **the only path. A skill anywhere else fails `docstat.py --sweep`** |
| Memories | `.claude/memory/` |
| Permissions and hooks | `.claude/settings.json` |
| Machine-local settings | `.claude/settings.local.json` |

`autoMemoryDirectory` is **ignored** when set in a checked-in `.claude/settings.json`, so
it is set in `.claude/settings.local.json` and points at `.claude/memory/`. If memories
start appearing under `~/.claude/projects/...`, that file was lost or overridden — fix it
rather than working around it.

The reason is the same one behind the whole documentation discipline: knowledge stored
outside the project is knowledge the next session in this project cannot reach, and a
skill that lives in a home directory silently applies to unrelated work.

## Skills — procedures, invoked when you are doing the thing

These live in `.claude/skills/<name>/SKILL.md`, and **that is the sole authoritative path**.
Invoke the one that covers what you are about to do rather than reconstructing the procedure —
each encodes failures that cost trials.

There is no second copy for another agent CLI, and adding one fails the sweep. `.agents/skills/`
held exactly that until 2026-08-23 — a Codex-flavoured duplicate that was never once in sync,
had no reader, and shipped an `add-game` missing the guard that exists because a shared preamble
contaminated a single-variable experiment. The reasoning, and what would re-open it, is in
`DECISIONS.md`; the measurement is #99. If you want cross-tool support, add a **pointer** to
`.claude/skills/`, never a copy of it.

| Skill | Use when | Authoritative file |
|---|---|---|
| `run-matrix` | launching, watching, diagnosing or stopping a trial run | `eval/PROTOCOL.md` |
| `evaluate-run` | grading a finished matrix, re-grading offline, running the judges | `eval/judge/RUBRIC.md`, `JUDGING.md` |
| `add-game` | writing a task prompt, a play-bot criterion, or changing one | `eval/suites/wholegame_prompts.py` docstring |
| `refine` | a run has finished and been evaluated — improve templates, prompts, rubrics, docs from it | `eval/IMPROVEMENTS.md`, `IMPROVEMENTS.md` |
| `audit-docs` | after a session, or when a rule failed to prevent what it was written for | this file |
| `tasks` | reading, claiming, closing or writing an item in the open-work queue | `tasks/` |
| `prune` | a cleanup exploration pass — text or code that no longer earns its space | `CLEANUP-LOG.md`, this file |

The usual order across one cycle is **`run-matrix` → `evaluate-run` → `refine`**, with
`add-game` when the task set changes and `audit-docs` folded into `refine` or run alone.

## The two monitors, and how to relaunch them

Both are background monitors owned by whatever session is driving the work. **They do not
survive a session**, so a new session should relaunch them — they are the mechanism by which
work keeps happening rather than waiting to be asked for.

| | fires | asks | measurement |
|---|---|---|---|
| **heartbeat** | hourly | *is new work happening?* verify the queue, merge finished task branches, pick the next item | `python3 eval/tools/heartbeat.py` |
| **cleanup** | every 6 hours | *what no longer earns its space?* explore one area, record it, file tasks | `.claude/skills/prune/SKILL.md`, log in `CLEANUP-LOG.md` |

**The heartbeat** diffs `heartbeat.py`'s counts against the previous hour and prints what
moved. It counts **outputs** (`judge_rounds`, `graded_submissions`) as well as source, because
judge rounds land inside existing run directories and moved no source-line count on three
separate occasions. `project_lines` is defined over **git-tracked files**, so agent worktrees —
which are full checkouts and once made it read a fivefold jump in one hour — are excluded by
construction rather than by a list.

> **"Nothing moved" is a claim about the snapshot, not about the world.** Three times the
> counters sat still through real work: once the file list went by extension, once by
> directory, once it counted source when the work produced JSON. Check the artifacts before
> concluding an interval was idle.

**The cleanup monitor** does not run a tool and report it. It **explores**: reads
`CLEANUP-LOG.md` to see what previous passes covered, picks one area nobody has looked at
recently, reads it properly, files tasks for what it finds, and appends what it looked at —
**including what it examined and judged sound**, so the next pass does not redo it.
`eval/tools/prune_scan.py` is an aid it may run, not its definition.

Both monitors are launched with the `Monitor` tool, `persistent: true`. Neither should ever do
the work itself beyond something small and obvious: their output is a prompt to the session,
and anything larger belongs in `tasks/` where it can be picked up, reviewed and reverted.

**A skill is a procedure; a doc is what is true; a rule is always loaded.** The rules
below are deliberately *not* skills — a constraint you have to remember to invoke is a
constraint that will fail, which is the lesson these rules were bought with.

Every skill names its authoritative file and states that if the two disagree, **the doc
wins and the skill is the bug.** That is what keeps a skill from becoming a second source
of truth — the failure mode recorded as #38.

## Instructions to agents live in files, not in messages

**Anything you would tell another agent must be written down first, and the message must point at
the file.** A protocol delivered in a chat message dies with the session; the next agent rebuilds
it from scratch, differently, and usually worse.

This is not bookkeeping — it is the only mechanism by which the instructions improve. A rule in a
file gets corrected when it fails and the correction survives; a rule in a message gets
re-invented.

| Instruction | Lives in |
|---|---|
| How to launch, watch and stop a run | `eval/PROTOCOL.md` |
| How the subjective layer works, and its gates | `eval/judge/JUDGING.md` |
| What each criterion asks and what the tiers weigh | `eval/judge/RUBRIC.md` |
| What every run cost and what it may be compared with | `eval/RUNS.md` |
| What is decided and why | `DECISIONS.md` |
| What went wrong and what it taught | `eval/FINDINGS.md` |

When you brief an agent, the brief should be *"read `eval/PROTOCOL.md` and follow it"*, not a
restatement of the protocol. If you find yourself explaining something in a message, that is the
signal it is missing from a file — write it there, then point at it.

When an instruction turns out to be wrong, **fix the file**. That is what makes the next session
start ahead of this one instead of level with it.

## Reflect on the documentation itself

The docs are an instrument like any other here, and the same question applies to them: *what would
it take for this to be wrong?* Review them deliberately, not only when something breaks.

**After any failure, ask which rule should have caught it.**

- If a rule existed and did not fire — the rule is unusable as written. Rewrite it, and record why
  it failed to fire. Several rules here were violated *by the person who had just written them*;
  that is evidence about the rule, not about the author.
- If no rule existed — write one, in the file where someone would look for it, not the file where
  you happen to be.
- If the rule fired and was ignored — it is in the wrong place, or buried under rules that do not
  earn their space.

**Periodically audit the rules the way criteria get audited.** Which have ever fired? Of those,
which fired correctly? A rule that has never fired is either preventing failures silently or is
dead weight, and those look identical from the outside — the way to tell them apart is to ask
whether you can construct a plausible situation where it would fire.

**Check the docs against reality, not against memory.** A file that names a flag, path or command
that no longer exists is worse than one that says nothing: it is confidently wrong, and it will be
followed. Verify before you write, and re-verify anything you are about to depend on.

**Prune.** Every rule that does not earn its place makes the ones that do harder to find. A
document nobody finishes reading protects nothing. When a rule is superseded, replace it — do not
annotate it.

The test of this documentation is not whether it is thorough. It is whether the next session makes
new mistakes instead of these ones.


## The rule audit, 2026-08-15

Run against one working session rather than from memory. **Fired** means the rule changed
what happened, not that it was read.

| rule | fired | correctly? | evidence |
|---|---|---|---|
| 1. A negative control is necessary and not sufficient | **yes** | yes | the g4 grader was green on the reference, on 19 fixture tests and on its own run, with a criterion that could not fail. Only the mutant disagreed (#39) |
| 2. Never infer a process's state from its artifact's state | **yes, twice** | yes | "no files written" said four agents had stalled while they were compiling (#37); later, CPU-time deltas and transcript ages — not artifacts — identified two that really were wedged |
| 3. A pipeline's exit status is the last stage's | **yes** | yes | the `--only` negative control read exit 0 through `\| head`; unpiped it was exit 1 |
| 4. Never compute a mean over a heterogeneous population | **yes** | yes | partitioning `wg-audio48` surfaced a `max_turns` population of one, which is #35 |
| 5. Never quote a value you did not just read | **yes** | yes | re-reading spend from disk gave $604.90 against a recorded $571.15, which is #36 |
| 6. A guard naming an external cause cannot fire on an internal one | no | — | **constructible:** any retry or wait added to the harness. Kept |
| 7. Every reason not to count a failure is a channel a bug can widen | **partly** | yes | it is why `stage.completes` is diagnostic-only rather than quietly excused per-submission |

Rules that fired and were **wrong as written**, now rewritten:

- **"Do not run judge or LLM calls during the build phase."** The useful thing to spawn
  during a build was a *subagent*, which is neither word. It named mechanisms; it now names
  the resource (account session capacity). A rule whose trigger is a list has to be
  re-derived by every reader who meets an item not on it.
- **The diagnostic order in `PROTOCOL.md`** listed four checks, all of which agreed and all
  of which were wrong (#37). It now leads with the descendant scan and adds transcript age
  and CPU-time deltas — the two checks that actually separated two wedged agents from two
  working ones an hour later.
- **"Run the check against something you know is happening."** Sound, and it did not save
  me: the control ran down a path with the same defect as the check. Restated as *a control
  shares the assumptions of the thing it controls unless you deliberately make it not*, with
  the four instances that share the shape (#37).

Documentation defects found by the mechanical sweep, not by reading:

- `RUBRIC.md` named **five judges that do not exist** (#38). Fixed, and the sweep now covers
  aspect ids, criterion ids, `--flags` and file paths across every doc. Everything else
  resolved.
- Two files named `IMPROVEMENTS.md` in different directories, referenced from `FINDINGS.md`
  by name alone, and listed in no index. Now indexed above, and citations must use the path.

**What the audit says about the documents as a whole:** every rule in this file has now
fired at least once except #6, for which a firing scenario is easy to construct. Nothing here
is dead weight.

**The result I did not expect is how the rules failed.** Not by being absent — by having
triggers written in the vocabulary of the incident that produced them.

> **A rule whose trigger is a list must be re-derived by every reader who meets an item not
> on the list. Write the trigger as the RESOURCE or the PROPERTY, never as an enumeration of
> the instances you happened to see.**

"Do not run judge or LLM calls during the build phase" is the cleanest case: it enumerated two
mechanisms when the thing that mattered was one resource — account session capacity — and the
next reader's mechanism was a subagent, which is on neither list. The rule was read, understood
and still had to be re-derived to fire.

The same shape runs through the others. "Two bad signals corroborate each other" enumerated
two; four agreed and were all wrong (#37). `LOCK_HINTS` enumerated the phrasings of an
*external* lock holder and could never match an internal one (#30). A rule stated as its
instances is a rule that fails on the first instance you did not have when you wrote it.

**When writing the next rule, state what it protects, not what went wrong last time.**

## Capture what the instrument DID, not only what it concluded

A judge round stores its scores and its reasoning. Since 2026-08-22 it also stores **which files
it opened**, and that capture was added for an unrelated question — did a larger pack make the
judge read more?

Two weeks later it was the only reason a serious defect could be bounded. Trial ids had reached
25 stored judge packs (#83), and the question *"did any judge actually read the answer key?"*
became a set intersection instead of an unanswerable suspicion: 37 of 63 rounds had the log, 14
had opened a leaking file, 3 held the complete key to their field. The other 26 rounds have no
log and are permanently unassessable.

**#32 concluded that no gate can ask what the judge knew. That is no longer true where the log
exists** — and false everywhere it does not.

> **An audit trail of what a mechanism did is worth more than the confidence you had when you
> built it, because the question it will be asked is not the one it was built for.** Record the
> inputs a component actually consumed, not merely the output it produced.

This generalises past the judge: `runstat` reads process state rather than inferring it from
artifacts (#37, #60), `bot_mutants` records which criteria a mutant flipped rather than only
whether it passed, and `anonymise` writes a manifest of what it dropped — which is what made #62
findable at all, four matrices late.

## Keep the documentation current

`README.md`, `DECISIONS.md` and `eval/FINDINGS.md` must not go stale. Update them **in the same
working session as the change**, not later:

| When | Update |
|---|---|
| A decision is made or changed | `DECISIONS.md` |
| A run completes or its results change | `README.md` status section, with real numbers |
| Something ran and measured nothing | `eval/FINDINGS.md` — a new numbered finding |
| A published number turns out wrong | Correct it, and mark it in `eval/FINDINGS.md` if it was acted on |
| Weights, rubric, or grading change | `eval/judge/RUBRIC.md` **and** the `README.md` grading table |

`README.md` and `DECISIONS.md` state what is true now — **replace superseded content rather than
annotating it.** `eval/FINDINGS.md` is the exception: it is a findings log, and a number that was
published and later proven wrong stays marked there, because someone may have acted on it.

## Decide it yourself unless it is genuinely the operator's call

**Idle time waiting for an approval is a real cost, and it is usually larger than the thing being
approved.** A one-line fix to a gate that had been reporting its build cache for four matrices —
measured at two seconds, with a control proving the obvious alternative fix does nothing — cost
six hours of nothing happening because it was raised as a question.

**A task in `tasks/` is already authorised. Being in the queue IS the go-ahead.** Do not park a
planned task waiting for permission to start it — the decision was made when it was filed, and
asking again spends attention to re-confirm something already agreed. If a task turns out to need
a decision that was not anticipated when it was written, raise *that specific question* and keep
working on everything else meanwhile. Never idle a queue behind one item.

**Decide and proceed** when the change is technical and its mechanism is measured: repairs to
graders, tools, criteria and docs; which field to judge; regime boundaries (they are *recorded*
in `eval/RUNS.md`, not catastrophic); anything reversible; anything whose cost is small against
what it protects. Report what you did and why. If it turns out wrong, it gets corrected — the
same as any other finding.

**Ask** only when the answer is not derivable from evidence:

| Ask | Because |
|---|---|
| It touches the operator's machine or attention — audio, window focus, deleting their files | Not ours to decide, and not recoverable by argument |
| It destroys evidence irreversibly | A regime boundary is recorded; deleted frames are gone |
| Genuinely large spend, or a research direction where the answer changes the conclusion | Their programme, their call |
| The evidence genuinely does not decide it | Otherwise you are outsourcing an inference you could make |

**A question is not free and it is not neutral.** It transfers the cost of a decision you could
make onto someone who has less context than you do about the measurement. Raising it costs their
attention; the wait costs the work.

And if you do ask: **relay the answer immediately.** Asking and then not passing the decision on
is worse than never asking — it spends the interruption and gets nothing for it.

## Rules this project learned the hard way

Every one of these was paid for. Ordered by how much they would have saved.

1. **A negative control is necessary and not sufficient.** `total=0 passed=0` is indistinguishable
   from "correctly failing". Every task needs a positive control proving the grader can go green,
   and ideally an adversarial one.

2. **Never infer a process's state from its artifact's state.** An artifact mid-write is
   indistinguishable from one never written. Check the exit code the process reported. This is the
   most-violated rule here, including by people who had just written it down — treat it as a
   discipline with a failure rate, not a fix.

3. **A pipeline's exit status is the last stage's.** `cmd | tail` reports `tail`'s status. A "pass"
   read through a pipe may come from a command structurally incapable of failing.

   Its sibling: **never write `cmd || echo 0`** on anything you will read as a measurement. The
   fallback turns an error into a plausible in-range number, which is the most dangerous shape a
   broken check can take. `pgrep -c` does not exist on macOS; wrapped that way it reported zero
   agents while four were running, twice. Let failures be visible and count with `wc -l`.

4. **Never compute a mean over a population you have not established is homogeneous.** Partition by
   terminal status first and report `n` per group. A mean across four real runs and four aborted
   ones is arithmetically correct and describes nothing.

5. **Never quote a value you did not just read from its source.** Not from memory, not from an
   earlier message — the underlying evaluator may have changed since.

The single pattern behind most findings in this repo: **a mechanism that runs, reports success, and
measures nothing.** When something passes, ask what it would have taken for it to fail.

Two refinements that pattern does not cover:

6. **A guard whose trigger names an external cause cannot fire on a failure with an internal one —
   and looks like a fix.** When you add a retry, a wait or a lock, name the party you are waiting
   for and check that it is not you (#30).

7. **Every reason not to count a failure is a channel a bug can widen.** All the defects here fail
   closed except #31, which would have excused genuine failures because a matcher and a log shared
   a buffer. A fail-closed defect costs you trials; a fail-open defect costs you the result.

8. **Change one thing. Before attributing an effect to a variable, list every variable that
   differs between the two things you are comparing.** Not "did I change anything else on
   purpose" — enumerate them, mechanically, from the artifacts.

   The budget-cap hypothesis has now moved twice, and **both moves came from a comparison that
   changed more than one thing, made by someone who knew this rule.** The first tested the effect
   on the one game with no headroom (#33). The second compared a capped 2D-arena trial with an
   uncapped 3D-arena one and read the doubling as a cap effect, when the task, the turn limit and
   the cap had all changed together.

   That is not carelessness, and treating it as carelessness is why it recurred. **A
   multi-boundary comparison is dangerous precisely because it is available, cheap, and produces
   a conclusion indistinguishable from a clean one.** The defence is mechanical: diff the
   artifacts. Diffing a rendered prompt against the stored one is what caught #41, in the setup
   for the very experiment meant to settle #33.

   **The qualifier, and it matters as much as the rule: hold variables constant, EXCEPT a
   ceiling that may be binding. Raise those, and let the measurement tell you whether they were
   binding.** A constant that is itself a constraint is not a control.

   Raising a ceiling is not the same class of change as altering a variable that acts: a higher
   limit can only remove a constraint, never impose one. It is also self-diagnosing, which is
   what makes it safe — the result reports whether the old ceiling mattered:

   | outcome | what it establishes |
   |---|---|
   | lands **below** the old ceiling | the ceiling never bound; the comparison was effectively single-variable after all |
   | lands **above** it | the earlier runs were bound by it — a finding in itself, and one that reinterprets their "completed" status |

9. **A repeated identical measurement across independent subjects is not corroboration. It is
   the signature of a shared cause, and the shared cause is usually the instrument.** Six
   independent TypeScript submissions each scoring exactly 6/14 read as a stack characteristic;
   the cause was `$TMPDIR` deleting 80% of their toolchain between building and grading (#45).
   Six arena submissions failing two criteria with byte-identical evidence read as a task
   property; the cause was a bot that stood still until it died (#46).

   The protected property is **independence**, not repetition: when subjects that share nothing
   but the instrument agree exactly, what they are reporting is the instrument.

10. **Hold the machine, not just the configuration — and check it, per arm, before spending.**
    Every variable-control rule here is about flags, prompts and starters. The largest confound
    this project has measured was none of those: a system daemon pegged for ten days gated
    `execve` of freshly created binaries, so the two arms that link new binaries shipped work
    their agents had never been able to compile or run, and the two that run pre-existing
    binaries were fine (#49).

    **A run is not a controlled experiment merely because it is one command.** Partition by
    terminal reason *and* by anything about the world that changed while it was in flight —
    including a date, which no aggregate here has ever been partitioned by.

11. **Read what the subject said about its own work before grading it.** Four agents wrote a
    paragraph headed *"What I could not verify — and why"* naming the exact mechanism behind a
    whole run's spread. `agent.final_text` is in every record; nothing reads it and no gate
    looks at it. A grader that ignores the subject's own account will keep re-deriving what the
    subject already told it.

12. **Every rule here says HOW to check. None says WHERE.** A correct method pointed at the
    wrong place produces a confident answer: `runstat.py` obeyed `-mmin, never -newermt`
    faultlessly against a path that no longer existed, and reported "no writes in last 10 min"
    through a build writing 2555 files in ten minutes (#60). **The address is an input to the
    check.** When a path, root or endpoint is spelled in two files, assert them equal in code —
    a comment promising they match is not a defence.

    **The corollary, measured over one session on 2026-08-23: rule 12 fires far more often
    against a person than against a tool, and it always looks like a result.** Five instances
    in a day, each a sound method aimed at an address nobody had verified:

    | what was aimed | at what | what it returned |
    |---|---|---|
    | an append to a task file | a filename guessed from a queue listing title | created a second, malformed task |
    | `packcheck --run` | a run *name* where a *path* was required | exit 0, "clean", on a run never opened |
    | `grep -c ... \|\| true` | bsdtar rejecting `--wildcards` | `0` for all 20 rows |
    | `endswith("project.godot")` | an AppleDouble `._` sidecar | "0 of 20 carry the defect" against a true 4 |
    | a monkeypatched module constant | a value already derived at import | linted the real tree while claiming a bad root |

    Three of the five returned **the same wrong answer for every subject**, which is what made
    them look like findings rather than bugs — rule 9 pointed at your own instrument.

    > **Before believing a census, prove the extraction on one case you already know the answer
    > to.** Not the whole set: one row whose true value you can state in advance. Every one of
    > these would have died on first contact with a single known-good example.

    The tell is uniformity. **A census that returns one value across a population it exists to
    discriminate is reporting the instrument, not the population.**

13. **Guard the RESOURCE, and verify on the path that actually holds it.** Tasks #14/#15
    were marked complete having guarded the capture and test recipes — already offscreen,
    already silent — while `just run` opened a window with audio on the operator's desk. The
    verification tested the guarded path and reported the defect unreproducible (#61).

    Its companion: **an accepted-but-ignored flag is worse than an unsupported one.** Unity's
    standalone player takes `-disable-audio` without error and does nothing with it, so
    `exit 0` meant "the command ran" and was read as "audio is off". An unsupported flag
    fails loudly; this one is indistinguishable from a working guard by anything a script
    can see.

14. **A control run after the fix tests the fix, not the claim.** Verifying a defect someone
    else reported means establishing the state first — mtime, `git diff`, or reproducing the
    broken behaviour — because a repaired binary can only agree with your independent
    measurement. This is the shared-assumption failure (#37) with a time axis instead of a code
    path, and it produced a confident "the tool is sound" two minutes after the tool was fixed
    (#60).

15. **A mutant asks whether a check can fail. Only a variant asks whether it can still pass.**
    A mutant removes the mechanism a check names; it cannot manufacture an input the check
    mishandles. Every false negative adjudicated in this project has been of the second kind —
    sixteen in one sweep, then three more under a harder task, then two more (#46). Both halves
    now run in `judge/bot_mutants.py`, because a discipline you have to remember is one that
    will fail.

    Worked example: the no-cap Tetris trial. The $48 run used **232 of its 250 turns**. Holding
    the limit at 250 "for cleanliness" would truncate an uncapped run that wanted 300, return
    ~$49, and support the conclusion *"the stated budget was pulling work short"* when the turn
    limit was — **a confident answer to a question the experiment did not test**, which is the
    exact failure it exists to avoid. At 1000 turns every outcome is interpretable; at 250 one of
    them is not.

16. **A weighted result must state what reweighting would change it — and a weight that cannot
    change anything is reporting that its tier has no variance, not that the weight is safe.**
    Every free parameter in an aggregate is a claim until someone varies it. `overall =
    0.31*tier1 + 0.69*tier2` was quoted in four documents and derived in none; sweeping it over
    68 stored trials moved **no ordering at any weight**, which sounds like a clean bill of health
    and is not. In 7 of 10 groups tier 1 returned a **single value across every submission**, so
    the weight was inert for the reason that matters least: there was nothing for it to weigh
    (#92).

    The check is free, it is offline, and it comes out either way — which is what makes it worth
    running before publishing any aggregate. `judge/weight_sensitivity.py` is the instance; the
    rule is about **any parameter chosen by judgement that a published number depends on.**

    Its companion, learned in the same hour: **sweep the OPEN interval.** The first version swept
    `[0,1]` and reported flips on 3 of 10 groups, every one of them at the endpoint where a tier
    is discarded outright — not a weight anyone would choose. *A check that fires where nothing is
    wrong spends exactly the attention that a check firing correctly needs.*
