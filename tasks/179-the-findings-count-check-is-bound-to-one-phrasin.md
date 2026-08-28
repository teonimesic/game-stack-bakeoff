---
id: 179
title: The findings-count check is bound to one phrasing, and a count 28 short survived beside its own producer
status: done
priority: 2
refs: eval/tools/docstat.py,README.md,AGENTS.md,tasks/177
done_when: 'Every place a live document states how many findings there are is reconciled against `docstat.py --findings`, not only those phrased ''N numbered findings''. The trigger is chosen the way the census-trigger section of DECISIONS.md requires: candidates measured against the live corpus and selected on false positives, with the count of red lines and the number of shipped pins each candidate gets wrong both recorded - the quantifier-based trigger that section rejected is the obvious wrong answer here too. Pinned red and green, with the ''entries'' phrasing among the pins. A null result is acceptable and closes this: if no closed-class trigger beats the current enumeration on the live corpus, extend the enumeration to cover ''entries'', say so with the numbers, and note that the next unlisted wording will fail the same way.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/58
established_by: 'docstat --count-triggers is the producer for the candidate table; shipped trigger 0 red / 0 of 19 pins wrong against the quantifier''s 13 red; 21 controls 0 failed, 9 mutants 0 survived; PR #58, 3 review rounds, reviewer rate-limited at the final head'
---

Found while clearing review on PR #46 on 2026-08-27.

`README.md` line 187 read '143 entries. Findings #19-#189, count and range from `python3 eval/tools/docstat.py --findings`' against a measured **171**. It was 28 short. The producer was named in the same sentence.

AGENTS.md's rule is 'a count with a producer goes stale for an hour; a count with none goes stale forever'. This is the case that rule does not cover: a count with a producer NAMED BESIDE IT and nothing running the comparison. The citation is what makes it dangerous - a reader has every reason to treat the figure as derived, and it was typed.

The mechanism is that `docstat.py --findings` reconciles counts written as 'N numbered findings' - it does enforce that, and correctly reddened `README.md` line 311 during this same session - while line 187 says 'entries' and matches nothing. **Same file, same fact, one gated and one not.** The RANGE on line 187 is checked (my first repair reworded it and the gate went red immediately, which is the system working); the COUNT beside it is not.

This is the open-class trigger problem AGENTS.md's rule audit records at length, in its documented-failure direction: the trigger is an enumeration of wordings, so it fails on the first wording nobody had when it was written. The audit's conclusion applies - prefer a CLOSED class, and choose between candidate triggers on the live-corpus false-positive count rather than on which sounds more general.

## note 2026-08-27

## note 2026-08-27 (orchestrator) — 176 has MERGED and it changed the corpus your check runs over

`tasks/176` landed as #198: `docstat.project_docs()` no longer globs the filesystem — it and
`_live_corpus()` share `_tracked_md()`, which lists with `git ls-files -z`, and `_corpus_pins`
asserts the two agree about membership. **No pinned count moved**, because on a clean checkout the
glob and the index returned the same 238 documents.

That matters for you in one specific way: **the population your count check runs over is now
defined by the index rather than by the disk**, so a candidate trigger's false-positive rate is
measurable against a stable corpus. Measure it there.

Also from that work, because it is the same file and you will read it: `_git` used to fold a
non-zero exit into `""`, so a failed listing and an empty tree were the same answer. It raises now.
If your repair adds any git read, do not reintroduce that shape.

**And the case your ticket exists for is still live.** `README.md` line 187 carried '143 entries'
against a measured 171 while naming `docstat.py --findings` in the same sentence, because the check
matches 'N numbered findings' and that line says 'entries'. It has since been corrected by hand and
the count has moved again — read it from the producer, do not trust any digit written here.

## note 2026-08-27

## note 2026-08-27 (agent, task 179) — what shipped, and the finding that needs a number

### The finding, unnumbered — the orchestrator allocates it against `main`

**A gate ran on every commit for 4 days, reported itself clean, and could not see the figure it
exists to protect, because its trigger was an enumeration of one wording.** `README.md` line 187
stated a findings count 28 short of the log with `docstat.py --findings` named in the same
sentence; a count of the same fact 128 lines lower, phrased `N numbered findings`, was gated and
correct. The gate's own output said nothing was wrong, and the producer citation made the wrong
figure read as derived.

This is `AGENTS.md`'s rule-audit conclusion firing against a regex for the second time (the first
was task 92, the aspect census). The generalisation that is new: **`a count with a producer goes
stale for an hour` does not cover a producer that is NAMED beside a count and never run. The
producer has to be run by something that is not a person**, and a citation without a runner is
worse than no citation, because it buys the figure trust it has not earned. `AGENTS.md` now
carries that as a blockquote under the existing count rule.

### What is in place now

- `_stated_counts` reads 2 triggers: `N numbered findings`, and any cardinal governing a plural
  noun on an unfenced line naming the log by its range sentence, its path, or its producer.
- `_count_corpus()` is the single spelling of the count corpus — the live corpus plus
  `RANGE_DOCS`, 58 documents on 2026-08-27, against 3 before.
- `python3 eval/tools/docstat.py --count-triggers` is the producer for the candidate table, and
  refuses an incomplete corpus at exit 2.
- `DECISIONS.md`, *the findings count is read from the log's ADDRESS*, is the authority.

### What the next agent must not re-derive

**The candidate measurement, and why the obvious answer is wrong.** Over the count corpus, holding
the word-form trigger constant: the shipped enumeration alone 0 red / 2 of 19 pins wrong; the same
list plus `entries` 6 red / 1 wrong; the quantifier governing `findings|entries` 13 red / 0 wrong;
the shipped conjunction 0 red / 0 wrong. Every red line in the rejected rows is a false positive.
**Re-run `--count-triggers` rather than quoting those numbers** — the quantifier row was 12 when
the entry was drafted and 13 when it was finished, and the 13th line is a sentence in `AGENTS.md`
written to document this decision.

**The free parameter is the word gap between the cardinal and the plural noun, and it is 2.**
Gaps 0-3 all measure 0 red; 2 catches 4 of 5 planted phrasings where 1 catches 3 and 3 catches no
more. Same cost, strictly more coverage.

**The word form was deliberately NOT scoped on the address.** It costs 2 false positives on the
live corpus (`eight ... lines`, `eleven ... days`), so a count spelled in words is still read only
in the `numbered findings` wording. A count governing no plural noun — `Findings #19-#198 — 143 of
them` — is invisible to every candidate at 0 cost. Both gaps are recorded in `DECISIONS.md`.

**The trigger's cost lands on the documents that explain it.** The fence-or-reword rule fired 4
times on this branch's own prose. That is the honest bound on how often it will fire, and it is
why the failure message names the repair.

### Review, and the 2 defects it found that the work had not

CodeRabbit found both, and both were real:

1. `findings_control.py`'s fixture builder ran `git init` / `git add -A` with `cwd=` alone. An
   inherited `GIT_DIR` outranks `cwd` silently at exit 0 — **#198, committed inside the file
   whose job is to be the independent reader.** Fixed with a `GIT_*` scrub, written out rather
   than imported from `docstat._git_at`, plus a `HOSTILE GIT_DIR` control carrying its own red
   half.
2. `--count-triggers`'s SHIPPED row measured only the address-scoped half of a rule that is a
   union of 2 triggers, so it reported `red 0` on an input `--findings` gates on. Fixed, and
   pinned by **a row that compares the producer's row against `_stated_counts`** rather than by
   making them the same object.

Also: a missing `RANGE_DOCS` document was dropped from `--count-triggers`'s corpus silently.
`--findings` records it; a producer whose exit code means nothing must refuse, and now does.

### Handed back while the reviewer's pool was exhausted

Round 4 never started. `gh pr checks` reads `CodeRabbit — pass — Review rate limited`, and 20
minutes of polling at the final head returned `NOT_YET` with no round ever in flight. 3 rounds
ran; every comment in all 3 was acted on or answered with evidence in its thread. The head
CI `gates` job is green.

## note 2026-08-27

## note 2026-08-27 (agent) — correction to the handback note above, and the final state

The section above said "3 rounds ran ... the head CI `gates` job is green" and gave the control
count as of round 3. Two things changed after it was written, and this replaces those figures:

- A 4th commit landed, `86bd391`, registering `docstat --count-triggers` in
  `.github/workflows/README.md` as a gate deliberately left out. `AGENTS.md` requires the
  register to name every gate excluded with the reason, and a producer that gates nothing is
  one — its rejected-candidate rows are meant to be non-zero, so gating on them would gate the
  wrong sign.
- `findings_control.py` is **21 controls, 0 failed**; `--all-mutants` **9 mutants, 0 survived**.

**The last head CodeRabbit reviewed is `bee8160`.** `6a37e30` (round 3's own repairs) and
`86bd391` are unreviewed, and the reason is the reviewer's allowance, not a clean round:
`gh pr checks` reads `CodeRabbit — pass — Review rate limited`, polling at the final head
returns `NOT_YET` with no round ever in flight, and one `@coderabbitai review` request did not
start one. The round budget was not restarted, because the pool is shared. This is stated in a
comment on the pull request as well as here.

**Every gate re-read at the final tree, unpiped, all exit 0**: `docstat --sweep`, `--selftest`,
`--findings`, `--count-triggers`, `--withdrawn`, `--renumbered`, `--citations`;
`findings_control.py` and `--all-mutants`; `withdrawn_control`, `corpus_control`,
`fragment_control`, `triage_control`, `integrity_census --windows`, `ci_minutes --selftest`,
`tasks.py check`, `linkcheck`. CI `gates` green at `86bd391`; CI `controls` was still running.

## note 2026-08-27

## note 2026-08-27 (agent) — the branch was merged with `main` by someone else, and the merged head is verified

`3ab6ab9 Merge branch 'main' into task-179-findings-count-trigger` was pushed to this branch
after the handback. `pr_review_state.py` refused with **`STALE HEAD`** at exit 1 rather than
polling — the head was `3ab6ab9` where `86bd391` was expected — which is the guard working as
`tasks/127` intended: the poll would otherwise have answered about a head nobody had verified.

**The merge is what this work most needed to be tested against, and it passes.** `main` brought
finding **#199**, moving the log from 180 to 181, so both of `README.md`'s count statements had to
move — the gated `181 numbered findings` on line 315 **and the `181 entries` on line 187 that
this task's trigger is the only thing that can see.** Both are correct at the merged head and
`--findings` is exit 0 over 58 documents.

Re-read at `3ab6ab9`, unpiped, all exit 0: `docstat --sweep`, `--selftest`, `--findings`,
`--count-triggers`, `--withdrawn`, `--renumbered`, `--citations`; `findings_control.py` and
`--all-mutants`; `withdrawn_control`, `corpus_control`, `fragment_control`, `triage_control`,
`integrity_census --windows`, `ci_minutes --selftest`, `tasks.py check`, `linkcheck`.

**The candidate rows did not move across the merge** — 0 / 6 / 13 / 0 — while the count they are
measured against did, which is the separation the producer exists to make visible. The figures in
`DECISIONS.md` are dated 2026-08-27 and stand as written; re-run `--count-triggers` rather than
quoting them.

Nothing to push: the local branch was fast-forwarded to the merged head, and the working tree is
clean. CI was re-triggered by the merge and was running at `3ab6ab9` when this was written.

## note 2026-08-27

## note 2026-08-27 (agent) — CI outcome at the merged head

All checks terminal and green at `3ab6ab9`: **`gates` pass 3m14s, `controls` pass 15m59s.**
`controls` is the long job and had not finished at the previous handback; it has now.

The third row reads `CodeRabbit — pass — Review rate limited`. **That is the rate limiter, not a
review.** The last head CodeRabbit actually read is still `bee8160`, and `3ab6ab9` is 3 commits
past it — the round-3 repairs, the CI-register row, and the `main` merge. Anyone reading the
checks table alone would take that row for a clean review, which is the reason it is written down
here.

## note 2026-08-28 (orchestrator) — CLOSED at the merge

Merged as squash `eacc3ae` (PR #58) after the branch went stale behind #64 and CI re-ran at the
updated head. The unnumbered finding the PR message requested is allocated against `main` as
**#207**, in `eval/findings/certifies-nothing.md`, from the ticket's drafted text. `docstat.py
--findings` green at **189 findings, #19-#207**, count and range agreeing across the three
stating documents.
