---
id: 208
title: 'renumbered-citation corpus: code files'
status: in_testing
priority: 3
refs: 'eval/tools/docstat.py (_check_renumbered_citations corpus, _tracked_md), eval/findings/documentation.md #211, tasks/207'
done_when: Either _check_renumbered_citations reads code files for finding-number citations, with its corpus asserted against a walking oracle the way the doc corpus one is, and both directions pinned in the selftest (a stale code citation planted at a historical commit is reported; a correct one is not), and the false-positive cost over the live tree measured before shipping - or the corpus is deliberately pinned to documents with the reason recorded beside the check and in this ticket, in which case the finding stands as the record and code-file citations are read only by passes. Whichever way, the finding text in documentation.md must name the real outcome instead of task <TASK>.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/88
established_by: 'evidence: docstat --sweep, --selftest (202 pins, 0 wrong), --withdrawn, --findings and tasks.py check all exit 0 at ee89eb8; corpus_control 7/7 mutants dead, triage_control, findings_control 21/0, withdrawn_control 54/54 all pass; review rounds 1-3 addressed (394d82f, 11a77b3, ee89eb8), each defect demonstrated RED as a selftest pin before its fix and green after (6 expected failures round 1, hostile-root round 2, 6 substring-exclusion failures round 3); md-only mutant re-measured at 9 pins red with the number corrected in DECISIONS.md; --renumbered at HEAD: 0 stale, 0 untriaged of 37, 276 documents + 444 code/data paths read, 15 skips named; --at bc605f0~1 reports the 14 known-stale rows at that revision, 0 at HEAD.'
---

Finding #211 (2026-08-29): the renumbered-citation check selects its corpus with _tracked_md, so a stale #N inside a .py docstring or comment is invisible to it. Measured: 8 stale code-file citations across two sessions (the judge_ledger/field_sweep pair in task 206, six more in task 207), 0 caught by the gate, every one found by manual reading, while --renumbered reported exit 0 in the same window. Each was correct when written - #119 changed hands four times on 2026-08-23 - so no resolve-check can see it either.

## note 2026-08-29

Findings for the next agent, from the two CodeRabbit rounds this ticket absorbed:

- Round 1 found a real corpus defect the selftest had missed: the corpus and its walking
  oracle spelled the same exclusion differently (relative path vs absolute), so a
  TOP-LEVEL runs/ or target/ sat in a gap no pin could see - the oracle pin only
  witnesses files the walk REACHED. If you add a corpus filter, write the probe at the
  top level of the excluded name, not only below it.
- Round 2 found the opposite failure one level up: testing the whole absolute path drags
  the checkout path into the exclusions, so a tree checked out under .../runs/ empties
  the corpus and a clean-looking 0 read 0 skipped prints. If a filter takes a root, make
  root a REQUIRED parameter (a defaulted root is an address bound at import, rule 12)
  and test root-relative with the leading separator KEPT: os.path.relpath strips the
  trailing separator a directory prune needs, so slice the prefix instead.
- Both were reproduced as red pins BEFORE the fix (selftest exit 1 with exactly the
  predicted failures), then green - the review discipline this repo asks for: verify the
  finding, pin it red, fix, green. The reviewer's suggested diff for round 2 was right
  about the defect and wrong about the mechanism (relpath); verify each one.
- The renumbered summary's document/code totals count files actually READ; every skip
  (NUL, symlink, unreadable, missing-on-disk) is named on the summary line. If you add a
  skip reason, name it there and extend the pins - a silent skip is the fail-open shape.
- The historical control --renumbered --at bc605f0~1 reports 14 stale rows while this
  branch is unmerged: task 207's 6 plus this branch's own 8 citation fixes, stale AT that
  revision because the fixes are not in its tree. That is the control working, not a
  regression; at HEAD it reports 0.

## note 2026-08-29

Round 3 (post-handback review at b328823), addressed in ee89eb8:

- The durable find: is_vendored matched PackageCache and node_modules as raw SUBSTRINGS,
  so a tracked file whose NAME merely contained one left the corpus - and the walking
  oracle shared the predicate through _outside_corpus, so no pin could see that class of
  exclusion by construction. A control sharing the assumption of the thing it controls
  (#37's shape, in a path filter). All 5 vendored entries are now complete path
  components; the two bare-name prune sites pass s + os.sep. If you add an exclusion
  name, make it a component and pin a file that merely contains it.
- The AGENTS.md fraction clause is gone: the sentence now states the split its own
  numbers show (first widened run: 15 rows, 8 decided, 7 handed to a person) and the
  standing truth (0 stale, 0 untriaged of 37 at HEAD), producer named.
- The oracle pin is one-directional and DECISIONS.md now says so.
- md-only mutant re-measured after the new pins: 9 red (was 8); recorded in DECISIONS.md.
