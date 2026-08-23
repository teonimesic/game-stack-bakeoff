---
id: 58
title: Nothing flags a citation of a finding that was renumbered at merge
status: open
priority: 3
refs: eval/tools/docstat.py cmd_sweep, eval/FINDINGS.md #94, eval/FINDINGS.md #80
done_when: a check reports every citation in the repository that names a finding number which git history shows was used for a different finding, run against tasks/ and the instruction docs; if it reports zero after the four known instances are repaired, that is the pass, and if the check cannot be made to fire on a planted stale citation it does not count as done
---

four closed tasks cite finding numbers that now name a different finding, and every citation still resolves so no existing sweep can see it

## What is this thing?

Findings in this project are cited by number: `eval/FINDINGS.md` holds an index of `#19`..`#111`
and each row points at the file in `eval/findings/` that carries the entry. Tasks, protocol docs,
decisions and the findings themselves all cite by that number. `eval/tools/docstat.py --sweep`
checks that cited names *resolve* — a finding number that does not exist fails the sweep, and it
can also fail on a number used twice inside `eval/FINDINGS.md`.

## What is wrong, and how do we know?

Numbers are chosen by the agent writing the finding, and parallel agents choose the same one.
When two branches merge, the collision is resolved by **renumbering one of the findings** — and
nothing updates the documents that already cited the old number. The citation still resolves, so
no sweep can see it; it now points confidently at somebody else's finding.

Measured 2026-08-23 by replaying every `## NN.` heading ever added under `eval/findings/` against
the current numbering. **Eight findings have been renumbered:**

| written as | now | claim |
|---|---|---|
| 89 | 90 | #87's decomposition got the boundary wrong |
| 90 | 91 | three of four mutants were inert |
| 90 | 92 | a scored tier that returns the same number for every submission |
| 91 | 93 | `suite.json` describes the last thing written into the directory |
| 95 | 97 | four of the nine performance fields had no reader |
| 99 | 100 | the stored `verify.green` evidence drops the gate's own passed line |
| 103 | 104 | the only record of the starter a run was given is a git commit |
| 104 | 105 | of 27 unread exit statuses, 24 were deliberate |

Four stale citations in `tasks/` were found and repaired by hand in the same pass — task 25 cited
#95 for what is now #97, task 34 cited #104 for #105, task 42 cited #103 for #104, and task 45
cited #99 for #100 in both its `refs` and its body. **`tasks/` is one directory of several, and
it was swept by grep, not by a tool.** `eval/PROTOCOL.md` carried a fifth (a `(#103)` that meant
#104) and was repaired at the same time. Nobody has looked at `DECISIONS.md`, `README.md`,
`eval/RUNS.md`, either `IMPROVEMENTS.md`, `research/`, the skills, or the cross-references
*inside* `eval/findings/` itself.

## Why does it matter?

This is #94 — three agents took the same task id because each guarded its own copy — with the
damage moved downstream. The collision itself is now caught, and that is the reason this defect
exists at all: **the fix renumbers the finding and leaves every reference to it pointing at a
stranger.** It is also #80's shape: a durable record that quietly lost its meaning while
remaining well-formed.

The cost is not theoretical. A reader following task 42's `FINDINGS #103` lands on a finding about
a merged capture buffer in `runner.py` and has no way to tell they were sent to the wrong place,
because #103 is a real finding and the sentence around the citation is about something else.

## What should be done?

The check is roughly twenty lines and needs no new dependency:

1. For each file under `eval/findings/`, walk `git log` and collect every `## NN. <heading>` ever
   added, keyed by heading text.
2. Compare against the current numbering to build a map of `old number -> current number` for any
   heading whose number moved.
3. Scan the citing corpus for `#NN` and `FINDINGS NN` forms and report any citation of a number
   that map says was reused, with the file, the line and both claims, so a human can judge which
   was meant. It cannot decide automatically — a citation of `#95` may legitimately mean today's
   #95 — so **report, do not fail**, in the manner `tasks.py check`'s reachability warning already
   establishes for a smell that is not a verdict.

Put it where the mechanical documentation checks already live, in `docstat.py`. Note that
`eval/tools/docstat.py` was under active edit on 2026-08-23; rebase before starting.

## Outcomes that count as success

- It reports the five known instances when run against the repository as of this task being
  filed, and nothing else that a reader judges wrong. That is the positive control, and it must
  be run *before* the five are repaired or against a revision where they still stand.
- It reports zero on the repaired tree.
- A planted citation of a renumbered number in a file that currently has none makes it fire.

A run that reports zero without the first control having fired establishes nothing — that is the
`total=0 passed=0` failure this project has already paid for.

## What NOT to conclude

Do not renumber any finding to fix a citation. The number in `eval/findings/` is the published
one and the citation is what is wrong. Never edit `eval/FINDINGS.md` or `eval/findings/` to make
a checker green.
