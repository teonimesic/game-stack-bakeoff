---
id: 75
title: Two more tree walkers glob one level deep and skip the four runs nested in archive-run1
status: open
priority: 4
refs: eval/tools/census.py, eval/tools/manifest.py, eval/judge/tier1_census.py, eval/findings/certifies-nothing.md finding 125
done_when: 'For each of manifest.py audit and judge/tier1_census.py: either it reaches the nested runs and its output is stated before and after, or it is documented as deliberately top-level-only with the reason. A depth fix that changes no number is a result, but it must be shown as a number that did not change, not asserted. Establish the current state first - manifest.py audit prints its own run-directory count on the last line.'
---

census.py reported 137 records where the tree holds 161 because archive-run1-byte-identical-prompts wraps four run directories one level deeper than the glob reached (#125, task 69). census.py is fixed. Two others were found with the same shape and deliberately left, because neither publishes a count: manifest.py audit_tree iterates runs_dir with iterdir() and is_run_directory() rejects the wrapper, so it examines 19 run directories and audits none of the four archived runs - verified, 0 lines of its output name archive-run1. judge/tier1_census.py globs */artifacts/*/eval/report.json. Neither has been checked for whether the archived runs would change what it reports.
