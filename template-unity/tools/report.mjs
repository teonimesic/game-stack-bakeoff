#!/usr/bin/env node
// Turn Unity's output into something an agent can read.
//
// A Unity batchmode log is tens of thousands of lines and a NUnit results file
// is deeply nested XML. Both are hostile to an agent with a context window, and
// "drowning in the log instead of reading the one failing assertion" is a real,
// observed failure mode. This prints a short pass/fail summary plus the full
// message of every failure, and nothing else.
//
// Regex, not an XML parser, on purpose: this machine's Homebrew Python has a
// broken pyexpat, and Node ships no XML parser in core. The results format is
// flat enough that regex is sufficient and has no dependency to install.
//
// Usage: node tools/report.mjs <results.xml> <unity.log> <label> <unityExitCode>

import { readFileSync, existsSync } from "node:fs";

const [xmlPath, logPath, label, unityExit] = process.argv.slice(2);

const decode = (s) =>
  s
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
    .replace(/&#xD;/g, "")
    .replace(/&#xA;/g, "\n")
    .replace(/&amp;/g, "&");

const strip = (s) => decode(s.replace(/<!\[CDATA\[|\]\]>/g, "")).trim();

function compileDiagnostics() {
  if (!existsSync(logPath)) return { errors: [], warnings: [] };
  const lines = readFileSync(logPath, "utf8").split("\n");
  const errors = [];
  const warnings = [];
  for (const line of lines) {
    // Only our own code: Assets/**. Package and engine diagnostics are not ours
    // to fix and must not be able to fail the gate.
    if (!/^Assets[/\\]/.test(line)) continue;
    // Any Roslyn diagnostic id, not just CS: the vendored analyzers report
    // PONG#### (determinism) and UNT#### (Unity idioms).
    if (/\)\s*:\s*error [A-Z]+\d+/.test(line) && !errors.includes(line)) errors.push(line);
    if (/\)\s*:\s*warning [A-Z]+\d+/.test(line) && !warnings.includes(line)) warnings.push(line);
  }
  return { errors, warnings };
}

const { errors, warnings } = compileDiagnostics();

if (errors.length) {
  console.log(`\n✖ ${label}: ${errors.length} compiler error(s)\n`);
  for (const e of errors) console.log("   " + e);
  process.exit(1);
}

if (!existsSync(xmlPath)) {
  console.log(`\n✖ ${label}: Unity produced no results file (${xmlPath}).`);
  console.log(`  Unity exit code ${unityExit}. Last lines of ${logPath}:`);
  if (existsSync(logPath)) {
    const tail = readFileSync(logPath, "utf8").trim().split("\n").slice(-25);
    for (const line of tail) console.log("   " + line);
  }
  process.exit(1);
}

const xml = readFileSync(xmlPath, "utf8");

const run = xml.match(/<test-run\b[^>]*>/);
const attr = (tag, name) => {
  const m = tag.match(new RegExp(`\\b${name}="([^"]*)"`));
  return m ? m[1] : "?";
};

const total = run ? attr(run[0], "total") : "?";
const passed = run ? attr(run[0], "passed") : "?";
const failed = run ? attr(run[0], "failed") : "?";
const skipped = run ? attr(run[0], "skipped") : "0";
const inconclusive = run ? attr(run[0], "inconclusive") : "0";
const duration = run ? attr(run[0], "duration") : "?";

// Every <test-case> element, with the body that follows it up to its close.
const cases = [...xml.matchAll(/<test-case\b([^>]*)>([\s\S]*?)<\/test-case>|<test-case\b([^>]*)\/>/g)];

const failures = [];
const ignored = [];
for (const c of cases) {
  const head = c[1] ?? c[3] ?? "";
  const body = c[2] ?? "";
  const name = attr(head, "fullname");
  const result = attr(head, "result");
  if (result === "Failed") {
    const message = body.match(/<message>([\s\S]*?)<\/message>/);
    const stack = body.match(/<stack-trace>([\s\S]*?)<\/stack-trace>/);
    failures.push({
      name,
      message: message ? strip(message[1]) : "(no message)",
      stack: stack ? strip(stack[1]).split("\n").slice(0, 4).join("\n") : "",
    });
  } else if (result === "Skipped" || result === "Inconclusive") {
    const reason = body.match(/<message>([\s\S]*?)<\/message>/);
    ignored.push({ name, reason: reason ? strip(reason[1]) : "" });
  }
}

// A skipped test is not a passing test. The render suite skips itself when the
// machine has no GPU adapter, which is the right call on a developer laptop and
// exactly the wrong call in CI: it reports green over zero pixel coverage.
// FAIL_ON_SKIP=1 (set by `just ci`) turns that into a failure.
const failOnSkip = process.env.FAIL_ON_SKIP === "1";

// The headline must not read "✓" when tests were skipped: a green tick over a
// suite that asserted nothing is the exact false-confidence this repo guards
// against everywhere else.
const headline = failures.length ? "✖" : ignored.length ? (failOnSkip ? "✖" : "⚠") : "✓";
console.log(
  `\n${headline} ${label}: ` +
    `${passed} passed, ${failed} failed, ${skipped} skipped ` +
    `(of ${total}, ${Number(duration).toFixed(1)}s)`,
);

if (ignored.length) {
  console.log(
    `\n   ${failOnSkip ? "✖" : "⚠"} ${ignored.length} test(s) SKIPPED — ` +
      "they asserted nothing:",
  );
}
for (const s of ignored) {
  console.log(`   ○ ${s.name}\n     ${s.reason.split("\n")[0]}`);
}

for (const f of failures) {
  console.log(`\n   ✖ ${f.name}`);
  for (const line of f.message.split("\n")) console.log(`     ${line}`);
  if (f.stack) for (const line of f.stack.split("\n")) console.log(`     | ${line}`);
}

if (warnings.length) {
  console.log(`\n   ⚠ ${warnings.length} compiler warning(s) in Assets/ (see \`just lint\`)`);
}

let ok =
  failures.length === 0 && Number(failed) === 0 && Number(total) > 0 && Number(unityExit) === 0;
if (Number(total) === 0) {
  console.log(
    "\n✖ zero tests were discovered. Check that Packages/manifest.json has " +
      '"testables": ["com.unity.test-framework"].',
  );
}
if (failOnSkip && ignored.length) {
  console.log(
    `\n✖ ${label}: ${ignored.length} skipped test(s), and skips are failures here.\n` +
      "  A skipped render test means the machine had no graphics device, so nothing\n" +
      "  was drawn and nothing was checked. Fix the environment, do not fix the test.",
  );
  ok = false;
}
process.exit(ok ? 0 : 1);
