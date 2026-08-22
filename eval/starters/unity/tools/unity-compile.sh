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

# Unity holds a PROJECT-WIDE lock. Two invocations against the same -projectPath do not
# queue and do not error -- the second blocks forever, silently. An agent running
# `just check` and `just warm` as background tasks stacks them and deadlocks its own
# trial: measured at 3h of frozen CPU with no output (FINDINGS #43).
#
# Two guards, because they cover different things:
#   1. compile against a COPY, so concurrent invocations never contend at all
#   2. a lock around the copy, as a backstop for any path that still touches the tree
#
# Measured on an idle machine (starter, 36 MB):
#   direct, warm Library   4.3 s
#   copy 0.5 s + compile   4.1 s      <- a copy does NOT force an asset reimport
#   second compile in copy 2.6 s
# An earlier note here claimed a copy was "237x slower". That was this script's own
# watchdog holding the caller's pipe open, not a reimport. See the >/dev/null below.
#
# `mkdir` is atomic on every filesystem we target; macOS ships no flock(1).
LOCK="$ROOT/.unity-compile.lock"
LOCK_TIMEOUT="${UNITY_LOCK_TIMEOUT:-600}"
waited=0
while ! mkdir "$LOCK" 2>/dev/null; do
  holder=$(cat "$LOCK/pid" 2>/dev/null || echo "")
  if [ -n "$holder" ] && ! kill -0 "$holder" 2>/dev/null; then
    rm -rf "$LOCK"; continue          # holder died without releasing; reclaim
  fi
  sleep 2; waited=$((waited + 2))
  if [ "$waited" -ge "$LOCK_TIMEOUT" ]; then
    echo "" >&2
    echo "✖ $LABEL: another Unity command held this project for ${waited}s (pid ${holder:-?})." >&2
    exit 124
  fi
done
echo $$ > "$LOCK/pid"

WORK="$(mktemp -d "${TMPDIR:-/tmp}/unity-compile.XXXXXX")"
cleanup() { rm -rf "$LOCK" "$WORK"; }
trap cleanup EXIT INT TERM

cp -Rc "$ROOT" "$WORK/proj" 2>/dev/null || cp -R "$ROOT" "$WORK/proj" || {
  echo "✖ $LABEL: could not copy the project for compilation" >&2; exit 1; }
rm -rf "$WORK/proj/artifacts" "$WORK/proj/.unity-compile.lock"

# THE STRICT GATE MUST ANSWER FROM THE CODE, NOT FROM THE CACHE.
#
# The copy above inherits Library/, so Unity re-uses cached compilation and analyzer
# results for assemblies it considers unchanged, and a violation that is STILL IN THE FILE
# is never re-reported. Measured on g4_platformer__unity__t1 (wg-g4c-2026-08-21), a tree
# holding five real CA1861 violations:
#
#   warm Library (what this script used to do)   exit 0  "all assemblies compile clean"  8.9s
#   Library/ScriptAssemblies deleted             exit 0  -- still wrong                   4.9s
#   whole Library deleted                        exit 1  all five reported               10.9s
#
# Deleting only ScriptAssemblies is NOT enough: Unity caches the analysis elsewhere under
# Library/. That surgical fix looks principled, changes nothing, and would have shipped as
# a repair (FINDINGS #66).
#
# Scoped to STRICT=warnings so `just lint` and `just verify` answer honestly while
# `just check` -- the fast inner loop agents run constantly -- keeps its warm cache. The
# cost of the cold path is ~2s here, not the minutes this was feared to be.
if [ "$STRICT" = "warnings" ]; then
  rm -rf "$WORK/proj/Library"
fi
rm -rf "$LOCK"; trap 'rm -rf "$WORK"' EXIT INT TERM   # copy done; release before compiling

UNITY_TIMEOUT="${UNITY_TIMEOUT:-900}"
"$UNITY" -batchmode -nographics -disable-audio -quit -logFile "$LOG" -projectPath "$WORK/proj" &
UPID=$!
# >/dev/null 2>&1 is LOAD-BEARING: a background subshell inherits this script's stdout,
# and an orphaned `sleep` holds that pipe open after the script exits. The caller then
# blocks until the sleep expires and reads the TIMEOUT as the command's duration. That
# artifact produced a 900 s reading for a 4 s compile and a bogus "237x" conclusion.
( sleep "$UNITY_TIMEOUT"; kill -9 "$UPID" 2>/dev/null ) >/dev/null 2>&1 & WATCHDOG=$!
wait "$UPID"; CODE=$?
kill "$WATCHDOG" 2>/dev/null; wait "$WATCHDOG" 2>/dev/null

if [ "$CODE" -ge 128 ]; then
  echo "" >&2
  echo "✖ $LABEL: Unity did not finish within ${UNITY_TIMEOUT}s and was killed." >&2
  echo "   A silent hang means a shared resource, not slow work. Log tail:" >&2
  tail -15 "$LOG" 2>/dev/null | sed 's/^/   /' >&2
  exit 124
fi

# Diagnostics name paths inside the copy. Rewrite them to the real tree, or an agent is
# told to fix a file in a temp directory that no longer exists.
if [ -f "$LOG" ]; then
  /usr/bin/sed -i '' "s#${WORK}/proj/#${ROOT}/#g" "$LOG" 2>/dev/null || true
fi

# Match ANY Roslyn diagnostic id, not just `CS`: the vendored analyzers in
# Assets/Analyzers/ report SIM#### (determinism) and UNT#### (Unity idioms),
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
