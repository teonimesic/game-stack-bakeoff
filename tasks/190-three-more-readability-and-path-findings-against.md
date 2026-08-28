---
id: 190
title: Three more readability and path findings against DECISIONS.md prose from tasks 175 and 185, raised inside another branch's merge
status: todo
priority: 4
refs: DECISIONS.md, eval/tools/ci_minutes.py, eval/judge/capability.py, tasks/175, tasks/185, tasks/188, pull request 62
done_when: Each of the 3 is read against its source and either applied or declined in writing with the reason. The path one is settled by checking which paths exist. docstat.py --sweep and linkcheck.py exit 0 after, both unpiped.
---

CodeRabbit raised 3 outside-diff findings against DECISIONS.md prose that landed on main from tasks 175 and 185. They surfaced on pull request 62 (task 138) only because merging main put those lines in the review's file set; task 138's diff touches none of them, so they were declined there and filed here. One is a correctness issue, not style: two sentences name judge/capability.py and judge/capability_selftest.py while the command above them uses eval/judge/, and docstat.py --sweep deliberately does not check paths.

## note 2026-08-27

The 3, with their line ranges as of `7804aee`:

**1. `DECISIONS.md:1452-1455` — FUNCTIONAL, and the only one that is not style.** The command
above these sentences is `python3 eval/judge/capability.py`, but the sentences beneath it name
`judge/capability.py` and `judge/capability_selftest.py`. A reader following them looks in a
directory that does not exist at the repository root. Settle it by checking which paths exist,
then make all four agree. **`docstat.py --sweep` deliberately does not check file paths** — that
exclusion is recorded in `AGENTS.md`, and `linkcheck.py` only covers markdown links, not paths
named in prose — so nothing catches this class today.

**2. `DECISIONS.md:1723-1730` — READABILITY.** *"What CI has consumed has a producer"* and *"the
projection that used to stand in the register"* make the data flow indirect. Suggested: name the
command, the API input, the rounding rule and the 2 rejected fields in separate sentences. The
2 rejected fields are the interesting content and they are currently buried in a subclause.

**3. `DECISIONS.md:1745-1766` — READABILITY.** The paragraph narrates when the filter moved, cites
a rejected proposal and a prior day, and quotes a pull-request measurement. `AGENTS.md` says a
live document states the choices in force and is not a log of how they got there. Suggested:
replace the history with the current trigger, the scope comparison, the guard and the audit
behaviour.

## Read each against its source before editing

A review comment is a second opinion, not a finding. Item 3's suggested wording asserts specific
behaviour — *"runs on every pull request"*, *"compares the merge commit with its first parent"*,
*"never filters `push`, `schedule`, or `workflow_dispatch`"* — and **that must be read out of
`.github/workflows/controls.yml` and `eval/tools/ci_minutes.py --scope`, not copied from the
review.** Replacing narrative with a confident description of behaviour nobody re-checked is a
worse defect than the narrative.

## Where this came from, and the pattern behind it

Task 138's agent declined all 3 in pull request #62's thread: the lines arrived there through
`git merge origin/main` and are already on `main` from tasks 175 (`6cc8859`) and 185 (`070d316`),
so editing them would have buried two other tickets' wording changes inside task 138's squash
commit.

> **CodeRabbit reviews the file set a merge brings in, not the branch's own diff.** This is the
> third ticket filed from that shape in one session — `tasks/188` from pull request #61,
> `tasks/189` from #62 (superseded by 188), and this one. A branch that keeps itself current with
> a fast-moving `main`, which `.agents/skills/work/SKILL.md` requires, inherits review comments on
> every other agent's landed prose and can never reach a clean round on its own diff. **The
> comments are worth having; what is missing is a route for them that does not attach them to an
> unrelated ticket.** Worth deciding whether that route is a standing ticket, a `.coderabbit.yaml`
> path or base setting, or simply this filing convention written down.

## note 2026-08-28

## note 2026-08-28 (orchestrator) — current at dispatch

**Line addresses have drifted since `7804aee`; locate by content.** Item 1's bare-name
sentences now sit at DECISIONS.md 1472, 1530, 1534, 1536; item 2's paragraph opens at
**~1805** ("What CI has consumed has a producer"); item 3 is the filter/gate narrative in the
`run-gates.sh` / "named subset" row neighborhood.

**Item 1 is measured, not just plausible** (read 2026-08-28): `judge/capability.py` and
`judge/capability_selftest.py` do not exist at the repository root; `eval/judge/capability.py`
and `eval/judge/capability_selftest.py` both do. Adjudicate whether the bare names are paths
(the reviewer's reading) or module names that happen to read as paths — either way the ticket's
bar holds: make the command and the sentences agree.

**What has landed under you since filing:**

- `tasks/192` merged as `e573323`: `eval/tools/ci_minutes.py` gained the register reader that
  locates the checks row inside its table (+321/−8). For item 3, read `--scope` behaviour and
  `.github/workflows/controls.yml` at the CURRENT head — never the filed version.
- `tasks/188` is landing now (PR #69, squash-armed): its DECISIONS.md hunks sit at ~3400+;
  no overlap with any of your three items. Once it lands nothing else holds DECISIONS.md.

**Out of scope for you:** the tail blockquote (a route for outside-diff findings that does not
attach them to an unrelated ticket) is an open process question for the operator; 188's round
confirmed the pattern a third time. Do not decide it inside this ticket.

**Baselines at the head you branch from:** `docstat.py --sweep` clean over 258 docs;
`linkcheck.py` exit 0. Run both unpiped after staging, as your done_when says.
