---
id: 118
title: 'FINDINGS #146 publishes a census with no producer, and it does not reproduce'
status: done
priority: 4
refs: eval/findings/certifies-nothing.md lines 4223-4272, tasks/112, eval/tools/docstat.py ARCHIVE_PATHS
done_when: 'Either a producer exists that re-derives #146''s census - a script or a documented command with its population stated - and #146 cites it, or #146''s figures are marked in place as unreproducible with the population that was actually counted. #146 is archive so its published figures stay, marked, per AGENTS.md. The ''unrepairable'' subsection is narrowed to say the citation was unrecoverable rather than the claim, citing tasks/112. docstat.py --sweep and tasks.py check exit 0 unpiped.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/5
established_by: 'docstat.py --citations is the producer: 49 matches on 43 distinct lines over 54 live documents at dce1172, against a published 20 rows over an unrecorded population. The gap is population, not range. 0 of 43 are true positives today. 10 in-memory pins, 4 red and 6 green, plus 6 mutants; the population is asserted against ARCHIVE_PATHS. It exits 0 as a report, because FINDINGS 146 measured the naive check at a bad false-positive ratio. PR #5, both CI workflows green, 2 review rounds with no actionable comments.'
---

#146 states '20 rows, 2 true positives' over 'the 53 live markdown files' and names no command. Re-run at HEAD under task 112 over git-tracked *.md minus docstat.ARCHIVE_PATHS - 54 live files - the same out-of-range #NN rule gives 51 matches on 43 distinct lines before that repair and 49 on 41 after, split research/ 26, DECISIONS.md 8, .agents/ 7, eval/ 5, AGENTS.md 3. Excluding research/ and .agents/ gives 15, not 20. The gap is population, not range: the published range only widened from #145 to #151, which can only reduce rows. The conclusion #146 draws is unaffected - the false-to-true ratio is still lopsided and the naive check still should not be built - but the figures cannot be re-derived, which is AGENTS.md's count-with-no-producer failure inside the findings log itself. #146 also calls the two eval/RUNS.md #17 citations unrepairable; task 112 repaired the sentences without renumbering anything, by naming the seventh comparability break and FINDINGS #64, so the word that holds is that the CITATION was unrecoverable, not the claim.

## note 2026-08-23

Done on branch `task-118-citation-census` (PR #5). Both halves of the first `done_when`
branch: the producer exists AND #146's figures are marked in place.

## The producer

```
python3 eval/tools/docstat.py --citations          # human
python3 eval/tools/docstat.py --citations --json   # rows, population, corpus_files
```

Every unfenced `#NN` in a LIVE document whose number falls outside the published findings
range. It prints its population (git-tracked `*.md`, minus vendored, minus
`docstat.ARCHIVE_PATHS`), the range, **the producer of that range** (`--findings`, never a
number typed into the file), every row, and the split by area.

**It exits 0 on every row and gates nothing.** That is #146's result, not a softening of it.
Do not wire it into `--sweep`; the naive check was measured at 18 false positives to 2 true
and the ratio has since got worse, not better.

## The numbers, each pinned to a revision because they move

| revision | reading |
|---|---|
| `dce1172` (before this landed) | **49 matches on 43 distinct lines** over 54 live documents, range #19-#152. research/ 22, DECISIONS.md 8, .agents/ 6, eval/ 5, AGENTS.md 2 |
| `24bc9af` (after) | **51 on 45** - the paragraph added to `audit-docs/SKILL.md` quotes `(#999)` and "the #1 risk" and adds two rows of its own. Predicted in writing before it was measured |
| #146 published | 20 rows over an unrecorded "53 live markdown files" |

The gap is the **population**, not the range: the range only widened after publication, and
widening it can only reduce rows. The 53-file set is not recoverable; nothing recorded it.

## Do not re-adjudicate this: 0 true positives of 43 at `dce1172`

All 43 rows were read. Not one is a finding citation:

- **PR numbers** - `PR #1`, `PR #2` in `DECISIONS.md` and `work/SKILL.md` (13 lines)
- **GitHub issue numbers** in `research/` - `#21838`, `#23642`, `bevy#23867`, `gdext #434` etc (14)
- **"the #1 risk" / "the #1 threat" / "Requirement #1"** (5)
- **rule numbers** (`except #6`), **task ids** (`Tasks #14/#15`, `task #5`), **table rows**
  (`the fall in #4` in G4-PLATFORMER.md), **a matrix ordinal** (`matrix #1` in PROTOCOL.md),
  and the quoted `[#999]` plant in `DECISIONS.md`

`eval/RUNS.md`'s two `#17`s - the only true positives #146 ever had - were repaired by
`tasks/112`, which is why the census now finds none.

**The trap that cost the most time here, and the one worth keeping:**
`research/06-non-rust-stacks.md:47` reads literally **"see finding #1"**. It is NOT dangling -
it resolves to `### 1.` under that document's own "THREE FINDINGS THAT DECIDE THIS". So
#146's proposed narrower trigger, *proximity to a findings word*, has a live counterexample
it did not have when it was written. The closed class would have to be a citation SYNTAX the
documents adopt.

## The extractor, and what it still cannot see

`_CITATION_RX = r"#(\d+)(?![0-9A-Za-z_])(?!-(?!#))"`. Both exclusions were chosen on the
live-corpus false-positive count, not by reading:

- `(?![0-9A-Za-z_])` - `#1a2b3c` is a colour and a bare `#(\d+)` reads `#1` out of it
- `(?!-(?!#))` - `#68-the-subjective-layer` is a markdown ANCHOR; `#19-#152` IS a range.
  A hyphen followed by `#` continues a range, anything else begins a slug
- **blind spot, declared**: a six-digit hex written `#123456` is indistinguishable from a
  citation of finding 123456. There is none in the live corpus today

**Three things about those exclusions that a live-corpus measurement will NOT tell you,
so do not re-derive them by running the census:**

| extractor | over the live corpus at `24bc9af` |
|---|---|
| shipped | **51 on 45** |
| bare `#(\d+)` | **51 on 45** - identical |
| anchor rule only (word-char dropped) | **71 on 65** |

1. The shipped pair and the naive regex return the **same totals**. 20 lines tokenise
   differently - 19 in `README.md`, 1 in `DECISIONS.md`, all anchors - and every anchor
   carries an in-range number the range test discards anyway. **The corpus cannot choose
   between the two extractors; the pins have to.**
2. **The two exclusions are one unit and half of them is worse than neither.** Drop only
   the word-char one and the greedy `#(\d+)` backtracks to `#3` inside `#30-a-guard-...`
   once the anchor lookahead rejects `#30` - 20 extra rows. A regex exclusion cannot be
   priced on its own.
3. `--at REV` is deliberately **not** supported: `_live_corpus` would read a revision while
   `read_findings_census` globs the disk, so the two halves would come from different trees
   and the answer would be in range with nothing saying which tree it describes.

Fenced lines are skipped. On the corpus at `dce1172` fence-masking changed nothing (49 either
way), but this module's own docstrings quote planted controls, so it is not free forever.

## The pins and their controls

10 in-memory cases inside `--sweep` and printed by `--selftest`: 4 red (the real pre-repair
`(#17)`, the fabricated `(#999)`, two numbers on one line = 2 matches on 1 row, a range whose
low end names no finding) and 6 green (both range endpoints, a range, an anchor slug, a
colour, a fence, an empty document). Plus the population pinned against `ARCHIVE_PATHS` -
`eval/FINDINGS.md` leaking in would move every figure printed.

**Every pin asserts BOTH counts.** Rows and matches are different quantities and #146's first
correction note conflated them; a pin testing only `bool(rows)` would have been green through
exactly that mistake.

Six mutants each turn the pins red and restore green (script not kept, 20 lines, rebuild from
this list): naive `#(\d+)`; each exclusion removed singly; a trigger requiring a following
space, so it stops matching in parentheses; one that matches nothing; `ARCHIVE_PATHS` emptied
of the findings log.

## Two things about the corpus that will confuse the next reader

- `.claude/skills` is a **symlink** to `.agents/skills`, so the 10 skill files appear in the
  census under `.agents/` and `git ls-files` shows `.claude/skills` as one 120000 entry.
- The scratchpad is shared between concurrent agents. A file written there was overwritten by
  another task mid-session, and a stray `inspect.py` left by a third shadowed the stdlib and
  crashed `argparse`. Use a subdirectory.

## Filed from this session: `tasks/121`

**The work skill's review-wait cannot observe a CLEAN review**, so a clean PR burns the whole
15-minute deadline. It polls `pulls/N/reviews` for a `coderabbitai` review at the head sha, and
when CodeRabbit finds nothing actionable it creates **no review object**: PR 5 returned
`reviews` = 0 and `pulls/5/comments` = 0 while its issue comment read *"No actionable comments
were generated in the recent review"* and named the head sha in full. The skill's pin was taken
on PR 1, which HAD comments and carries 3 review objects - the control shared the assumption it
was controlling for.

Both directions, if you need them again:

```
gh api repos/OWNER/REPO/issues/N/comments \
  --jq "[.[] | select(.user.login==\"coderabbitai[bot]\") | .body] | any(contains(\"$HEAD\"))"
```

`true` for PR 5 at `24bc9aff9233cd481534df260c72a8d1077e2dd8`, `false` for a sha never reviewed.

## Not done, on purpose

- **#146's published figures stay**, marked. It is archive.
- The **"unrepairable" subsection was already narrowed** by an earlier pass, with a box citing
  `tasks/112`. Verified, not rewritten.
- **No `DECISIONS.md` entry.** The reasoning lives in #146 (the measurement) and in
  `audit-docs/SKILL.md` (the procedure); a third copy is where a second source of truth starts.
- **No finding number requested.** Nothing here ran and measured nothing; the new evidence is
  an amendment to #146 and is recorded inside it.
