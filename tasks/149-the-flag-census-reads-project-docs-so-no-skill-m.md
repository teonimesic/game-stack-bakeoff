---
id: 149
title: The flag census reads project_docs(), so no SKILL.md is checked for phantom flags
status: done
priority: 2
refs: 'eval/tools/docstat.py, .agents/skills/audit-docs/SKILL.md, tasks/147, #170, #38'
done_when: Either a planted phantom flag in a SKILL.md turns `--sweep` red - with the plant also proved in a document already covered, so a broken plant cannot masquerade as success - and whatever ratchet the corpus change touches is re-baselined deliberately with the new number stated; or the exclusion is written down in docstat.py AND in the audit-docs skill's list of what --sweep does not cover, naming which checks read skills and which do not. Either way `--sweep`, `--selftest` and the corpus pins stay green.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/29
established_by: 'PR #29 squash-merged. The ticket''s title is refuted by its own corrected notes: the flag census reads reference_docs(), every skill is in it, and the gate was HARNESS_TRIGGER admitting 4 of 10 skills. project_docs() untouched, no ratchet moved. The four-way control shows the coverage bought (a harness-free skill goes exit 0 to exit 1) and that the gate did not become unconditional (an ordinary harness-free document stays exit 0). The answer FLIPPED mid-branch: at 07:00 admitting all 10 skills cost 8 correct lines so the exclusion was right, then my unrelated 6bfc80b put those 9 tokens in FOREIGN_FLAGS_EXACT and the cost fell to 0, which is why it ships widened.'
---

`docstat.py --sweep`'s flag census — *"flag `--x` matches no argparse in eval/"* — reads
`project_docs()`. **All 10 `SKILL.md` files are outside that corpus**, so none of them is
flag-checked. Skills are where commands and their flags are most densely written, which makes this
the worst place for the check to be absent.

Measured on `main`, one plant and a positive control, because an all-green result and a broken
probe look identical:

| identical plant, `` `--zzqwerty-nonexistent` `` | `--sweep` |
|---|---|
| `.agents/skills/prune/SKILL.md` | **exit 0** |
| `DECISIONS.md` | exit 1, naming the flag |

Skills **are** inside `reference_docs()`, so the reference and structure checks do read them. It is
specifically the flag census that does not, and the split is not an oversight in one place — it is
`cmd_sweep()` holding two corpora and different checks reading different ones.

## This is #170's territory, and 147 is adjacent — read both before starting

`tasks/147` found the same class for `.github/workflows/README.md` and closed it for
`reference_docs()` only. That ticket's note carries the measurement and the reason
`project_docs()` was deliberately NOT widened: it feeds an **exact-count ratchet**, and a larger
corpus moves that ratchet in the **passing** direction. So the naive fix — widen `project_docs()` —
loosens a different gate, and that is the whole difficulty here.

## What would satisfy this

Either the flag census reads a corpus that includes skills, with the ratchet it feeds decoupled or
re-baselined deliberately and the new baseline stated; **or** the exclusion is recorded in
`docstat.py` and in `.agents/skills/audit-docs/SKILL.md` — which already lists what `--sweep`
deliberately does not cover — saying which checks read skills and which do not.

**A recorded exclusion is an acceptable outcome and closing this that way is not a failure.** What
is not acceptable is the current state, where a reader of the audit-docs skill would reasonably
believe skill flags are checked.

## What NOT to do

Do not widen `project_docs()` without measuring what the ratchet does. And do not verify a fix by
planting a flag only in a skill: plant in a skill AND in a document already covered, so a
green-everywhere result cannot come from a broken plant.

## note 2026-08-24

## note 2026-08-24 — THE CAUSE IN THIS TICKET'S BODY IS WRONG. Read this before the body.

The body says the flag census reads `project_docs()` and that skills are outside it. **That is not
the mechanism.** Corrected by the agent working `tasks/147`, and re-measured here decisively:

| identical plant, `` `--zzqwerty-nonexistent` `` | `--sweep` |
|---|---|
| `.agents/skills/evaluate-run/SKILL.md` — **names a harness** | **exit 1** |
| `.agents/skills/prune/SKILL.md` — names none | exit 0 |

Skills **are** in the corpus. The backticked-flag half is gated **file-wide** at
`docstat.py:3664`, `re.search(r"(wholegame|runner|judge/|evaluate|regrade)\.py", text)`, and only
runs when the document names one of those four. **4 of the 10 skills do; 6 do not**, and those 6
have their backticked flags unchecked.

The bare-fenced half is deliberately outside that gate, and its own docstring says why: the
document-wide form *"hid a false positive for three weeks until an unrelated edit added a harness
name"*.

## What this changes about the ticket

The `done_when` still stands — a planted flag in a skill must turn `--sweep` red, proved alongside
a plant in a document already covered. **What must not happen is the repair the wrong cause
implies:** widening `project_docs()` would not fix this and would move the exact-count ratchet in
the passing direction for nothing.

**The obvious repair here is also measured and also bad.** Task 147's agent widened the harness
trigger to `_our_script_names()`: 43 documents to 165, **25 new rows, 0 true positives** — `gh`,
`git`, Godot and Chrome flags. So the file-wide trigger cannot simply be opened up, and this is the
census-trigger lesson again: choose on the live false-positive count, not on which sounds more
general.

That makes **recording the exclusion the likely right answer**, and closing this ticket that way is
success, not a shortfall. Task 147 already records it in three places for the register; this ticket
is the same question for the 6 skills that name no harness.

## What NOT to conclude from this note

That the class is understood. **Two mechanisms have now been proposed for one symptom and the first
was wrong** (#170 carries the correction). Before changing anything, reproduce both plants above
and confirm the split is the harness name and not something else that happens to correlate with it.

## note 2026-08-24

## The premise in this ticket's title is refuted — measured over all 10 skills, task 147

**The flag census does NOT read `project_docs()`.** It reads `refs = reference_docs()`, and every
skill is already in it. In `cmd_sweep()` the only `for p in docs:` loop — `docs = project_docs()`
— is the bare-trial-id ratchet, and it is scoped to `findings/`. Both flag halves live inside
`for p in refs:`.

What actually gates the backticked half is **file-wide**, 40 lines into that loop:

    harness = re.search(r"(wholegame|runner|judge/|evaluate|regrade)\.py", text)
    if harness:   # a doc that never mentions our harness names someone else's flags

A document naming none of those 4 never has its backticked flags checked, wherever it lives.

**The two hypotheses agree on `DECISIONS.md` and on the register and disagree on skills**, which
are in `reference_docs()` and not in `project_docs()`. Planting the identical backticked token in
each of the 10 skills separates them decisively:

| skill | names a harness | `--sweep` |
|---|---|---|
| add-game, audit-docs, evaluate-run, run-matrix | yes | **exit 1** |
| dispatch, prune, refine, tasks, update-readme, work | no | exit 0 |

`any SKILL.md in project_docs()` is `False`. Under the corpus hypothesis all 10 rows would be
exit 0; 4 are not. The split is on the harness gate and on nothing else. `prune/SKILL.md`, the
positive control in this ticket's own table, is one of the 6 that name no harness — so the
observation was right and the cause was read off a single row.

### What that changes about the work

- **Widening a corpus fixes nothing here**, so the ratchet difficulty this ticket is built around
  does not arise. `project_docs()` can stay exactly as it is.
- The real question is whether to widen the `harness` trigger, and **the obvious widening is
  measurably worse.** Replacing the 4-name enumeration with the closed class
  `_our_script_names()` admits 166 documents instead of 43 and adds **25 rows, 0 of them true
  positives** — `--auto`, `--body-file`, `--ours`, `--theirs` (`gh`/`git`), `--doctool` (Godot),
  `--enable-unsafe-webgpu` (Chrome), and tokens task files name as deliberately fake. 9 of the 25
  are in skills, which is where this ticket wants coverage. That is `AGENTS.md`'s recorded shape:
  an open-class property that fires on correct input is how a gate gets disabled.
- **`python3 eval/tools/docstat.py --selftest` is now the producer** for those counts (task 147,
  `_harness_trigger_census()`), so re-derive them rather than quoting these.
- The **bare-fenced** half is line-scoped on a script name and already reads every skill and the
  register. It is the higher-damage shape — the text a reader copies — and it is covered.

So the honest framings of this ticket are: *find a trigger for the backticked half that beats the
4-name enumeration on live-corpus false positives*, or *record the exclusion*. Task 147 recorded
it for `.github/`; the same reasoning applies to the 6 skills, and the register's
`Which gates read THIS file` section is the shape to copy.

## note 2026-08-25

## What the next agent should not re-derive (PR #29)

### Closed by the SECOND arm of `done_when` — the exclusion is recorded, with a producer and pins

The corrected notes above were right: the flag census reads `reference_docs()`, every skill is
in it, and the backticked half is gated file-wide by `HARNESS_TRIGGER`. `project_docs()` is
untouched and **no ratchet moved**, so the difficulty this ticket was built around never arose.

### Every candidate widening was measured, and every one loses

`python3 eval/tools/docstat.py --selftest` is the producer and reprints all of this live — do
not quote these figures, re-run it:

| trigger | reads | rows | genuine |
|---|---|---|---|
| the shipped 4 harness names, file-wide | 10/28 | 0 | — |
| one of our scripts named on the same line | 2/28 | 2 | 0 |
| one of our scripts in the same section | 26/28 | 8 | 0 |
| every skill admitted unconditionally | 28/28 | 8 | 0 |

`reads` is the recall half and it is the half that is easy to forget: the line-scoped trigger
looks cheap only because it reads 2 of the 28 flag mentions a skill really makes, and it still
reddens 2 correct lines. The 8 rows are `gh`, `git` and `just` flags argued about in prose.

**The cost showed up in the act of writing the record.** `audit-docs/SKILL.md` names a harness,
so it is already admitted; listing those 7 foreign flags there backticked took the shipped
trigger from 0 candidate rows to 7 on a paragraph whose subject is that they are foreign. A
widening whose own documentation trips it will keep tripping on correct prose.

### What now stops the record going stale

`_published_skill_figures()` builds each published sentence **from the live census** and asserts
it appears in the document that publishes it — `_backticked_flags`'s docstring table,
`DECISIONS.md`'s table and prose, and the audit-docs entry including both skill-name lists.
Widen the trigger and the pin reddens naming the figure that moved. 27 pin cases, 0 red.

### A CANDIDATE FINDING for the orchestrator to number — do not allocate one

**`HARNESS_TRIGGER` has five alternatives and one of them can never match.** The regex is
`(wholegame|runner|judge/|evaluate|regrade)\.py`; the `\.py` applies to the whole group, so the
`judge/` alternative requires the literal text `judge/.py`, which occurs **0 times** in the
corpus. `eval/judge/blind_dir.py` does not admit through it. That is why every write-up in
`docstat.py` says *4 harness names* for a 5-alternative regex — the count was right and the
reason was never written down. Recorded and pinned rather than repaired: making it mean
`judge/<anything>.py` widens the trigger and moves every published figure above, which needs its
own adjudication. **That would be a task, not a drive-by.**

### Traps, in the order they cost time

1. **The obvious repair is not the only bad one.** Three widenings were measured here and a
   fourth in `_harness_trigger_census()`. Before proposing a fifth, run `--selftest`: it prints
   recall as well as cost, and a trigger that looks cheap is usually one that reads nothing.
2. **A boundary tightening on `HARNESS_TRIGGER` is wrong, and it looks right.** The unanchored
   `wholegame\.py` is the **only** alternative admitting a document that names
   `eval/judge/regrade_wholegame.py`, one of our own harnesses, named in 8 places. Requiring a
   complete path component drops it and changes admission for 0 documents in exchange. Pinned
   both ways.
3. **Section ids must be fence-aware.** 31 of the 130 lines starting with `#` across the 10
   skills are inside a ``` fence. `ln.startswith("#")` splits real sections and understates the
   section trigger's reach. Use the shared `_fence_mask()` and `_ATX_HEADING`.
4. **A producer must count the population the CHECK reads.** `_skill_flag_coverage()` counted a
   resolving flag before applying the deliberately-fake exemption, while `_backticked_flags()`
   drops the whole line. Latent at 0 such lines, so nothing disagreed with anything.
5. **`_DELIBERATELY_FAKE` matches `plant*`, `phantom`, `does not exist`.** `--zzq-unresolved-tok`
   is the neutral token that works; anything with `phantom` in it exempts its own line.

### Left deliberately

- `project_docs()`, `reference_docs()` and the bare-fenced half are unchanged.
- No `eval/starters/` file was touched.
- `FOREIGN_FLAGS_EXACT` was **not** extended with the 7 foreign flags. Doing that would make
  admitting all 10 skills look free, but it buys the coverage with 7 permanent global
  exemptions on tokens (`--merge`, `--body`, `--auto`, `--offline`) that are plausible names for
  a flag of ours — `AGENTS.md` rule 7, and the list would grow with every tool ever discussed.

## note 2026-08-25

## SUPERSEDES the note above — closed by the FIRST arm, not the second

The note above was written while this branch was recording the exclusion. **Merging `main`
invalidated its central measurement and the answer flipped.** Read this one; the figures above
are the pre-merge ones and are wrong now.

### What changed the answer

`6bfc80b` put all 9 foreign tokens the skills argue about into `FOREIGN_FLAGS_EXACT`, for an
unrelated reason: ticket prose was reddening the sweep with the same flags. The cost of
admitting every skill to the backticked half fell from **8 correct lines to 0**. An exclusion
argued from a cost of 8 does not survive the cost becoming 0.

**The asymmetry is the argument, and it is the part worth carrying forward.** The exemptions are
the fail-open half and were paid for regardless of what this ticket did; widening the trigger is
the fail-closed half. Declining the coverage would have paid the price and taken nothing for it.

### The state now

`_backticked_flags()` is gated on `HARNESS_TRIGGER` **or** the document being a `SKILL.md`. All
10 skills are read; it reads 28 of the 28 backticked mentions of a real flag of ours that the
skills make, at 0 rows.

The four-way control, the identical planted token `--zzq-unresolved-tok` backticked inline:

| plant | before | after |
|---|---|---|
| `.agents/skills/prune/SKILL.md` — a skill naming no harness | exit 0 | **exit 1** |
| `.agents/skills/evaluate-run/SKILL.md` — a skill naming one | exit 1 | exit 1 |
| `DECISIONS.md` — ordinary, names one | exit 1 | exit 1 |
| `eval/PERF-HOST.md` — ordinary, names none | exit 0 | exit 0 |

The last row matters as much as the first: the gate did **not** become unconditional. Ordinary
documents naming no harness are still out of scope, and widening to the closed class
`_our_script_names()` still loses at 13 candidate rows over the reference corpus, 11 of them in
`tasks/`. That exclusion is recorded in `docstat.py` and in the audit-docs skill.

### What to watch, and what NOT to do about it

**Admitting every skill is only defensible while it costs 0 rows**, and a skill that starts
discussing a new tool's flag will redden `--sweep` on correct input. `_skill_flag_pins()` holds
that as a live case (`admitting every skill still costs 0 correct lines`). **When it fires, the
repair is `FOREIGN_FLAGS_EXACT`, not narrowing the trigger back** — narrowing gives up the
coverage while the exemptions stay paid for.

### Still true from the note above

The candidate-finding about `HARNESS_TRIGGER`'s inert `judge/` alternative, the boundary
measurement, the fence-aware section ids, and the trap list all stand unchanged.

## note 2026-08-25

## ACTION REQUIRED BEFORE COMMITTING THIS TICKET — one line reddens the sweep

Measured, not suspected: running the backticked half over this file returns one unresolved
token, so committing the queue as it stands turns `docstat.py --sweep` red on `main`. This is
the same shape as 6bfc80b, arriving from the other direction.

**The line**, in the note headed *SUPERSEDES the note above*, immediately before the four-way
control table. It reads:

> The four-way control, identical (backtick)--zzq-unresolved-tok(backtick) backticked inline:

The token is genuinely a deliberately-fake control name, so the designed repair is the
line-scoped exemption rather than an entry in `FOREIGN_FLAGS_EXACT`. **Add an exemption word to
that one line**, e.g. end it with *"— a token planted as a control"*. `_DELIBERATELY_FAKE`
matches `plant*`, `phantom` and `does not exist`.

I could not do it myself: `tasks.py` appends and never rewrites, and worktree isolation refuses
`Edit`/`Write` against the shared checkout. Every other occurrence of the token in this file
already sits on a line carrying an exemption word, which is why only one line is affected.

**The general shape is worth more than the instance.** An agent working a ticket about foreign
or phantom flags must catalogue them to do the job, its notes land in a swept corpus through the
shared queue, and the sweep goes red on prose that is correct. It has now happened twice in one
day on this one ticket. The two available answers are a line-scoped exemption written as the
note is composed, or an archive exemption for `tasks/` in the flag check — the latter is what
`findings/` already has for the aspect check, and 11 of the 13 rows the wider trigger would add
are in `tasks/`. That is a decision, not a drive-by, so it is stated here rather than taken.
