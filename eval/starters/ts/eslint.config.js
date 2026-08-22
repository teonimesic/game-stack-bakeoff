import js from '@eslint/js';
import tseslint from 'typescript-eslint';

/**
 * Type-aware linting is the point: without `projectService` the rules that
 * catch real bugs (floating promises, unsafe `any`, unnecessary conditions)
 * cannot run at all.
 *
 * The `src/sim` block below is the architectural firewall. It is one of three
 * layers, deliberately overlapping, because each catches what the others miss:
 *
 *   1. `tsconfig.sim.json` — no DOM lib, no node types. `document` and friends
 *      are COMPILER errors. Cannot be silenced by a comment.
 *   2. this file — bans the imports and the nondeterministic call sites, with a
 *      message that says what to do instead.
 *   3. `tests/sim/boundary.test.ts` — walks the real import graph, so a dynamic
 *      `import()` or a transitive hop is caught too, and proves in the suite
 *      that the checks actually fire.
 */

/** Everything that would make a replay unreproducible. */
const NONDETERMINISTIC_PROPERTIES = [
  {
    object: 'Math',
    property: 'random',
    message: 'src/sim: use world.rng (SimRng) — Math.random is not part of the snapshot.',
  },
  {
    object: 'Date',
    property: 'now',
    message: 'src/sim: no wall clock. Simulation time is world.tick.',
  },
  {
    object: 'performance',
    property: 'now',
    message: 'src/sim: no wall clock. Simulation time is world.tick.',
  },
  {
    object: 'crypto',
    property: 'getRandomValues',
    message: 'src/sim: use world.rng (SimRng) — unseeded entropy breaks replay.',
  },
  {
    object: 'crypto',
    property: 'randomUUID',
    message: 'src/sim: ids are assigned explicitly, not generated.',
  },
  {
    object: 'Object',
    property: 'keys',
    message:
      'src/sim: iterate an explicit array sorted on SimId, not object key order, so ordering is declared rather than inherited.',
  },
];

/**
 * Syntax-level bans. `no-restricted-globals` and `no-restricted-properties`
 * cannot express these.
 */
const NONDETERMINISTIC_SYNTAX = [
  {
    selector: "NewExpression[callee.name='Date']",
    message: 'src/sim: no wall clock. Simulation time is world.tick.',
  },
  {
    selector: 'CallExpression[callee.name=/^(setTimeout|setInterval|queueMicrotask)$/]',
    message: 'src/sim: a tick is a call to step(). Nothing in the simulation schedules itself.',
  },
  {
    selector: 'AwaitExpression, ForOfStatement[await=true]',
    message:
      'src/sim must be synchronous: `await` makes tick ordering depend on the host task queue.',
  },
  {
    selector: ':function[async=true]',
    message:
      'src/sim must be synchronous: an async system makes tick ordering depend on the host task queue.',
  },
  {
    selector: "NewExpression[callee.name='Promise']",
    message:
      'src/sim must be synchronous: a Promise resolves on the microtask queue, not the tick.',
  },
  {
    selector: "CallExpression[callee.property.name='sort'][arguments.length=0]",
    message:
      'src/sim: `.sort()` with no comparator sorts by string. Sort on SimId: `.sort((a, b) => a.id - b.id)`.',
  },
];

export default tseslint.config(
  {
    ignores: [
      'public/**',
      'coverage/**',
      'node_modules/**',
      'tests/render/artifacts/**',
      // Build-time tooling, not shipped code, and outside every tsconfig — so
      // the type-aware rules have nothing to read.
      'scripts/**',
    ],
  },
  js.configs.recommended,
  tseslint.configs.recommendedTypeChecked,
  {
    languageOptions: {
      parserOptions: {
        projectService: { allowDefaultProject: ['eslint.config.js'] },
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },
  {
    // THE FIREWALL. Scoped to src/sim only; everything else may use the DOM,
    // three, and the wall clock freely.
    files: ['src/sim/**/*.ts'],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          patterns: [
            {
              group: ['**/view/**', 'three', 'three/*', '*.css'],
              message:
                'src/sim must not depend on the renderer. Move the rule into src/sim and let src/view read it.',
            },
            {
              group: ['node:*'],
              message:
                'src/sim must run unchanged in a browser, a worker and a host process. No node builtins.',
            },
          ],
        },
      ],
      'no-restricted-globals': [
        'error',
        // `tsconfig.sim.json` already makes most of these "Cannot find name".
        // These are here so the message says WHY, and so an editor pointed at
        // the root tsconfig still flags them.
        { name: 'window', message: 'src/sim has no DOM. Put presentation in src/view.' },
        { name: 'document', message: 'src/sim has no DOM. Put presentation in src/view.' },
        { name: 'navigator', message: 'src/sim has no DOM. Put presentation in src/view.' },
        { name: 'localStorage', message: 'src/sim holds no I/O. Persist from src/view.' },
        { name: 'fetch', message: 'src/sim holds no I/O. Fetch from src/view.' },
        {
          name: 'requestAnimationFrame',
          message: 'src/sim advances by step(); frames belong to src/view.',
        },
        { name: 'process', message: 'src/sim must run in a browser too.' },
      ],
      'no-restricted-properties': ['error', ...NONDETERMINISTIC_PROPERTIES],
      'no-restricted-syntax': ['error', ...NONDETERMINISTIC_SYNTAX],
    },
  },
  {
    // Tests may assert on the wall clock and construct dates; the harness is
    // async by nature. `no-restricted-*` above is scoped to src/sim so nothing
    // needs turning off here — this block only relaxes rules that are noisy on
    // test code.
    files: ['tests/**/*.ts'],
    rules: { '@typescript-eslint/no-non-null-assertion': 'off' },
  },
);
