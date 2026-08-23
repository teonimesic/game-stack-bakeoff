---
name: update-readme
description: "Edit README.md, the project's front door: what belongs in it, what must never enter it, how a number gets in, how a reference gets in, and the gates the edit must leave green."
when_to_use: "You are about to change README.md - the result moved, a weight or tier changed, a count went stale, a reference is bare, or someone said the file is hard to read. Trigger phrases: update the readme, the readme is stale, the readme is unreadable, is the headline still true, link the references."
---

# Editing the front door

**Authoritative files: `AGENTS.md` (what the README is, and how documents are kept current)
and `README.md` itself (what is true now). If this skill disagrees with either, they win and
this skill is the bug.**

`README.md` is the only document read by someone who has read nothing else. Everything below
exists because the alternative was tried here and cost something.

## 1. The file is four things

What the project is · what it has found · how to run it · how a submission is graded.

Anything else has a home and belongs there:

| it is | it goes to |
|---|---|
| what a run cost, what went wrong in it, what it may be compared with | `eval/RUNS.md` |
| a defect and what it taught | `eval/FINDINGS.md` |
| a decision and its reasoning | `DECISIONS.md` |
| an always-loaded rule | `AGENTS.md` |
| a procedure | `.claude/skills/<name>/SKILL.md` |

The file had become a run diary and a register of retired figures, and that was 38% of its
length. **When a section is neither of the four, move it — do not shorten it in place.**

## 2. No information particular to a run. Anywhere, including inside a caveat

No run names, no trial ids, no per-run costs, no per-run trial counts. The argument for keeping
scope inline was falsifiability — a claim with no scope cannot be checked. **A producer command
or a finding link does that job without the provenance**, so cite one of those instead.

This bites hardest where a price is the point. *"A harder game would cost $421"* is a per-run
cost; *"the price is in `DECISIONS.md`, section X"* is not, and the reader who needs the number
is one click away.

## 3. Every quantity carries its producer, and you run the producer in this session

Writing the command beside a number is **not** the discipline — running it is. A figure that
cited its producer and had gone stale by forty instructions is #144, and the citation is exactly
what made it read as fresh.

```
python3 eval/tools/census.py                  # the stored tree
python3 eval/tools/docstat.py --findings      # the findings log: count AND range
python3 eval/judge/judge_ledger.py --tree eval/runs/   # judge spend
python3 eval/tools/instruction_census.py      # the always-loaded instruction set
python3 eval/judge/tier1_census.py --runs-root <main checkout>/eval/runs
python3 eval/judge/tier2_census.py --runs-root <main checkout>/eval/runs
python3 eval/judge/field_ranks.py --rounds <a stored round directory>
python3 eval/judge/bot_mutants.py             # criteria pinned, variants, controls
```

Three things worth knowing before you reach for these:

- **You are probably in a worktree, and `eval/runs/` is gitignored** — it does not exist there.
  Pass `--runs-root` or `--rounds` an absolute path into the main checkout.
- **If a quantity has no producer, that is the defect.** Write one, or do not publish the number.
  If you keep it anyway because it is genuinely a hand adjudication, *say so in the sentence* —
  "this is a reading of the record, not a measurement" — so nobody re-quotes it as output.
- **Write counts in digits.** No check can read a cardinal spelled in words; one survived
  eleven days that way, and `docstat.py --findings` could not see it.

## 4. Define a term before its first use

The result section is the first thing a stranger reads and it is the densest. `tier`, `gate`,
`cell`, `trial`, `submission`, `field`, `criterion`, `saturated`, `noise floor` and `blinding`
all appeared in it while their definitions sat further down the file.

**A short glossary before the result is cheaper than moving the grading section**, and one line
per term is enough — the detail stays where it already is. Budget the lines out of dense prose,
not out of caveats.

## 5. References are links, and you verify them with the method proved first

`docstat.py --sweep` **does not check file paths.** A phantom `eval/RUBRIC.md` (for
`eval/judge/RUBRIC.md`) passed a green sweep. So:

```
python3 eval/tools/linkcheck.py --selftest   # both directions, on planted good and bad links
python3 eval/tools/linkcheck.py              # the live documents; exit 1 if anything dangles
```

Run `--selftest` **before** believing any run over the real file — that is rule 12's corollary,
prove the extraction on a case whose answer you can state in advance.

**Findings are linked reference-style.** Write `[#128]` in the prose and put the target in one
block at the bottom of the file:

```
[#128]: eval/findings/certifies-nothing.md#128-tier-2-saturates-because-...
```

Why this shape and not the two alternatives:

| shape | why not |
|---|---|
| bare `(#128)` | means nothing to a reader who cannot click it — the operator's own objection |
| inline `[#128](very-long-anchor)` | a 150-character URL in every sentence, in a file whose problem was readability |
| linking to `eval/FINDINGS.md` with no fragment | always resolves and never lands on the finding; the index is a table, and GitHub gives table rows no anchors |

The anchor is GitHub's heading rule and it dies **silently** when a heading is reworded, which is
worse than a bare number because it looks checked. `linkcheck.py` is what makes it safe: it
derives the anchors from the target file's own headings, so a reworded heading turns the gate
red instead of turning the link into a lie.

## 6. Two passages survive every cut

- **the comparability warning** — that results from different runs mostly may not be pooled, and
  that `eval/RUNS.md` says which may;
- **a null is a noise floor, not proof of equality.**

They are what stop a reader computing a number that must not be computed. Simplifying the words
is fine and is usually an improvement; losing the meaning is not. **That is harder than either
keeping the sentence verbatim or cutting it, and it is the actual work.**

## 7. If you are touching the result, go and check it — do not restate it more confidently

A stated null with no statement of what would settle it reads identically to a stalled
investigation. The file has to pick one, and both are honest.

1. **Re-run the producers.** Not "has anything obviously changed" — run them.
2. **Read the findings that landed since.** Ask specifically whether any of them is about the
   *instrument* rather than the subjects. An instrument repair can subtract a whole route from a
   result without changing any number in it.
3. **Price every route that would settle it**, and link the pricing rather than restating it.
4. **Say what is actually being done.** Read the queue (`python3 eval/tools/tasks.py list`) and
   `eval/IMPROVEMENTS.md`. If nothing is running against the question, **write that**. Do not
   manufacture a plan to fill the section — a front door implying work is in flight when none is
   is worse than one that admits a pause.

## 8. Before cutting, verify the destination — and move in its own commit

Confirm the content exists where you are sending it. One block existed **only** in the README
and had no producer anywhere; "it lives in `eval/RUNS.md`" was assumed, not checked. If it lives
nowhere else, move it first, in its own commit, so the move is reviewable separately from the cut.

## 9. Gates the edit must leave green — unpiped

```
python3 eval/tools/docstat.py --sweep       # names that do not exist; structure
python3 eval/tools/docstat.py --findings    # count AND range, in the same pass
python3 eval/tools/docstat.py --withdrawn   # no live document states a retired figure
python3 eval/tools/linkcheck.py             # every relative link, path and fragment
```

Two of these fail in ways that are easy to misread:

- **`--findings` needs the literal string `Findings #A-#B`.** Rephrasing the sentence around the
  range makes the check report that the README states no range at all. It demands count and range
  updated in the same pass, and it is right to.
- **`--sweep` checks that quoted lines still exist.** `renumber_triage.json` pins exact
  substrings of this file; deleting a `(#100, #103)` from a code comment turns it red. Restore the
  text or re-record the row — do not delete the pin.

A pre-existing red is not yours to fix silently. Establish it — `git status`, or the sweep on an
unmodified tree — and report it rather than absorbing it into your change.
