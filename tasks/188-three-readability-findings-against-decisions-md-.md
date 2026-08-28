---
id: 188
title: Three readability findings against DECISIONS.md prose from tasks 171 and 167, one of them a claimed contradiction in rally.counts
status: todo
priority: 3
refs: DECISIONS.md,eval/judge/bot_pong.py,eval/judge/scene_mutants.py
done_when: each of the 3 is read against its source and either applied or declined in writing, with the reason. Item 1 is settled by reading judge/bot_pong.py's rally.counts beside DECISIONS.md 3219-3227 and saying which of the two is wrong; a decline needs the sentence that resolves the apparent conflict quoted. docstat.py --sweep and linkcheck.py exit 0 after.
---

Three CodeRabbit readability findings against DECISIONS.md prose that landed on main from tasks 171 and 167. They surfaced on PR #61 (task 185) only because merging main put those lines in that review's file set; task 185's diff touches DECISIONS.md at one hunk, @@ -1443,13 +1443,30 @@, and none of these lines. `git log -1 -L 3219,3232:DECISIONS.md` names e03be27 (task 171) and `-L 3309,3312` names 2b9a82a (task 167), so neither belongs to the branch that was asked about them.

The three, verbatim in substance:

1. DECISIONS.md ~3219-3227, FUNCTIONAL: "Limit the rule to non-scoring hits." Line 3219 says every readable hit must be counted while line 3226 excludes a hit that also carries the point, which is an internal contract conflict. Suggested: "Every non-scoring hit visible to the play-bot must be counted. A skipped increment is as incorrect as a late increment. Therefore rally.counts is all-or-nothing, like paddle.deflects in the same loop." This is the one worth reading first: it is a claimed contradiction inside a criterion's own definition, not a style note, and if it is real the rule as written admits two readings of what rally.counts requires.

2. DECISIONS.md ~3230-3232 and ~3278-3282, READABILITY: both re-open notes for rally.counts read as fragments rather than rules. The first opens "To re-open the all-or-nothing reading of `rally.counts`:" with a noun phrase and calls the partial-counter case a "correct submission"; the second packs trigger, consequence, alternatives and rationale into one sentence. A re-open condition is the part of a decision a future session acts on, so it is the worst place for prose that has to be parsed twice.

3. DECISIONS.md ~3309-3312, READABILITY: "Read the count from `python3 eval/judge/scene_mutants.py`, not from this sentence." tells the reader not to trust the sentence they are reading. The producer is right; the self-reference is the defect. Suggested: "Run `python3 eval/judge/scene_mutants.py` to refresh these counts."

Whoever takes this should check each against the source before editing - a review comment is a second opinion, not a finding - and item 1 in particular needs `judge/bot_pong.py`'s rally.counts read alongside the paragraph, because the fix is either the sentence or the criterion and the two are not the same task.

## note 2026-08-27

**A fourth finding, in `eval/RUNS.md` rather than `DECISIONS.md`, and it is the same shape as
item 1** — task 171's prose, reviewed inside somebody else's merge commit. It surfaced on pull
request **#62** (task 138) at head `03189ef`, where merging `main` put those lines in the review's
file set; task 138's own diff does not touch them.

**`eval/RUNS.md:2647-2650`, READABILITY.** *"Replace the hard-to-parse comparison clause."*

> It now requires a rise on **every** hit the drive can read, which is the standard
> `paddle.deflects` beside it already held.

The clause makes the reader reconstruct the comparison. Suggested: state the rule and the matching
standard as separate sentences — *"...which is the standard already used by `paddle.deflects`."*

Same caution as the three above: read it against `eval/judge/bot_pong.py` before editing, and note
that this sentence and item 1 describe the **same** criterion in two documents — if item 1's
adjudication changes what `rally.counts` requires, this sentence changes with it, and the two must
not be edited to say different things.

Task 138's agent declined it in #62's thread rather than editing task 171's landed prose inside
task 138's squash commit, and filed it as `tasks/189` before this ticket was visible on `main`.
**`tasks/189` is a duplicate of item 1 plus this one; close it in favour of this ticket.**

## note 2026-08-28 (orchestrator) — current at dispatch

**Your line addresses have drifted; DECISIONS.md moved under them.** Find the three items by
content, not by number:

- Item 1 (the claimed all-or-nothing contradiction) now sits around **DECISIONS.md ~3411-3420**
  ("Every hit the play-bot can read must be counted…" beside "A hit tick that also carries the
  point is counted in neither half…"). **The current prose already carries a reconciliation
  sentence** — the exclusion is justified by the point zeroing `rally` on that same line and the
  verdict requiring a non-empty denominator, "so the exclusion cannot swallow the criterion". So
  item 1 may already be RESOLVED on main, or the reconciliation may itself be the defect. Settle
  it by reading `judge/bot_pong.py`'s `_rally` beside the paragraph and either declining with the
  quoted sentence that resolves the conflict, or applying a fix. `tasks/159` is named at ~3390
  as where that decision lives — read it too.
- Item 2 (the two re-open notes) around **~3471** and its partner — grep "To re-open".
- Item 3 (the self-referential producer sentence) now at **~3505**.

**Task 191 has MERGED** (`fdfa375`): `judge/bot_pong.py` changed (`_match_ends`, a new
`GRACE_BUDGET`; `_rally` itself untouched — the word rally appears in its diff only inside
evidence strings) and `judge/bot_mutants.py` grew ~334 lines of pong end-window pins. Baseline
on main: `bot_mutants.py` exit 0 at **53 mutants / 45 criteria / 17 variants / 0 pending / 3
session-lock controls / 70 hazards / 0 unmet**; `--selftest` 36/36. **If item 1's honest
resolution is a criterion change rather than a sentence change, file that as a task — this
ticket is a prose adjudication and does not carry a criterion repair.**

**Overlap with `tasks/189`:** it was filed from the same review thread against the same
rally.counts prose family. If your item 1 or 2 settles 189's finding, say so in your handback;
189 gets currented against your result rather than dispatched blind.

PR 68 (task 192) is in review touching `ci_minutes.py` + `.github/workflows/README.md` only —
no conflict with yours. Nothing else holds DECISIONS.md.
