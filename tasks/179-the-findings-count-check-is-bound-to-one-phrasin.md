---
id: 179
title: The findings-count check is bound to one phrasing, and a count 28 short survived beside its own producer
status: in_review
priority: 2
refs: eval/tools/docstat.py,README.md,AGENTS.md,tasks/177
done_when: 'Every place a live document states how many findings there are is reconciled against `docstat.py --findings`, not only those phrased ''N numbered findings''. The trigger is chosen the way the census-trigger section of DECISIONS.md requires: candidates measured against the live corpus and selected on false positives, with the count of red lines and the number of shipped pins each candidate gets wrong both recorded - the quantifier-based trigger that section rejected is the obvious wrong answer here too. Pinned red and green, with the ''entries'' phrasing among the pins. A null result is acceptable and closes this: if no closed-class trigger beats the current enumeration on the live corpus, extend the enumeration to cover ''entries'', say so with the numbers, and note that the next unlisted wording will fail the same way.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/58
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
