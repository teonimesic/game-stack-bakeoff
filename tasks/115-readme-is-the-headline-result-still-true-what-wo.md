---
id: 115
title: 'README: is the headline result still true, what would resolve it, and make it readable by someone who knows nothing'
status: done
priority: 1
refs: README.md, eval/FINDINGS.md, eval/findings/, eval/judge/RUBRIC.md, eval/judge/JUDGING.md, DECISIONS.md, tasks/107
done_when: the headline result is either re-established as still true with what re-established it, or restated to what the evidence now supports; the README says what would resolve the question and what is being done about it, or states plainly that nothing is; the three tiers are defined before their first use; every finding and decision reference is a working link verified to resolve; and the whole file is checked against a reader who knows nothing - naming which passages were rewritten and why
established_by: 'README re-established against re-run producers: tier2_census 5 of 10 saturated, tier1_census 7 of 10 single-valued and 0 of 10 both-vary, field_ranks 1.9000/2.2750 pre and 2.1000/1.9250 post, bot_mutants 36 pinned 0 unmet, audit_criteria 16 of 16 false_negative. Headline restated from five routes to four: no stored tier-3 round is blind (83, 131, 137). New section prices every route that would settle it and states plainly that nothing is running against the question. Glossary of 12 terms plus the three tiers now precedes the result. All 59 relative links resolve under the new eval/tools/linkcheck.py, whose selftest pins three link shapes in both directions and which was proved on README.md itself with a planted phantom path, a truncated anchor and a dangling shortcut. instruction_census re-read at 112-155, correcting README and DECISIONS.md. Branch task-115-readme-headline-and-readability.'
---

The operator read the cut-down README on 2026-08-23 and raised four things. THE SUBSTANTIVE ONE: 'THE RESULT: there is no best stack, and the finding is that the question does not resolve - is this still true? What are we doing to answer this question?' The file states a null and never says what would settle it or what is being done about it, so a reader cannot tell whether they are looking at a conclusion or a stalled investigation. THE THREE READABILITY ONES: tiers are referenced repeatedly before anything defines them; the phrasing is too complex throughout and should assume the reader knows nothing about the project; and references are not links - FINDINGS #68 means nothing to someone who cannot click it. Task 107 cut the file from 643 to 281 lines and fixed WHAT is in it; this fixes whether a stranger can read it.

WHAT THIS IS

`README.md` is the front door, cut to 281 lines by `tasks/107`. That task fixed **what is in it**.
This one fixes **whether a stranger can read it**, and whether its headline claim is still one the
evidence supports.

THE FOUR THINGS, IN THE OPERATOR'S WORDS

> *"THE RESULT: there is no best stack, and the finding is that the question does not resolve —
> Is this still true? What are we doing to answer this question? Tiers are mentioned willy nilly,
> but there isn't any tier description prior to them being mentioned. Also the overall text is way
> too complex in phrasing, readme should assume person knows nothing about the project and is
> reading it. Another thing is that references should be linked. E.g.: FINDING #68 means nothing
> without a link a person can click to read on that thing further."*

---

## 1. Is the headline still true, and what would settle it?

**This is the substantive half of the task and it is not a writing exercise.** Do not restate the
null more confidently; go and check it, and say what checked it.

The file currently asserts a null and **never says what would resolve the question or what is
being done about it**, so a reader cannot tell a finished conclusion from a stalled
investigation. Both are honest answers; the file has to pick one.

What to establish, from the artifacts and not from the README:

- **Has anything landed since the claim was written that bears on it?** The findings log has moved
  from #19-#141 to #19-#148 in a day. Several concern the *instrument*: the play-bot's traversal
  ceiling was a key-press length, tier 1 became a gate, tier 2 is saturated on half the corpus, and
  a blinding leak means the subjective rounds are not defensible as blind. Read them and ask
  whether any of them changes what the null can be read as.
- **What would resolve it?** The file already says a tie needs roughly 96 judge rounds per aspect
  and that the deterministic tiers cannot separate anything at any *n*. That is most of an answer
  and it is buried in a licensing bullet rather than stated as the plan.
- **What is actually being done?** Check `tasks/` and `eval/IMPROVEMENTS.md`. If the honest answer
  is *"nothing is currently running against this question"*, **say that**. A front door that
  implies work is in flight when none is is worse than one that admits a pause.

> **Do not manufacture a plan to fill the section.** If the evidence says the question is not
> currently being pursued, the README should say so and say what it would take. That closes this
> half of the task.

## 2. Define the tiers before using them

`overall`, `tier 1`, `tier 2`, `tier 3`, `gate`, `criteria`, `the play-bot`, `aspects` and
`fields` are all used in the result section, which comes **before** the grading section that
explains any of them. A reader meets "tier 2 is the only scored tier" with no idea what a tier is.

Either move the grading explanation above the result, or put two or three plain sentences at the
top. **The three tiers in one sentence each, in words a reader without context can hold**, is
probably enough — the detail belongs where it already is.

## 3. Plain phrasing, for a reader who knows nothing

The prose is dense and assumes the project. Symptoms to fix rather than a style to impose:

- **Jargon used before it is introduced** — the vocabulary in item 2, plus `arm`, `cell`,
  `submission`, `trial`, `field`, `pack`, `starter`, `blinding`, `saturated`, `noise floor`.
  A reader needs *cell*, *trial* and *submission* to parse the result at all.
- **Sentences carrying three clauses and a caveat.** Split them.
- **Precision that reads as hedging.** Keep the caveats that change what a reader may conclude;
  a caveat protecting against a misreading nobody would make is costing attention.

**Do not flatten the meaning to simplify the words.** The comparability warning and "a null is a
noise floor, not proof of equality" are load-bearing and were kept deliberately by `tasks/107`.
They must survive in a form a stranger understands — that is harder than either keeping or cutting
them, and it is the actual work here.

## 4. Every reference becomes a link

**11 bare finding references** in the file today (`grep -c "(#[0-9]" README.md`), plus bare
mentions of `DECISIONS.md`, `eval/RUNS.md`, rubric sections and tool paths.

Findings live as `## NN. <heading>` in `eval/findings/*.md`, and `eval/FINDINGS.md` is the index
that maps a number to a file. GitHub generates a heading anchor by lowercasing, dropping
punctuation and hyphenating spaces — so a finding heading yields a predictable `#nn-...` fragment.

**Verify every link resolves rather than assuming the anchor rule.** `docstat.py --sweep` does
**not** check file paths — that is stated in `AGENTS.md`, and `tasks/107`'s agent wrote a phantom
path (`eval/RUBRIC.md` for `eval/judge/RUBRIC.md`) that passed a green sweep. So:

1. Prove your link-checking method on **one link you know is good and one you know is broken**
   before believing any count over the file (rule 12's corollary).
2. Then check all of them.

If per-finding anchors turn out fragile — a heading gets reworded and the fragment dies silently —
linking to `eval/FINDINGS.md` instead is a defensible choice. **Say which you chose and why.** A
link that resolves to the wrong place is worse than a bare number, because it looks checked.

WHAT NOT TO DO

- **Do not put run information back in.** `tasks/107` removed every run name, per-run cost and
  trial id on the operator's instruction, and that stands. If a claim seems to need its run to be
  credible, cite the producer command or the finding instead.
- **Do not grow the file back.** 281 lines is not a target, but a rewrite that lands at 500 has
  undone the previous task. If clarity genuinely costs lines, spend them on definitions and take
  them out of dense prose.
- **Every number you touch must be re-read from its producer in this session** — `AGENTS.md`
  rule 5, and #144, which is exactly this failure: a figure with a producer cited beside it, that
  nobody ran, wrong by forty instructions.

WHAT EACH OUTCOME MEANS

- **The null holds, and the file now says what would settle it** — the expected result.
- **Something has changed what the null means** — much more interesting. Say what, cite it, and
  restate the headline to what the evidence supports. That is a finding and needs a number
  allocated at merge, not by you.
- **The question is not currently being pursued** — a legitimate answer. State it plainly and say
  what it would take to resume.

## 5. Write the `update-readme` skill — the operator asked for it, and you are the one who can

> *"and maybe this warrants an update-readme skill that properly instructs how readme should be
> done"* — the operator, 2026-08-23.

**Write it at the end, from what the work taught you, not at the start from this ticket.** A skill
assembled by paraphrasing a ticket is a second copy of the ticket. A skill written after doing the
thing records the decisions that were hard.

`.claude/skills/update-readme/SKILL.md`, and **that path is the only one** — `AGENTS.md` names it,
and `docstat.py --sweep` fails a `SKILL.md` anywhere else. Match the seven existing skills' shape:
frontmatter with `name`, `description`, `when_to_use`; an **authoritative file** named at the top
with the standing sentence that *if the skill and the doc disagree, the doc wins and the skill is
the bug*; and steps that are procedures rather than principles.

What it has to encode, because these were all decided against a real alternative:

| rule | the alternative it was chosen over |
|---|---|
| the file is four things — what it is, what was found, how to run it, how it is graded | it had also become a run diary and a register of retired figures, 38% of its length |
| **no information particular to a run**, anywhere, including in caveats | scope inline was thought necessary for falsifiability; a producer or a finding link does the same job without the provenance |
| a quantity gets its **producer command** beside it, and the producer is **run in the session** | #144 — citing a producer is not running it, and a citation reads as freshness |
| define a term before its first use | tiers were used throughout a section that precedes their definition |
| references are **links**, verified to resolve, method proved on a known-good and a known-bad first | `--sweep` does not check paths, and a phantom path passed a green sweep |
| write counts in **digits** | no check can read a cardinal spelled in words; one survived 11 days |
| the comparability warning and *a null is a noise floor, not proof of equality* survive any cut | they are what stop a reader computing a number that must not be computed |
| verify the destination **before** cutting, and move content in its own commit if it lives nowhere else | one block existed only in the README and had no producer |

Also name the gates a README edit must leave green — `docstat.py --sweep`, `--findings`,
`--withdrawn` — and that `--findings` will demand the count and range be updated **in the same
pass**, since it fails otherwise.

**What the skill must NOT become:** a style guide, or a second statement of what is true. It is a
procedure for editing one file. Anything that is a *fact about the project* belongs in the
documents; anything that is an *always-loaded rule* belongs in `AGENTS.md`. If you find yourself
writing either into the skill, that is the signal it goes elsewhere.

## What was measured while doing this, 2026-08-23 — do not re-derive it

**The headline holds, and one route was subtracted from it.** Every producer named in the result
section was re-run against the main checkout's `eval/runs` (a worktree has none — pass
`--runs-root`/`--rounds` an absolute path):

| producer | what it returned |
|---|---|
| `tier2_census.py` | 68 trials carry tier-2 criteria; **5 of 10** groups saturated; 9 selective failures, all from one run |
| `tier1_census.py` | 68 submissions; **7 of 10** groups single-valued; **0 of 10** with both tiers varying; **7** failing trials, 2 of them blocking build failures |
| `field_ranks.py` on `pre` | rank+pool **1.9000 vs 2.2750** |
| `field_ranks.py` on `post` | rank+pool **2.1000 vs 1.9250** |
| the eight readings, computed from those two | max excess of between over within **+22.6%** (`<= 23%` holds); between is **smaller on 4 of 8** |
| `bot_mutants.py` | 36 criteria pinned, 4 variants, 3 session-lock controls, 0 unmet |
| `docstat.py --findings` | 130 bodies, #19-#148, 0 gaps |
| `instruction_census.py` | **112-155**, not the 110-153 the README carried, and not the **73-113** `DECISIONS.md`'s reversal table carried. Both repaired. #144 exactly |
| `audit_criteria.py` `ADJUDICATED` | **16** entries, every one `false_negative` |

**The subtraction, and it is the only substantive change to the headline.** The file claimed
*"five instruments, five different routes, the same null"*. Tier 3 is no longer usable as one of
them: `#83` (pack files named the submissions), `#131` (the anonymiser's vocabulary was a list of
spellings; 22 leaking Rust packs, and 9 of 9 architecture rounds with a file-open log opened one)
and `#137` (2,083 arm-naming tokens in all 84 packs, the densest written by the packer itself)
together mean **no stored subjective round is defensible as blind**, and `eval/IMPROVEMENTS.md`
iterations 14-15 licence new rounds while repairing none. The README now says four routes, not
five. **This is a re-reading of published findings, not a new measurement — it needs no finding
number.**

`#133` and `#139` were checked and do **not** move the null: both removed *false differences*
(a minimised window freezing one arm's frames; a scalar that reordered whenever the bot improved).

**"What is being done" is: nothing, and that is the honest answer.** `tasks.py list` holds no item
that would produce a new stack measurement, and `DECISIONS.md`'s harder-task section records that
the free pre-test ran and came out *against* buying the matrix. The README says so plainly rather
than implying work is in flight.

## The link decision, and why anchors were taken despite being fragile

Shipped **reference-style** links: `[#68]` in the prose, one definition block at the foot of the
file. The two alternatives and why they lost are in `DECISIONS.md`, section *"A finding cited in a
live document is a reference-style link"*. The short version: a bare number is unclickable, an
inline anchor is a 150-character URL in a file whose defect was readability, and
`eval/FINDINGS.md` has no anchors to aim at because its index is a table.

**`eval/tools/linkcheck.py` is new and is what makes the anchor safe.** It resolves path and
fragment, derives anchors from the target's own headings rather than assuming GitHub's rule, and
masks inline code spans — without that it fired on `DECISIONS.md`'s own explanation of the
convention, which is the fail-open-attention direction. `--selftest` pins three link shapes in
both directions plus the anchor rule. Proved on `README.md` itself before any count over it was
believed: a phantom `eval/RUBRIC.md`, a truncated anchor and a dangling `[#999]` each went red,
then were reverted.

## Two gates that will bite the next README edit

- **`docstat.py --findings` needs the literal `Findings #A-#B`.** Rewording the sentence around
  the range makes it report that the README states no range at all. Cost one iteration here.
- **`docstat.py --sweep` gates on `renumber_triage.json`'s pinned substrings.** Dropping
  `(#100, #103)` from a code-block comment turned it red. Restore the text; do not delete the pin.

Both are now in `.claude/skills/update-readme/SKILL.md`, section 9.

## Pre-existing reds, established rather than absorbed

- `docstat.py --sweep` fails on **9** `.agents/skills/*/SKILL.md`. They are tracked at this
  branch's HEAD and unmodified by this work (`git status` shows only the files below). A merge
  resurrected the mirror deleted at `bec16e3`. **Task 114 owns it.**
- `tasks.py check` fails on task 109's status `in_review`, which is not in the allowed set.
  Another agent's ticket.
- Filed **task 116**: `DECISIONS.md`'s Open section says the platformer is designed and not
  launched, and carries a duplicated paragraph fragment.

## What changed

`README.md` (rewritten, 284 -> 365 lines, of which 19 are the link-definition block),
`eval/tools/linkcheck.py` (new), `.claude/skills/update-readme/SKILL.md` (new),
`AGENTS.md` (one skill-table row), `DECISIONS.md` (the link decision; the stale instruction
count), `.claude/skills/audit-docs/SKILL.md` (names `linkcheck.py` and what `--sweep` does not
cover).
