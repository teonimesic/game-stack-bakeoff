---
id: 120
title: tasks.py done accepts - as literal evidence and silently writes a one-character durable record
status: in_testing
priority: 4
refs: 'eval/tools/tasks.py cmd_done and cmd_note, tasks/112, FINDINGS #80'
done_when: 'Either tasks.py done reads evidence from stdin on - the way note does, or it rejects a bare - with a non-zero exit and a message naming the alternative. Pinned both directions: a control shows the old behaviour writing the 1-character record and the new behaviour either storing the full text or exiting non-zero, and a normal inline evidence string still stores unchanged. Whichever is chosen, note and done agree on what - means. tasks.py check and docstat.py --sweep exit 0 unpiped.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/6
established_by: '- now means stdin in note, testing and done alike, read once in _stdin_arg; cmd_evidence refuses an empty evidence string and refuses a multi-line one naming note, writing neither the field nor the status. Broken state established first on a scratch queue against dce1172: done 70 - over a 2280-character account stored the 1-character string at exit 0 with the ticket closed, and so did testing 70 - and done 70 "". tasks_control.py direction 8 went 62 to 79 measurements, 0 FAILED, 0 NOT CHECKED, exit 0, with dce1172 as the positive control that still reproduces the 1-character record on the same harness, 5 refusal rows asserting exit 1 AND a byte-identical ticket, and 5 accepting rows including the backtick line argv cannot carry. tasks_mutants.py 16 to 21 mutants, 0 survived, inert mutation SURVIVED 0 red of 79. Census: 0 of 114 done or in_testing tickets carry a degenerate established_by, extraction pinned by planting one which the same census reads as 1. Two review rounds on PR 6: round 1 found a real \r hole and a control row whose name and fixture disagreed, both fixed and pinned; round 2 declined with the mutated source and a 9-of-21 measurement. docstat.py --sweep exit 0, tasks.py check exit 0 at 120 tasks. This evidence string was passed on stdin through the repaired command.'
---

tasks.py note takes - to read the section from stdin and its help says so is the only safe way to pass backticks or newlines (#80). tasks.py done takes no such option, and its evidence string is at least as durable - it is the established_by line every later reader trusts. Under task 112 the obvious call, done 112 - < file, was accepted and recorded established_by=- , a 1-character record replacing 2100 characters of measurement, with exit 0 and no warning. That is #80's shape moved from backticks to a stdin sentinel: the record is silently emptied and nothing reports it. It fails open, so the loss is only visible to someone who re-reads the ticket afterwards. Two sibling commands disagreeing about - is also the enumeration failure AGENTS.md keeps recording: the safe path was added where the problem had been seen, not where the property lives.

## note 2026-08-23, task 120 worked

Closed by making `-` mean stdin in **every** subcommand that takes durable text, and by
refusing the two inputs that were being written silently. Branch
`task-120-evidence-stdin-sentinel`, PR #6. `11cad60` is the work; `af24169` repairs two
defects in its own docstrings; `dd91f0f` is review round 1; the rest (`8c07811`, `06d1e02`,
`83515cc`, `f72f402`) repair `.agents/skills/work/SKILL.md`, which this ticket's own
hand-back walked into — see the last two sections.

## The broken state, measured before anything changed

On a scratch main+worktree pair against `dce1172`, all at **exit 0** with the status
flipped and nothing printed:

| call | stored in `established_by` |
|---|---|
| `done 70 - < 2280-char account` | `-`, 1 character |
| `testing 70 - < same account` | `-`, 1 character |
| `done 70 ""` | the empty string |
| `done 70 "   "` | three spaces |
| `done 70 "<normal inline>"` | the string, correctly |

**Two of those shapes are not in this ticket, and one of them matters more than the one
that is.** `testing` carries the identical defect, and `testing <id> "<evidence>"` is what
`.agents/skills/work/SKILL.md` §7 tells every dispatched agent to run — `done` is the
orchestrator's command at merge. The ticket named the sibling that gets used less.

## What was built, and why this branch of the `done_when` rather than the other

Both branches are satisfied at once. `-` **means stdin everywhere** (branch 1), and the
call that actually lost the record — a multi-line account redirected in — **exits 1 naming
`tasks.py note <id> -`** (branch 2).

- `_stdin_arg(value)` is the sentinel, read **once**. `note`, `testing` and `done` all go
  through it. The property is *an argument that becomes a durable record*, not the
  subcommand the defect happened to be seen in.
- `cmd_evidence(tid, status, value)` refuses an **empty** evidence string, refuses a
  **multi-line** one naming `note`, and in both cases writes **neither the field nor the
  status**. The pre-fix code closed the ticket while destroying the record, so *"it
  refused"* and *"it refused without closing the task"* are different claims and only the
  second is worth anything to the orchestrator. Each refusal row asserts both.
- A **one-line** stdin string is accepted. That is the half `note` cannot cover: an
  evidence sentence containing a backtick cannot reach the program through argv at all
  (#80), and `note` puts it in the body, not in `established_by`.

Reading stdin *without* the multi-line refusal was the obvious implementation and is the
wrong one: it re-opens tasks 105 and 106's workaround with nicer syntax — a whole account
inside YAML frontmatter, where the next agent does not look (task 113).

## Pinned both directions

`eval/tools/tasks_control.py` **direction 8**: 62 → **79 measurements, 0 FAILED, 0 NOT
CHECKED, exit 0** (75 as first shipped, 79 after review round 1). `--skip-prefix` reports
**3 NOT CHECKED, exit 3** — not a pass.

- Positive control first, `PRE_EVIDENCE_COMMIT = "dce1172"`: that copy must still store `-`
  at exit 0 over 2280 characters **on this very harness**. It does. Without it every
  refusal row would also pass against a `tasks.py` that had never heard of the sentinel.
- 5 refusal rows (exit 1 **and** byte-identical file), 1 row asserting the message names
  `note`, 5 accepting rows (rule 15's variant half), 1 row asserting the sibling agreement
  directly, 1 asserting the queue a refused `done` leaves behind still lints.

`eval/tools/tasks_mutants.py`: 16 → **21 mutants, 0 survived**, inert mutation **SURVIVED
(0 red of 79)**, anchor-drift refusal ok, exit 0. New, with the rows each killed:
`evidence_no_stdin` (13 red), `evidence_refusal_still_writes` (7),
`evidence_multiline_allowed` (5), `evidence_empty_allowed` (3), `evidence_cr_ignored` (1).

Gates unpiped: `docstat.py --sweep` exit 0 over 183 docs; `tasks.py check` exit 0 at 120
tasks (`python3 eval/tools/tasks.py check`, read 2026-08-23; the queue is live and peers
write to it, so re-run it rather than quoting this).

## What the next agent must not re-derive

- **The damage is bounded and there is nothing to repair.** 0 of 114 `done`/`in_testing`
  tickets carry an `established_by` shorter than 30 characters. Task 112's was repaired by
  hand before this ticket was filed. The extraction was pinned before it was believed:
  planting a `-` into a copy of the queue makes the same census read **1**.
- **No `check` rule was added for short `established_by` values**, deliberately. There are
  no live instances, so the rule would have no true positive to be measured against, and a
  length threshold is an open-class trigger of exactly the shape `AGENTS.md`'s
  census-trigger section says to measure before shipping.
- **No `sys.stdin.isatty()` guard**, deliberately. A `-` typed at a terminal blocks on a
  read, which is loud; the failure closed here is the silent one. It cannot be pinned in
  both directions without a pty.
- **`add --why` / `--done-when` do not take `-`**, deliberately. `add` takes several text
  options and stdin can feed only one, so the sentinel is genuinely ambiguous there. If a
  future ticket wants it, that ambiguity is the thing to solve first.
- `PRE_EVIDENCE_COMMIT` pins direction 8's positive control to `dce1172`, which must stay
  reachable from `main` — the same constraint `PRE_NOTE_COMMIT` (`ea9f853`) and
  `FIX_COMMIT` (`466d436`) already carry.
- This ticket's `refs` names *"eval/tools/tasks.py cmd_done and cmd_note"*. **There was no
  `cmd_done`** — `done` and `testing` were one-line `_set` calls inside `main()`, which is
  part of why neither had a validation path. `cmd_evidence` is now the function the ref
  meant.

## For the orchestrator: one finding needs a number

No number was allocated (the `work` skill's rule). The claim, if it is judged worth one:

> **A sentinel that means "read from stdin" in one sibling command and a literal value in
> another is #80's failure with the backtick replaced by a hyphen.** `tasks.py done <id> -`
> stored the one character `-` over a 2280-character redirected account, at exit 0, and
> closed the ticket while doing it; `testing` — the command every dispatched agent runs —
> carried the same defect unreported, and `done <id> ""` closed a ticket with an empty
> reason. Reproduced against `dce1172` on a scratch queue; 0 of 114 stored tickets carry
> the resulting record, so the measured exposure is one ticket, repaired by hand.

It is a modest finding and the *generalisable* half is already in `DECISIONS.md`: the rule
audit's enumeration failure applied to a **sentinel** rather than to a rule — the safe path
was added where the problem had been seen, not where the property lives.

## Defects in `.agents/skills/work/SKILL.md`, found by following it

Every one fired against this ticket's own hand-back, inside an hour. All are fixed on this
branch; none is in scope for task 120, and they are recorded here because the next agent
will otherwise meet them again.

**1. The review-deadlock check enumerated one notice and missed the other (`8c07811`).**
The skill matched the single string `review paused by coderabbit.ai`. PR #6 came back
*"Review limit reached — you've used all 10 included reviews currently available"*, the
check read **0**, and the 15-minute poll loop was on course to spend all of it reporting
"not yet reviewed" about a review that had never started.

**The first replacement was worse than what it replaced, and only measuring said so.**
Keying on `> [!WARNING]` — the notice actually in front of me — reads **1 on #6 and 0 on
#1**, because the pause notice is a `> [!NOTE]`. It would have swapped which of the two
deadlocks hangs the loop while looking like a generalisation. Shipped instead: extract the
heading from a GitHub **alert callout** (a closed class of five) in a coderabbit issue
comment and *read* it. Measured across every PR this repository has had — `Reviews paused`
on #1, `Review limit reached` on #6, **empty on #2**, which was reviewed normally. 2 true
positives, 0 false positives on a corpus of 3, and the skill says so — including that the
corpus is small — rather than implying the trigger is settled.

**The replacement then validated itself on an instance nobody had when it was written
(`f72f402`).** Waiting for round 2 on this same PR produced a **third** heading —
`Review skipped — No new commits to review since the last review`. The retired string check
would have read 0 and polled to its deadline; the shipped one printed it on the first poll.
It is a third *meaning*, not a third phrasing: it is not a deadlock at all. That is the whole
argument for a closed-class shape over a list of sentences, and it arrived within the hour.

**And the retired check had BOTH failure directions on one PR within twenty minutes
(`83515cc`).** Twenty minutes after reading **0** on a real declined review, the same string
check read **1** on the same PR — matching a comment *I* had posted, which quoted the string
while explaining the bug. It filtered on no author. **A check on an unfiltered comment stream
is a check the agent can trip by writing about it.** The replacement filters
`select(.user.login=="coderabbitai[bot]")` and reads empty on that PR.

**2. `git commit -F` aimed at a stale scratchpad file, and shipped it (`06d1e02`).**
`-F .../commitmsg2.txt` picked up a **previous session's** file and put *"Task 117, review
round 1: the gate had two addresses for one repository"* on task 120's commit, at exit 0.
Amended while unpushed. The skill's existing warning is about the message's **content**
(backticks in `-m`, #80); this is about its **address**, which `-F` cannot report, because a
message file that exists is indistinguishable from the one you meant. The skill now says to
name the file for the ticket and to read back what the commit got.

## What review round 1 changed, and what it did not

PR #6, reviewed at `8c07811`. 4 comments; **2 accepted whole, 1 accepted in half, 1 declined
in the main and accepted in a part.** Every declined item has a reply in the thread.

- **`\r` was a real hole (accepted).** `cmd_evidence` tested `"\n" in text` and every account
  fixture here uses `\n`, so nothing could see a **lone carriage return** — an old-Mac line
  break carrying a genuine second line into frontmatter. Now `"\n" in text or "\r" in text`,
  with mutant `evidence_cr_ignored` reverting exactly that half: **CAUGHT, 1 red of 79**.
- **A control row whose name and fixture disagreed (accepted — the best comment of the
  round).** `check is clean on the ticket a refused done left behind` ran straight after a
  **successful `note`**, so it was green about a fixture no refusal had touched. Rule 12
  inside a control. The refusal now runs on that fixture with its own assertions as a
  separate row.
- **Ruff F541 (accepted).** An `f""` with no placeholder.
- **"Remove only one terminal newline; preserve other whitespace" (declined).** `strip()`
  removes only whitespace, so nothing a caller wrote is lost; the reviewer's own example
  (`printf 'proof\n\n'`) loses nothing, while `printf 'para1\n\npara2\n'` still contains
  `\n` and is still refused. The proposed rule would refuse a good one-line file that ends
  in a blank line — a refusal firing where nothing is wrong. Both blank-line cases are
  pinned as **accepting** rows so the decision is visible rather than assumed.
- **"Write cardinals as digits" (2 of ~15 accepted).** The rule's stated purpose in
  `AGENTS.md` is that a staleness check can read a count of *what the project has*. Fixed:
  *"a closed class of five"* → `5`, and *"The two headings seen so far"* — a census of the
  table under it — replaced by making **the table its own census**, which is what
  `AGENTS.md` asks for when a quantity has no producer. Declined for the determiners
  (*"one sentinel, one meaning"*, *"One process"*, *"one unbroken line"*): they count
  nothing the project has, cannot go stale, and `1 sentinel, 1 meaning` is worse prose
  protecting nothing.

## note 2026-08-23, review round 2 and hand-back

One comment, **declined**, code unchanged. Recorded because the disproof is worth more than
the verdict.

**The claim:** `evidence_empty_allowed`'s replacement omits `return 1` from its anchors, so
after `_write_copy` the mutated file reads `if False:` followed by an *unconditional*
`return 1`, making valid one-line evidence fail too — a mutant testing the wrong behaviour
while reporting CAUGHT.

**It is false, and two independent things say so.** `_write_copy` was run and the generated
file read: `return 1` is still indented **inside** the `if False:` block, dead together with
the `print`. And the mutant's own output is the stronger check — **3 red of 79, 0 unnamed**,
exactly the 3 empty-evidence rows, with every accepting row (`a normal inline evidence
string still stores unchanged`, `the same through testing`, `stores a ONE-LINE stdin string
in full`, `carries a backtick that argv cannot`) still **green**. If valid evidence had
started failing, those rows are what would have gone red. They exist for exactly that (rule
15: a mutant asks whether a check *can* fail; only a variant asks whether it can still
*pass*).

**The second half — "fail `_cycle` when unnamed control rows go red" — was declined on a
measurement, not on principle.** Over the 21 mutants here, **9 produce unnamed reds**, 8 of
them predating this ticket:

| mutant | red | unnamed |
|---|---|---|
| `evidence_no_stdin` | 13 | 9 |
| `note_truncates` | 8 | 5 |
| `note_writes_worktree` | 8 | 5 |
| `escape_ignored` | 4 | 3 |
| `note_no_separator` | 5 | 2 |
| `evidence_multiline_allowed` | 5 | 2 |
| `evidence_refusal_still_writes` | 7 | 2 |
| `status_dropped` | 3 | 1 |
| `legacy_dropped` | 3 | 1 |

An unnamed red is normally **correct**: `evidence_no_stdin` removes one sentinel that `note`
and `done` both read, so 9 of its 13 red rows are `note`'s — that shared reading is the
whole change. The proposal would report 9 failures with no defect behind any of them.

**What the review did buy:** the question was fair and the file did not answer it, so
`_cycle`'s docstring (`420b994`) now carries the measurement, why an unnamed red is reported
rather than failed, and what actually guards the case — the accepting rows, with
`evidence_empty_allowed`'s 3-red-0-unnamed as the worked example.

## Where this ended

`in_testing`, branch `task-120-evidence-stdin-sentinel`, PR #6, head `420b994`. **Two review
rounds, which is the budget** — round 1 at `8c07811` (4 comments), round 2 at `f72f402` (1).
Nothing is outstanding in the thread; every declined item has a reply.

**Round 2 reviewed `f72f402`, not `420b994`.** The final commit is the docstring paragraph
above and nothing else, so the code the reviewer saw is the code being merged.

Final gates, unpiped: `tasks_control.py` **79 measurements, 0 FAILED, 0 NOT CHECKED**;
`tasks_mutants.py --selftest` **21 mutants, 0 survived**, inert **SURVIVED (0 red of 79)**;
`docstat.py --sweep` exit 0 over 183 docs; `tasks.py check` exit 0 at 120 tasks.

This ticket's own `testing` transition was made with the repaired command, so the hand-back
exercises the code it is about.
