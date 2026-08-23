---
id: 125
title: Four claims from today were left unverified because the case that would test them did not arise
status: done
priority: 3
refs: 'eval/findings/certifies-nothing.md #152 #153 #156, eval/tools/coderabbit_config.py, eval/tools/docstat.py duplicate-fragment and orphaned-tail, .coderabbit.yaml'
done_when: each of the four is either verified with the measurement stated, or closed with why it still cannot be tested and what would change that; the SkillSpector one requires a real pull request that edits a SKILL.md, and reporting zero attachments without one does not close it
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/11
established_by: 'Three of four claims settled; the fourth needs a real skill diff. The one that produced a tool: a misspelled key in .coderabbit.yaml''s tools block is accepted and silently ignored, confirmed against the published schema - (root).additionalProperties is false but reviews.tools does not set it, so the closure is one level deep. coderabbit_config.py --schema reddens undeclared keys, pinned green on the real file and red on a misspelled tool name; deliberately not in CI because it needs the network. PR #11, both workflows green.'
---

Each was stated honestly as unestablished by the agent that shipped it, and each is now cheaply testable because the blocking condition has passed. Left together because they are one question - a check whose triggering case has not occurred is indistinguishable from a check that cannot fire - and separately none is worth a dispatch. (1) FINDINGS 153: SkillSpector was disabled and the pull request that disabled it touched no SKILL.md, so its zero attachments are zero for the wrong reason; any pull request editing a skill settles it. (2) FINDINGS 153: a misspelled tool key in .coderabbit.yaml is accepted and silently ignored, because that schema does not forbid unknown properties - it was documented rather than gated because confirming it needed the network. (3) FINDINGS 152: the stranded-tail gate has a corpus census of 0, so it is protecting silently and its only known instance is historical. (4) FINDINGS 156: the 12-word window was chosen against a 183-document corpus with two words of margin over the nearest antithesis, and the corpus grows daily.

## note 2026-08-23

## What was measured, and the one that could not be

Three of the four are verified with a measurement; the fourth is closed the other way and the
ticket's own closing condition turned out to be insufficient.

### (3) The stranded-tail gate's census of 0 — verified, and given a denominator

**0 at HEAD is what a census of HEAD MUST return for a defect that was repaired**, so it could
never distinguish a gate that is protecting silently from one that cannot fire. The population
that can is every *version* of every reference document, and there was no producer for it.
There is now: `python3 eval/tools/integrity_census.py`.

| | incidents | versions carrying it | corpus at HEAD |
|---|---|---|---|
| stranded tail | 1 | 34 | 0 |
| duplicate fragment | 1 | 55 | 0 |

over 1,551 distinct (version, path) pairs, 219 paths, all 451 commits reachable from `--all`.
**The denominator moves with every commit; the incident count has not moved.** Two runs 20
minutes apart read 1,543 and 1,551 versions and the same 1 and 1. Re-derive rather than quoting.

**A version is not an incident and a span is not either.** An unrepaired defect is re-counted in
every version of its file, and one rewrite is seen as several *overlapping* windows of itself —
the fragment defect is 4 spans for one bullet edited once. Spans are therefore grouped on the set
of versions they appear in, which is what overlapping views of one rewrite share, and the
ungrouped span count is printed beside it because that grouping is a heuristic.

### (4) The 12-word window's margin — verified, and the published count is the wrong quantity

`integrity_census.py --windows`, over 188 documents against the 183 the window was chosen on:

| window | corpus hits | distinct phrases | the real defect |
|---|---|---|---|
| 8 | 11 | 5 | 11 |
| 10 | 3 | **1** | 7 |
| 11 | 0 | 0 | 5 |
| **12** | **0** | **0** | **4** |
| 16 | 0 | 0 | 0 |

**The margin has not eroded** — 11 and 12 still measure 0. But the hit count at 10 went 1 → 3,
and **all three are the same antithesis**: `DECISIONS.md`'s headroom blockquote, quoted twice in
that file and once in `tasks/119` *because it was named as the false positive that set the
boundary*. The corpus acquired copies of the hit already counted, not a new kind of hit.

> **A trigger that fires on a passage correct documents QUOTE grows its own false-positive count
> by being documented.** Reading that growth as evidence of an open class would argue for
> widening a window that has not moved. The quantity that decides a retune is the
> **distinct-phrase** column.

### (2) The misspelled tool key — confirmed against the schema, and now gated

`#153` documented rather than gated it because confirming needed the network. Read from the
published schema:

    (root).additionalProperties          False   <- a misspelled TOP-LEVEL key is rejected
    reviews.additionalProperties       absent
    reviews.tools.additionalProperties absent    <- a misspelled TOOL key is accepted

Draft 2020-12 permits unknown properties where the keyword is absent, so **the closure is exactly
one level deep**: `reviws:` fails, `reviews.tools.skillspecter:` passes and is silently ignored.
That is sharper than #153 stated — it named the tools object and the boundary is one level up.

`coderabbit_config.py --schema` is the gate, `--schema --control` pins it green on the shipped
config and red on `skillspector` misspelled. Not in CI (network); recorded as a deliberate
exclusion in `.github/workflows/README.md` rather than left silently absent.

### (1) SkillSpector — NOT closed, and this ticket's `done_when` is insufficient

The ticket asked for *a real pull request that edits a SKILL.md*. **PR #11 is one, and it still
does not settle it.** `#153`'s own data says why: the `[AS3]` trigger is a **property** — one
skill referencing another skill's file — and **3 of the 5 comments on a skill that names no other
skill carried no attachment while the tool was still enabled**.
`.agents/skills/audit-docs/SKILL.md` names no other skill, so zero attachments here is zero for
the same wrong reason the finding already recorded.

**What would settle it:** a diff that draws a review comment onto one of the three skills that
carry the cross-references `AGENTS.md` requires — `dispatch/SKILL.md` (lines 10-11, naming
`tasks` and `work`), `tasks/SKILL.md` (lines 52-53 and 196), or `update-readme/SKILL.md` (line
28). An attachment there with SkillSpector disabled means the switch did not work; none means it
did. **Do not accept "the diff touched a skill" as the condition again** — that is this ticket's
own version of the enumeration failure #152 records, a closing condition specified in the
vocabulary of the incident rather than as the property.

### The defect this work put in its own instrument, and the control that caught it

The first enumeration of "every version of every reference document" used
`git log --all --name-only`. **Git omits a merge commit's file list by default**, so
`.agents/skills/update-readme/SKILL.md` — tracked, introduced by merge `6129034` — appeared in no
revision at all. **216 paths and 1,196 versions against a true 218 and 1,543 on the same tree**,
with no error reported: a base rate understated by 22% by an enumeration that named no failure.

`enumeration_control` now asserts that every reference document tracked at HEAD appears in the
historical enumeration — HEAD's file list being the one membership statable in advance. Pinned
red three ways: `log_based_enumeration` (the defect that happened, names the missing skill),
`no_skill_files` (10 missing), `empty_enumeration` (188 missing).

> **Rule 12's address can be the POPULATION, not only the path.** Every guard in
> `integrity_census.py` was about reading the right blobs; the thing that was wrong was which
> blobs existed. `--diff-merges=first-parent` also recovers all 218; the tool walks trees instead
> because the tree *is* the population and there is nothing left to be subtly wrong about.

### Incidental corrections, and what was deliberately not touched

- `.github/workflows/README.md` and `gates.yml` said the lint backlog "stands at 64"; measured
  **67** (`python3 eval/tools/lint.py --counts`). The command is now beside the number.
- `audit-docs/SKILL.md` said `fragment_control.py` prints the count that decides the window. It
  prints only the count at the *shipped* window (0), which is not that count.
- `DECISIONS.md` carried 180 and 183 as the corpus size for two measurements taken the same day.
- **`eval/findings/` and `eval/FINDINGS.md` untouched.** #152, #153 and #156 stated these limits
  correctly when written; the archive records what was believed.
- **No finding number allocated.** The base-rate result, the antithesis self-quotation effect and
  the merge-commit enumeration defect are each worth one; handed to the orchestrator.
