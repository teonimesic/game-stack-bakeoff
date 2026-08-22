import { defineConfig } from 'vitest/config';

/**
 * Two projects, because they have nothing in common except the language.
 *
 * `sim` is pure logic: milliseconds, no browser, safe to parallelise.
 * `render` drives one headless Chromium with one WebGL context, so it runs
 * single-threaded — concurrent GL contexts in one process contend and produce
 * flaky empty frames.
 */
export default defineConfig({
  test: {
    projects: [
      {
        test: {
          name: 'sim',
          include: ['tests/sim/**/*.test.ts'],
          environment: 'node',
        },
      },
      {
        test: {
          name: 'render',
          include: ['tests/render/**/*.test.ts'],
          environment: 'node',
          fileParallelism: false,
          testTimeout: 120_000,
          hookTimeout: 120_000,
          pool: 'threads',
          maxWorkers: 1,
        },
      },
    ],
    coverage: {
      include: ['src/sim/**'],
      reporter: ['text', 'html'],
    },
  },
});
