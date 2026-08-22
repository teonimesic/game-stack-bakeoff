#!/usr/bin/env node
// Summarise a Unity Code Coverage run.
//
// The package writes a full HTML site plus OpenCover XML. Neither is readable
// in a terminal, and an agent that cats the HTML burns its context for nothing.
// This prints the assembly total, the per-class table sorted worst-first, and
// the path to the HTML report.
//
// Usage: node tools/coverage.mjs <coverageResultsPath> [minLineCoverage]

import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";

const [dir, minArg] = process.argv.slice(2);
const min = minArg === undefined ? null : Number(minArg);

const summaryPath = join(dir, "Report", "Summary.json");
if (!existsSync(summaryPath)) {
  console.log(`\n✖ coverage: no report at ${summaryPath}`);
  console.log("  The run produced no coverage data. Common causes:");
  console.log("   - -enableCodeCoverage missing, or the package is not in Packages/manifest.json");
  console.log("   - assemblyFilters excluded everything (check the filter matches an asmdef name)");
  process.exit(1);
}

const report = JSON.parse(readFileSync(summaryPath, "utf8"));
const s = report.summary;
const assembly = report.coverage.assemblies[0];

const pct = (n) => `${Number(n).toFixed(1)}%`.padStart(6);

console.log(
  `\n✓ coverage: ${assembly.name} — ` +
    `${pct(s.linecoverage).trim()} lines (${s.coveredlines}/${s.coverablelines}), ` +
    `${pct(s.methodcoverage).trim()} methods (${s.coveredmethods}/${s.totalmethods})`,
);

const classes = [...assembly.classesinassembly].sort((a, b) => a.coverage - b.coverage);
console.log("\n   least covered first:");
for (const c of classes) {
  const uncovered = c.coverablelines - c.coveredlines;
  console.log(
    `   ${pct(c.coverage)}  ${c.name.padEnd(28)} ` +
      `${String(c.coveredlines).padStart(4)}/${String(c.coverablelines).padEnd(4)} lines` +
      (uncovered ? `  (${uncovered} uncovered)` : ""),
  );
}

console.log(`\n   html report: ${join(dir, "Report", "index.html")}`);
console.log("   Uncovered lines are shown in red there, line by line.");

if (min !== null && s.linecoverage < min) {
  console.log(
    `\n✖ coverage: ${pct(s.linecoverage).trim()} is below the ${min}% floor.\n` +
      "  Add tests for the classes at the top of the list above.",
  );
  process.exit(1);
}
