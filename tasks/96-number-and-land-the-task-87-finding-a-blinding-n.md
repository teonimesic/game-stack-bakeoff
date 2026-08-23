---
id: 96
title: 'Number and land the task 87 finding: a blinding named a property and implemented a suffix, and its densest leak was a file the harness itself wrote'
status: done
priority: 3
refs: tasks/87, eval/judge/field.py blind_extensions, eval/judge/blind_ext_selftest.py
done_when: the finding is numbered against the highest number on main at the time, placed in the eval/findings file whose shape it matches, indexed in eval/FINDINGS.md, and docstat.py --sweep is green unpiped
established_by: 'Landed as two findings: #137 in eval/findings/one-arm-bias.md (the blinding named a property and implemented a suffix; 2,083 arm-naming extension tokens across all 84 stored packs after neutralise and 0 after, 1,876 in 76 of 84 packs not the ticket''s 78, and CHANGED.txt is a clean per-arm partition contributing 345 of 667 tokens against 322 in all 199 code files) and #138 in eval/findings/fail-open.md (field.py pack read sees and not blind_language: 199 of 207 evidence files keeping their real suffix and 667 tokens pre-repair, 0 and 11 post, established by reverting the keyword in a copy of the module and rebuilding the same field twice). docstat.py --sweep exit 0 unpiped, docstat.py --findings reports 120 findings #19-#138 agreeing with 120 index rows and every live document, findings_control.py 13 of 13, tasks.py check 103 well-formed, blind_ext_selftest.py --runs-root green on all 7 checks. Main moved to #136 mid-task so the numbers drafted as 136/137 are published as 137/138; main merged into the branch and the conflicts resolved there.'
---

Task 87 is a finding and this queue has three peer worktrees holding findings-heavy tasks (86, 91, 93), so the number was deliberately NOT allocated - eleven collisions happened on 2026-08-23 because every agent reads the highest number from a branch forked before the last merge. The claim, with the numbers already measured and reproducible via judge/blind_ext_selftest.py --runs-root: blind_language was specified as 'the judge is not told the language' and implemented as 'rename the file on disk to .src', so it hid the extension of the file the judge OPENS and none of the ones it READS - 2,083 arm-naming extension tokens across all 84 stored packs after neutralise, 0 after the repair, with 81 import.meta occurrences declined as a language construct rather than a path. The part worth publishing is WHERE the worst of it was: not in agent-authored code but in CHANGED.txt, which field.build_pack writes itself from git diff --stat - a complete list of every authored path with its true suffix, sitting in a directory whose every file had just been renamed to .src. 80 .cs, 78 .gd, 60 .meta, 43 .ts and 43 .rs in the 8 stored blind packs, from the harness. Every gate the project owns looked at what the SUBMISSION carried; none looked at what the packer added. Also worth recording: the 1,876/78-of-84 figure in the task 87 ticket reproduces exactly on the count and is 76, not 78, on the pack union. A SECOND CLAIM belongs in the same finding or in one beside it, found by pointing the finished repair at a real run rather than at the fixture: field.py pack read the aspect's sees and not its blind_language, so the one entry point the module docstring tells a human to type produced a completely unblinded architecture pack - 199 of 207 files keeping their real suffix and 663 extension tokens - while field_sweep.py passed both properties at all three of its call sites, so no stored round is affected and nothing ever noticed. Every test called build_pack directly, where the argument is explicit. The generalisation is: when an object gains a property, grep for every reader of its siblings.

## What was established while closing this, so the next agent does not re-derive it

**Landed as TWO findings, not one, because the two claims have different denominators.** The
extension leak affects 84 of 84 stored packs; the CLI defect affects 0 stored rounds. Putting
"84" and "0" in one finding is how a reader takes the wrong one away.

- **#137**, `eval/findings/one-arm-bias.md` - the blinding named a property and implemented a
  suffix. Sits with #32, #53, #83, #131, the other "the blind pack leaks the arm" findings.
- **#138**, `eval/findings/fail-open.md` - `field.py pack` read half the aspect. A guard that
  silently did not run on one path, which is that file's shape.

**The numbers were re-measured rather than copied, and three of them moved.**

| quantity | ticket said | measured | why |
|---|---|---|---|
| pack union, four language suffixes | 78 of 84 | **76 of 84** | the count 1,876 reproduces exactly; only the union was wrong |
| files in an unblinded CLI pack | 199 of 207 | **199 of 207 evidence files**, 208 on disk | the 208th is the packer's own `.claude/skills/sampling-code/SKILL.md`, which carries 0 extension tokens. Both denominators are defensible; say which one a ratio uses |
| extension tokens in that pack | 663 | **667** | under the `field.BLIND_EXT` alternation with a `(?![A-Za-z0-9_])` tail over every file in the pack, measured twice with identical results. The earlier pattern was not recorded, so the gap of 4 is **unresolved**. It does not touch the split that carries the argument |

**Two things measured here that the ticket did not have, both now in #137:**

1. `CHANGED.txt` is not a smear across the field - it is a **clean partition**. Each of the 8
   stored `architecture` packs names exactly one arm's suffixes and no other arm's (A/C `.ts`
   22/21, B/E `.gd` 38/40, D/F `.rs` 26/17, G/H `.cs` 38/42 with `.meta` 27/33). Not a hint, a
   label.
2. In a whole `architecture` field rebuilt with the blinding off, **345 of the 667 extension
   tokens are in `CHANGED.txt` against 322 in all 199 code files put together** - the harness
   contributed more than half of what the blinding was for.

The stored packs and the rebuilt field are the **same 8 `g4_platformer` submissions** (5 of 8
`CHANGED.txt` byte-identical, arm-suffix totals equal), so those two figures corroborate the
extraction and not the claim (rule 9). Said so in the finding rather than leaving a reader to
assume two independent measurements.

**How the CLI defect was pinned in both directions:** copy `eval/judge/` twice, delete
`blind_language=aspect.blind_language` from one copy's `pack` branch, run
`field.py pack --run <wg-g4c> --game g4_platformer --aspect architecture` from each. Pre-repair
199 real suffixes / 191 arm-naming filenames / 667 tokens; post-repair 0 / 0 / 11, all 11
`import.meta`. Establishing the broken state first is the point - a run after the fix tests the
fix (rule 14).

**The collision this ticket was written to avoid happened anyway, mid-task.** Main was at #135
when the work started and a peer merged **#136** into it while the finding was being written, so
what was drafted as #136/#137 is published as **#137/#138**. Re-reading the highest number
before taking one is necessary and not sufficient: the exposure is the window between reading it
and merging, and it is minutes wide. `main` was merged into the task branch and the conflicts
resolved there rather than left for the orchestrator, because the numbering is only checkable on
a tree that holds both.

