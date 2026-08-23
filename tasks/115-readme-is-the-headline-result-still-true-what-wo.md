---
id: 115
title: 'README: is the headline result still true, what would resolve it, and make it readable by someone who knows nothing'
status: open
priority: 1
refs: README.md, eval/FINDINGS.md, eval/findings/, eval/judge/RUBRIC.md, eval/judge/JUDGING.md, DECISIONS.md, tasks/107
done_when: the headline result is either re-established as still true with what re-established it, or restated to what the evidence now supports; the README says what would resolve the question and what is being done about it, or states plainly that nothing is; the three tiers are defined before their first use; every finding and decision reference is a working link verified to resolve; and the whole file is checked against a reader who knows nothing - naming which passages were rewritten and why
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
