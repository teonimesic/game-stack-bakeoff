#!/usr/bin/env bash
# Measure how much of Assets/Sim/ the tests actually execute.
#
# Coverage is deliberately NOT part of `just verify`: it roughly triples the
# test run and a coverage number is not a pass/fail signal. Run it when you want
# to know what is untested, not on every edit.
#
# Usage: tools/unity-coverage.sh [minLineCoveragePercent]
#
# TRAP: never add `-quit` alongside `-runTests`.
set -uo pipefail

MIN="${1:-}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNITY="${UNITY_BIN:-/Applications/Unity/Hub/Editor/6000.0.45f1/Unity.app/Contents/MacOS/Unity}"
OUT="$ROOT/artifacts"
COV="$OUT/coverage"
mkdir -p "$OUT"
rm -rf "$COV"
rm -f "$OUT/coverage.log" "$OUT/coverage.xml"

if [ ! -x "$UNITY" ]; then
  echo "✖ Unity 6000.0.45f1 not found at $UNITY (override with UNITY_BIN=...)" >&2
  exit 127
fi

# assemblyFilters keeps the report to the simulation; +Sim is the asmdef name.
# View/EditorTools are excluded on purpose: their coverage number would be
# dominated by engine glue nobody should be writing unit tests for.
"$UNITY" -batchmode -logFile "$OUT/coverage.log" -projectPath "$ROOT" \
  -runTests -testPlatform EditMode -testResults "$OUT/coverage.xml" \
  -enableCodeCoverage \
  -coverageResultsPath "$COV" \
  -coverageOptions "generateAdditionalMetrics;generateHtmlReport;assemblyFilters:+Sim;pathFilters:+**/Assets/Sim/**"
CODE=$?

node "$ROOT/tools/report.mjs" "$OUT/coverage.xml" "$OUT/coverage.log" coverage-tests "$CODE" || exit 1
node "$ROOT/tools/coverage.mjs" "$COV" $MIN
