#!/usr/bin/env bash
# Run a slice of the EditMode test suite and print a readable summary.
#
# Usage: tools/unity-tests.sh <label> <assembly-filter|-> <graphics:on|off> [name-filter]
#
# TRAP: never add `-quit` alongside `-runTests`. The editor quits before the
# test runner starts, exits 0, and writes no results file — a false green.
set -uo pipefail

LABEL="$1"
FILTER="${2:--}"
GRAPHICS="${3:-off}"
NAME_FILTER="${4:-}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNITY="${UNITY_BIN:-/Applications/Unity/Hub/Editor/6000.0.45f1/Unity.app/Contents/MacOS/Unity}"
OUT="$ROOT/artifacts"
mkdir -p "$OUT"
LOG="$OUT/$LABEL.log"
XML="$OUT/$LABEL.xml"
rm -f "$LOG" "$XML"

if [ ! -x "$UNITY" ]; then
  echo "✖ Unity 6000.0.45f1 not found at $UNITY (override with UNITY_BIN=...)" >&2
  exit 127
fi

# `-disable-audio` on every invocation. Grading runs these unattended and
# concurrently for hours and nothing downstream ever listens: the audio criteria
# decode each clip with `ffmpeg` into a PIPE and analyse the samples (judge/audio.py),
# and the grader contains no playback call at all. Silencing the engine cannot change
# a criterion, and an editor that opens an audio device also contends for one.
ARGS=(-batchmode -disable-audio -logFile "$LOG" -projectPath "$ROOT"
      -runTests -testPlatform EditMode -testResults "$XML")
# Render tests need a real graphics device; `-nographics` gives a Null device
# and every pixel capture would have to be faked. Sim tests do not, and skip it.
[ "$GRAPHICS" = "off" ] && ARGS=(-nographics "${ARGS[@]}")
[ "$FILTER" != "-" ] && ARGS+=(-assemblyNames "$FILTER")
[ -n "$NAME_FILTER" ] && ARGS+=(-testFilter "$NAME_FILTER")

"$UNITY" "${ARGS[@]}"
CODE=$?

node "$ROOT/tools/report.mjs" "$XML" "$LOG" "$LABEL" "$CODE"
