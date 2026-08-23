---
id: 81
title: The Rust starter ships two binaries in crates/game with no default-run, so just run is ambiguous on a pristine tree
status: done
priority: 3
refs: 'eval/FINDINGS.md #98, eval/tools/disclosure.py, eval/starters/rust/justfile:152, eval/starters/rust/crates/game/Cargo.toml'
done_when: either cargo run -p game --release has been observed on a pristine copy of eval/starters/rust and the observed behaviour recorded (ambiguous-binary error, or it runs), and if ambiguous the starter repaired with the regime boundary recorded in eval/RUNS.md and verify_blind.py plus starter_parity.py re-run; or the decision to leave it is recorded with the reason
established_by: 'REPRODUCED then FIXED. Pristine copy of eval/starters/rust, cargo 1.97.1: cargo run -p game --release --offline exits 101 with could-not-determine-which-binary in under a second having compiled nothing, unpiped. default-run = game added to crates/game/Cargo.toml; the same command then enters compilation with no target-selection error. Both directions also pinned on a two-binary fixture that executes: exit 101 without the key, exit 0 printing RAN=game with it, still RAN=game with a third binary added. The ticket count was low - 12 rust trials across 5 runs, not 4 across 3, from a grep of runs/**/artifacts/*rust*/agent_result.json .result; disclosure.py located 4 of the 12, filed as tasks/94. All 12 predate the seventh comparability break, after which just run returns 1 from the STARTER_NO_RAISE=1 refusal before reaching cargo - verified. Recorded in eval/RUNS.md as THE RUST STARTER GAINED default-run ON 2026-08-23. Gates unpiped: verify_blind BLIND exit 0 on an out-of-repo copy and CONTAMINATED exit 1 with the canary planted in the changed file; starter_parity --skip-tests all four stacks exit 0, no drift, four chains at 401; parity_selftest 60 of 60 exit 0 from the main checkout; docstat --sweep and --selftest exit 0; tasks.py check exit 0. Parity hash chain byte-identical pre and post, 401 hashes, first 0x912e3a873849bcce last 0x9d53ded21eb09ce7, compared through starter_parity.hash_chain with its own perturb-one-tick control reporting a difference. No finding number allocated: ten worktrees live and this branch forked two findings behind main. Branch task-81-rust-default-run.'
---

Four independent Rust agents across three runs (wg-matrix pong t1, wg-matrix tetris3d t1, wg-matrix arena t1, wg-audio48 tetris3d t1) wrote in their closing messages that just run was broken in the starter baseline because crates/game ships two binaries and cargo run -p game was ambiguous; two of them added default-run themselves. Surfaced by eval/tools/disclosure.py on its first pass over the stored corpus - the reader that tasks/71 built. NOT yet reproduced by running cargo: the manifest has no default-run and the crate has src/main.rs plus src/bin/film.rs, which is the documented cargo condition for the error, but nobody has executed the recipe. just run is not a graded criterion (RUNS.md records it as REFUSED under the harness for this stack), so the cost is turns and money inside a trial, not a score - the same shape as FINDINGS 98, which cost no published number either.

## What was established, 2026-08-23 (branch task-81-rust-default-run)

REPRODUCED. On a pristine copy of eval/starters/rust with cargo 1.97.1,
`cargo run -p game --release --offline` exits 101 with "could not determine which binary
to run / available binaries: film, game" in under a second, having compiled nothing. Read
unpiped. FIXED with default-run = "game" in crates/game/Cargo.toml; the same command then
enters compilation with no target-selection error. Both directions were also pinned on a
two-binary fixture that really executes - exit 101 without the key, exit 0 printing
RAN=game with it, and still RAN=game after a third binary is added, which is the shape the
agents actually produced (several of them say "four binaries", not two).

THE COUNT IN THE TITLE AND BODY IS LOW: it is 12 trials across 5 runs, not 4 across 3.
Producer: grep of runs/**/artifacts/*rust*/agent_result.json -> .result for
default-run|two binar|ambiguous|could not determine which binar|just run|cargo run.
wg-matrix (all six rust trials), wg-audio (g1_pong t0, t1), wg-audio48 (g1_pong t0,
g2_tetris3d t1), archive-arena2d-wg-audio48 (g3_arena t0), wg-g4 (g4_platformer t1).
disclosure.py's cue set located 4 of the 12, so it under-reports on the starter-arrived-
broken family as well as on the one its docstring measures. Filed as a follow-up.

THE EXPOSURE IS OLDER THAN IT LOOKS AND IS NOW MOSTLY CLOSED. All 12 trials predate the
seventh comparability break (2026-08-17), after which `just run` on rust returns 1 from
the STARTER_NO_RAISE=1 refusal branch BEFORE reaching cargo - verified on a pristine copy.
Both wg-g4c rust agents wrote that they did not launch it. The residual path today is an
agent typing `cargo run -p game` directly, which the Bash allowlist permits and which no
stored trial after that date is on record doing. So this repair buys back turns that were
already being lost before 2026-08-17, and closes a path that is currently unexercised
rather than one costing money today.

WHY default-run AND NOT `--bin game` IN THE RECIPE: the failing thing is the command, by
whatever path it is typed, and agents type it directly. Repairing only justfile:152 leaves
every other caller broken. `just film` and `just probe` already pass --bin and were never
affected; justfile:152 is the only unqualified `cargo run -p game` in the tree.

THE CHANGE IS INERT TO EVERYTHING THE PARITY GATE MEASURES. Hash chain byte-identical
before and after (401 hashes, seed 7, starter_parity's own tape; first 0x912e3a873849bcce,
last 0x9d53ded21eb09ce7), compared through starter_parity.hash_chain itself rather than a
re-implementation, with its own control - perturb one tick - reporting a difference.
Recipes 19 both sides, AGENTS.md 2032 words both sides, harness files unchanged.

GATES, all unpiped. verify_blind.py on an out-of-repo copy of the repaired starter: BLIND,
81 criterion ids, exit 0 - and CONTAMINATED, exit 1 with the canary planted in the very
file that changed. starter_parity.py --skip-tests over all four stacks with the repaired
rust in place: exit 0, no drift, all four chains 401. parity_selftest.py: 60 expectations,
0 failed, exit 0 - run from the MAIN CHECKOUT, because a worktree has no node_modules and
its ts positive control cannot run there; in a worktree it reports exactly that one
failure, which is environmental and which eval/AGENTS.md already documents.
docstat.py --sweep and --selftest: exit 0. tasks.py check: exit 0.

DO NOT RE-DERIVE: docstat --sweep's flag check exempts any LINE matching
_DELIBERATELY_FAKE (does not exist|phantom|plant\w*|do not name them), so a control that
plants a fake flag and calls it "phantom" silently passes and reads as "the check is
dead". Use a neutral sentence. cargo's `--bin` is now in FOREIGN_FLAG_PREFIXES because
eval/RUNS.md quotes cargo's own error text verbatim.

NO FINDING NUMBER WAS ALLOCATED. Ten agent worktrees were live and this branch forked two
findings behind main (#129 against #131), which is the collision the work skill says to
avoid. If a number is wanted for "a starter recipe was red on a pristine tree for ten days
and twelve agents each repaired it privately", the orchestrator should allocate it.

RECORDED IN eval/RUNS.md as "THE RUST STARTER GAINED default-run ON 2026-08-23". The
ordinal reads SIXTEENTH against main at 4052927; cite the heading, not the number.
