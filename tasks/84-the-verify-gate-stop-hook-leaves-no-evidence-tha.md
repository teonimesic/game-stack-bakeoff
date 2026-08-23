---
id: 84
title: The verify-gate Stop hook leaves no evidence that it ran
status: done
priority: 2
refs: eval/starters/*/.claude/hooks/verify-gate.sh, eval/wholegame.py, tasks/78
done_when: either every starter's verify-gate.sh records each invocation and its verdict somewhere the harness collects and the graded diff does not see, with a control showing a green run and a blocked run are distinguishable afterwards from stored artifacts alone and a control showing the log does not appear in diff.stat or the submission tarball, or the hook is measured live in one real trial per stack and the result recorded so that 'the gate is live in all four' stops resting on file presence
established_by: 'Branch one of the done_when, on branch task-84-stop-hook-audit-trail, commit 5f001a5. All four verify-gate.sh hooks append two tab-separated lines per invocation to STARTER_HOOK_LOG - invoked with the project directory, then pass, block, skip with the guard that fired, or no_project_dir. wholegame.py addresses that at runs/RUN/artifacts/TRIAL/hook_log.tsv, summarises it into trials/TRIAL.json under stop_hook with absent as a distinct third value, and stores leaked_into_tree per trial; hook_log_path refuses to launch a trial whose log address is inside the tree, because the tree becomes the graded diff (#106). Both directions measured with eval/tools/hook_audit_control.py: 7 ok 28 FAILED exit 1 with the four hooks reverted, 39 ok 0 FAILED exit 0 after, the 7 being harness rows that were not reverted. Eight directions per stack - green, blocked, cold, the three arms pairwise DISTINCT, a per-arm assertion that nothing appeared inside the project dir, a grader row rebuilding diff.stat and tree.txt and submission.tar.gz and requiring the log in none, a MUTANT with every hook_log call deleted which makes green go red, and two VARIANTS: append-not-truncate over a pre-seeded log, and the unset-variable fallback still landing outside the tree. Four further rows drive wholegame.build_trial itself with run_agent replaced, asserting the substitution took effect before reading anything from it. The live direction, which no shim can supply, ran twice against the real claude CLI with the harness flags: STARTER_HOOK_LOG reaches the hook, nothing appears in the project dir, 0.045 USD for the run whose result JSON parsed. Gates: verify_blind BLIND exit 0 on out-of-repo copies of all four, 81 criterion ids, and CONTAMINATED exit 1 with a criterion id planted in the edited hook so the scanner was shown able to fail on this input; starter_parity --skip-tests exit 0 no drift, chains 401 on all four, guide word counts 2032/2267/2209/2273 unmoved because no guide was edited, Stop still wired in 4 and named in 4; parity_selftest 60 expectations 0 failed exit 0 with the ts positive control really running 67/67 via a node_modules symlink to the main checkout whose lockfile hashes equal; starter_gate_control --skip-verify on rust and ts, 4 measurements each 0 FAILED exit 3 for the NOT CHECKED arms; bash -n exit 0 on all four hooks; no justfile or _shared file references verify-gate or STARTER_HOOK_LOG, so no recipe reaches the hook. tasks.py check 99 tasks well-formed. docstat --sweep is RED on this branch for exactly one reason and it is proved: eval/RUNS.md skips seventeenth, because this worktree forked before main''s SEVENTEENTH break merged - with a placeholder seventeenth inserted the sweep reads clean exit 0, and with the RUNS.md change stashed it is exit 0, so the gap closes on merge. A duplicate ordinal was the alternative and is worse. No finding number taken: tasks/86 owns numbering this one and now carries a note that the defect is repaired. Not established and stated in the ticket: no real trial has yet run under the trail, and stop_hook absent on any trial of the next matrix is a defect to chase, not a green gate.'
---

Measured under task 78, at CLI 2.1.220 with the harness's own flags: a Stop hook that BLOCKS writes a user entry with isMeta true beginning 'Stop hook feedback:' into the transcript; a Stop hook that EXITS 0 writes nothing anywhere. Both arms of that control are recorded in tasks/78. Consequence: across every stored trial transcript, 19 carry a block and all 19 are dated 2026-08-11 or 2026-08-12; no transcript from wg-matrix (2026-08-13) onward carries one. That single observation is equally consistent with 'just verify was green at every stop' and with 'the hook never ran', and NO stored artifact separates them. Task 67 recorded the hook as live in all four arms on the strength of file presence, which is rule 2 - never infer a process's state from its artifact's state. What is established is only that the per-stack warm guards could not have short-circuited in wg-g4c: node_modules, Library, CARGO_TARGET_DIR and just on PATH all held in the live work trees. The fix is an audit trail - AGENTS.md: record the inputs a component actually consumed, not merely the output it produced. The design constraint that makes this non-trivial and is why it is a separate ticket: the trial tree BECOMES the graded diff, so a log written into the project directory contaminates files_changed, tree.txt, diff.stat and the submission tarball, which is exactly the shape of #106. It has to land outside the tree - an env var the harness sets, or TMPDIR - and that is a starter edit plus a harness change, so it is a regime boundary with three gates.

---

## What was done, 2026-08-23 — branch one of the done_when

Branch `task-84-stop-hook-audit-trail`. The full regime note, with every gate figure, is
`eval/RUNS.md`, **"ALL FOUR STOP HOOKS GAINED AN AUDIT TRAIL ON 2026-08-23"** — cite the
heading, not the ordinal.

**The shape.** Each `eval/starters/*/.claude/hooks/verify-gate.sh` appends two tab-separated
lines per invocation to `$STARTER_HOOK_LOG`: `invoked` carrying the project directory, then one
of `pass` / `block` / `skip <guard>` / `no_project_dir`. `eval/wholegame.py` addresses that at
`runs/<run>/artifacts/<trial>/hook_log.tsv`, summarises it into `trials/<trial>.json` under
`stop_hook`, and stores `leaked_into_tree` per trial.

## THINGS THE NEXT AGENT MUST NOT RE-DERIVE

1. **The CLI DOES pass a custom environment variable through to a Stop hook it spawns.**
   Measured live, twice, with the harness's own flags, at $0.045 for the run whose result JSON
   parsed. `tools/hook_audit_control.py --live` is that measurement, kept. No shim can answer
   it, and every offline row is a statement about bash until it runs.
2. **`CLAUDE_PROJECT_DIR` arrives RESOLVED.** `/var/folders/...` was passed and
   `/private/var/folders/...` came back. Only matters if something compares it to an
   unresolved path — the offline control does, and compares unresolved on purpose.
3. **`--output-format json` returns a STREAM of typed events, not one object.**
   `json.loads(stdout).get("total_cost_usd")` reads an array and silently returns nothing;
   `wholegame.parse_agent` is the one correct reader. That cost one re-run.
4. **`skip` is the value that did not exist and matters most.** Every hook short-circuits on a
   warm guard, and a short-circuit was indistinguishable from a pass in every artifact stored.
5. **The log is TSV, not JSONL, deliberately.** Every one of these hooks carries a comment
   saying shell-interpolated JSON produced an invalid document the first time, and a project
   path with a quote in it would do the same to the log. `printf` is a bash builtin, so the
   line still runs on the PATH where `just` is missing (godot's cold arm).
6. **The guides were deliberately NOT edited.** Telling an agent its gate is being recorded is
   an observer effect on the thing being measured, and it changes nothing an agent should do.
   `starter_parity` still reports Stop wired in 4 and named in 4; all four word counts unmoved.
7. **`parity_selftest`'s ts positive control CAN run in a worktree** — symlink
   `eval/starters/ts/node_modules` at the main checkout's, after checking `pnpm-lock.yaml` and
   `package.json` hash equal. 60 expectations, 0 failed, tests really ran 67/67. Without it the
   worktree reports 54 expectations and 1 environmental failure, and the six expectations after
   the abort never run at all.

## The durable check

`eval/tools/hook_audit_control.py`, wired into `tools/precampaign_smoke.py`. Offline, ~3s, no
toolchain — `just` is a shim that exits 0 or 1 on demand. Eight directions per stack, three
harness-helper rows, and four rows that drive `wholegame.build_trial` itself with `run_agent`
replaced (a helper that works and is called from nowhere is #133's shape; the substitution is
asserted to have taken effect before anything is read from it). Per stack: green / blocked / cold, the three arms' logs pairwise DISTINCT, a per-arm
assertion that nothing appeared inside the project dir, a `grader` row rebuilding `diff.stat`,
`tree.txt` and `submission.tar.gz` and requiring the log in none of them, a MUTANT (every
`hook_log` call deleted — `green` must go red), and two VARIANTS: append-not-truncate over a
pre-seeded log (a hook using `>` passes every single-invocation row), and the unset-variable
fallback still landing outside the tree.

**Both directions, measured:** 7 ok / 28 FAILED, exit 1 with the four hooks reverted;
39 ok / 0 FAILED, exit 0 after. The 7 that pass in the red arm are the harness rows, which
measure `wholegame.py` and were not reverted. `verify_blind` was likewise shown able to fail on this exact
input — a criterion id planted in the edited hook returns CONTAMINATED, exit 1.

## What is NOT established

- **No real trial has run under the trail yet.** It is proved to work under the CLI on a
  throwaway project, not on a `g1_pong` build. The first matrix that runs will be the first
  evidence about the four real starters' guards, and `stop_hook.log == "absent"` on any trial
  of it is a defect to chase, not a green gate.
- **`starter_gate_control.py` was run on rust and ts only, with `--skip-verify`** (4
  measurements each, 0 FAILED, exit 3 for the NOT-CHECKED arms). godot's `just verify` opens a
  window on the operator's desk and unity needs an editor launch, so the full ~15-20 minute
  sweep was left for `precampaign_smoke`. The mechanical argument that it cannot have moved:
  `grep` for `verify-gate` and `STARTER_HOOK_LOG` over the four justfiles and
  `starters/_shared/` returns nothing, so no recipe reaches the hook, and the tree-state
  direction compares a tree with itself across a recipe, which is content-independent.
- **`docstat.py --sweep` is RED on this branch, for one reason, proved.** It reports
  `eval/RUNS.md skips seventeenth between fifth and eighteenth`. This worktree was forked
  before main's SEVENTEENTH break was merged. Control: with a placeholder seventeenth heading
  inserted the sweep reads `sweep clean`, exit 0; with the RUNS.md change stashed, exit 0. The
  gap closes on merge. **A collision was the alternative and is worse** — a gap is repaired by
  a merge, a duplicate ordinal moves the damage to every citation.
- **No finding number was taken.** `tasks/86` owns numbering this one, and eleven collisions
  happened on 2026-08-23. 86's wording can now cite the repair rather than only the defect.
The defect this ticket exists to fix is FINDINGS #130 - read the measurement, its extraction control and its two live probe arms there rather than here, so there is one copy of them. In one line: a Stop hook that BLOCKS is visible in the transcript, one that EXITS 0 leaves nothing anywhere, so no stored artifact separates a green gate from a gate that never ran, and 'the gate is live in all four' had only ever been inferred from file presence, which is rule 2. What this ticket adds to #130 is the fix and the constraint on it. The fix is an audit trail - AGENTS.md: record the inputs a component actually consumed, not merely the output it produced. The design constraint that makes this non-trivial and is why it is a separate ticket: the trial tree BECOMES the graded diff, so a log written into the project directory contaminates files_changed, tree.txt, diff.stat and the submission tarball, which is exactly the shape of #106. It has to land outside the tree - an env var the harness sets, or TMPDIR - and that is a starter edit plus a harness change, so it is a regime boundary with three gates.
