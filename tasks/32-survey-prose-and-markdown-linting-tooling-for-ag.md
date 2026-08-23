---
established_by: research/11-doc-linting-for-agents.md committed on task-32-doc-tooling-survey. Eleven tools run against real files here on 2026-08-23: markdownlint-cli2 9697 alerts, vale+Microsoft+Google 4234 on six docs, write-good 137, alex 35, proselint 18, typos 161, cspell 17, agnix 279, remark-lint 0, textlint refuses without config, claude plugin validate --strict 5 errors. Two defects total, both structural: five SKILL.md frontmatter blocks are invalid YAML (positive control: quoting them makes all seven validate clean), and AGENTS.md rules 10-16 detach five paragraphs under CommonMark. Zero prose defects. Recommendation is to adopt no prose linter, with the false-positive counts recorded per tool. Follow-ups filed as tasks 35, 36, 37, 38, 39.
id: 32
title: Survey prose and markdown linting tooling for agent-read documentation
status: done
priority: 3
refs: research/AGENTS.md, CLEANUP-LOG.md, eval/FINDINGS.md #59, .claude/skills/prune/SKILL.md
done_when: research/11-doc-linting-for-agents.md exists, naming each tool the survey examined with its maintenance status and its measured output when run against this repository's real markdown, and stating explicitly which claims are demonstrated and which are guessed. If no tool is worth adopting, the file records that as the result with the evidence behind it, and that closes the task too
---

## What is this thing?

The documentation in this repository — `AGENTS.md`, the skills under `.claude/skills/`, the
per-stack starter docs, `eval/FINDINGS.md`, the `research/` briefs — is read almost entirely by
**agents**, not by people. It is context loaded into a model. Measured 2026-08-23: 108 markdown
files outside `eval/runs/`, ~198,600 words. Several sections are long enough that nothing reads
them to the end.

A **prose linter** is a tool that reads English text and reports style defects — passive voice,
weasel words, reading grade, terminology inconsistency. A **markdown linter** reports structural
defects — heading levels skipped, inconsistent list markers, broken links. Neither category was
built for a model reader.

## What is wrong, and how do we know?

Nothing lints this repository's documentation. Measured 2026-08-23: no `vale`, `markdownlint`,
`proselint`, `write-good`, `textlint`, `alex`, `remark-lint` on the machine or in any config
file, and no Python linter either.

That is not by itself a defect. The defect the project already knows about is different: the
existing sweep (`eval/tools/docstat.py`) asks whether names in the docs **resolve** — it caught
five judges named in `eval/judge/RUBRIC.md` that do not exist (`eval/FINDINGS.md` #38) — and
`eval/tools/prune_scan.py` asks whether text **earns its space**. Neither asks whether a
document is *usable as instruction*, and the rule audit in `AGENTS.md` records the shape of
failure that matters here: rules that were read, understood, and still failed to fire because
their trigger was written as an enumeration rather than a property.

## Why does it matter?

If a tool exists that catches the class of defect that makes a rule fail to fire, it is worth
more than any of the grading work, because every future session pays for those defects.

If no such tool exists — and that is the likelier outcome — then knowing so plainly is worth
having written down, because otherwise it gets re-investigated. The trap is the same one the
project exists to distrust: **a prose linter that runs and produces a tidy score is a mechanism
that runs, reports success, and measures nothing.** Readability scores are the clearest case:
trivially gameable, validated on human comprehension, with nothing establishing that they
predict whether an agent follows a rule. That is the proxy-metric failure recorded as
`eval/FINDINGS.md` #59.

## What should be done?

Write `research/11-doc-linting-for-agents.md` to the standard in `research/AGENTS.md` — date
every claim, name the version, source every claim, label unverified claims as unverified.

Cover four things:

1. **The landscape.** `vale`, `markdownlint`/`markdownlint-cli2`, `textlint`, `proselint`,
   `write-good`, `alex`, `remark-lint` and the unified/remark ecosystem, plus anything newer.
   Maintenance status with a date. What each catches. What it costs to run.
2. **The agent-specific question**, which is where the real answer lives. `AGENTS.md`
   conventions, `llms.txt`, context-engineering practice, doc-linting aimed at retrieval or
   agent consumption. Web and GitHub, with activity dates.
3. **Claude Code skills, plugins and marketplace entries** for documentation quality, doc
   auditing or context compression. Whether any is worth installing.
4. **A recommendation for this repository**, with cost and effort.

**The measurement that decides it, and it is not optional:** for each candidate, run it against
real files here and report what it actually fired on. `uvx`, `npx`, `pipx` and `brew` are
available; prefer one-shot runs and install nothing permanently without saying so. A tool that
fires on a real document here and names something a reader agrees is a defect is worth more
than a popular tool that scores everything clean.

## Outcomes that count as success

| result | what it means |
|---|---|
| a tool fires on real files and the hits are defects | adopt it; file a follow-up task for the config |
| a tool fires and the hits are noise | record the false-positive rate measured here, and reject it |
| nothing fires, or everything that fires is a proxy for human readability | **that is the answer.** Write it down with the evidence and stop |

## What NOT to conclude

- **Do not conclude a tool is useful because it produced output.** Volume of warnings is not
  evidence; a reader agreeing a specific hit is a defect is.
- **Do not conclude a readability score means anything here** without something that connects
  it to agent behaviour. Nothing in the literature currently does.
- **Do not manufacture a recommendation to have one.** "No established practice exists and the
  available tools optimise for a different reader" is a complete answer.

## Constraints

- **Do not rewrite any documentation from this task.** File follow-up tasks instead; a doc
  rewrite bundled into a research pass cannot be reviewed or reverted separately.
- **Never propose touching `eval/findings/`, `eval/FINDINGS.md`, or the regime boundaries in
  `eval/RUNS.md`.** Retractions and comparability boundaries are what make every other number
  safe to read — see `.claude/skills/prune/SKILL.md`.
- **`template*/` and `eval/starters/*/` are the product.** Do not edit them. Reading them to
  measure a linter against them is fine.
