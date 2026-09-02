---
id: 229
title: heartbeat.py asserts the main checkout is a work tree, then counts the tree its own file lives in
status: in_testing
priority: 3
refs: Clean-up pass 40 (CLEANUP-LOG.md); AGENTS.md rule 12; task 228 for the --selftest pattern and its census consideration; the worktree agents' fork of the fivefold-jump incident, heartbeat.py docstring case 2
done_when: 'heartbeat.py refuses to count, with the refusal naming both paths, when ROOT is not the main checkout (the main path is already computed by _main_checkout_path - the comparison is one line plus the message). The refusal is pinned so it does not decay the way pass-37''s prose-only verification did: a --selftest mode (following findings_control.py''s pattern, task 228) asserts the refusal fires when the two addresses differ and does not fire when they match; if --selftest is added, ci_minutes.py''s census rule applies (named by a workflow step or recorded as left out in .github/workflows/README.md). The pin runs red-first: demonstrate the current code counting happily from a worktree copy before adding the refusal. Hand-run verification counts too, but only if the pin exists afterwards - the reverse (fix now, pin later) is the decay this queue exists to prevent.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/109
established_by: 'PR #109 head b063b41 (025f3a1 fix+pin, 2a908de round-1 order flip, b063b41 round-2 wording): pre-fix heartbeat.py from a worktree copy counted branch-local at exit 0 (runs=0/judge_rounds=0/graded_submissions=0 vs main''s 16/97/85), now refuses at exit 1 naming both paths; heartbeat_control.py 11/11 from a linked worktree and 11/11 from a throwaway main-checkout repo (live row both branches); swapping the two refusal calls in collect() turns exactly bare_main_from_worktree_refuses_address red, and an inverted comparison turns 5 rows red; docstat --sweep, tasks.py check (228 well-formed), ci_minutes --selftest (124 mutants died, 80 variants passed), --controls (47 controls / 31 modes, 0 unrecorded) and --gates (74+12) all exit 0 unpiped against staged trees; CodeRabbit round 1 (4 comments: 3 fixed, 1 declined with evidence) and round 2 (2 comments, both fixed, resolutions confirmed by CodeRabbit inline replies 12:12:18Z and 12:15:15Z) addressed, final round LANDED_COMMENT with nothing actionable.'
---

Cleanup pass 40 read eval/tools/heartbeat.py whole. _assert_main_checkout_is_a_work_tree probes git rev-parse --is-inside-work-tree AT the path git names as the main checkout - and then collect() counts ROOT, derived from __file__, i.e. the checkout the RUNNING COPY lives in. Nothing compares the two. Run from a linked worktree's copy (agent worktrees are full checkouts), the refusal passes - the main checkout IS a work tree - and every count goes branch-local: findings, tasks and project_lines become plausible-and-wrong for the branch (read as work disappearing), and eval/runs/ is absent in a fresh worktree so the three output counts read 0. The docstring's claim that worktrees are 'excluded by construction' is true only when the copy that runs is the main checkout's - AGENTS.md states that exclusion as a property of the metric, and it is a property of the invocation address. This is AGENTS.md rule 12's shape exactly: the check verifies one address while the measurement reads another.

## note 2026-09-01

## note 2026-09-01

Landed on PR #109 (3 commits: 025f3a1 fix + pin, 2a908de review-round-1 order flip,
b063b41 round-2 wording), 2 of the 5 review rounds used, final round LANDED_COMMENT.

**The pin is NOT a --selftest mode, and the ticket's letter was wrong about that.**
Pass 40 read `heartbeat.py` whole and missed that `eval/tools/heartbeat_control.py`
already existed (task 184 / PR #64, gated in gates.yml on every push, built around a
throwaway main checkout plus a linked worktree). The refusal is pinned there instead:
end-to-end in fresh processes, already on a duty cycle, and census-neutral -- heartbeat.py
declares no --selftest, so ci_minutes' mode population stayed 31 and no register count
moved. A new mode would have duplicated the pin and moved 3 ci_minutes selftest pins for
the same protection. The `done_when`'s other parts are met as written: the refusal names
both paths; the pin asserts refusal on differing addresses and counting on matching ones;
red ran first.

**Review round 1 moved the refusal order, which no round of this session's own testing
had questioned.** As first written, the work-tree guard ran before the address
comparison, so a worktree copy with a broken main checkout got the bare refusal -- naming
only the main checkout, and ending "linked worktrees go on working", which that reader
would have taken as licence to count branch-local. `collect()` now runs
`_assert_root_is_main_checkout` FIRST: every refusal a worktree copy can get names both
addresses, and the work-tree refusal only fires where ROOT is the main checkout. The
control's `bare_main_from_worktree_refuses_address` row pins the combined state;
swapping the two calls in collect() (demonstrated in a throwaway main-checkout repo
holding control+heartbeat+tasks.py) turns exactly that row red, 10/11. The same throwaway
repo is how `live_green` was exercised off CI -- the live row is environment-adaptive:
main checkout expects counts, linked worktree expects the refusal with both real
addresses, main path derived from `git rev-parse --git-common-dir` (a different command
than the subject's `worktree list`, per task 113).

**One review suggestion declined, with evidence:** removing the `tasks/229` citation
from the register and AGENTS.md. The register itself cites `tasks/212` and AGENTS.md
carries 5 `tasks/` citations; a citation is sourcing, not history narration. Round 2's
two findings were wording-accuracy defects in sentences this branch added or preserved:
"no history" was false (the fixture holds one local commit) and the "all 3 output counts
as 0" figure named no producer -- both fixed, producer `python3 eval/tools/heartbeat.py`
named in AGENTS.md and the register.

Both mutant anchors in the control assert `count == 1` (cleanup pass 39's rule);
measured at 1 each. The comparison-inverted mutant turns 5 rows red; the pre-fix
worktree counting (exit 0, runs=0, vs main's 16 runs / 97 judge rounds / 85 graded
submissions) was captured before any edit and is reproduced permanently by
`mutant_root_compare_silent`.

No finding number needed: the defect is this ticket's own subject, and every number
above is recorded here and in the commit messages. Nothing was filed.

## Orchestrator verification, 2026-09-01 (against artifacts, throwaway worktree /tmp/p109-verify at b063b41)

Red half reproduced directly: the PR's heartbeat.py run from the worktree copy exits 1 with
the address refusal naming BOTH paths as whole lines plus the one-line repair; the main
checkout's copy (old code) still counts at exit 0. `heartbeat_control.py` from the PR tree:
11/11 rows, including `live_red_from_worktree` against the real repository (the control
itself ran from a worktree, so the new live branch was exercised) and both mutants
reproducing the pre-fix counting at exit 0 with output identical to healthy. Green battery
in the PR tree, unpiped: `docstat --sweep` exit 0 (296 docs; the +1 vs pass 40's 295 is
this ticket becoming tracked in 607e278 — tracked .md sets verified identical),
`--renumbered` exit 0, `tasks.py check` exit 0 (228 well-formed), `ci_minutes --selftest`
exit 0 (124 mutants/80 variants), `ci_minutes --controls` exit 0. GitHub: both required
checks SUCCESS at head b063b41. The recorded deviation from the ticket's letter (pin in the
existing gated heartbeat_control.py rather than a new --selftest mode) is accepted: it is
census-neutral, gated on every push, and the ticket's requirement — the pin exists — is met
in both directions, with the mutant-anchor count==1 assertion from cleanup pass 39 applied.
Merge awaits the operator's explicit approval, with #107 and #108.
