#!/usr/bin/env bash
# Stop hook: refuse to end the turn while `just verify` is red.
#
# Motivated by measurement, not preference. In an 18-trial eval run on the Rust
# sibling of this template, 14 trials ended with the agent's own `just verify`
# failing and `terminal_reason: completed` - the agent decided it was finished
# while the gate it had been told to respect was red. An instruction in
# AGENTS.md is advisory; a Stop hook is not. Claude Code overrides after 8
# consecutive blocks, so this cannot trap a session that is genuinely stuck.
#
# Output contract: exit 0 silently to allow the turn to end; print a JSON object
# with decision=block to keep it going, with a reason the agent can act on.

set -uo pipefail
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0

# Never block before the first asset import. `just verify` on an empty
# `Library/` takes ~25s rather than ~10s, and a half-imported project produces
# failures that say nothing about the change under review.
[ -d Library ] || exit 0

output=$(just verify 2>&1)
[ $? -eq 0 ] && exit 0

# Build the JSON with node, not shell interpolation: a quoted string nested
# inside a quoted field produced invalid JSON the first time this was written,
# and a malformed hook response is indistinguishable from no hook at all.
# (node, not python3 — this machine's Homebrew python has a broken pyexpat and
# the tooling here avoids it entirely.)
printf '%s' "$output" | node -e '
let tail = "";
process.stdin.on("data", (c) => (tail += c));
process.stdin.on("end", () => {
  console.log(JSON.stringify({
    decision: "block",
    reason:
      "`just verify` is failing, so the work is not finished. Fix the cause " +
      "and re-run it before stopping. Do NOT disable, skip, ignore, or weaken " +
      "a test to get past this gate.\n\nLast output:\n" + tail.slice(-1500),
  }));
});
'
exit 0
