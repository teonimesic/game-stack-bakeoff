---
id: 188
title: Three readability findings against DECISIONS.md prose from tasks 171 and 167, one of them a claimed contradiction in rally.counts
status: done
priority: 3
refs: DECISIONS.md,eval/judge/bot_pong.py,eval/judge/scene_mutants.py
done_when: each of the 3 is read against its source and either applied or declined in writing, with the reason. Item 1 is settled by reading judge/bot_pong.py's rally.counts beside DECISIONS.md 3219-3227 and saying which of the two is wrong; a decline needs the sentence that resolves the apparent conflict quoted. docstat.py --sweep and linkcheck.py exit 0 after.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/69
established_by: 'Verified against artifacts: true scope from the merge base is prose only (DECISIONS.md 32 lines, RUNS.md 6); the item-1 decline checked against bot_pong.py - countable = hits - scoring_hits, rose_on_hit incremented only under if not scored; sweep, linkcheck and tasks check exit 0 unpiped in the worktree; scene_mutants reproduced byte-identical at 23 mutants / 15 criteria / 11 variants / 0 unmet; 2 review rounds converged with all 3 threads resolved on evidence-backed replies; handback note present in the ticket'
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

## note 2026-08-28

All four findings adjudicated against source; the round-1 review worked at head 8d2c8a8; nothing left for a blind dispatch to re-derive.

## Item 1 — the claimed all-or-nothing contradiction: DECLINED as a contradiction, APPLIED as a one-word precision fix

**Neither the criterion nor the prose is wrong.** `bot_pong._rally` computes `countable = hits - scoring_hits`, increments `rose_on_hit` only inside `if not scored:`, and returns `(countable > 0 and rose_on_hit == countable, ...)`. The resolving sentence stands in the same block as the headline: **"A hit tick that also carries the point is counted in neither half — the point zeroes `rally` on that same line — and the verdict requires a non-empty denominator, so the exclusion cannot swallow the criterion (rule 7)."** The exclusion is definitional, not a dodge: `rally.resets` requires exactly the zero the point publishes on that tick, so no reading of the contract asks a scoring hit tick's counter to rise — there is no partial-counting failure being excused. The reviewer's premise-check fails: the reconciliation was written in the SAME commit (e03be27) that wrote the headline.

What was real: the headline's input domain. Two independent review threads (PR #61 and PR #62) read "Every hit the play-bot can read" and both constructed the same misreading — n=2, independent instruments, same wrong answer, which is why the fix is not merely stylistic. The headline now reads "**Every non-scoring hit the play-bot can read must be counted**", confirmed against the code exactly as tasks/189's done_when required. The reviewer's full rewrite was declined: its content (skip = late, all-or-nothing, the `paddle.deflects` standard) is already in the paragraph verbatim, and it would discard the three-facts pointer and the `tasks/171` reference.

## Item 2 — the two re-open notes: half applied, half declined

- Applied: "a correct submission" → "a real submission" in the all-or-nothing note, aligning it with the one-tick note two paragraphs down, which names the identical class "a real submission" and states why (such a submission violates the state contract; "correct" presumes what the re-open exists to ask).
- Declined: the "reads as a fragment" complaint. "**To re-open X:**" + noun phrase is the house shape of all 17 re-open notes in DECISIONS.md; rewriting 2 of 17 makes the file less consistent, not more readable.
- Applied: the one-tick note's final em-dash sentence split in two, no words changed.

## Item 3 — the self-referential producer sentence: APPLIED

"Read the count from `python3 eval/judge/scene_mutants.py`, not from this sentence." → "Run `python3 eval/judge/scene_mutants.py` to refresh these counts." The producer stays beside the figure — that is what tasks/167 added the sentence for. The figures were re-verified before republishing: registry lines 124, 134, 144 hold exactly the 3 named mutants; line 256 holds the 1 offset-inside-own-span variant; the tool run reports `23 mutants over 15 criteria, 11 variants, 0 expectation(s) unmet` suite-wide.

## Item 4 — RUNS.md 26th comparability break: APPLIED

"which is the standard `paddle.deflects` beside it already held" → "which is the standard already used by `paddle.deflects`", and the new reading's domain named **non-scoring** there too, so the two documents state the same requirement (the `scoring_hits` exclusion was introduced in the same e03be27 change the section records).

## Review round 1 (PR #69, both threads on the floor paragraph — prose my diff sits beside, not in)

- Thread 1 (direct wording): applied the splits (em-dash sentence → three sentences; semicolon sentence → two), every clause preserved. Declined the replacement with evidence in-thread: "the trace contradicts the hit count" inverts the derivation (the count is read from the line's own events; the contradiction is internal to one line — fact 3), "like paddle.deflects" drops "in the same loop", and the floor rewrite drops "the contract is per hit, so one hit measures it" — the justification for why 1 and not 6 or arbitrary slack.
- Thread 2 (live-Markdown conventions): applied "ONE" → "1" (digits rule; the block's own usage is digits elsewhere). Declined `[`#46`]` with the census: 173 plain `#NNN` citations vs 2 linked (both `#95`, which has a link definition into eval/findings/); `#46` appears plain twice (3134, 3418), so a one-line conversion makes the same finding read two ways, and a definition-less reference resolves nothing. Both replies posted as JSON, stored bodies diffed byte-identical apart from the API's trailing newline.

## Review round 2 (one new thread; declined with evidence; all threads resolved)

- Thread "Replace the metaphor in the denominator rule" ("swallow the criterion" called figurative): **declined** with the census — "swallow" is the file's established verb for this failure mode (lines 2052, 2537, 3688), the exact phrase "cannot swallow the criterion" mirrors `bot_pong.py`'s docstring line 476 verbatim so the two artifacts state the reconciliation in the same words, and the sentence already carries the literal mechanism ("The verdict still requires a non-empty denominator") before the idiom glosses what it protects. The replacement restates `countable > 0`, which the preceding sentence and the code's first verdict conjunct already state. Stored reply diffed byte-identical.
- Round 2 re-flagged nothing else — the round-1 sentence I offered to rework ("A count of the hits the lines carry…") was not raised again, so the round-1 resolutions stand.
- All 3 review threads resolved (2 round-1, 1 round-2), each after its evidence-backed reply, not instead of one. `mergeable.py` now reports only the orchestrator's merge-time rows: required `controls` check in_progress (CI re-running at 8d2c8a8) and the branch 4 behind main — left there deliberately per the coordinator, since main's 4 commits touch neither DECISIONS.md nor eval/RUNS.md (`git diff HEAD...origin/main -- DECISIONS.md eval/RUNS.md` is empty).

## Deliberately not done — what the next session must not re-derive

- **`bot_pong.py` untouched.** Its docstring (line 460) carries the same headline-plus-exclusion structure and reconciles itself in-block ("WHAT IS EXCLUDED…"). No reviewer flagged it; tasks/189 explicitly holds the criterion file still. If the docstring's headline should also say "non-scoring", that is a one-word follow-up the orchestrator can take or leave.
- **`eval/RUNS.md`'s re-open line** ("**What re-opens it.** A correct submission failing with `0 < rose_on_hit < countable`.") still says "correct" — same falsifier condition, adjective only, outside every flagged item. If DECISIONS.md's "real submission" alignment is extended, this is the line to take with it.
- **The "swallow" idiom** stays (4 DECISIONS.md uses + the docstring mirror). If it is ever purged, that is a sweep-wide wording change — all uses together, never line-by-line under review rounds.
- **tasks/189 is the duplicate** (items 1 + 4); its own second note says "Superseded by `tasks/188` — close this as a duplicate". Its done_when's code-confirmation requirement is discharged above. Its general lesson is already recorded there: two agents filed the same ticket within the hour because CodeRabbit reviews the whole file set a merge brings in — any branch that merges `main` inherits review comments on other people's landed prose. This round confirmed it again: both round-1 threads anchored on the floor paragraph, prose this branch never touched.
- **Branch left 4 behind main** per the coordinator — main's 4 commits touch neither DECISIONS.md nor eval/RUNS.md (`git diff HEAD...origin/main -- DECISIONS.md eval/RUNS.md` empty), so no merge was needed for the repairs.

## Fact-check of the review comments (the ticket asked: a review comment is a second opinion, not a finding)

Item 1's contradiction claim: false as stated (reconciliation predates it, same commit), pointed at a real imprecision. Item 2: half right ("correct submission" real; fragment complaint a house-style false positive). Item 3: right. Item 4: right. Round-1 thread 1: intent right, concrete wording lossy. Round-1 thread 2: half right (digits yes; citation format contradicts the file's own census).

## Gates

docstat.py --sweep exit 0, linkcheck.py 0 unresolved exit 0, tasks.py check exit 0 — all unpiped, run after staging, twice (initial commit and round-1 commit).
