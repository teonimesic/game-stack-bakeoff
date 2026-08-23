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

root=$(git rev-parse --show-toplevel) || exit 1
cd "$root" || exit 1

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

failed=""
run() {
    # No pipe. A pipeline's exit status is the last stage's (AGENTS.md rule 3).
    if ! python3 "$@"; then
        failed="$failed
  python3 $*"
    fi
}

run eval/tools/docstat.py --selftest
run eval/tools/docstat.py --findings
run eval/tools/docstat.py --withdrawn

if [ "$queue_blocks" = 1 ]; then
    run eval/tools/tasks.py check
elif ! python3 eval/tools/tasks.py check; then
    printf '\n%s: tasks.py check is RED on the SHARED queue in the main checkout.\n' "$tier" >&2
    printf 'Not blocking here — this is a linked worktree and the queue is not in this commit.\n' >&2
fi

# pre-push only: 10.9s measured, which is past what a per-commit hook can hold before it
# gets bypassed as a habit. It is also the gate that actually failed — the stale-citation
# rows stayed red across several merges because nothing was running it.
if [ "$tier" = pre-push ]; then
    run eval/tools/docstat.py --sweep
fi

if [ -n "$failed" ]; then
    printf '\n%s: gate(s) RED:%s\n' "$tier" "$failed" >&2
    printf 'Fix it, or use --no-verify and say why in the commit message or the handback.\n' >&2
    exit 1
fi
exit 0
