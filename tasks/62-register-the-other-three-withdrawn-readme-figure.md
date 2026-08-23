---
id: 62
title: Register the other three withdrawn README figures, and measure whether any live document still states them
status: done
priority: 4
refs: eval/withdrawn.json, eval/tools/docstat.py, eval/tools/withdrawn_control.py, README.md corrections table
done_when: eval/withdrawn.json carries an entry for each of 20-of-24, the 380-paired-criteria pair (0 verdict differences and 219 of 380), each with match patterns proved against an archive anchor; docstat.py --withdrawn is green at HEAD after whatever repairs those entries name; and each entry was measured RED at a revision before its own withdrawal landed, so it is known the patterns can fire
established_by: 'eval/withdrawn.json carries WR-20-of-24, WR-paired-verdict-tie and WR-paired-evidence-diff, each anchor-proved against eval/findings/certifies-nothing.md. docstat.py --withdrawn was RED at HEAD on first run with 8 hits over 4 live documents - README twice, DECISIONS.md twice, eval/judge/JUDGING.md twice - and is exit 0 after the repairs. Historical red over the real tree: 727759d, the commit before 307c957, publishes both 380 halves in README''s headline evidence row; a3d0fd1 publishes 20-of-24 in README. That entry has no claim-as-current revision at all, because its withdrawal predates the first commit, and the limit is stated in withdrawn_control.py rather than smoothed over. withdrawn_control.py goes 41 to 54 controls, all five mutants still flip, and it now carries a VARIANT proving the per-scope replacement wording stays green. DECISIONS.md''s re-open row for the deterministic-tier ranking ban rested on the withdrawn figure and is repaired to the scoped 5 of 436 and 0 of 232; choosing a threshold size is filed as task 70. docstat.py --sweep, --selftest and tasks.py check all exit 0.'
---

Task 55 built the register and seeded it with two entries: the tier-3 pair (task 54) and finding 54's redundancy claim. README's corrections table declares three more withdrawals that predate it and are in no register entry, so nothing checks whether a live document still states them. They were left out of task 55 deliberately - that task's instruction was to record decisions already made, one at a time, each with its own anchor proof and its own historical red measurement, and adding three unverified entries would have been the vacuous-green shape the register exists to avoid. The 20-of-24 figure is the harder one: eight different combinations of cells reach it, so its signature may need more than the bare number to avoid firing on unrelated prose.

## What was found, 2026-08-23 - do not re-derive this

THREE ENTRIES, NOT TWO. The 380 pair is two register entries (`WR-paired-verdict-tie`,
`WR-paired-evidence-diff`), not one. A single entry over all three patterns is silent on a
document that restates only one half, and both halves are separately restated in the wild.

THE done_when'S LAST CLAUSE IS NOT REACHABLE FOR `WR-20-of-24`, and that is a fact about the
repository, not a failure to look. Its withdrawal predates the first commit: `git log -S"20 of
24"` over all paths returns exactly `a3d0fd1`, the initial import, whose README already carries
the withdrawal notice. **What to report when a historical red is unreachable: say so, name the
earliest tree that exists, and state what its red does prove.** Here `a3d0fd1` gives a real red
on README.md - the patterns fire on the real wording in a block that carried no machine-readable
marking - and the claim-as-current case is covered by planted POSITIVE controls instead, which is
weaker and is labelled as weaker in `withdrawn_control.py`. The 380 pair had no such problem:
`727759d` (the commit before `307c957`) publishes both halves in README's headline evidence row.

THE ANCHOR FOR `WR-20-of-24` STATES IT IN WORDS, THE LIVE DOCUMENTS IN DIGITS.
`eval/findings/certifies-nothing.md` #50 reads "Twenty of the twenty-four cells now sit at
exactly 1.000"; README read "20 of 24" and "20/24". So the entry's first pattern is an
alternation over all three forms, and the anchor proof only ever exercises one branch of it - the
other two are planted separately in the controls. **An alternation with an unproved branch is a
pattern that has been read, not measured.**

REGISTERING THESE FOUND THREE LIVE DOCUMENTS NOBODY KNEW WERE STALE. The withdrawal had been
recorded in README's corrections table and propagated nowhere: `DECISIONS.md` (twice, including
the row stating what would re-open the deterministic-tier ranking ban) and `eval/judge/JUDGING.md`
(twice) were still asserting `0 of 380` as current. That is the register's first non-vacuous
result and the argument for the whole mechanism.

REPAIRING ONE OF THOSE MOVED A DECISION. `DECISIONS.md`'s re-open condition read "any instrument
change producing non-zero within-cell verdict variance - currently 0 of 380". The scoped recount
is 5 of 436 in `wg-matrix` and 0 of 232 in `wg-audio48`, so the condition is met in letter by a
quantity that had no reason to be exactly zero once it was scoped. The row now says "large enough
to resolve a between-stack gap" and the size is left open in **task 70**.

DO NOT PUT A REGISTER `match` PATTERN INSIDE AN ENTRY id. An id is scanned as ordinary text, so
an id containing `380` would satisfy another entry's `380` pattern and quietly widen its
exemption. That is why these are `WR-paired-*` and not `WR-380-*`.
