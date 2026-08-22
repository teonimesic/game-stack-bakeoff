#!/usr/bin/env bash
# Stop hook: refuse to end the turn while `just verify` is red.
#
# Motivated by measurement, not preference. In an 18-trial eval run on the sister
# Rust template, 14 trials ended with the agent's own `just verify` failing and
# `terminal_reason: completed` - the agent decided it was finished while the gate
# it had been told to respect was red. An instruction in AGENTS.md is advisory; a
# Stop hook is not. Claude Code overrides after 8 consecutive blocks, so this
# cannot trap a session that is genuinely stuck.
#
# `just verify` here is ~5s warm, so this is cheap. It DOES open a window for a
# second (the render tests cannot run headless - see AGENTS.md).
#
# Output contract: exit 0 silently to allow the turn to end; print a JSON object
# with decision=block to keep it going, with a reason the agent can act on.

set -uo pipefail
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0

command -v just >/dev/null 2>&1 || exit 0

output=$(just verify 2>&1)
[ $? -eq 0 ] && exit 0

printf '%s' "$output" | python3 -c '
import json, sys
tail = sys.stdin.read()[-1500:]
print(json.dumps({
    "decision": "block",
    "reason": (
        "`just verify` is failing, so the work is not finished. Fix the cause "
        "and re-run it before stopping. Do NOT disable, skip, ignore, or weaken "
        "a test, a boundary rule, or a warning level to get past this gate.\n\n"
        "Last output:\n" + tail
    ),
}))
'
exit 0
