# Documentation and rubric defects

A document naming something that does not exist is confidently wrong and will be
followed. Prose is executed by a person, and a person gets no argparse error.

> Index and the distilled rules: `../FINDINGS.md`


## #21 — an LLM judge's verdict stability is a property of the ARTIFACT, not the rubric

This is the most transferable result this project has produced, and it generalises to
any rubric-based LLM evaluation, not just game grading.

### The measurement

The same judge, the same thirteen binary criteria, the same model, run six times over
each of two submissions with nothing changed between runs:

| submission | score min–max | spread | instability | criteria contested |
|---|---|---|---|---|
| a good agent-built Pong | 1.000 – 1.000 | **0.000** | 0.000 | 0 / 13 |
| the `broken` control fixture | 0.000 – 0.308 | **0.308** | up to **0.462** | 5 / 13 |

On the contested artifact, **six of thirteen criteria disagreed with themselves on
presentation order within a single run**, and the aggregate score varied by 0.308
across runs — roughly a third of the scale.

Crucially, the *same criteria* behave differently on the two artifacts.
`code.function_size`, `code.magic_numbers`, `code.comments` and `code.robustness` were
rock-solid 6/6 on the good submission and flipped on the broken one. Nothing about the
rubric changed.

### The result

**Criteria agree when the answer is obvious and diverge when it is borderline.**
Stability is therefore not a property of the rubric, the model, or the prompt — it is a
property of how clear-cut the artifact is.

Two consequences follow, and both are traps:

1. **Measuring judge reliability on clear-cut fixtures systematically overstates it.**
   A validation suite built from an obviously-good and an obviously-broken example will
   report high agreement, because those are exactly the cases where agreement is cheap.
2. **The reliability you measure is highest precisely where you need the judge least.**
   If the artifact is unambiguous, a script can usually classify it. The judge earns
   its place only on borderline work — and that is where its verdicts are least stable.

### We made this exact error, in our own validation gate

The gate for shipping the judge tier was a discrimination test over three fixtures:
`ref_pong` (good), `ref_adversarial_pong`, and `broken`. It passed cleanly — 0.92 /
0.62 / 0.23, monotone separation — and `ref_pong` came back with **instability 0.000**.
That figure was reported as evidence the judge was sound.

It was evidence of nothing except that `ref_pong` is unambiguous. The tier was
validated on the easy end of its own range, and the number that looked most reassuring
was the least informative one in the set. The failure only surfaced when a variance
study was run against a *contested* artifact, and by then the tier had already been
weighted and reported.

### What to do instead

* **Validate a judge on borderline artifacts, not on the extremes.** Deliberately
  construct submissions that sit near the boundary of each criterion. If you cannot
  construct them, you do not yet know what the criterion means.
* **Report per-artifact stability, never a single global reliability figure.** A mean
  instability across a fixture set is dominated by whichever fixtures were easy.
* **Treat a low instability reading as a statement about the artifact.** It says the
  case was clear; it does not say the instrument is good.
* **Sharpening the questions does not fix it.** Three criteria here were rewritten to
  remove unstated thresholds. On the contested artifact the corrected rubric was *more*
  unstable than the original (0.308 vs 0.154). Better questions are still worth having;
  they are not a route to stability.

### Why the tier was dropped from the score

Two independent arguments, kept separate because they fail differently:

1. **It cannot reorder anything.** Bounded contribution 0.10 against a tightest
   adjacent gap of 0.0622 on the deterministic tiers. True regardless of noise.
2. **Its aggregate is noisiest exactly where it would matter** — the result above.
   True regardless of weight.

The judge still runs on all 24 matrix submissions and its per-criterion verdicts and
evidence strings are reported. What is discarded is the *aggregate number*. The
per-criterion output remains genuinely useful: on `broken` it correctly and stably
failed eight criteria, quoting the fixture's own docstrings and the pixel-identical
frames. **The detail was informative; the total was noise.**

---


## 38. A document that names a component which does not exist

`RUBRIC.md` — the file that is supposed to be the subjective layer's contract — carried this
table, written 2026-08-14:

| aspect | judge |
|---|---|
| Gameplay & fun | `fun` |
| Game feel & responsiveness | **`feel`** |
| Difficulty & tuning | **`tuning`** |
| Audio | `audio` |
| Visual coherence | **`look`** |
| UX & onboarding | `ux` |
| Idiomatic stack use | **`idiom`** |
| Code quality | **`code`** |

`aspects.py` defines five: `fun`, `ux`, `audio`, `idiomatic`, `architecture`. **Five of the eight
names in the contract do not exist**, one exists under a different name (`idiom` / `idiomatic`),
and one that does exist (`architecture`) is absent from the table. `field_sweep.py` takes
`choices=sorted(ASPECTS)`, so `--aspects feel` is rejected by argparse.

### Why this is its own entry and not filed under carelessness

Every other defect in this catalogue is a mechanism that runs and measures nothing. This one does
not run at all — and it is worse than saying nothing, because **a document is executed by a
person, and a person does not get an argparse error.**

The failure mode is concrete and was one step away. The brief for this session said: *"if `fun`,
`feel`, `ux` and `idiomatic` produce the same ordering, that is one judge with four names."* That
instruction was written from the table, names a judge that cannot be run, and would have produced
either a crash or — worse — a three-aspect independence result silently reported as four. An
independence gate is precisely where a phantom aspect does damage: the gate's whole job is to
count how many *distinct* judges there are.

Note the direction of the error. The table is not out of date; it was **never** true. It describes
the layer that was designed rather than the layer that was built, and nothing connected the two.

### What made it findable, and what did not

It was not found by reading `RUBRIC.md`, which is internally coherent and reads well. It was found
by asking the code what it accepts:

```
python3 -c "from aspects import ASPECTS; print(sorted(ASPECTS))"
```

That is the same move as #32, where the judge pack's answer key was found by **listing the
directory** rather than reading the code that filled it. Two instances now: when a document
describes a component, verify it against the component, not against the document's own coherence.

### Swept for the same defect

The check is mechanical, so it was run across every doc rather than only the one that failed:

| layer | result |
|---|---|
| aspect ids | `RUBRIC.md` wrong (fixed); `JUDGING.md`'s implemented table correct — it lists exactly the five |
| criterion ids in `RUBRIC.md` vs the three bots plus `static.py`/`audio.py`/`checks.py` | all present, except `look.feedback` and `look.legible`, which are retired vocabulary from the withdrawn 13-criterion judge and are labelled as withdrawn |
| `--flags` named in any doc vs every harness argparse | all resolve; the one exception is Godot's own `--headless` |
| backticked file paths in any doc | all resolve |

So the defect was confined to one table, and the sweep is the evidence for that rather than an
assumption. **Run the sweep after writing any doc that names code.** It costs seconds and it is
the only check in this project that can be complete.

---

---

## 70. A trial id is not a key, and two runs' `g2_tetris3d__unity__t1` are different games

*(The two runs are `wg-matrix-2026-08-13` and `wg-audio48-2026-08-14`.)*

A re-film was about to be avoided by a clever, free substitution: the judged
`wg-matrix-2026-08-13` field had one submission captured at 420x640 against a 640x400 field,
and `wg-audio48-2026-08-14` held a 640x400 capture of *the same submission id*. Use those frames
instead. No filming, no regime mix, no cost.

**Pinned before relying on it, and the pin failed.** The two are not the same work:

| | `wg-matrix-2026-08-13` | `wg-audio48-2026-08-14` |
|---|---|---|
| files in submission | 266 | **442** |
| files present in only one | 6 | **182** (a whole `Assets/Audio/` tree) |
| same path, different content | — | **27**, including `Assets/Sim/Sim.cs` |
| prompt | 5,889 bytes, **0** audio mentions | 7,507 bytes, **8** audio mentions |

`wg-audio48` set an audio requirement that `wg-matrix` did not. **The id denotes a different
task, a different prompt and different code.** Substituting those frames would have put a
different game's pixels into the judged field — and it would have looked completely fine,
because the id matched and the geometry matched.

> **An id is a name within a run, not an identity across runs.** The instinct that "the same
> submission was filmed twice" is the same instinct that read "IMPROVEMENTS iteration 1b" as
> unambiguous when two files share that name — a defect this project already fixed once by
> requiring paths, recurring in a namespace nobody had thought of as a namespace.

### It had already cost a round of confusion

#59 cited `g2_tetris3d__rust__t0` filming at 768x576 with no run named. Measured from PNG IHDR
bytes across the archive, **four geometries exist and each belongs to a different run**:

| id | geometry | run |
|---|---|---|
| `g2_tetris3d__unity__t1` | 420x640 | `wg-matrix-2026-08-13` |
| `g2_tetris3d__rust__t0` | 768x576 | `wg-audio48-2026-08-14` |
| `g2_tetris3d__ts__t1` | 720x540 | `wg-audio-2026-08-14` |
| everything else (32) | 640x400 | all runs |

Two people reading the same finding disagreed about which submission diverged, and **both were
right about different runs.** The third case was named by neither.

### Fixed

- #59 and the citations in #66, #67 and #68 now name their run.
- `docstat --sweep` fails on a trial id cited with no run in section scope, as a **ratchet**: the
  count may fall, never rise. An allowlist of specific ids would be a channel a bug can widen
  (rule 7); a number that can only decrease is not.
- The ratchet was first set to 20 against an actual 18, and **a planted bare id passed**. A guard
  with headroom is not a guard. It is set to the exact count and pinned in both directions.

### The same defect again, in a second namespace: a pack LABEL is not a key across rounds

2026-08-22, verifying the Unity refutation (#76). A reviewer pooled scores **by pack label** over
two rounds, resolving them through only the **first** round's mapping — and got a clean, plausible
table putting Unity 1st on `g3_arena` where the correct answer is 3rd.

`build_pack` **reshuffles the label→submission mapping independently for every round**; that is
the entire point of an order seed. So `A` in round 0 and `A` in round 1 are different
submissions, and averaging them averages different games' scores together. The result does not
look wrong — it looks like a tidy contradiction of a correct finding.

> **Two namespaces now, same rule.** A trial id is a name within a run. A pack label is a name
> within a *round*. Neither is an identity, and both produce plausible tables when treated as one.
>
> **Any analysis joining scores across rounds must resolve every score through its own round's
> mapping.** Every stored round already carries `submissions[].submission`, resolved at judging
> time — use that field, never `label`.

**Guarded, because it is greppable**: `docstat --sweep` fails any module that reads multiple
rounds (a `rep*`/`seed*` glob) and also indexes `["label"]`, which is wrong by construction.
Pinned both ways.

**What made the disagreement resolvable** is worth recording next to the error. The refutation had
controlled for the n confound — tetris restricted to consecutive round-pairs, Unity topping 6 of 6
windows at n=2 — rather than dismissing it. A result that has already survived its most obvious
objection can absorb a contradiction and locate the fault; one that has not simply becomes a
standoff.

**The re-film decision reverts: the substitution is invalid.** Either film, accepting that it
creates a *third* geometry for that id, or do not judge that field on frames — which the parity
gate now enforces without anyone remembering to.

---

## 80. Two durable records that quietly lost content: a shell-substituted evidence string and an overwritten task

Both on 2026-08-22, both writing to a record meant to outlive the session, both silent.

### The evidence string that executed itself

Closing task 07 with `tasks.py done 07 "...so \`just lint\` and \`just verify\` answer from the
code while \`just check\` keeps its warm cache..."` — written inside double quotes, so the shell
treated each backticked phrase as **command substitution**. `just` ran three times in a directory
with no justfile, printed `error: no justfile found` to stderr, and substituted **empty strings**.

The stored record became *"so / answer from the code while  keeps its warm cache"*. Three phrases
gone. `tasks.py` reported success, because from its side nothing failed: it received a string and
wrote it faithfully.

> **The corruption happened before the tool that owns the record ever saw the data.** No amount of
> validation inside `tasks.py` would have caught it — the string it was handed was already wrong.
> The three `error: no justfile found` lines were the only signal, and they looked like noise from
> an unrelated command.

Prose destined for a durable record should be written **to a file**, not passed through a shell
argument. Where it must go through a shell, single-quote it.

### The task that was overwritten by a concurrent writer

`tasks.py add` computed the next id by reading the directory and then called `write_text`, which
truncates. Two agents adding a task at the same time both computed `12`, and **one task vanished
with no error from either side.**

Fixed: exclusive creation (`open(..., "x")`), and on collision take the next free id and retry —
checking the **id**, not the filename, because the same number with a different slug is still the
same task. Pinned: a decoy squatting id 18 is left intact and the new task lands on 19.

### What the pair have in common

Neither was a bug in the thing being written to. One was corrupted upstream by the shell; the
other by a writer that never asked whether the destination already existed. **A record is only as
durable as the weakest step in the path that reaches it**, and both weak steps were outside the
component that looked responsible.

This is the same shape as #62 — a field nothing read — but worse in one respect: there, the data
was present and ignored. Here the data was **destroyed**, and the destruction left a success
message behind.

### A game is not a field either: the same defect one level up again

2026-08-22. `fun`'s rounds were reported as having read pre-repair telemetry, and tier 3's only
positive result (#68) was briefly marked compromised. **It was not.** The wrong field was
inspected.

`g2_tetris3d` is not a field. It is a **game with four stored fields in different states of
repair**:

| run | representative telemetry |
|---|---|
| `wg-matrix-2026-08-13` | **0 of 8** |
| `wg-audio-2026-08-14` | 0 of 3 |
| `wg-audio48-2026-08-14` | **8 of 8** — re-driven 2026-08-17, deliberately, before the judge round |

The rounds read `wg-audio48`. Established by **fingerprint**, because the stored round does not
record which run it judged: all **7 of 7** `quiet_fraction_of_run` values and **4 of 4**
`events_per_second` values quoted in #68's evidence appear in `wg-audio48`'s stored telemetry, and
**none** appears in `wg-matrix`'s.

> **A trial id is not unique across runs; a GAME is not unique across runs either.** Same rule,
> third namespace. And the failure mode is the one this session keeps producing in new costumes:
> **a claim true of one population, quoted about another.** It appeared as code-vs-evidence in
> `DECISIONS.md` — "the confound is gone by construction" described the code and was read as
> describing the field — and immediately again as evidence-vs-evidence across two runs of the
> same game.

**Fixed at the source rather than by being more careful.** `run_field` recorded the game and not
the run, so no stored round could answer "which field was this?". `build_pack` had the run in its
mapping record all along; `field.py` now carries `mapping["run"]` into every stored round. The
fingerprint match was only possible because the evidence quoted numeric telemetry — a round whose
aspect cites no numbers would have been unresolvable.

**What made this recoverable was insisting the answer come from the round files rather than from
either party's reasoning.** Both readings were coherent, both were argued from real evidence, and
one was wrong. The values decided it in a single query.

---

## 86. What a round cannot say about itself, and why prose is not a substitute for a field

Two fields were missing from every stored judge round, and both turned out to matter within days
of being noticed:

- **`files_opened`** was added in task 09 to answer an unrelated question — does a bigger pack
  make the judge read more? It is the only reason #83 could be bounded to 14 compromised rounds
  instead of a class-wide suspicion.
- **`run`** was absent, so a round named only its **game**. `g2_tetris3d` is four stored fields in
  different states of repair, and that gap produced a false report that tier 3's only positive
  result was compromised.

The second was recovered by matching numbers quoted in `fun`'s evidence prose against stored
telemetry — 7 of 7 quiet-fractions and 4 of 4 events-per-second, unique to one run.

> **That rescue was a property of one aspect's writing style, not of the record.** `ux` and
> `idiomatic` quote no telemetry figures. In the same position the question would have been
> unanswerable, and the false report would have stood. **Prose is not a substitute for a field:**
> it happens to contain the answer, for aspects that happen to cite numbers, until it does not.

### The question worth asking of any record

**If someone asks in a month what this round saw, which parts of the answer are gone?** Applied
to a judge round, everything below was in that category and is now recorded:

| field | why it is not reconstructible later |
|---|---|
| `run` | the same game exists as several fields in different repair states |
| `sees`, `blind_language` | which evidence channels the judge was given, and whether paths were neutralised |
| `brief_sha256`, `brief_chars` | **the brief is not fixed** — a geometry note was added to it on 2026-08-22, and rounds either side saw different text. This is why task 08 had to re-run seven repeats rather than top up four, a decision made by argument that a hash makes a comparison |
| `evidence_counts` | how much of each kind of evidence each label actually had |
| `capture_geometry` | frame sizes, which #59 turned on |
| `knowingly_truncated` | whether the completeness gate was deliberately bypassed |
| `max_turns`, `per_call_budget_usd` | limits are visible to the callee and instruct it (#33) |
| `judged_at` | which side of a repair a round sits on |

`field_sweep.warn_rounds_without_provenance()` reports stored rounds that predate this: 10 of 10
in the tetris judge round, 12 of 12 in the cross-game sweep. They are not wrong — they are
**unfalsifiable about their own inputs**, which is the same defect as an aggregate without its
scope, one level down.

### The general form

**Capture what the instrument did, not only what it concluded** — and the test of whether a field
is needed is not whether you can imagine using it, but whether its absence would be recoverable.
`run` and `files_opened` were each cheap to add and each answered a question nobody had when they
were added. Neither would have been recoverable from the conclusion alone.

---

## 93. `suite.json` describes the last thing written into the directory, not the run

Found while executing task 11. `game-research-gpt` freezes its evaluated template as
`evaluation/baselines/template-v3-{tree.json,source.tar.gz}` and retains a protocol hash
recorded before the earliest completed outcome. Asking the same question here — *what is
this project's immutable record of what a stored run was configured to be?* — the answer is
`suite.json`, and it is not immutable.

### The measurement

Comparing each run's `suite.json` against the reports actually on disk, over all 18 stored
run directories:

| run | manifest says | on disk |
|---|---|---|
| `wg-matrix-2026-08-13T14-02-50` | 2 stacks x 1 game x 2 = **4 trials** | 4 stacks x 3 games, **24 reports** |
| `wg-audio48-2026-08-14T19-55-47` | 4 stacks x 1 game (`g3_arena`) x 2 = **8** | 4 stacks x 2 games (`g1_pong`, `g2_tetris3d`), **16 reports** |
| `wg-audio-2026-08-14T12-29-42` | 4 stacks x 3 games x 2 = **24** | 4 stacks x 2 games, **11 reports** |

Seven of eighteen diverge. Four of those are runs that produced no reports at all, where a
manifest describing an intent that never completed is defensible. The three above are not.

### The mechanism, and the tell nobody was looking at

A partial re-run launched into an existing run directory **overwrites `suite.json`**. The
canonical manifest then describes the re-run, and the run it is named for has no manifest
at all.

Each of the three carries a self-evident tell that no check reads — **the manifest's own
`started_at` contradicts the directory name it sits in**:

| run directory | `started_at` inside `suite.json` |
|---|---|
| `wg-matrix-2026-08-13T14-02-50` | `2026-08-14T00:43:58` |
| `wg-audio48-2026-08-14T19-55-47` | `2026-08-15T12:52:52` — **a day later** |
| `wg-audio-2026-08-14T12-29-42` | `2026-08-14T15:29:43` |

`wg-audio48` is the worst of the three: its `suite.json` names `g3_arena`, a game with
**zero reports in that directory**. A reader establishing that run's configuration from its
manifest would get the games wrong, the trial count wrong, and the date wrong.

### What is NOT affected, stated so it is not re-litigated

**#68 stands.** `DECISIONS.md` records it as verified against `wg-audio48` by matching
stored telemetry values — 7 of 7 `quiet_fraction_of_run` and 4 of 4 `events_per_second`
figures. That verification read per-trial telemetry, never `suite.json`, so the manifest
defect cannot touch it. This is the 2026-08-22 fingerprint check paying for itself a second
time, against a defect it was not built for.

Two of the three directories also retain the real manifest under another name
(`wg-audio48/suite-full-matrix.json`) or a prose note (`wg-matrix/rerun-note.json`, which
documents the four re-run trials honestly and completely). **Someone noticed, twice, and
rescued the content into a file with a non-canonical name** — while leaving the name every
tool reads pointing at the wrong thing.

### The rule existed and could not fire

#86 added per-round provenance for judge rounds. The pack builder writes
`files_dropped_for_length` into every manifest. And #77 states the principle outright:

> The stored manifest of the original build is the only record of what the filter decided
> when it was still correct, which is a reason to keep manifests rather than just scores.

That is exactly this defect, written down before it was found here. It did not fire because
its trigger names **judge packs** — the artifact whose manifest was being discussed at the
time. Run manifests are the same object under a different name, and the rule reads as though
it is about something else.

This is the `AGENTS.md` meta-rule with a third instance: *a rule whose trigger is written in
the vocabulary of the incident that produced it must be re-derived by every reader who meets
an item not on the list.* The protected property is **any durable record of what a
measurement was configured to be**, not the two artifact types that happened to have one.

### What would have caught it

An equality assertion between the manifest and the directory, of the kind #60 argues for:
the address is an input to the check, and here the manifest and the artifacts are two
spellings of the same run that nothing asserts equal. Filed as a task rather than fixed
here, because writing run manifests is harness behaviour and a bad repair to it is worse
than the defect.

## 99. A second copy of the skills for an agent that was never here, never once in sync

Task 27. `.agents/skills/` held a duplicate of this project's skills, tool-name-substituted
for the Codex CLI. It was tracked in git from the first commit. Nothing in any document,
script or tool referenced it — `docstat.py` globbed `.claude/skills/` and `prune_scan.py`
carried an explicit `MIRROR = ".agents/"` exemption so the duplicate would stop crowding out
everything else it reported.

### The question the artifacts could not answer, and the artifacts that answered it

The ticket said the deciding question — *is a Codex-run sibling of this project actually
maintained?* — was not derivable. Three measurements decided it.

**1. The sibling is not a consumer.** `~/Documents/heavenstudio/game-research-gpt` exists and
is a genuine independent attempt at this research question (iteration 12 in
`eval/IMPROVEMENTS.md`). It has **no `.agents/` directory, no `SKILL.md` anywhere, no root
`AGENTS.md`, and zero occurrences of "codex" in its readable surface** — `README.md`, `docs/`,
`scripts/`, `template/AGENTS.md`. Its only agent-convention file is `template/AGENTS.md`. It
cannot be reading a skills tree it does not have.

**2. The mirror was never in sync — not on the day it was created.** From `git show --stat` on
the initial commit:

| file | `.claude/skills` | `.agents/skills` |
|---|---|---|
| `add-game/SKILL.md` | 126 lines | **87** |
| `tasks/SKILL.md` | 146 lines | **absent** |
| `prune/SKILL.md` | added later | **never added** |

So this is not a maintained fork that decayed. The 39 lines `add-game` was short at birth are
the whole *"Assert the prompt structure — run the tool, do not eyeball it"* section: the
`prompt_guard.py` procedure that exists because a mouse-aiming clause written for the 3D arena
landed in Pong, Tetris and the platformer and would have contaminated the one experiment whose
entire design was a single variable (#41). A non-Claude agent following the `.agents/` copy is
told to eyeball what this project measured that it must not eyeball.

**3. Zero content-bearing edits, against six.** Every commit touching either tree, counted after
the initial import so the import itself is not doing the work:

| tree | commits | after the import | of those, changed a procedure |
|---|---|---|---|
| `.claude/skills/` | 8 | 7 | **6** — the seventh is the mechanical frontmatter quoting of task 35 |
| `.agents/skills/` | 3 | 2 | **0** — one snapshot copy of `tasks` that went stale the same night, and that same task-35 fix, which was applied to both trees by a change that was about YAML |

The `tasks` snapshot is the sharpest instance. It was copied in at 23:54 on 2026-08-22, and the
two subsequent edits to `.claude/skills/tasks/SKILL.md` — 00:03 and 00:17, twenty-three minutes
later — did not reach it. The `.agents` copy was
still missing the section headed *"The queue is shared, and lives in the main checkout"* —
the section that exists because three agents each filed a "task 27" in one hour and every
exclusive-create guard succeeded against its own copy (#94). **The stale copy of the skill was
missing exactly the lesson of the failure that a stale copy causes.**

The mirror also carried two statements that are simply false here: that `--max-turns` and
`--permission-mode` belong to the Codex CLI (`eval/runner.py:510,519` passes both to `claude`,
and `docstat.py`'s own `FOREIGN_FLAG_PREFIXES` comment says so), and a capacity probe spelled
`Codex -p "Reply READY." --model haiku`, which is not a runnable command.

### What was done

Deleted, not synced. Syncing buys one day: three of six copies were identical on the morning of
2026-08-23 and four of six differed by the afternoon, because `tasks` drifted while the ticket
sat open. A mirror with no reader has nothing pulling it back into line.

`docstat.py --sweep` now fails on **any `SKILL.md` outside `.claude/skills/<name>/`**. The
trigger is the address, not the directory name, so it fires on `.codex/`, `.cursor/`, a bare
`skills/` or a wrong nesting depth without being rewritten — the meta-rule about triggers
written as enumerations.

### The check was vacuous on its first run, and only the positive control said so

Written with `glob.glob(ROOT + "/**/SKILL.md", recursive=True)`, it reported clean against a
deliberately planted `.agents/skills/run-matrix/SKILL.md`. **Python's `glob` does not descend
into dot-directories**, and every skill in this project lives under one, so the pattern returned
zero paths — including the seven authoritative ones — and the loop passed by iterating over
nothing. It is the house pattern exactly: a mechanism that runs, reports success, and measures
nothing.

Two consequences. The check walks with `os.walk` instead. And it now reports finding *no*
`SKILL.md` at all as a failure in its own right, because that is the one result a
correctly-addressed check and a misaddressed one cannot otherwise be told apart by (#60).

The same trap is live for anything else asking a question about the skills: `project_docs()` in
`docstat.py` uses `glob` and has therefore **never seen a file under `.claude/`** — its "108
docs checked" excludes all seven skills. Task 37's planned frontmatter gate globs the same way
and would pass vacuously.

### Controls

| control | expected | got |
|---|---|---|
| planted `.agents/skills/run-matrix/SKILL.md` | exit 1 | exit 1 |
| planted `.claude/skills/run-matrix/nested/SKILL.md` (right root, wrong depth) | exit 1 | exit 1 |
| `SKILL.md` planted under `eval/runs/` (stored data) | exit 0 | exit 0 |
| `SKILL.md` inside a checkout under `.claude/worktrees/` | exit 0 | exit 0 |
| the walk enumerates the real skills | 7 | 7 |
| repaired repository | exit 0 | exit 0 |

The last four are variants, not mutants: they ask whether the check can still *pass* on input
it must not fire on, which is the half that catches false positives (rule 15).

---


## 112. The repaired capture page had a second live copy, and no commit in the project's history had ever touched it

Task 31 repaired three defects in the TypeScript capture page (#101) and, in the same session,
filed task 48 because `template-ts/src/view/harness.ts` carried the identical pre-fix code.
That ticket was right, and the interesting part is not the duplicate — it is **why a duplicate
of a defect under active repair could sit in a tracked, buildable, `just verify`-green tree
without anything noticing.**

### The state, established in the real page before anything was changed

The seam `evaluateInCapturePage` was added first and nothing else, so the reading is of the
page the harness actually builds, not of a replica that would share its assumptions (#37):

| property | `template-ts`, pre-fix | after the port |
|---|---|---|
| `location.origin` | `"null"` | `http://harness.localhost` |
| `document.baseURI` | `about:blank` | `http://harness.localhost/` |
| `fetch('./index.html')` | **THREW: Failed to parse URL** | `status 200` |
| `window.__determinismApplied` | absent — the init script never ran | `true` |
| `Math.random` is the injected LCG | **false** | `true` |
| `performance.now()` across a 60 ms wall sleep | **130.9 → 194.4** | `0 → 0` |
| `Date.now()` | `1787476067666` (real epoch) | `0` |

The clocks were **not frozen**. They were on wall time, in a harness whose stated purpose is
reproducibility — #101's shape reproduced independently, in a second tree, a day later.

### What made it invisible, in numbers

- **`wholegame.py` cannot reach it.** `STARTERS = HERE / "starters" / s` is the only starter
  address in the file, and no `run` subcommand takes a template path. Confirmed by reading, not
  assumed: no whole-game number is affected, then or now.
- **One executable reference to `template*/` exists in the whole repository** —
  `eval/run-bakeoff.sh`, driving `runner.py --template`. The spec-change suite it feeds has not
  been run since **2026-08-12**; every run since is `wg-*`.
- **0 of the 105 commits since the initial import touched any `template*/` directory. 6 touched
  `eval/starters/`.** That is the same asymmetry as #99 (0 content-bearing edits against 6) with
  a different subject.
- **No gate compares the two.** `starter_parity.py` defaults to `eval/starters` and measures the
  four *stacks* against each other, never a stack against its own second tree. `verify_blind.py`
  takes explicit paths. `docstat.py --sweep` reads `template-ts/AGENTS.md` for names that do not
  resolve, which a stale-but-coherent document passes.

### Where this is NOT #99, and it changes what can be done about it

`.agents/skills/` was a **copy**: one source of truth, one degraded duplicate, so "sync or
delete" were the only two options and deletion won. These two trees are a **fork**. Measured
across the pair, excluding `node_modules`:

| | count |
|---|---|
| files only in `template-ts` | 3 |
| files only in `eval/starters/ts` | 7 |
| shared paths, byte-identical | 15 |
| shared paths, differing | 18 |
| changed lines across the shared paths | **1119** |

`template-ts` is a finished Pong; `eval/starters/ts` is a game-agnostic placeholder with a probe
and film contract. Most of that 1119 is *supposed* to differ. **So no content-parity gate can be
written over these trees until someone decides what agreement is supposed to mean** — and a gate
that is red on the day it lands is a gate that gets switched off (`DECISIONS.md`).

That is the generalisable part:

> **"Is there a second copy?" and "is there a second implementation?" have different answers and
> different remedies. A copy can be gated on equality. A fork cannot be gated on anything until
> the shared part is named, and naming it is a judgement, not a scan.**

The instrument was the shared part here — the capture harness — and nothing had ever said so.
After the port, `src/view/harness.ts` differs between the trees on **prose only**: `just film`
and "ball" against "marker", 22 lines, no executable difference. `src/view/capture.ts`'s
`declare global` block is identical.

### The naming collision that kept it out of view

`DECISIONS.md`, `README.md`, `starter_parity.py` and this log all say **"template"** for
`eval/starters/*/`. `DECISIONS.md`'s *"The templates are measured at each stack's best"*
(2026-08-22) was implemented by task 26 entirely inside `eval/starters/`. `README.md`'s
*"What does a building agent read? → `template*/AGENTS.md`"* has been wrong for every whole-game
run since 2026-08-12. A reader auditing "the templates" reads the starters and finds them
current; the directory literally named `template-ts/` is not what they looked at.

> **When two directories share a colloquial name, every audit of one is evidence about the other
> that nobody collected.**

### Controls

The suite is the starter's `capture-environment.test.ts`, ported and re-pointed at this tree's
background colour. Mutants restore one removed mechanism each; the file is written back in a
`finally`.

| control | expected | got |
|---|---|---|
| pristine, ported tree | 8 green | 8 green |
| M1 `setContent` instead of `route`+`goto` — literally the pre-fix page | red | **red, 7 of 8 failed** |
| M2 clocks pinned to a constant instead of virtual | red | red, the clock test |
| M3 `__capturePreload` fired but not awaited | red | red, the failing-preload test |
| M4 document-root containment removed | red | red, the escape test |
| *variant:* a legitimate nested asset `./sprites/x.png` | 200, not 403 | 200 |
| *variant:* golden frame after the port | unchanged, not re-blessed | unchanged |
| *variant:* `just verify` on the ported tree | green | green, 53 sim + 13 render |
| `verify_blind.py` on an out-of-repo copy | BLIND | BLIND, exit 0 |
| the same copy with the canary planted | CONTAMINATED | exit 1 |

**M3 reddens 1 test here and reddened 2 in the starter.** The second one asserts a preload
counter *after* `captureFrame` returns, and an unawaited hook has often finished by then — it is
a race, not a second pin. The mechanism is held by the failing-preload test, which is
deterministic. Recorded rather than tuned: a mutant sweep whose counts are quietly matched
across trees is reporting the tuning.

---


## 116. The re-sync trigger named an event, so the copy missed the one class the project had just proved it could not rebuild

Task 17 built a second copy of the evidence and closed with a claim that was **true when
written**: 14,196 files, verified at the destination by SHA-256 on both sides, `MEASURED.json`
stamped `2026-08-23T00:08:58-0300`. Four hours and sixteen minutes later the source held 7.5 MB
that the copy did not, and it was the 7.5 MB the project had spent a whole finding establishing
it could not reconstruct from anything else.

### The measurement

Read from both trees on 2026-08-23, source addressed by absolute path because `eval/runs/` is
gitignored and does not exist in an agent worktree (rule 12):

| | source | destination, before |
|---|---|---|
| `eval/runs/*/starter-baselines/` directories | 3 | **0** |
| files in them | 44 (22 archives + 22 `ls-tree`s) | 0 |
| bytes | 7,574,790 | 0 |
| every file's mtime | `2026-08-23T04:24:27`–`04:24:29` | — |
| destination `MEASURED.json` `verified_at` | — | `2026-08-23T00:08:58` |

The copy predated the files by 4h15m. **Nothing was misclassified**, and establishing that first
was the point: `evidence_set.py` classifies all 44 as evidence *by its own rule*, because nothing
in the tree discharges the burden of proving them regenerable — confirmed by running the
classifier and intersecting its output, with `report.json` as a row whose answer was stateable in
advance. Had the classifier been the fault, the fix would have been a different and much larger
one; a missing file at a destination does not distinguish the two, and the order matters.

### What the rule said, and why it could not fire

`eval/PROTOCOL.md` had a section headed **"Re-sync after any run completes, before the work root
is reclaimed"**. The starter baselines were not created by a run. They were created by a
**repair**: `git archive` of each work tree's root commit, taken deliberately so the work roots
could be reclaimed without destroying the only record of the starter each agent was handed
(#104). A repair is not on the list, so a rule that was written, read and understood did not
apply — this file's most-repeated defect, in a new instance:

> **A rule whose trigger is a list must be re-derived by every reader who meets an item not on
> the list. Write the trigger as the RESOURCE or the PROPERTY, never as an enumeration of the
> instances you happened to see.** (`AGENTS.md`, the 2026-08-15 rule audit)

The trigger now names the resource — *the set of files `evidence_set.py` classifies as evidence
has grown or changed, whatever made it move* — and, because a resource-shaped trigger still asks
the reader to judge, it is backed by a mechanical answer: `backup_evidence.py --verify-only`
re-classifies and reports what is missing, so a non-zero count *is* the signal. The question
"does this count as a run?" is gone.

### What else the snapshot had missed

The baselines were the reason for the task; they were 44 of 97 files.

| missing at the destination | files | bytes | created by |
|---|---|---|---|
| `*/starter-baselines/` | 44 | 7,574,790 | the repair that preserved the root commits |
| `wg-g4c-*/repack-2026-08-23-stale-files-removed/` | 24 | 143,454 | task 42 quarantining what `repack.py` removed |
| `wg-aspect-reliability/*.json` judge rounds | 29 | 1,259,688 | a sweep still running at 00:08 |

And **10 files whose destination copy was a stale prefix that had verified correctly.**
`REPRODUCIBILITY.json` was 220 bytes at the destination against 49,666 at the source, `sweep.log`
88 against 8,070; the other 8 were `wg-g4c` reports the re-pack rewrote. The two truncated ones
are the sharper half:

> **A SHA-256 match proves the copy equals the source at classification time. It says nothing
> about whether the source had finished writing.** Tier 2 was correctly green on a file holding
> 0.4% of its eventual content, because both sides genuinely held those 220 bytes.

That is rule 2 with the roles swapped — not inferring a process's state from its artifact, but a
*verifier* that is structurally unable to ask the question at all. The defence is not a better
hash; it is checking for recent writes before spending on a copy, and re-syncing after.

### The copy is a superset, and that was invisible too

Twenty-three files existed at the destination and no longer at the source: the stale judge-pack
entries `repack.py` removed from `wg-g4c` that morning. `rsync` runs without `--delete` and
nothing removes from the destination — which is correct, since a mirror that faithfully
reproduces an `rm -rf` protects against nothing — but it means a stale file there is
indistinguishable from a current one, and anyone re-packing from the second copy resurrects
exactly what was removed. `backup_evidence.py` now reports the count every run and writes every
path to `DEST_ONLY.txt` at the destination. It is an inventory and does not fail the tool:
**deleting at the destination to make an inventory question go away is how an inventory question
becomes lost evidence.**

### The new tier, and its controls

"The bytes arrived" is the wrong question for a starter baseline. The question it will be asked
is *"is this still the commit it claims to be?"*, so tier 4 recomputes the git blob id —
`sha1("blob <len>\0" + data)` — of every member **from the destination's bytes** and matches it
against the `ls-tree` in the companion `.blobs.txt`, whose first line carries the root commit id.
It is not sampled: the class is 7.5 MB and irreplaceable, and a sample of an irreplaceable class
tells you about the sample.

`eval/tools/backup_evidence_control.py` adjudicates it against a real git repository, the same
way `evidence_set_control.py` adjudicates the matcher against real git rather than against a
hand-written expectation.

| control | expected | got |
|---|---|---|
| **positive:** a genuine `git archive` + `ls-tree` pair | clean | clean |
| **positive:** all 22 real baselines (`--runs-root`) | clean | 22/22 clean, 1,238 blobs |
| flipped byte inside a member | problem | caught |
| member dropped from the archive | problem | caught |
| member added to the archive | problem | caught |
| ls-tree oid rewritten | problem | caught |
| commit header garbled | problem | caught |
| ls-tree records zero blobs | problem | caught |
| gzip truncated | problem | caught |
| companion `.blobs.txt` missing | problem | caught |
| M1 `no_blob_compare` | red | red — 2 cases |
| M2 `no_missing_check` | red | red — the dropped member |
| M3 `no_extra_check` | red | red — the added member |
| M4 `no_header_check` | red | red — the garbled header |
| M5 `no_empty_check` | red | red — the empty ls-tree |

Every mutant is caught by exactly the case that names its mechanism, and none is inert.

### Verified by reading the destination back, twice, by two paths

The re-sync's own tiers report 14,270/14,270 present, 14,270 SHA-256 matches, 759/759 harness
JSON records parsed, 89/89 tarballs extracted (25,642 members), 22/22 baselines re-derived from
1,238 blob ids. Those all run inside `backup_evidence.py`, so a defect in it would be shared by
its own check (#37). A second pass therefore re-read the destination without importing that
module at all, extracting each baseline and asking **`git hash-object`** — git itself — for the
blob ids: 1,238 re-hashed, 0 mismatches, 68 `report.json` parsed to non-empty objects, and the
two formerly-truncated files read back at their full 49,666 and 8,070 bytes.

### Still not copied, and why that is a decision rather than a gap

`~/game-research-work/wg-g4b-*` and `wg-g4c-*` have no second copy. Checked **per tree, never per
run** — the distinction that already saved evidence once in `PROTOCOL.md` — all 16 of those trees
have both a `submission.tar.gz` and a starter baseline under `eval/runs/`. Only `wg-g4`'s two
Unity trees lack a tarball, and `wg-g4`'s work root is the one that was copied. This is now
written down at the destination rather than being true by accident.

And the copy is still **same-disk**, still not a backup, and this task did not change that.

---


## 118. Fixing the collision is what created the dangling reference, and the dangling reference resolves

`_check_findings_integrity` was added on 2026-08-23 because parallel agents in isolated worktrees
each read the highest finding number from their own branch and take the next one (#94). It works:
a duplicate number now fails `docstat.py --sweep`, and the resolution is to renumber one of the
two findings at merge.

**Nothing updates the documents that already cited the old number, and no sweep in this project
could ever have seen that.** The citation still resolves. `#95` is a real finding; it is simply
no longer the one the author meant. There is no broken link to detect — only a reference that
changed meaning while staying well-formed, which is #80's shape moved from a stored record to a
cross-reference.

The cost is measurable in the direction that matters: a reader following task 42's `FINDINGS #103`
landed on a finding about a merged capture buffer in `runner.py`, with no signal at all that they
had been sent somewhere else.

### The map, derived rather than listed

`eval/tools/docstat.py --renumbered` replays every `## NN.` heading ever committed under
`eval/findings/` and reports the numbers that have named more than one finding. **Ten events, all
on 2026-08-23**, nine of them within six hours:

| written as | now | the finding |
|---|---|---|
| 89 | 90 | #87's decomposition got the evidence boundary wrong |
| 90 | 91 | three of four mutants were inert |
| 90 | 92 | a scored tier that returns the same number for every submission |
| 91 | 93 | `suite.json` describes the last thing written into the directory |
| 95 | 97 | four of the nine performance fields had no reader |
| 99 | 100 | the stored `verify.green` evidence drops the gate's own passed line |
| 103 | 104 | the only record of the starter a run was given is a git commit |
| 104 | 105 | of 27 unread exit statuses, 24 were deliberate |
| 112 | 113 | a withdrawn figure is still published in three live documents |
| 115 | 116 | the re-sync trigger named an event, not the resource |

The map is **derived from history on every run and never written down**. A hand-kept table of
renumbers is a second source of truth, and it would go stale in precisely the way the citations
it describes went stale.

### Decidable in one case out of three, and the tool says which

A citation cannot be judged by whether it resolves. It has to be resolved against the numbering
**its own author was looking at** — the findings tree at the commit that wrote the line — and that
finding then followed to the number it carries today.

| case | decidable? | why |
|---|---|---|
| citation and renumber in **different commits** | **yes** | the citing commit's tree names one finding; today's tree gives it a different number. No judgement in it |
| both in the **same commit** | no | the merge lands the renumbered heading and the closing task's `established_by` string together, and there is no ordering inside a commit |
| the author's tree was **never committed** | no | task 45 cited `#99` for a finding that was `#99` only in another agent's worktree. On every committed tree of that hour `#99` already meant the skills mirror |

So the tool reports two lists: a verdict, and a short list for a person. It prints and does not
gate — the second list contains correct citations by construction and can never reach zero, and a
permanent block of output that cannot be cleared is how a reader learns to skip a command entirely.

**The five citations repaired by hand on 2026-08-23 are the positive control, and they land on both
sides of that boundary.** Run against `1120695^`, the commit before the repair: `eval/PROTOCOL.md`
is decided, tasks 25, 34, 42 and 45 are undecidable, all five are reported. Run at HEAD, none of
them appear. A check that cannot find a defect known to be there is reporting its own silence.

### `blame -w` is load-bearing, and that is a finding in itself

`AGENTS.md` rule 16's `(#90)` was written against a tree where `#90` was the weight-sensitivity
finding, now `#92`. A later commit **re-indented rules 10-16 by one space and changed nothing
else**. Plain `git blame` therefore dates that citation after the renumber and reads it as fresh;
with `-w` it dates to the commit that wrote it and the staleness is visible.

> **A whitespace-only edit must not be able to launder a claim about when something was written.**
> Anything that dates evidence by `git blame` inherits this, and the failure is silent in the
> direction that reports clean.

The same shape in the other direction: a merge that renumbers is *also* where blame stops, so the
check descends into the single parent that carries the line verbatim before reading a tree. Without
that descent, every citation touched by a merge resolves against the merge's own tree — which is
the tree that just disagreed with the author.

### What it found, beyond what it was built for

**27 stale citations across eleven files**, every one repaired here as a citation and never as a
finding. The earlier cleanup pass grepped `tasks/` only; the other corpora had never been looked
at, and one of them is the worst-hit document in the repository:

| corpus | stale, repaired | reported and read as correct |
|---|---|---|
| `eval/IMPROVEMENTS.md` | 10 | 2 |
| `tasks/` | 9 | 1 |
| `DECISIONS.md` | 3 | 3 |
| `README.md` | 1 | 3 |
| `AGENTS.md` | 1 | 1 |
| `CLEANUP-LOG.md` | 1 | 1 |
| `eval/judge/RUBRIC.md` | 1 | 0 |
| `eval/PROTOCOL.md` | 1 | 0 |
| `research/11-doc-linting-for-agents.md` | 0 | 3 |
| `eval/RUNS.md` | 0 | 2 |
| `eval/findings/` (cross-references) | 0 | 3 |
| `eval/FINDINGS.md`, `eval/judge/AGENTS.md` | 0 | 2 |

`eval/IMPROVEMENTS.md` is the one nobody would have thought to grep: ten citations of `#112` in a
single iteration, all meaning what is now `#113`, because that iteration and the renumber were
three minutes apart.

The right-hand column is not a residue to be cleaned up. `#99` cited in `AGENTS.md`, `DECISIONS.md`
and `research/11` correctly means today's `#99`; `#112` in `README.md` and `eval/RUNS.md` correctly
means today's `#112`, while `#112` in tasks 54 and 55 meant `#113`. The two are separated by reading
the sentence, which is why that half of the output is addressed to a person.

### The false-negative channel, named rather than discovered later

**`tasks.py` rewrites a whole queue file when it writes one**, including re-quoting YAML scalars it
did not otherwise touch. A closed task's `established_by` line is therefore blamed to the last queue
write, not to the session that recorded the evidence. Measured: this check reports **12** `tasks/`
citations at `1120695^` and **0 of those 12** today, on lines whose text is unchanged apart from a
pair of quotes. Five were the known repairs and seven were correct citations, so nothing was lost —
but the mechanism that hid them is indifferent to which kind they were.

Generally: **any content edit that leaves a stale number in place moves the line past the renumber
and launders it.** `-w` closes the whitespace case because that is the one an automated reformat
produces. The rest is a fail-closed limit — it costs recall, never a false accusation — and it is
the second reason this is a smell detector and not a gate.

**Then it caught two nobody had noticed at all.** Rebasing onto `main` mid-task pulled in the tenth
event — `115 -> 116`, landed an hour earlier — and the check immediately reported fresh stale
citations in `DECISIONS.md` and `eval/PROTOCOL.md`, plus one in task 57's own evidence string. Not
planted, not historical: **the defect was still actively producing instances while the check for it
was being written.**

### The rule this pays for

> **A fix that resolves a collision by renaming one of the colliding things must find what already
> cited the old name.** Renaming is not a repair on its own; it moves the damage downstream to
> every reference, where it is invisible because the reference still resolves.

This project has four identifier namespaces allocated by hand — task ids (#94), finding numbers,
regime ordinals, pack labels (#70) — and **every one of them has collided.** Each now has a
mechanism: a shared queue, a duplicate check, an ordinal check, a ban on joining rounds by label.
Every one of those catches the collision. **This is the only one that asks what the collision
broke.**


## 119. A withdrawal that was declared in one live document and contradicted in three, all of which resolve

FINDINGS #113 is about a retired FIGURE. This is the same shape one level up: a retired
CLAIM, withdrawn in the archive on 2026-08-17 and still cited as support in three live
documents six days later. It is the withdrawal register's first catch, and it was found by
building the register rather than by anyone reading the documents.

### The measurement

`eval/judge/JUDGING.md` says, under "RESULT after the repairs": **"#54 is withdrawn."** The
claim was that `architecture` and `ux` — which share no evidence at all, one reading only
source, the other only frames — ranked the field identically on both presentation orders, so
their agreement evidenced a shared prior. It rested on tau 1.00 across two orders of one
round. The repeat gives **0.385** (seed 0, 13 comparable pairs) and **0.667** (seed 1, 12),
and the redundant pairs the second round finds are different ones that agree with neither.

Every live citation of #54 in the repository on 2026-08-23, before this task:

| site | what it said |
|---|---|
| `README.md`, In flight | "`architecture` and `ux` ... rank the field identically on both orders (#54)" — present tense, no marking |
| `DECISIONS.md`, tier-3 weight | "`architecture` and `ux` are redundant with each other while sharing no evidence (#54)" — listed as a ground for the decision |
| `eval/judge/JUDGING.md`, RESULT 2026-08-16 | "> They share no input at all (#54)" — 114 lines above the same file's own withdrawal notice |

The ticket for this task named one of the three. The other two were found by the check.

### Why nothing could see it

Every reference check in `docstat.py` asks whether a name RESOLVES. `#54` resolves: it is a
real finding, with a real body, correctly numbered. `--renumbered` cannot see it either —
the number never moved. And the cross-document figure-agreement check built under task 11
could not see its sibling #113 for the reason that generalises here: **the restatements of a
withdrawn thing agree with each other, and with the original.** Propagation and consistency
are the same observation.

The one thing that separates a live claim from a retired one is not in the text of either.
It is whether a withdrawal was ever DECLARED — a fact about the record, which has to be
written down before any check can use it.

### What the register does, and the one thing it does not

`eval/withdrawn.json` declares a retired figure or claim by id, with the regexes that are its
signature and an ARCHIVE document that states it in full. `docstat.py --withdrawn` reports any
block of a LIVE document that matches every signature pattern without citing the id.

**It does not decide whether a sentence is STATING a retired figure or ASSERTING it as
current. Nothing mechanical can: they are the same characters.** What it does is force the
author to declare which, in place, for the price of one parenthetical. Three of the six hits
at HEAD were legitimate historical statements in live documents — including `JUDGING.md`'s own
withdrawal notice — and the repair for all three was to add the id, which also warns the
reader who lands on that line rather than the one who reads 114 lines further down.

### The rule

> **A correction has to be DECLARED, not inferred.** A consistency check finds disagreement,
> and a stale figure does not disagree with anything — it agrees, in every document, to the
> digit. The only detectable property of a retirement is that somebody recorded it.

Its corollary, which is why the exemption is an id and not a marker word: **`withdrawn`,
`superseded` and `retracted` are an enumeration**, and this project has already measured an
enumeration failing on one inflection of one verb — the aspect check exempted `planted` and
went red on `planting`. An id has no inflections.

Measured red before it was wired in: at `25fe630`, the commit before task 54 ran, the check
reports the withdrawn 1.70/2.05 pair published in `DECISIONS.md`, `README.md` and
`eval/judge/JUDGING.md` — the exact three sites #113 names — and reports none of them today.
`eval/tools/withdrawn_control.py` runs 33 controls and five mutants, each mutant flipping the
control that names its mechanism.
---

## 120. One function guarded one durable record and destroyed the other, eleven lines apart

Found while executing task 30, which was filed from #93. #93 said the manifest overwrite affected
**three** stored directories and that each carried the same tell. Measured mechanically over all
19 stored run directories, it is **five**, plus a sixth directory holding the other end of one of
them, and the tell fires on a different set than #93 named.

### The two lines

`wholegame.py cmd_build` writes two durable configuration records into a run directory. The
prompt snapshot has been kept-not-overwritten since #57 — *"a rewrite would erase the very drift
it exists to catch"* — and eleven lines below it, `suite.json` was written unconditionally.

`runs/wg-g4-2026-08-17T09-38-32` holds both halves to the millisecond:

| record | mtime | matches |
|---|---|---|
| `prompts/index.json` | `2026-08-17T09:38:32.783 UTC` | the directory name, to the second |
| `suite.json` | `2026-08-17T10:57:39.697 UTC` | its own `started_at`, 79 minutes later |

A second launch went into that directory. The snapshot survived; the manifest was replaced, and
the run the directory is named for now has no record of what it was configured to be.

**The reason one was guarded and the other was not is that #57 was written about prompts, and #77
— *keep manifests, not just scores* — was written about judge packs.** Neither trigger contained
the word `suite.json`, so neither reached it. This is AGENTS.md's own meta-lesson producing a
fresh instance eleven lines from its own fix.

> **Any durable record of what a measurement was configured to be is append-only.** Not "manifests",
> not "snapshots" — the resource. A second launch adds a record; it never replaces one.

### What the census alone would have missed, and what the tell alone would have missed

Two independent checks, and **neither finds all five**:

| run | manifest vs reports beside it | `started_at` vs directory name |
|---|---|---|
| `wg-matrix-2026-08-13T14-02-50` | **MISMATCH** — declares 4, holds 24 | **+27668 s** |
| `wg-audio48-2026-08-14T19-55-47` | **MISMATCH** — declares `g3_arena`, holds 16 reports and zero `g3_arena` | **+50225 s** |
| `wg-g4-2026-08-17T09-38-32` | **INCOMPLETE** — declares 8, holds 4 | **+4747 s** |
| `wg-arena3d-2026-08-15T12-46-30` | clean — declares 8, holds exactly those 8 | **+79236 s** |
| `wg-audio-2026-08-14T12-29-42` | **INCOMPLETE** — declares 24, holds 11 | **clean, 1 s** |
| `archive-arena2d-wg-audio48` | **no manifest at all** beside 8 reports | n/a |

`wg-arena3d` is the one that matters. Its manifest **was** overwritten — `started_at`
`2026-08-16T13:47:06.522` equals `g3_arena__unity__t0`'s start to 2 ms, because the run was built
in two waves and the second rewrote the manifest — and the census clears it completely, because
both waves declared the same shape. That two-wave line is the same one `RUNS.md` draws for #49,
where it had to be reconstructed by hand from trial records and from what the agents said about
themselves. It is one field comparison in the manifest.

### #93's third row is wrong, and the reason is worth more than the row

#93 listed `wg-audio-2026-08-14T12-29-42` as carrying the tell, on the strength of `15:29:43`
inside a directory named `12-29-42`. **They are the same instant.** `started_at` is UTC and this
machine is UTC-3; the delta is **1 second**, and the manifest is the original. Its real defect is
smaller and different in kind — the run stopped after 11 of 24 declared trials, so the manifest
overstates a run that never finished rather than describing a different one.

The directory names are chosen by the operator on the `--run-dir` command line, and this project
has stamped them **both ways**: `wg-calib`, `wg-cal48`, `wg-cal48b` and `wg-audio` in local time,
`wg-g4b` and `wg-g4c` in UTC. Any check that assumes one basis reports a three-hour drift across
half the corpus, which is rule 9's shape — a uniform answer across subjects that share only the
instrument.

> **A comparison between two timestamps written by different clocks is not a comparison until you
> have said which clocks.** Two strings that do not look alike are not thereby different instants,
> and "does not look like" is how this row got into a findings file.

The audit takes the closer of the two bases. The separation is not marginal — consistent runs land
at **1, 1, 1, 1, 12 and 24 seconds**, inconsistent ones at **4747, 27668, 50225 and 79236** — so
the tolerance sits an order of magnitude clear of both edges. From schema 2 on, the manifest records
its own `run_dir` and the question is an equality test with no clock in it; the stamp comparison is
kept anyway, because a check that switched to the new field would be weaker on the 18 stored
directories than on the ones written tomorrow.

### The stored records are marked, not repaired

`eval/runs` is evidence, and **a manifest reconstructed today is not the record that was written
then.** For `wg-matrix`, `wg-arena3d` and `wg-g4` the original was destroyed and no honest
replacement exists; for `wg-audio48` the original survives as `suite-full-matrix.json` and was
*deliberately not* promoted, because renaming it over `suite.json` would erase the evidence that
the canonical name had ever been wrong.

Each of the six carries a `MANIFEST-DEFECT.json` recording what was found, what survives, and any
reconstruction — clearly under `reconstructed_*` keys, never under a `suite*.json` name, because a
file named like a manifest reads like one. The marker stores **the exact issue list it
acknowledges**, and the audit re-measures and compares on every run: a marker that still matches
downgrades the error, and a marker that no longer matches raises `MARKER_STALE`. It can only
acknowledge an unchanged known state, never hide a change (rule 7).

Mechanism, controls and the timezone reasoning: `eval/tools/manifest.py`, controls in
`eval/tools/manifest_selftest.py`. The mutant there is the pre-repair writer itself, so the suite
can demonstrate the defect rather than only the fix (rule 14) — and it immediately earned its keep
on something else: `cmd_build` loads `tools/` modules by path, the first version of that loader did
not register the module in `sys.modules`, and `@dataclass` resolves annotations through
`sys.modules[cls.__module__]`. Every test that imported the module normally was green while the
harness path raised at import.
---

## 122. Retiring a suite would have deleted the only copy of what its trials were asked to do

**The four `template*/` trees were retired on 2026-08-23** (task 56, `DECISIONS.md`). The ticket's
`done_when` said to remove the trees, `eval/run-bakeoff.sh` **and `eval/suites/bakeoff-*.toml`.**
The last of those three would have been a mistake, and the reason is not visible from any file
listing.

**What a stored spec-change trial records about its own task is the string `t1_rally`.** Not the
prompt, not the requirement, not a hash of either. Read from
`runs/bakeoff-ts-2026-08-11T15-33-41/trials/t1_rally__typescript_three__t0.json`, the keys are
`trial_id, task, arm, trial, started_at, session_id, wall_s, agent, diff_stat, changed_files,
tampering, touched_protected, self_verify, reverted, holdout, passed, score, finished_at`. The
prompt is in none of them, and `agent` holds cost, tokens, turns and `final_text` — the answer,
never the question.

Scanned for the first line of the rally prompt across everything under `eval/runs/`:

| corpus | files containing the task text |
|---|---|
| `eval/runs/**` — 12 run directories, **71 trials**, including the work trees and `bakeoff.log` | **0** |
| `eval/suites/` | 6 — four `bakeoff-*.toml`, `core.toml`, `prompts.py` |
| everywhere else in the repository | 0 |

**The extraction was proved on a case whose answer was known before it ran** (rule 12): the same
scanner was pointed at `eval/suites/`, where the string was read by eye minutes earlier, and
returned the six files. A census that returns zero is worth nothing until the scanner has been
shown able to return non-zero.

So the answer key and the question both lived outside the evidence, in files the retirement was
about to delete. `eval/holdout*/` is the same shape — it is what `score: 1.00` meant — and
`eval/variants/AGENTS.no-api-notes.md` is the *treatment* of an 18-trial ablation arm. All were
kept; only the trees and the launcher went.

### Why this was reachable at all, and where it is already fixed

`wholegame.py`, the harness that replaced this one, writes `prompt.txt` into every trial's
artifacts and snapshots a run-level `prompts/` directory with an index that `prompt_guard.py`
diffs. **That capture exists because of #41, where a rendered prompt disagreed with the stored
one.** It was added for provenance — *did this run send what we think it sent* — and the property
it happens to give is the one that matters here: a whole-game run directory is legible on its own.
The older one is not, and no gate would have said so.

> **Evidence you can still read is not the same as evidence you can still interpret.** A record
> that stores an identifier instead of the thing it identifies is complete, well-formed, parseable
> and worthless the moment its lookup table is deleted — and nothing about the record announces
> that it has a lookup table.

The generalisation, which is the reason this is filed rather than fixed and forgotten: **before
deleting anything, ask what the surviving artifacts DEREFERENCE into it.** A dependency scan finds
imports and file reads. It does not find a foreign key in a JSON field, and the thing being deleted
looks unreferenced precisely because the reference is data, not code.

Two deletions on this same day were the same class — #104, where the only record of a starter was a
commit no archive contained, and task 07's closure removing the sole reproduction of #66's defect.
**All three were judged safe by looking at what pointed at the target. In every case what pointed
at it was a string inside something else that was being kept.**

### What made this deletion different, and it should be said plainly

The four trees are in git across **139 commits** and pushed: `git log -- template-ts` resolves, and
both commits that ever touched them (`a3d0fd1`, `ee8625f`) are on `origin/main`, verified with
`git branch -r --contains` rather than assumed. #104's work tree was never committed and had no
such property. **A deletion whose recovery has been verified and a deletion whose recovery is
assumed look identical until someone needs the file.**

## 124. The index of the findings log split into two tables, and the sweep that checks the log was green on it

`eval/FINDINGS.md` is the index: one row per finding, and the only route from a citation to
the entry it names. A blank line between two rows **ends the table** under CommonMark, so
everything below becomes a second table with no header — an index that visibly stops.

It happened, and `docstat.py --sweep` **was green on it for as long as it stood.** The gap was
measured before it was closed: with the committed file, a blank line planted between the `#105`
and `#106` rows left the sweep at **exit 0**.

Three reasons it was invisible, and the third is the transferable one:

- `grep` sees no difference. Every row still matches, so any row-based check passes.
- The existing reconciliation compares **sets** — body against index. A number indexed *twice*
  collapses in a set, both differences come back empty, and both rows resolve. **Only counting
  sees it.**
- The range sentence is spelled in **three** live files and only one was ever checked. That is
  why the index got repaired while `AGENTS.md` went on saying `#19-#110`.

> **A structural defect in a document is invisible to every check that reads it as records.**
> The rows were all present, all correct, and all resolvable. What was broken was the thing
> holding them together, which no query over the rows can ask about.

Repaired with a contiguity check, a duplicate-**row** check distinct from the set
reconciliation, and a range check over all three files that also fires if a file stops stating
a range at all — so it cannot go quiet by the sentence being deleted. The pins run inside
`--sweep` on every invocation rather than in a command someone has to remember, because a gate
whose ability to fail is never exercised is the shape this project keeps finding.

Two green cases matter as much as the red: a blank line **after** the last row legally ends the
table and must stay silent, as must a `| **7** |` row inside a fence. An earlier draft got both
wrong.

Also recorded, because it is the rule-12 shape wearing an answer:
`grep -rhno "^## #?[0-9]+" eval/findings/*.md | sort -n | tail -1` returns the highest **line
number**, not the highest finding. It gave 117 against a true 118.

## 163. A disagreement that looks like rounding may be a disagreement about the input, and rounding the other candidate is what tells them apart

Two live documents stated the same three-call judge figure as **$4.39** and **$4.38**, and the
same sum as **$13.16** and **$13.15**. The ticket filed for it — written by the orchestrator —
read the mean disagreement as a rounding convention:

> *13.16 / 3 = 4.38667 rounded up in one document and truncated in the other … neither figure can
> be re-read from source, so which way it goes is a decision rather than an edit.*

That premise is wrong, and it was wrong in the direction that closes the question:

    13.16 / 3 = 4.386667  ->  4.39
    13.15 / 3 = 4.383333  ->  4.38

**Half-up rounding takes each sum to the mean printed beside it.** Nothing was truncated; each
document was internally consistent, and the disagreement was never about rounding at all. It was
about the **sum** — and a sum, unlike a rounding convention, is a claim with evidence behind it.

$13.16 then wins on arithmetic that still runs: the ledger table's `g2_tetris3d` rows sum to
**$33.63**, which `judge_ledger.py --tree` re-derives to the cent from
`wg-tetris-judge-2026-08-17/pre/`, against a published day total of **$46.79**. `46.79 − 33.63 =
13.16` exactly; $13.15 would need $46.78.

> **Before concluding that a numeric disagreement is undecidable, apply the suspected
> transformation to the OTHER candidate too.** One derivation was performed on one value and the
> conclusion — *"one of these was truncated"* — was reached without ever testing it on the second.
> A tie declared undecidable stops the search; that is what makes the premise expensive rather
> than merely wrong.

The limit is stated rather than glossed: this is coherence with a published total, not a
re-reading, and $46.79 has no artifact either. `DECISIONS.md` carries the reversal clause.

**The ticket was the defect, and the agent that worked it overturned it.** A ticket states what is
believed at filing time; when the belief is load-bearing — here, *"no measurement can break the
tie"* — it should be written as the thing to attack first, not as the frame the work happens
inside.

---

## 164. A loop that built its command from a variable ran nothing, and returned an exit code small enough to read as a verdict

Verifying a merge, six gates were run over the combined tree with:

    for c in "docstat.py --sweep" "tasks.py check"; do python3 eval/tools/$c; done

Every one returned **2**, and 2 sat comfortably in the range a gate returns. The reading was
*"the merged combination fails six gates"*. Run individually, each returned **0**.

The shell is **zsh**, which does not word-split unquoted parameter expansions. `$c` arrived as a
single argument, so python was asked for a file literally named `docstat.py --sweep` and answered
`[Errno 2] No such file or directory`. **The gates never ran.** In bash the same line works, which
is why the habit exists.

> **This is the project's central pattern with a new mechanism: something that runs, reports a
> number, and measures nothing.** It is not a pipeline status (rule 3) and not `|| echo 0` — it is
> a shell-dialect difference that suppresses execution while returning a plausible small integer.
> Exit 2 from a missing file is indistinguishable, to the reader, from exit 2 from a check.

What separated them was not suspicion of the shell. It was that **0 and 2 disagreed for the same
command depending on how it was invoked**, and the disagreement was chased rather than averaged.

Two things make this survivable rather than lucky:

- The full-gate sweeps used in the same session read their commands with `eval "$cmd"`, which
  re-parses the string and therefore works. Those results stand, and **CI re-ran the same gates
  independently and agreed** — a second instrument on a different machine, which is what made the
  earlier greens more than a claim.
- The failure direction was fail-closed: it reported red where the truth was green. The dangerous
  version of this bug reports **green**, and it would if the loop's exit code were ever used as
  `&& merge`.

**A command assembled from a variable is an address (rule 12), and the shell is part of it.**
Prefer an explicit array or `eval`, and prove the loop runs at all by making one iteration fail on
purpose before trusting the ones that pass.

---

## 167. The textbook robustness fix, applied where its named failure mode really occurs, measured 9 pairs worse than doing nothing

The scene probe's image-side check estimates how far a background band shifted between two frames,
by minimising a sum of absolute differences over horizontal gradients. It has a known weakness: one
strong edge — the car, its headlights — can dominate the sum and offer a competing minimum at zero.

**That weakness is real and was measured**, not hypothesised: 43 of 44 frame pairs correct on the
reference and 39 of 44 on a variant that deals the same seeded textures to different bands, with
**every miss in the bottom band, where the car is.**

The standard remedy for one strong edge dominating a sum is to clip the profile at a multiple of
its own mean. Applied here, against the same 88 pairs:

| candidate | reference | nearest-first | total |
|---|---|---|---|
| SAD over normalised horizontal gradients, growing overlap — **shipped** | 43/44 | 39/44 | **82/88** |
| the same, over a fixed central window | 43/44 | 39/44 | 82/88 |
| the same, **with the profile clipped at 3× its own mean** | 40/44 | 33/44 | **73/88** |
| normalised cross-correlation | 41/44 | 34/44 | 75/88 |
| SAD on the **sign** of the gradient | 37/44 | 20/44 | 57/88 |

**The fix aimed at the actual failure mode is the second-worst of the five.** Nothing about the
diagnosis was wrong — the car does dominate, and the misses are where it is. The remedy simply
does not help, because clipping discards the same high-gradient information the estimator needs to
find any minimum at all.

> **Choose between candidate implementations on the measurement, never on which one sounds more
> principled about the defect you diagnosed.** A correct diagnosis licenses a search; it does not
> license the first remedy the diagnosis suggests. Both are cheap to run against the same
> population, and the difference between them here is 9 pairs.

This is the census-trigger lesson (AGENTS.md) arriving in a second domain. There, the property
that *sounded* more general than an enumeration turned out to redden 31 correct lines with no true
positive, and the enumeration it was meant to replace was strictly better. Here, the transform that
sounds more robust than the naive sum is strictly worse. **In both cases the argument was sound and
the number disagreed**, and in both cases the only thing that could tell them apart was running the
candidates side by side over one fixed population.

**Where the robustness went instead:** into the criteria. A band is treated as measurable only when
its per-pair estimates **agree with each other** — a statement about repeatability derived from the
measurements rather than from the answer expected of them. A band whose estimates disagree cannot
support a conclusion drawn from one of them, and saying so is cheaper and more honest than a
transform that pretends the disagreement away.

---

## 171. The exemption that lets a document discuss phantom flags is the same mechanism that disarms a probe testing for them, and it fired three times in one day

`docstat.py` exempts any line matching `does not exist|phantom|plant\w*|do not name them`, so a
document may write about a made-up flag without the flag check firing on it. Necessary: several
documents here explain that check.

**A probe for that check is written in exactly that vocabulary.** Three instances, all 2026-08-24,
by three different authors:

| probe | intended | actual |
|---|---|---|
| `--zzqphantomflag` | red | green — already recorded in `docstat.py`'s own comment |
| a plant introduced as *"A phantom flag `--zzphantomflag` …"* | red in one file, green in the other | **green in both**, read as "neither file is covered" |
| `--zzq-real-phantom` in a census control | 25 → 26 rows | 25 → 25, read as the census working |

The middle one is the expensive shape. It was a **differential** probe — the same plant in two
files, expected to separate them — and the exemption suppressed both sides, so the differential
returned *"no difference"* and the conclusion drawn was that neither document was checked. A
neutral token separated them on the first try.

> **A probe named after a term the system special-cases is disarmed by the thing it is testing, and
> a disarmed probe is indistinguishable from a passing one.** The exemption is a line-level
> substring test over four open-class English words, and the words are precisely the ones anybody
> writing about the check reaches for.

**Documenting it did not stop it.** The hazard is recorded in a comment beside the constant, and
it caught nobody: the second and third instances were written by authors who had the file open.
A comment warns the reader who is already looking at that line; the probe is written somewhere
else, minutes later, in prose.

**What actually works is a rule about naming, not about the exemption.** Name a probe token after
nothing the system knows — a random string — and **run the positive half first**: plant in a
document you have already seen the check fire on. A probe that cannot go red on a known-good case
has not been shown to work, and every one of these three read green while measuring nothing.

The general form, which this project has met in `|| echo 0`, in pipeline exit status, in a
one-turn probe (#168) and now here: **the failure mode is not a wrong answer, it is a right-looking
answer from a mechanism that never ran.**

---

## 178. The guard that keeps the rubric out of the prompts held only the rubric's OWN wordings, so the plainest statement of a criterion walked past it

`prompt_guard.assert_no_rubric_vocabulary` exists to stop `eval/SCENES.md`'s criteria reaching a
prompt — teaching to the test is what it prevents. Its `RUBRIC_TERMS` list was built from the way
the criteria are **written in the design document**.

The two claims the scenes exist to withhold, said the way a prompt-writer would actually say them:

> *"the layers scroll at rates ordered by depth"*
> *"the water surface stays level while the glass tilts"*

Both read **0 hits on all 8** scene prompts. The list held 28 terms and neither phrase, so the
guard was **green on a clean corpus and a leaking one alike** — the shape this project keeps
finding, and here it sat inside the check written to prevent exactly this leak.

> **A vocabulary list drawn from how WE describe a thing does not cover how someone else would
> describe it.** The design document says *"layers scroll at distinct rates ordered by declared
> depth"*; a prompt would say *"the far hills move slower than the road"*. Same criterion, no
> shared substring. The list was an enumeration of one author's phrasing, presented as a check on
> everyone's.

The repair is two more spellings, and it is recorded as such rather than as a fix: `ordered by
depth` and `stays level` are now entries at 0 false positives, **a third phrasing still walks
past, and `DECISIONS.md` says so.** That is the honest position — this project has measured twice
that the property-shaped alternatives are worse (an open-class quantifier trigger at 31 red lines
and 0 true positives; a widened harness trigger at 25 rows and 0 true positives), so an
enumeration that is known-incomplete beats a property that fires on correct input.

### The same round: a false claim that spread by being copied

`aspects.applicability`'s docstring said **"a field is 8 model calls"**. `run_field` makes exactly
**one** `subprocess.run`. The claim predated the branch, and the agent working it copied the
sentence into **three more places** before checking it.

> **A wrong sentence in a docstring is a template.** Nobody re-derives a claim they are quoting —
> the act of copying is precisely the act of not checking — so the cost of a false statement is
> not one wrong reader, it is one wrong reader per copy, and the copies look like corroboration.

This is #169 and #174 in a third form: a fact stated in prose beside the code that contradicts it,
with nothing comparing them. The difference here is that the propagation was caught **in the same
session that caused it**, which is the only reason the count is four and not more.

---

## 181. A POPULATION with no producer goes stale exactly as a quantity does, and it is harder to see because the count beside it still looks right

`eval/RUNS.md` carried a four-row census of stored judge rounds with its producer printed directly
above it. Three rows were stale by 4; the fourth was correct. But the digits were the cheap part.

Two sentences beside the table made claims about **what the numbers covered**:

- *"**10** — all in `wg-aspect-reliability`"*
- a section headed *"EVERY STORED CODE ROUND WAS TOLD ITS PACK MIGHT BE TRUNCATED"*

Both were false at the new population, and neither was produced by anything. The 14 hashed rounds
partition **10 in `wg-aspect-reliability`** and **4 in a later blind judge-field sweep** — so the
universal was refuted by 4 rounds that read the repaired brief, and the single-directory claim by
the same 4.

> **A count has a producer; the sentence saying what it counts usually does not.** This project
> already knows that *a count with a producer goes stale for an hour and a count with none goes
> stale forever*. The population statement is the second kind, always — and it is worse, because a
> reader who re-runs the producer sees the digit agree and stops.

**The row that did NOT move is the tell.** Three rows moved by exactly 4 and one stayed at 26.
Adding 4 to everything would have produced a table that was internally consistent, arithmetically
tidy, and wrong — and nothing in the document would have disagreed.

### The repair reproduced the defect one level in

The fix counted a hashed code round whose aspect no longer exists **in the headline** and **skipped
it from the population** — the same numerator/denominator mismatch as #174, committed while
repairing a population claim. Caught in review, fixed with a third verdict column and the invariant
`n = same + moved + unbuildable`.

**And the first version of that invariant check summed only its own literals**, so it could not
fail. It parses the census output now.

> **An invariant asserted over the numbers you wrote is not an invariant; it is a restatement.** It
> has to be computed from the thing under test, or it is `total=0 passed=0` wearing arithmetic.

### What the ticket bought beyond the numbers

The census reads a **gitignored path**, so no gate had ever seen it — which is why it could rot for
days. It is now pinned by a fixture tree whose answers are written as literals, established **red
first** (3 red rows with the 4 counts already correct), with a 7-mutant red half and a
`--variant-control` that measures whether the variant is load-bearing: without it the mutant comes
back SURVIVED.

---

## #208 — the path census read prose, and the fenced commands a reader copies were outside it

### What happened

Task 193's filing census counted bare `judge/`- and `tools/`-prefixed references in the live
documents by matching them as inline backtick spans, and the ticket was dispatched on that
population. When the task's agent re-derived the census before repairing — this time reading
fenced command blocks too — the population moved. `README.md`, a root-frame document, carries
**10 fenced lines with bare `judge/` paths** (verified by the orchestrator on the branch: 10 in
fences, 0 inline), none of them in the filing census, and `eval/RUNS.md`'s line-matches moved
53→68 the same way. `README.md` was not in the ticket's document set at all, because a census
that cannot see fences found nothing there to put it in scope for. The ten commands remain
unrepaired on `main` at the time of writing; the repair is tasked separately.

### Why this matters

Fenced commands are not a corner of a document — they are the part a reader copies and runs,
which makes them the highest-risk instance of the defect this class of census exists to find
(a document naming a path that is not there is confidently wrong). The census did not
miscount: it counted a population defined by a document *feature* it never stated, and
everything outside that feature read as clean. Clean is what a reader cannot distinguish from
empty.

### The rule

Before trusting any census over documents, state the document FEATURE the population lives in
— prose span, fence, table row, frontmatter — and defend why the defect cannot live in the
others. A census keyed to one surface reports the others as clean.

## 210. The lie was in the MECHANISM, not the name: a document described a refusal gate that never existed, every name in the claim resolved, the sweep stayed green all seven days — and an operator following it would have erased real data

Task 202, filed by the 2026-08-28 cleanup pass on `field.py`. From 2026-08-21 to 2026-08-28,
`eval/judge/JUDGING.md` and the header of `eval/tools/frame_parity.py` stated that
`pack_parity` ran inside `build_pack` and **refused** packs of mixed capture geometry, naming
re-filming at 640x400 as the remedy for the 420x640 unity trial. `git log -S` over `field.py`
shows `pack_parity(` entered in the initial squash and **never called at any committed
revision** — the paragraph described working-tree state no commit ever carried. What the path
actually does, and had done all along: measure each blind label's geometry from its first
frame, record `capture_geometry`, and annotate `BRIEF.md` when sizes vary. Refusing was
rejected on purpose, in the code comment beside the measurement — geometry is a design choice
the task leaves open, and a refusal path would have forced re-filming `g2_tetris3d__unity__t1`
(`wg-matrix-2026-08-13`) at 640x400: **the erasure-as-normalisation move the comment warns
against, prescribed by the document an operator reads first.**

Two structural facts made this invisible to every gate that existed:

- **Every name in the false claim resolved.** `pack_parity` was a real function at a real
  address; `JUDGING.md` and `frame_parity.py` were real files; `#38`'s sweep — built to catch
  phantom names — was green throughout. The defect was in what the text claimed the names DO,
  and no name-level check can read a mechanism claim. It was found by a cleanup pass reading
  the file whole and checking each claim against callers, the method this log's pass entries
  repeat and no gate automates.
- **The described gate would not merely have wasted attention — it pointed at destruction.**
  The phantom-check findings here (#38 and kin) cost confidence; a phantom REFUSAL with a
  remedy costs evidence: re-filming is overwriting the thing the instrument exists to measure.
  The direction of a doc-vs-code lie matters, and the harmful direction reads exactly as
  authoritative as the harmless one.

The closing measurement is a corpus property and lives where comparability questions are
asked, in `eval/RUNS.md` (2026-08-28): **67 stored submissions with frames across 7 run dirs,
804 frames, 0 holding frames of more than one size, 0 unreadable** — the property the
first-frame read cannot see has never fired in the stored corpus. Producer:
`python3 eval/tools/frame_parity.py --runs-root <main checkout>/eval/runs`, fixture-pinned in
both directions and gated; the population agrees with task 182's record-based census, sharing
no code with this instrument. `pack_parity` is deleted, the decision is in `DECISIONS.md`
(2026-08-28), and the first-frame read remains a live blind spot for **future** submissions —
the corpus answer pins nothing going forward, which is why the census's header says to run it
before trusting any frame-derived number.

> **A false claim whose every proper noun resolves is not a reference defect and no reference
> check can see it.** The unit of doc truth here is the mechanism claim — who calls this, when,
> and what happens — and it is verifiable only against the code or a mutant. **And when the
> phantom is a gate rather than a check, the doc is not describing missing scrutiny; it is
> prescribing destruction of the measurement.** Both facts generalize: sweep the names, but
> budget reading time for the verbs.

## 211. The renumbered-citation check reads tracked markdown and only that: every stale citation living in a code file was invisible to it, and 8 were found by reading while the gate stayed green

`_check_renumbered_citations` selects its corpus with `_tracked_md` (`eval/tools/docstat.py`,
line ~2969). A `#N` inside a `.py` docstring or `#` comment never enters the check, whatever
its history — and no other check here reads code files for finding-number citations either:
`--sweep`'s reference checks (paths, flags, censuses) are all over the document corpus too.
So the sentence in `AGENTS.md` that said "`--renumbered` is the only thing that asks what
the collision broke" was true of documents and silent about code, and the silence was read
as coverage.

**The measurement, 2026-08-29, two sessions.** The sixth cleanup pass read `judge_ledger.py`
whole and found 2 stale `#119` citations (fixed in task 206, merged as `f69902e`); task 207
grepped live code for survivors and found 6 more — `weight_sensitivity.py:8`, `runner.py:20`,
`runner.py:1077`, `runner.py:1105`, `docstat.py:596`, `docstat.py:5100` (PR #87). All 8 were
**correct when written**: `#119` changed hands four times on 2026-08-23 (its stories now live
at #120, #122, #123 and the withdrawal register), and each citation was written against a
tree whose `## 119.` still held the story it names — verified against the authoring commits
(`69de88c8`, `e86e09d0`, `31d66bb5`), not assumed. Because each resolves today, no
resolve-check can see it; the authoring-commit method of `--renumbered` is the right
instrument and it was pointed at the wrong corpus — rule 12's shape once more, with the
confident answer being a clean report: `--renumbered` ran exit 0 in the same window, twice,
36 triaged rows, 0 fresh rows naming a code file.

The finder that worked was the crudest one: `grep -rn '#119' --include='*.py' eval/`, read
beside the finding each hit names. That is the same method the sixth pass used, and the same
one #118's original 33 came from before the tool existed.

> **A gate's corpus is an input to the gate.** A correct method at the wrong address
> produces a confident answer, and a clean report over an unread corpus is that answer.
> Same-day citations are the danger case for renumber drift — the author's tree still held
> the old number when they were written — and they are exactly the case a same-day sweep
> of the renumber's own day would have caught in ANY corpus.

**Outcome, task 208, 2026-08-29.** Code joined the corpus. `_check_renumbered_citations` now
reads every tracked path at the authoring revision except two recorded exclusions — `eval/runs/`
(data, not guidance) and the vendored analyser trees — with binaries excluded by the NUL-byte
property of git's own binary heuristic and every non-text skip named in the summary. The dry-run
of the check's own logic that decided the question reported 8 DECIDED STALE rows: **exactly the 8
above, all 8 true, 0 false positives** — the widened instrument reproduces the hand work and adds
none. The 7 UNDECIDED rows it also reported (a code corpus cites from docstrings and comments,
where blame's same-commit case is common) were read and adjudicated into
`eval/renumber_triage.json`, 36 → 43 entries. Cost measured before shipping: ~23 s against 21 s
md-only, because blame is only asked of files whose text cites a reused number. The corpus is
asserted against a walking oracle that never consults git's listing, and pinned in both
directions in `--selftest`: the md-only revert is a red mutant (9 pins — re-measured 2026-08-29 after the
round-3 pins; it read 4 when first written and 8 at the round-2 handback, neither re-read when
the pins grew; oracle naming the unread code files), a stale code citation at a historical commit is REPORTED while its correct twins
are not, and the tracked `.claude/skills` symlink — a correct input the first widened run
crashed on — is skipped by name. It remains a report, never a gate, on the 2026-08-23 grounds.
