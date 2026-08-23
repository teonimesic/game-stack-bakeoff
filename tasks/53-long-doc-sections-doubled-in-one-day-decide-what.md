---
id: 53
title: Long doc sections doubled in one day - decide what is earned and what is accumulation
status: done
priority: 3
refs: eval/tools/prune_scan.py --only fat, CLEANUP-LOG.md, .claude/skills/prune/SKILL.md
done_when: each section over 6000 chars is either kept with a stated reason, split, or compressed with the meaning preserved; and the total is re-measured and recorded in CLEANUP-LOG.md, or the growth is judged earned and that judgement is recorded with the per-section reasoning
established_by: 'Read all 14 sections prune_scan.py --only fat reported. Measured 28,852 tokens over 14 before, 27,212 over 13 after the edits, 28,890 over 14 including this pass log entry - the tool was left unchanged so both numbers came from one instrument. 2 splits, 11 keeps, 1 protected. SPLIT: the turn-ceiling worked example (232 of 250 turns) sat under AGENTS.md rule 15, mutants and variants, when it is the evidence for rule 8s qualifier about a binding ceiling - moved, one clause reworded, no text cut; and audit-docs SKILL.md section 1 held four things under one heading, now three subheadings, off the list entirely at 1,639 tokens, plus the authoritative-file line it was the only skill of seven to lack. KEEP with reasons recorded per section in CLEANUP-LOG.md: the five tasks/ files are 50 percent established_by by measurement (17,341 of 34,731 chars, task 52 is 90 percent) and none loads unless a reader opens that ticket, so (preamble) is the wrong unit; this logs own 2026-08-23 entry is the cleared-list that stops the next pass re-reading 42 tasks; README THE RESULT and In flight, eval/IMPROVEMENTS Verdicts and the DECISIONS templates-at-best section are numbers with their populations and caveats attached, and were also held by other agents. FILED task 60 - cat_fat accepts include_archive and never uses it, so eval/FINDINGS.md Every finding, 3,994 tokens and 14 percent of the total, heads a list the prune skill forbids touching; not fixed here because changing the instrument between the before and after reading is the multi-variable mistake. FILED task 61 - JUDGING.md Validation gates, six gates each with its own evidence under one unaddressable heading, left unedited because four agents were in eval/judge. Cleared: eval/PROTOCOL.md, eval/judge/RUBRIC.md, research/ and the other six skills have no section over 6,000 chars, so the doubling is concentrated in four files rather than general bloat. docstat.py --sweep exit 0 unpiped, clean over 131 docs, before and after; its --renumbered half found 3 citations of #117 that now names a different finding, 2 repaired in AGENTS.md and audit-docs, the third in DECISIONS.md left for its owner. Commit 953b7fc on task-53-fat-sections.'
---

WHAT THIS IS

`python3 eval/tools/prune_scan.py --only fat` reports document **sections** longer than 6,000
characters — not files, because a large file of short sections is fine and what defeats a reader
is one section that will not end. These are the summarisation candidates.

WHAT WAS MEASURED

On 2026-08-23 the same command was run twice, about twelve hours apart:

    morning   6 sections   ~12,053 tokens if all loaded
    evening  (more)        ~24,416 tokens if all loaded

**The cost of the repository's longest sections doubled in a single working day.**

WHY IT MATTERS, AND WHY IT MIGHT NOT

Everything here is loaded into an agent's context, and `AGENTS.md` states the principle: *a
document nobody finishes reading protects nothing.*

But **growth is not automatically waste, and this task must not assume it is.** That day produced
roughly twenty genuine findings, three comparability breaks and four new gates. Much of the new
text is evidence someone paid for. The question is not "is it bigger" — it is **"would a fresh
agent reading this section be better off than reading half of it?"**

WHAT SHOULD BE DONE

1. Run `python3 eval/tools/prune_scan.py --only fat --top 40` and take the list.
2. For each section, one of three outcomes, each recorded:
   - **Keep** — it is load-bearing, and say what would be lost. This is a legitimate and
     probably common answer.
   - **Split** — it is several things under one heading, so the reader cannot skip what they do
     not need.
   - **Compress** — it says one thing at length. Preserve the *evidence pointer* and the
     *trigger*; those are what make a rule fire. A rule stripped to its imperative is one the
     next reader talks themselves out of.
3. Re-measure and record both numbers in `CLEANUP-LOG.md`.

WHAT NOT TO TOUCH

`eval/findings/`, `eval/FINDINGS.md`, and the regime boundaries in `eval/RUNS.md`. A findings log
is an archive; `FINDINGS.md`'s "Every finding" index is long *because* it indexes 90-odd findings,
which is the section doing its job. The `prune` skill explains why these are excluded and the
scanner skips them by default.

WHAT NOT TO CONCLUDE

**Do not treat the token total as the target.** Compressing text until a number falls is how a
document loses the specific incident that makes a rule credible — and this project has already
recorded that rules stated without their evidence get re-derived and re-broken. If the honest
answer is *"22,000 of these tokens are earned and here is why, section by section"*, that closes
this task.

## Dispatch knowledge, 2026-08-23 — written back from a launch message

**What compression must preserve, and this is the whole risk:** the *trigger* and the *evidence
pointer*. A rule stripped to its imperative is one the next reader talks themselves out of — this
project has recorded rules failing precisely because their trigger was rewritten shorter. If a
section cannot be compressed without losing the incident that makes it credible, **keep** is the
right answer and a real one.

**Files under active edit by peers when this was dispatched** — `eval/judge/`,
`eval/tools/docstat.py`, `README.md`, `DECISIONS.md`, `eval/IMPROVEMENTS.md`, `eval/RUNS.md`. A
conflict in a document that states what is true now costs more than a few thousand tokens are
worth. Report and file rather than edit those; work in `AGENTS.md`, the skills,
`eval/PROTOCOL.md`, `JUDGING.md`, `RUBRIC.md`, `research/`, `CLEANUP-LOG.md` and `tasks/`.
