---
id: 53
title: Long doc sections doubled in one day - decide what is earned and what is accumulation
status: open
priority: 3
refs: eval/tools/prune_scan.py --only fat, CLEANUP-LOG.md, .claude/skills/prune/SKILL.md
done_when: each section over 6000 chars is either kept with a stated reason, split, or compressed with the meaning preserved; and the total is re-measured and recorded in CLEANUP-LOG.md, or the growth is judged earned and that judgement is recorded with the per-section reasoning
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
