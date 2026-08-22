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
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0

# Never block on a cold setup. `just verify` with no node_modules/ and no
# browser downloads ~100MB first, and gating on that would be worse than the
# problem this solves.
[ -d node_modules ] || exit 0

output=$(just verify 2>&1)
[ $? -eq 0 ] && exit 0

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
