---
id: 190
title: Three more readability and path findings against DECISIONS.md prose from tasks 175 and 185, raised inside another branch's merge
status: done
priority: 4
refs: DECISIONS.md, eval/tools/ci_minutes.py, eval/judge/capability.py, tasks/175, tasks/185, tasks/188, pull request 62
done_when: Each of the 3 is read against its source and either applied or declined in writing with the reason. The path one is settled by checking which paths exist. docstat.py --sweep and linkcheck.py exit 0 after, both unpiped.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/70
established_by: 'Verified against artifacts: true scope from merge-base a9de747 is DECISIONS.md only (56+/51-), no spill into task 193''s repo-wide class, starters untouched, no finding numbers allocated on the branch. The bare-path class checked in the branch tree: zero bare judge/ or tools/ refs remain, the boundary.gd starter-relative exception stands at :1446, and every eval/judge/* and eval/tools/* path referenced in the new DECISIONS.md text exists in the tree. Claims verified against source, not the handback: the filter list in the rewritten scope-step section matches FILTER_PREFIXES/FILTER_EXACT exactly (ci_minutes.py:136-137); the 607s/588s run_duration figure is the tool docstring at :16; the lint producer-deferral reconciles with a live lint.py --counts run (112 total, per-rule counts match the ticket census). Gates reproduced myself in the branch worktree at 33d8be8: docstat.py --sweep exit 0, linkcheck.py exit 0, both unpiped; CI controls+gates green at that head. Review loop 3 of 5 rounds, both declines evidence-backed (finding-number allocation is the merge orchestrator''s; refused-field measurements are the reasons), reviewer accepted both at round 3, no unresolved threads. Merged squash as f84972d; branch and worktree cleaned.'
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

## note 2026-08-28

## Round 1 adjudications, and the relocated lint census (2026-08-28)

CodeRabbit round 1 (PR #70) returned 2 comments, both on this task's own edits. Both threads
answered on the pull request; this records what was done.

**The dated lint census moved here out of DECISIONS.md** (review comment at DECISIONS.md ~1689).
The paragraph there keeps the reason — the triage-to-0 did not hold — and points at the
producer; the per-site list is archive material:

> Re-measured later the same day as the 2026-08-23 triage there were 11 new sites: 10
> `PLW1510` (`eval/judge/blind_dir_selftest.py`, `eval/judge/blind_ext_selftest.py`,
> `eval/judge/starter_parity.py` x2, `eval/tools/disclosure_mutants.py`,
> `eval/tools/findings_control.py`, `eval/tools/tasks_control.py` x3,
> `eval/tools/tasks_mutants.py`) and 1 `BLE001` (`eval/tools/tasks_control.py:497`).
> Paths in that list were bare (`judge/...`, `tools/...`) in DECISIONS.md until this task
> prefixed them; they were verified to resolve under `eval/` before the edit.

Current counts, read 2026-08-28 with the producer (`python3 eval/tools/lint.py --counts`):
37 `PLW1510`, 8 `BLE001`, and the untriaged backlog 17 `F541`, 14 `F401`, 13 `B905`, 10 `B007`,
7 `B023`, 4 `F841`, 1 `B904`, 1 `S112`. Never quote these without the command.

**What this task established, for the next agent:**

- Item 1 (the path finding) was applied to all 23 bare `judge/`-/`tools/`-prefixed references in
  DECISIONS.md, each verified against the filesystem; `tools/boundary.gd` at the capability
  decision is starter-relative (`eval/starters/godot/tools/boundary.gd`) and deliberately left
  bare — prefixing it would manufacture a phantom path. The same class in OTHER live documents
  is task 193, and there the frame differs: docs under `eval/` write eval-relative commands
  (`python3 judge/bot_mutants.py` works from `eval/`), so bare paths there need a per-document
  frame check, not a blind prefix. DECISIONS.md is root-frame, which is what made all 23 wrong.
- Items 2 and 3 were rewritten from `eval/tools/ci_minutes.py` and
  `.github/workflows/controls.yml` at the post-task-192 head, never from the review's wording.
  Verified claims worth not re-deriving: `scope_decision` returns True for every
  non-`pull_request` event, None and empty changed-path sets; `pull_request_changed_paths`
  diffs the merge commit against its first parent; `emit_scope` prints verdict, filter, reason
  and changed paths and treats an unwritable `$GITHUB_OUTPUT` as an error, not a false;
  `run_duration_ms` is measured once in the tool's docstring (607 s run vs 588 s job,
  run 32657248359) and is not fetched on the census path; `billable.UBUNTU.total_ms` IS read
  every census run (`fetch_billable_field`) but only for the audit trail.

## note 2026-08-28

## Round 2 adjudications (2026-08-28)

Round 2 returned 2 outside-diff Minors against the item-3 rewrite (they live only in the review
summary — no inline threads to reply to; the adjudication is recorded in the PR body). Both
acted on in commit 33d8be8:

- Taken: a non-`pull_request` event is an explicit class, not an unknown diff. The guard
  paragraph now separates the two, in the order `scope_decision` branches: unknown or empty
  pull-request diffs run the whole suite, and so does every non-`pull_request` event, because
  scope filtering applies only to pull requests.
- Taken in part: the scope paragraph states current behaviour directly (scope step runs
  `python3 eval/tools/ci_minutes.py --scope` before the slow suites; merge commit vs first
  parent; `relevant=true` on a filter match over `eval/`, `.agents/`, `.claude/`,
  `controls.yml`; `relevant=false` only when no changed path matches) and the cross-reference
  to the previous paragraph is gone. Declined removing the house attribution (decided
  2026-08-24, task 131) — every paragraph in the section carries one and it points at the
  decision's evidence.

## note 2026-08-28

**2026-08-28, review round 3 — clean, loop stopped.** `pr_review_state.py` verdict LANDED_COMMENT at head 33d8be8: the one comment was CodeRabbit's acceptance of both round-1 adjudications ("The revised paragraph addresses the structure concern. Keeping the 607 s / 588 s and 0 for 58 of 58 measurements is appropriate... The requested eval/findings/ relocation does not apply to branch work"), and its sibling thread accepted the lint-census fix the same way. No new actionable finding; both prior threads closed by the reviewer. Verified the state directly rather than from the relay: mergeable.py 70 reports controls and gates SUCCESS (required) at 33d8be8, branch behind by 0, no unresolved review thread, GitHub agrees. Two self-checks before closing: the only finding citation near the edited region (#105, DECISIONS.md line 1691) is pre-existing text outside the branch diff, and the document's citation convention is bare #nn throughout, so the reference-link learning CodeRabbit carried was not a finding against this PR; and the removed "Measured at PR #14's head: two gates, zero controls" line was the item-3 edit working as specified — history replaced by current behaviour, the measurement surviving in the PR diff and git history. Rounds used: 3 of 5.
