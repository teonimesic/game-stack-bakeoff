#!/bin/sh
# The gate runner both hooks use. `run-gates.sh pre-commit` / `run-gates.sh pre-push`.
#
# ONE FILE, because two hooks spelling the same gate list would disagree eventually and
# the disagreement would look like the repository moving rather than like a bug
# (AGENTS.md rule 12).
#
# Install:  git config core.hooksPath .githooks
# Bypass:   git commit --no-verify  /  git push --no-verify
# Register: .github/workflows/README.md — what runs where, and what is left out and why.
#
# WHAT THIS READS, and it is not the index. These tools read the WORKING TREE, so a
# partial `git add -p` is checked as the tree, not as the commit. The alternative is a
# stash-and-restore hook, and this repository has already lost an hour of uncommitted
# work to a tool that told someone to `git checkout` (#134). A hook that can destroy
# work is worse than a hook with a stated blind spot.
set -u

tier="${1:?usage: run-gates.sh pre-commit|pre-push}"

# VALIDATE THE TIER, because an unrecognised one FAILS OPEN. `pre-push` is selected by an
# equality test below, so `run-gates.sh pre-pushx` would silently run the pre-commit set,
# skip the sweep, print `pre-pushx: ...` and exit 0 -- fewer gates, and indistinguishable
# from a hook that worked. AGENTS.md rule 7: every reason not to run a check is a channel a
# bug can widen. Raised by CodeRabbit on PR #3.
case "$tier" in
    pre-commit|pre-push) ;;
    *) printf 'run-gates.sh: unknown tier %s (want pre-commit or pre-push)\n' "$tier" >&2
       exit 2 ;;
esac

root=$(git rev-parse --show-toplevel) || exit 1
cd "$root" || exit 1

# NESTING IS BOUNDED, AND IT HAS TO BE. `ci_minutes.py --selftest` is one of the gates
# below, and its control RUNS THIS SCRIPT -- once under GATES_LIST_ONLY to prove the mode
# lists, and once with the flag off and `python3` shadowed on PATH by a shim, to prove the
# mode does not execute. The shim is the only thing standing between that second call and
# the gate list, so if it ever stopped intercepting `python3`, hook and gate would call each
# other without bound. That is worse than either failing: a check whose failure mode is a
# HANG reports nothing at all, which ci_minutes.py's own docstring records having measured
# one exit away. So depth is counted -- one hook, one control invocation beneath it -- and
# anything deeper refuses BY NAME and BY VALUE, which turns the hang back into a red line.
# THE VALUE IS MATCHED, NEVER COMPUTED ON. This hook is the only writer of GATES_DEPTH and
# it writes 1 or 2, so unset/0/1 is the whole set that may enter -- a CLOSED class, and the
# default branch refuses everything else. Arithmetic here would set the ceiling aside rather
# than reach it, and fail OPEN doing it: measured under /bin/sh, `$((${GATES_DEPTH:-0} + 1))`
# reads -1000 as -999 and allows 1002 levels, and reads `abc` as 0 and starts the count over.
# Raised by CodeRabbit on PR #60.
case "${GATES_DEPTH:-0}" in
    0) depth=1 ;;
    1) depth=2 ;;
    2) printf 'run-gates.sh: GATES_DEPTH=2 makes this depth 3, past the ceiling 2.\n' >&2
       printf 'A gate below is running this hook, and its shim is not intercepting python3.\n' >&2
       exit 3 ;;
    *) printf 'run-gates.sh: GATES_DEPTH=%s is not a value this hook writes.\n' \
           "${GATES_DEPTH:-0}" >&2
       printf 'Only unset, 0 or 1 may enter; this hook writes 1 or 2 for the gate beneath it.\n' >&2
       exit 3 ;;
esac
GATES_DEPTH="$depth"
export GATES_DEPTH

# THE QUEUE IS NOT YOURS TO GATE ON FROM A WORKTREE. `tasks.py` resolves `tasks/` to the
# MAIN checkout on purpose, so from an agent worktree `tasks.py check` reads a queue this
# commit does not contain and that peers are writing to concurrently. Measured 2026-08-23:
# it went red mid-session on `109: status 'in_review' not in (...)`, a peer's in-flight
# edit, and would have blocked a commit that touched no task file.
#
# So it BLOCKS where the queue is yours (the main checkout, which is where merges happen)
# and WARNS where it is somebody else's. A gate that fires on another agent's work is a
# gate that gets bypassed as a habit, and bypassing is silent. CI blocks on it either way:
# there the checkout root IS the queue root, and the queue is the committed one.
if [ "$(git rev-parse --absolute-git-dir)" = "$(git rev-parse --path-format=absolute --git-common-dir)" ]; then
    queue_blocks=1
else
    queue_blocks=0
fi

# LIST-ONLY MODE, and it is what makes the register checkable rather than believed.
# `.github/workflows/README.md` names the commands each tier runs. That is one fact spelled
# in two files, so `ci_minutes.py --selftest` asserts them equal (AGENTS.md rule 12) -- and
# it reads THIS SCRIPT by running it rather than by re-parsing it, so the list it checks
# comes out of the same control flow the hook takes. A second reader of the source can
# disagree with the source; running it cannot.
#
#   GATES_LIST_ONLY=1 .githooks/run-gates.sh pre-push
#
# prints one `python3 ...` line per gate, executes none of them, and exits 0.
list_only() { [ "${GATES_LIST_ONLY:-}" = 1 ]; }

failed=""
run() {
    if list_only; then printf 'python3 %s\n' "$*"; return 0; fi
    # No pipe. A pipeline's exit status is the last stage's (AGENTS.md rule 3).
    if ! python3 "$@"; then
        failed="$failed
  python3 $*"
    fi
}

# The same gate, advisory instead of blocking. A SEPARATE function rather than a flag on
# `run`, so that both spellings go through `list_only`: the queue lint used to be invoked
# directly in the warning branch, which made the tier's command list depend on which
# checkout you were standing in, and would have executed it under a list-only run.
run_advisory() {
    if list_only; then printf 'python3 %s\n' "$*"; return 0; fi
    if ! python3 "$@"; then
        printf '\n%s: python3 %s is RED on the SHARED queue in the main checkout.\n' \
            "$tier" "$*" >&2
        printf 'Not blocking here — this is a linked worktree and the queue is not in this commit.\n' >&2
    fi
}

run eval/tools/docstat.py --selftest
run eval/tools/docstat.py --findings
run eval/tools/docstat.py --withdrawn

if [ "$queue_blocks" = 1 ]; then
    run eval/tools/tasks.py check
else
    run_advisory eval/tools/tasks.py check
fi

# pre-push only, for two different reasons. No figure is written down for either: hook
# timings are local wall clock on one machine, and two readings taken for task 153 on the
# same host minutes apart differed by more than the whole pre-commit tier costs. Time the
# tier you care about with `time .githooks/run-gates.sh pre-push`.
#
# `docstat --sweep` is here because it costs a multiple of the others, and a per-commit hook
# past a few seconds gets bypassed as a habit. It is also the gate that actually failed —
# the stale-citation rows stayed red across several merges because nothing was running it.
#
# `ci_minutes --selftest` is here for the opposite reason: it is cheap, and what makes it a
# push-time gate is its DUTY CYCLE — most commits cannot move its verdict, and all of them
# would pay for it. The fraction, its producer and the reasoning are in the register; no
# figure is repeated here, because a comment is a copy nothing can disagree with.
if [ "$tier" = pre-push ]; then
    run eval/tools/ci_minutes.py --selftest
    run eval/tools/docstat.py --sweep
fi

if [ -n "$failed" ]; then
    printf '\n%s: gate(s) RED:%s\n' "$tier" "$failed" >&2
    printf 'Fix it, or use --no-verify and say why in the commit message or the handback.\n' >&2
    exit 1
fi
exit 0
