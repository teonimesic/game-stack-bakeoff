---
id: 154
title: ci_minutes.py --scope accepts --json and ignores it, and the selftest calls that a VARIANT
status: in_testing
priority: 3
refs: eval/tools/ci_minutes.py main() and filter_problems, .github/workflows/controls.yml scope step, .github/workflows/README.md, AGENTS.md rule 13, PR 31
done_when: 'Either (a) main() rejects --scope --json with a non-zero exit and a message naming the unsupported combination, and filter_problems reclassifies that command as a MUTANT with the selftest still exit 0; or (b) --scope honours --json and emits its scope decision as JSON, with the variant kept and a row asserting the JSON is parseable and carries the relevant verdict. Either way: state which was chosen and why, ci_minutes.py --selftest exits 0 unpiped, and the mutant/variant counts in its closing line are re-read rather than carried forward. A third acceptable outcome is a measured NO - evidence that the flag combination is unreachable from any workflow the repository can hold - but the current variant text says the opposite, so that would have to explain the variant away.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/35
established_by: 'PR #35, 5 review rounds, all green: ci_minutes --selftest exit 0 unpiped at 63 mutants / 33 variants re-read from its closing line, and 16 mutants planted on the shipped file all DIED with 0 survivors. Chose (a) refuse over (b) honour; 6 mode/flag combinations exited 0 on a discarded flag before the change, all now exit 2. gates, controls, sweep, tasks check, linkcheck, lint all green on a head merged up to main.'
---

main() dispatches --selftest, then --scope, then --gates, and only the --gates branch reads args.json. So `ci_minutes.py --scope --json` exits 0 having silently ignored the flag. That is the shape AGENTS.md rule 13 names: an accepted-but-ignored flag is worse than an unsupported one, because exit 0 reads as "the command did what I asked". It is worse here than in general, because filter_problems classifies exactly that command as a VARIANT - an input the check must not redden - so the selftest actively asserts that a scope step invoked with a flag it does not honour is a correct scope step. A workflow edited to `ci_minutes.py --scope --json` would pass every pin. Found by CodeRabbit on PR 31, on code that arrived from main in task 148 and is outside that PR https://github.com/teonimesic/game-stack-bakeoff/pull/31 diff, which is why it was not fixed there.

## note 2026-08-25

## What was chosen, and what the next agent must not re-derive

**(a) — every mode REFUSES the flags it does not read.** Not (b). `--scope` already has a
machine-readable channel and it is the one the workflow reads: `relevant=` in `$GITHUB_OUTPUT`.
A JSON payload on stdout would have no consumer and would have to be kept in step with the one
that has. More importantly, (b) answers the instance and leaves the shape: measured on `main`
before any edit, **6** combinations exited 0 having discarded a flag — `--scope --json`,
`--scope --gates`, `--selftest --json`, `--path-filter --no-timing`, `--gates --cache DIR`,
`--hooks --no-timing`.

`MODE_ACCEPTS` is the table; `main` checks the invocation against it before dispatching and
exits 2; `filter_problems` asks the workflow's scope step the same question through
`scope_invocation_problems`.

## The findings, needing a number from the orchestrator

**Primary.** *A gate carried, as a VARIANT it must not redden, the exact command the tool
ignored a flag on — so the pin asserted the defect was correct behaviour.* `--scope --json`
contains `--scope`, the check was a substring test, and the selftest's variant list said a
scope step invoked with a flag the tool ignores is a correct scope step.

**Its generalisation, and it fired 3 times on this branch.** *A check whose failure mode is the
process LEAVING or HANGING reports nothing at all, and it is invisible until a mutant is aimed
at it.* Each was found by the controls rather than by reading:

1. `main(["--selftest", "--json"])` inside `_selftest` re-enters `_selftest`, which drives
   subprocesses at every level. Under the mutant that removes the refusal it **hung**; the
   control run timed out rather than reporting.
2. `problems_of` caught `Exception`; `SystemExit` is not one. With `_Parser.exit` mutated away,
   the `--scope --help` row ended the whole selftest at **status 0** — green, silent, nothing
   asserted — and the mutant came back **SURVIVED**.
3. The `main`-refusal rows read a *returned* status and could not see a *taken* one.

**Second generalisation, 2 instances.** *The obvious mutant for a fix tests the branch you just
wrote, not the one you did not.* `echo …` and `sh -c …` die on the head check alone, so a suffix
match and a deleted `--scope` requirement both SURVIVED until
`python3 tools/vendor_ci_minutes.py --scope` and `python3 eval/tools/ci_minutes.py --gates` were
added. Likewise an unbalanced quote reddens either way — a whitespace fallback misses the script
and reports a *different reason with the same verdict* — so the row that kills the swallowing
mutant asks WHICH answer came back.

## The review found 5 real defects across 5 rounds. Do not assume the surface is exhausted.

| round | what it found | direction |
|---|---|---|
| 1 | `--help` reaches `ArgumentParser.exit()`, never `error()`; `filter_problems` printed a help screen and raised `SystemExit(0)` | no verdict |
| 2 | `echo eval/tools/ci_minutes.py --scope` satisfies the substring and runs `echo` | fail-open |
| 3 | `str.split` keeps quote characters, so `python3 "eval/tools/ci_minutes.py" --scope` was reddened; a trailing `# note` became 2 unrecognised args | false positive |
| 4 | the `comments=True` fix was fail-open across a newline — a `#` on line 1 of a `run: \|` block hides the line that overwrites `relevant` | **fail-open** |
| 5 | a suffix match accepts `nested/eval/tools/ci_minutes.py`, and `nested/python3` is the same substitution with the roles swapped | fail-open |

Rounds 4 and 5 were still finding real defects, so the honest reading is that the surface has not
been exhausted rather than that it is clean. Round 5 is the per-task ceiling.

## What is NOT pinned, and why

3 rows of `MODE_ACCEPTS` are **read, not measured**: that the census reads `--cache` and
`--no-timing`, and that `--path-filter` reads `--cache`. Exercising them needs the Actions API and
`--selftest` is offline. The comment above the block says so. What IS pinned: the table's shape,
that `MODES` is `main`'s real dispatch order (read out of `main`'s source with `inspect`, because
`invocation_problems` reports which mode *would* have run), that no modifier is dead, every
refusal, and that `--gates --json` / `--hooks --json` really produce JSON.

## One declined recommendation, with its reason

The reviewer asked for the mutation inventory to move to `eval/RUNS.md`. Declined: that file is
*"what resource every run used, and what it may be compared with"* — a run there is a trial
matrix, not a CI gate — so the register's own content would end up at an address no reader of the
register looks at. It is also not history: it is the current statement of what the gate catches,
which is what `--selftest`'s closing line counts.

## One number I got wrong, and corrected

The round-5 commit message on the branch says **17** planted mutants. It is **16** — I carried it
forward instead of re-reading it, which is what this ticket's own `done_when` warns against. The
pull request body (the permanent record, since the repository is squash-only) says 16 and lists
all 16 rows, and a correction is posted on the pull request.
