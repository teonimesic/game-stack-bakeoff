#!/usr/bin/env bash
# Stop hook: refuse to end the turn while `just verify` is red.
#
# Motivated by measurement, not preference. In an 18-trial eval run, 14 trials
# ended with the agent's own `just verify` failing and `terminal_reason:
# completed` - the agent decided it was finished while the gate it had been told
# to respect was red. An instruction in AGENTS.md is advisory; a Stop hook is
# not. Claude Code overrides after 8 consecutive blocks, so this cannot trap a
# session that is genuinely stuck.
#
# Output contract: exit 0 silently to allow the turn to end; print a JSON object
# with decision=block to keep it going, with a reason the agent can act on.

set -uo pipefail

# AUDIT TRAIL: one line saying the hook RAN, one saying what it decided.
#
# MEASURED (CLI 2.1.220, the harness's own flags): a Stop hook that BLOCKS writes
# a "Stop hook feedback:" entry into the transcript; a Stop hook that EXITS 0
# writes NOTHING, ANYWHERE. So "no block in the transcript" cannot tell a gate
# that passed from a gate that never ran, and the archive's only blocks come from
# two days in August. "The gate is live in all four arms" rested on the file
# being present in the starter, which is AGENTS.md rule 2 - never infer a
# process's state from its artifact's state.
#
# THE LOG MUST NOT LAND IN THE PROJECT DIRECTORY. The trial tree becomes the
# graded diff, so a file written here turns up in files_changed, diff.stat,
# tree.txt and submission.tar.gz - the shape of #106, a gate that rewrote the
# tree it was measuring. `eval/wholegame.py` passes an absolute path OUTSIDE the
# tree in STARTER_HOOK_LOG and refuses to launch a trial if it is inside; with no
# harness it falls back to $TMPDIR, which is outside too.
#
# Tab-separated, not JSON, for the reason recorded further down this file: shell
# interpolation of JSON produced an invalid document the first time it was
# written here, and a project path containing a quote would do it again.
HOOK_LOG="${STARTER_HOOK_LOG:-${TMPDIR:-/tmp}/starter-verify-gate.tsv}"
hook_log() {
  printf '%s\t%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" rust "$1" "${2:--}" \
    >> "$HOOK_LOG" 2>/dev/null
}
hook_log invoked "${CLAUDE_PROJECT_DIR:-$PWD}"

if ! cd "${CLAUDE_PROJECT_DIR:-.}"; then
  hook_log skip no_project_dir
  exit 0
fi

# Never block on a cold build: `just verify` from an empty build directory takes
# minutes, and gating on that would be worse than the problem this solves.
#
# MEASURED BUG, fixed here: this used to test `[ -d target ]`. Any harness that
# sets CARGO_TARGET_DIR - which is the normal way to give each run an isolated
# build cache - has no `target/` in the project directory, so the hook silently
# disabled itself in exactly the situation it was written for.
#
# The skip is LOGGED with its reason. A short-circuit and a green gate are the
# same silence to everything downstream, and this arm is the one no stored
# artifact could ever see.
if [ ! -d "${CARGO_TARGET_DIR:-target}" ]; then
  hook_log skip cold_build_no_target_dir
  exit 0
fi

output=$(just verify 2>&1)
# `rc` is captured on its own line deliberately: `$?` is the last command's
# status, so anything inserted between the assignment and the test - a log line,
# a diagnostic - silently changes which command is being tested.
rc=$?
if [ $rc -eq 0 ]; then
  hook_log pass
  exit 0
fi
hook_log block

# Build the JSON in Python. Doing it with shell interpolation produced invalid
# JSON the first time (a quoted string nested inside a quoted field), and a
# malformed hook response is indistinguishable from no hook at all.
printf '%s' "$output" | python3 -c '
import json, sys
tail = sys.stdin.read()[-1500:]
print(json.dumps({
    "decision": "block",
    "reason": (
        "`just verify` is failing, so the work is not finished. Fix the cause "
        "and re-run it before stopping. Do NOT disable, skip, ignore, or weaken "
        "a test to get past this gate.\n\nLast output:\n" + tail
    ),
}))
'
exit 0
