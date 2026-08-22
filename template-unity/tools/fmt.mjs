#!/usr/bin/env node
// Mechanical whitespace formatting for the C# sources.
//
// There is no `cargo fmt` for a Unity project: `dotnet format` needs a solution
// that only the editor generates, which would make `just fmt` cost a full
// editor launch. This does the subset that actually causes review noise — tabs,
// trailing whitespace, CRLF, missing or duplicated trailing newlines — and
// nothing that could change semantics.
//
// Usage: node tools/fmt.mjs [--check]

import { readdirSync, readFileSync, writeFileSync, statSync } from "node:fs";
import { join } from "node:path";

const check = process.argv.includes("--check");
const roots = ["Assets", "tools"];
const exts = [".cs", ".asmdef", ".json", ".shader", ".mjs"];

// Build output, not source. `tools/analyzer/obj/` in particular is full of
// generated JSON that this would happily rewrite on every run.
const skipDirs = new Set(["bin", "obj", "Library", "Temp", "node_modules"]);

function* walk(dir) {
  for (const entry of readdirSync(dir)) {
    const path = join(dir, entry);
    if (statSync(path).isDirectory()) {
      if (!skipDirs.has(entry)) yield* walk(path);
    } else if (exts.some((e) => path.endsWith(e))) {
      yield path;
    }
  }
}

function normalise(text) {
  return (
    text
      .replace(/\r\n?/g, "\n")
      .replace(/\t/g, "    ")
      .split("\n")
      .map((line) => line.replace(/[ \t]+$/, ""))
      .join("\n")
      .replace(/\n+$/, "") + "\n"
  );
}

const changed = [];
for (const root of roots) {
  for (const path of walk(root)) {
    const original = readFileSync(path, "utf8");
    const formatted = normalise(original);
    if (formatted === original) continue;
    changed.push(path);
    if (!check) writeFileSync(path, formatted);
  }
}

if (check && changed.length) {
  console.log("✖ fmt: these files are not formatted:");
  for (const path of changed) console.log("   " + path);
  process.exit(1);
}
console.log(check ? "✓ fmt: clean" : `✓ fmt: ${changed.length} file(s) rewritten`);
