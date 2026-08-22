#!/usr/bin/env bash
# Compile every assembly (including the EditMode test assemblies) and report
# diagnostics. This is the closest thing Unity has to `cargo check` / `clippy`.
#
# Usage: tools/unity-compile.sh <label> <errors|warnings>
#   errors   -> fail only on `error CS`   (just check)
#   warnings -> fail on warnings too      (just lint, mirrors clippy -D warnings)
#
# `-quit` IS safe here: there is no `-runTests`. It is only a trap when the two
# are combined, because the editor then exits before the test runner starts.
set -uo pipefail

LABEL="$1"
STRICT="${2:-errors}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNITY="${UNITY_BIN:-/Applications/Unity/Hub/Editor/6000.0.45f1/Unity.app/Contents/MacOS/Unity}"
OUT="$ROOT/artifacts"
mkdir -p "$OUT"
LOG="$OUT/$LABEL.log"
rm -f "$LOG"

if [ ! -x "$UNITY" ]; then
  echo "✖ Unity 6000.0.45f1 not found at $UNITY (override with UNITY_BIN=...)" >&2
  exit 127
fi

"$UNITY" -batchmode -nographics -quit -logFile "$LOG" -projectPath "$ROOT"
CODE=$?

# Match ANY Roslyn diagnostic id, not just `CS`: the vendored analyzers in
# Assets/Analyzers/ report PONG#### (determinism) and UNT#### (Unity idioms),
# and a grep for `error CS` would let every one of them through.
ERRORS=$(grep -E '^Assets[/\\].*\)\s*:\s*error [A-Z]+[0-9]+' "$LOG" | sort -u)
WARNINGS=$(grep -E '^Assets[/\\].*\)\s*:\s*warning [A-Z]+[0-9]+' "$LOG" | sort -u)

if [ -n "$ERRORS" ]; then
  echo ""
  echo "✖ $LABEL: compiler errors"
  echo "$ERRORS" | sed 's/^/   /'
  exit 1
fi

if [ "$STRICT" = "warnings" ] && [ -n "$WARNINGS" ]; then
  echo ""
  echo "✖ $LABEL: compiler warnings (treated as errors, like clippy -D warnings)"
  echo "$WARNINGS" | sed 's/^/   /'
  exit 1
fi

if [ "$CODE" -ne 0 ]; then
  echo ""
  echo "✖ $LABEL: Unity exited $CODE with no Assets/ diagnostics. Log tail:"
  tail -25 "$LOG" | sed 's/^/   /'
  exit "$CODE"
fi

[ -n "$WARNINGS" ] && { echo "⚠ $LABEL: $(echo "$WARNINGS" | wc -l | tr -d ' ') warning(s)"; }
echo "✓ $LABEL: all assemblies compile clean"
