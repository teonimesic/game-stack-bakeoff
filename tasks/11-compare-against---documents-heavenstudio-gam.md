---
id: 11
status: in_flight
priority: 5
title: Compare this project against the game-research-gpt attempt and import what is better
refs: ~/Documents/heavenstudio/game-research-gpt
done_when: a table of candidate imports exists — each with the axis, what it replaces here, and a verdict of ADOPT with its verification run and measured result, REJECT with why, or OPEN with what would settle it and why it was not run (cost, regime boundary, or no stored evidence to test against) — plus an explicit list of things we do that they do not
---

This project measures how well coding agents build whole games in four stacks
(Rust/Bevy, TypeScript/three.js, Unity, Godot). Submissions are graded in three tiers:
tier 1 programmatic checks, tier 2 a scripted play-bot, tier 3 six LLM-judged 'aspects'
(architecture, idiomatic, fun, fun_frames, ux, audio) that score eight anonymised
submissions side by side as a 'field'. Tier 3 currently has weight 0.00.

WHAT IS THERE: `~/Documents/heavenstudio/game-research-gpt` is a second, independent attack on a
similar problem — about 30G, with `docs/`, `evaluation/`, `research/`, `scripts/` and a SINGLE
`template/`. Its docs mention a frozen Godot study, so it may be single-stack.

GOAL: find approaches, structures and results there that are better than ours, import them, and
PROVE each import improved something measurable here.

WRITE A PLAN BEFORE DOING ANY OF IT. This is large. First deliverable is a written plan naming
what will be compared, in what order, what "better" means per axis, and how each candidate import
will be verified.

ESTABLISH WHICH QUESTION THEIR DESIGN SERVES BEFORE JUDGING THEIR ANSWERS. If it is single-stack,
it optimises "how good can one template get"; we optimise "which of four stacks differs". A
structure can be better for theirs and wrong for ours.

AXES, roughly by expected value:
  1. Evaluator and judge design — criteria, blinding, controls, how they decide a criterion is
     trustworthy. This is where we have spent the most and found the most defects (#25-#72).
  2. Template structure and the agent-facing AGENTS.md — what a building agent is told, and how
     verification is exposed to it.
  3. How results are reported under uncertainty — do they publish orderings we would refuse to?
  4. Harness mechanics: work roots, artifact durability, run ledgers, cost accounting.

VERIFICATION IS THE HARD PART AND IS NOT OPTIONAL. The method differs by axis:
  - judge/evaluator changes: re-grade STORED submissions offline, before versus after. Free,
    repeatable, 60+ stored submissions across 4 games. Most imports should be testable this way.
  - criterion changes: must pass both halves of `judge/bot_mutants.py` — a mutant that makes it go
    red AND a variant that keeps it green. Without both it is installed, not verified.
  - template changes: need a fresh matrix (~$420) and are a regime boundary. Prove the mechanism
    offline first.
  - doc/process changes: name which finding in `eval/FINDINGS.md` the change would have prevented.

TRAPS, each already paid for here:
  - Do not import a NUMBER across regimes. Their costs and scores come from a different harness,
    model, task set and machine.
  - Do not adopt a structure because it looks cleaner. Name what it would have prevented, or leave it.
  - "They do X, we do Y" is a description, not a finding. Every entry needs a verdict: adopt (with
    its verification), reject (with why), or open (with what would settle it).
  - Run the comparison BOTH WAYS. Assuming they are ahead is how you import a regression.

PROGRESS — axes 1, 2 and 3 are DONE. Axis 4 is all that remains.

Everything is written up in `eval/IMPROVEMENTS.md`, iteration 12: one section per axis, each with
its candidate table, its verdicts, its both-ways list and what was adopted. **Read that file
first; do not re-read `game-research-gpt` from scratch.**

Axis 3 (2026-08-23) produced `eval/judge/field_ranks.py`, FINDINGS #112, and tasks 54 and 55. It
also **corrected axis 1**: their `-v1`/`-v2`/`-v3` are not replicates that ran. The dispositions
say unfinished, invalidated and unadmitted, so no confirmation run of theirs ever produced a
comparative result. A forward pointer sits at the end of the axis-1 section.

AXIS 4 — harness mechanics: work roots, artifact durability, run ledgers, cost accounting.

  Lead: task 28. Sanctioned reading: `evaluation/reports/` and the per-study `README.md`
  dispositions ONLY — never the raw artifacts under `evaluation/runs/`, which are 30G.

  One thread axis 3 opened and deliberately left, because it is cost accounting: the stored judge
  rounds' own `cost_usd` fields sum to $33.63 and $31.66 for the two `wg-tetris-judge-2026-08-17`
  fields, while their `SEQUENTIAL.json` records `measured_cost_usd` 25.55 and 21.05, and
  `README.md` quotes 21.05 and $46.79. Three accountings of one spend, and they disagree. Start
  there — it is a real defect with stored evidence, and it is exactly axis 4's subject.
