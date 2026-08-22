#!/usr/bin/env bash
# Four-stack bake-off. Per stack: check-suite (writes that stack's control
# floors) immediately followed by run (which snapshots them into the run dir).
# Never interleave stacks — floors.json is global until snapshotted.
#
# Each trial spawns a BLANK `claude -p` session in a fresh copy of the template.
# The agent sees only that template and the task prompt: no conversation
# context, no global CLAUDE.md (--setting-sources project), no operator MCP
# servers (--strict-mcp-config).
set -u
cd "$(dirname "$0")"
TRIALS="${TRIALS:-2}"
for pair in "bakeoff-rust:../template" \
            "bakeoff-ts:../template-ts" \
            "bakeoff-unity:../template-unity" \
            "bakeoff-godot:../template-godot"; do
  suite="${pair%%:*}"; tmpl="${pair##*:}"
  echo "═══════════ $suite ($tmpl) $(date +%T) ═══════════"
  if ! python3 runner.py check-suite --suite "suites/$suite.toml" --template "$tmpl" 2>&1 | tail -6; then
    echo "!! control failed for $suite — skipping its run"; continue
  fi
  python3 runner.py run --suite "suites/$suite.toml" --template "$tmpl" \
      --trials "$TRIALS" --parallel 1 2>&1 | grep -vE "^\s*$"
done
echo "═══════════ BAKE-OFF COMPLETE $(date +%T) ═══════════"
