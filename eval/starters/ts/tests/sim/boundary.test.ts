/**
 * The hexagonal boundary, as a test.
 *
 * `src/sim` is the source of truth and must stay runnable with no browser, no
 * GPU, no clock and no entropy. Three mechanisms enforce that, deliberately
 * overlapping:
 *
 *   1. `tsconfig.sim.json` re-checks `src/sim` with `lib: ["ES2023"]` and
 *      `types: []`. `document`, `window`, `performance`, `process` are COMPILER
 *      errors there. Strongest, but blind to `Math.random` (that is plain ES).
 *   2. `eslint.config.js` bans the imports, the globals and the calls, with a
 *      message that says what to use instead. Silenceable by a comment.
 *   3. this file: walks the real import graph from the simulation entry points
 *      and scans every reachable file. Catches dynamic `import()`, catches a
 *      violation reached transitively, and runs in `just test-sim` (~0.5s) so
 *      you find out before you get to `just lint`.
 *
 * The second half of this file is the part that matters most: it feeds each
 * rule a source string that violates it and asserts the checker reports it. A
 * guard nobody has seen fail is not a guard.
 */

import { readFileSync, readdirSync } from 'node:fs';
import { dirname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, test } from 'vitest';

const REPO = fileURLToPath(new URL('../..', import.meta.url));
/** Trailing separator on purpose, so a sibling `src/simulation/` cannot pass a
 * `startsWith` check. */
const SIM_DIR = join(REPO, 'src', 'sim') + sep;

/** Entry points a host may import. Everything reachable from here is `sim`. */
const ENTRY_POINTS = ['src/sim/index.ts', 'src/sim/replay.ts'];

export interface Violation {
  readonly file: string;
  readonly line: number;
  readonly rule: string;
  readonly detail: string;
}

// --------------------------------------------------------------------------
// The checker
// --------------------------------------------------------------------------

/**
 * Blank out comments — and optionally string/template literal bodies — while
 * preserving every byte offset and newline, so reported line numbers stay true.
 *
 * Without this, the prose in `src/sim/index.ts` that *warns against*
 * `Math.random` would itself be reported as a use of `Math.random`.
 *
 * Regex literals are not modelled: `src/sim` contains none, and treating `/` as
 * division is the fail-safe direction (it can only over-report).
 */
function blank(source: string, alsoStrings: boolean): string {
  const out = source.split('');
  const hide = (from: number, to: number): void => {
    for (let i = from; i < to && i < out.length; i += 1) {
      if (out[i] !== '\n') out[i] = ' ';
    }
  };
  let i = 0;
  while (i < source.length) {
    const two = source.slice(i, i + 2);
    if (two === '//') {
      const end = source.indexOf('\n', i);
      hide(i, end === -1 ? source.length : end);
      i = end === -1 ? source.length : end;
    } else if (two === '/*') {
      const end = source.indexOf('*/', i + 2);
      hide(i, end === -1 ? source.length : end + 2);
      i = end === -1 ? source.length : end + 2;
    } else if (source[i] === "'" || source[i] === '"' || source[i] === '`') {
      const quote = source[i]!;
      let j = i + 1;
      while (j < source.length && source[j] !== quote) {
        j += source[j] === '\\' ? 2 : 1;
      }
      if (alsoStrings) hide(i + 1, j);
      i = j + 1;
    } else {
      i += 1;
    }
  }
  return out.join('');
}

function lineOf(source: string, index: number): number {
  let line = 1;
  for (let i = 0; i < index; i += 1) {
    if (source[i] === '\n') line += 1;
  }
  return line;
}

/** Every module specifier this source pulls in, static or dynamic. */
export function importsOf(source: string): { specifier: string; line: number }[] {
  const code = blank(source, false);
  const patterns = [
    /(?:^|[\n;])\s*(?:import|export)\s[^;]*?\sfrom\s*['"]([^'"]+)['"]/g,
    /(?:^|[\n;])\s*import\s*['"]([^'"]+)['"]/g,
    /\bimport\s*\(\s*['"]([^'"]+)['"]\s*\)/g,
    /\brequire\s*\(\s*['"]([^'"]+)['"]\s*\)/g,
  ];
  const found: { specifier: string; line: number }[] = [];
  for (const pattern of patterns) {
    for (const match of code.matchAll(pattern)) {
      // Report the line of the SPECIFIER, not of the match: the patterns start
      // at the preceding newline or `;`, which would be one line early.
      found.push({
        specifier: match[1]!,
        line: lineOf(code, match.index + match[0].indexOf(match[1]!)),
      });
    }
  }
  return found;
}

/**
 * Everything `src/sim` may not name. Each entry carries the remedy, because a
 * failure message that only says "forbidden" costs a turn.
 */
const BANNED: { rule: string; pattern: RegExp; detail: string }[] = [
  { rule: 'rng', pattern: /\bMath\s*\.\s*random\b/g, detail: 'use world.rng (SimRng)' },
  {
    rule: 'rng',
    pattern: /\bcrypto\s*\.\s*(?:getRandomValues|randomUUID)\b/g,
    detail: 'use world.rng (SimRng)',
  },
  { rule: 'clock', pattern: /\bDate\s*\.\s*now\b/g, detail: 'simulation time is world.tick' },
  { rule: 'clock', pattern: /\bnew\s+Date\b/g, detail: 'simulation time is world.tick' },
  {
    rule: 'clock',
    pattern: /\bperformance\s*\.\s*now\b/g,
    detail: 'simulation time is world.tick',
  },
  {
    rule: 'scheduler',
    pattern: /\b(?:setTimeout|setInterval|queueMicrotask)\s*\(/g,
    detail: 'a tick is a call to step(); the simulation never schedules itself',
  },
  {
    rule: 'async',
    pattern: /\b(?:async|await)\b/g,
    detail: 'src/sim is synchronous; async ordering depends on the host task queue',
  },
  {
    rule: 'async',
    pattern: /\bPromise\s*[.(]|\bnew\s+Promise\b/g,
    detail: 'src/sim is synchronous; a Promise resolves on the microtask queue, not the tick',
  },
  {
    rule: 'dom',
    pattern:
      /\b(?:document|window|navigator|localStorage|sessionStorage|requestAnimationFrame|XMLHttpRequest)\b/g,
    detail: 'no DOM in src/sim; presentation belongs in src/view',
  },
  {
    rule: 'host',
    pattern: /\bprocess\s*\.\s*(?:env|hrtime|argv)\b/g,
    detail: 'src/sim must run unchanged in a browser, a worker and a host process',
  },
];

/** True for a specifier that stays inside `src/sim`. */
function staysInSim(fromFile: string, specifier: string): boolean {
  if (!specifier.startsWith('./') && !specifier.startsWith('../')) return false;
  const target = resolve(dirname(fromFile), specifier);
  return target.startsWith(SIM_DIR);
}

/** Scan one file's source. `file` is an absolute path, used for resolution. */
export function scan(source: string, file: string): Violation[] {
  const violations: Violation[] = [];
  const label = relative(REPO, file) || file;

  for (const { specifier, line } of importsOf(source)) {
    if (!staysInSim(file, specifier)) {
      violations.push({
        file: label,
        line,
        rule: 'import',
        detail: `imports '${specifier}'. src/sim may only import from src/sim — move the rule into src/sim and let src/view read it.`,
      });
    }
  }

  const code = blank(source, true);
  for (const { rule, pattern, detail } of BANNED) {
    for (const match of code.matchAll(pattern)) {
      violations.push({
        file: label,
        line: lineOf(code, match.index),
        rule,
        detail: `uses \`${match[0].trim()}\` — ${detail}.`,
      });
    }
  }
  return violations;
}

function report(violations: readonly Violation[]): string {
  return violations.map((v) => `  ${v.file}:${v.line}  [${v.rule}] ${v.detail}`).join('\n');
}

/** Transitive closure of `src/sim` imports, starting from the entry points. */
function reachableFiles(): string[] {
  const seen = new Set<string>();
  const queue = ENTRY_POINTS.map((p) => join(REPO, p));
  while (queue.length > 0) {
    const file = queue.pop()!;
    if (seen.has(file)) continue;
    seen.add(file);
    const source = readFileSync(file, 'utf8');
    for (const { specifier } of importsOf(source)) {
      if (staysInSim(file, specifier)) {
        queue.push(resolve(dirname(file), specifier));
      }
    }
  }
  return [...seen].sort();
}

function allSimFiles(): string[] {
  const walk = (dir: string): string[] =>
    readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
      const full = join(dir, entry.name);
      if (entry.isDirectory()) return walk(full);
      return entry.name.endsWith('.ts') ? [full] : [];
    });
  return walk(SIM_DIR).sort();
}

// --------------------------------------------------------------------------
// The guard, applied to the real repository
// --------------------------------------------------------------------------

test('src/sim depends on nothing outside src/sim', () => {
  const violations = allSimFiles().flatMap((file) => scan(readFileSync(file, 'utf8'), file));
  expect(
    violations.length === 0 ? '' : `\n${report(violations)}\n`,
    'the simulation reached outside its boundary',
  ).toBe('');
});

test('every file reachable from the sim entry points lives in src/sim', () => {
  const outside = reachableFiles().filter((file) => !file.startsWith(SIM_DIR));
  expect(outside, `reachable from ${ENTRY_POINTS.join(', ')} but outside src/sim`).toEqual([]);
});

test('the sim entry points are actually reachable', () => {
  // Guards the guard: if resolution silently broke, `reachableFiles` would
  // return a tiny set and the test above would pass vacuously.
  const files = reachableFiles().map((f) => relative(REPO, f));
  expect(files).toContain('src/sim/index.ts');
  expect(files).toContain('src/sim/replay.ts');
  expect(files).toContain('src/sim/vec2.ts');
});

// --------------------------------------------------------------------------
// The guard, applied to itself — proof that it fires
// --------------------------------------------------------------------------

describe('the boundary checker actually fires', () => {
  const HERE = join(SIM_DIR, 'fixture.ts');
  const rulesFor = (source: string): string[] => scan(source, HERE).map((v) => v.rule);

  test.for([
    ['static three import', "import * as THREE from 'three';", 'import'],
    ['renderer import', "import { createView } from '../view/index.ts';", 'import'],
    ['deep renderer import', "import { Frame } from '../../src/view/harness.ts';", 'import'],
    ['node builtin', "import { readFileSync } from 'node:fs';", 'import'],
    ['side-effect import', "import 'three/addons/controls/OrbitControls.js';", 'import'],
    ['dynamic import', "const t = await import('three');", 'import'],
    ['require', "const t = require('three');", 'import'],
    ['Math.random', 'const r = Math.random();', 'rng'],
    ['crypto entropy', 'crypto.getRandomValues(buf);', 'rng'],
    ['Date.now', 'const t = Date.now();', 'clock'],
    ['new Date', 'const t = new Date().getTime();', 'clock'],
    ['performance.now', 'const t = performance.now();', 'clock'],
    ['setTimeout', 'setTimeout(() => step(world), 16);', 'scheduler'],
    ['queueMicrotask', 'queueMicrotask(() => step(world));', 'scheduler'],
    ['async function', 'async function tick() {}', 'async'],
    ['new Promise', 'const p = new Promise(() => {});', 'async'],
    ['document', 'const c = document.createElement("canvas");', 'dom'],
    ['window', 'const w = window.innerWidth;', 'dom'],
    ['requestAnimationFrame', 'requestAnimationFrame(loop);', 'dom'],
    ['process.env', 'const debug = process.env.DEBUG;', 'host'],
  ] as const)('rejects %s', ([, source, rule]) => {
    expect(rulesFor(source), `"${source}" should be reported as [${rule}]`).toContain(rule);
  });

  test.for([
    ['a relative sim import', "import { f32 } from './vec2.ts';"],
    ['a nested sim import', "import { f32 } from './math/vec2.ts';"],
    ['prose that names the banned APIs', '// Never use Math.random or Date.now here.'],
    ['a block comment naming three', "/* This must not import 'three'. */"],
    ['a string that names the banned APIs', 'const why = "no Math.random in the sim";'],
    ['ordinary f32 arithmetic', 'const y = f32(a.y + b.y);'],
  ] as const)('accepts %s', ([, source]) => {
    expect(scan(source, HERE), `"${source}" is legitimate and must not be reported`).toEqual([]);
  });
});
