---
established_by: 'Deleted. The Codex sibling question is settled by three measurements. (1) game-research-gpt, the only Codex-adjacent sibling (task 11), has no .agents/ directory, no SKILL.md anywhere, no root AGENTS.md, and zero occurrences of codex in README.md, docs/, scripts/ or template/AGENTS.md - its only agent-convention file is template/AGENTS.md, so it was never a reader. (2) The mirror was never once in sync: in the initial commit add-game was 87 lines against 126, tasks was absent, prune was never added. The 39 missing lines are the whole prompt_guard.py section, the guard that exists because of #41. (3) After the import it took 0 edits that changed a procedure against the authoritative trees 6; its tasks copy was snapshotted at 23:54 on 2026-08-22 and edits at 00:03 and 00:17 did not reach it, leaving it missing the shared-queue section that exists because of #94. It also asserted --max-turns and --permission-mode belong to the Codex CLI, contradicted by eval/runner.py:510,519 which passes both to claude. Mechanism, not a one-time reconciliation: docstat.py --sweep now exits 1 on any SKILL.md outside .claude/skills/<name>/, triggered on the address rather than the directory name so it fires on .codex/, .cursor/, a bare skills/ or a wrong nesting depth. The check was vacuous on its first run and only the planted control revealed it - glob does not descend into dot-directories, so the pattern matched none of the seven real skills either; it walks now and reports finding zero SKILL.md as a failure in its own right (#60). Controls: planted .agents mirror exit 1; wrong nesting depth inside .claude/skills exit 1; SKILL.md under eval/runs exit 0; SKILL.md in a .claude/worktrees checkout exit 0; walk enumerates 7; repaired repo exit 0. The last four are variants not mutants (rule 15). prune_scan.py loses its MIRROR suppression and its dup category now runs unfiltered, exit 0. AGENTS.md and DECISIONS.md name .claude/skills/<name>/SKILL.md as the sole authoritative path, with a reversal condition. Recorded as FINDINGS #99. Commit bec16e3 on task-27-agents-skills-copies. NOTE for task 37, in flight: its spec says to glob .claude/skills/ and .agents/skills/ - the second no longer exists, and glob would have made its frontmatter gate vacuous for the same reason mine was; use docstat._all_skill_files().'
id: 27
title: Decide whether the .agents/skills Codex copies are maintained or dropped
status: done
priority: 2
refs: .claude/skills/, .agents/skills/, AGENTS.md skills table
done_when: either .agents/skills is removed with the reason recorded, or it is kept with a check that fails when it drifts from .claude/skills; and AGENTS.md names which path is authoritative
---

WHAT THIS IS

A **skill** in this project is a procedure an agent invokes when it is about to do something —
launching a trial run, grading a finished matrix, adding a game. There are six, and `AGENTS.md`
says they live in `.claude/skills/<name>/SKILL.md`.

There is a **second complete copy** of all six at `.agents/skills/<name>/SKILL.md`. Both are
tracked in git. `.agents/skills/` entered in the very first commit and nothing in any document,
script or tool references it — `docstat.py`, which sweeps the docs, globs `.claude/skills/` only
and is structurally blind to it.

WHAT IS WRONG, AND HOW WE KNOW

The two copies are not duplicates by accident — they are a **deliberate fork for a different
agent CLI**. Measured 2026-08-23, three of the six differ, and the differences are systematic
substitutions of the tool name:

    audit-docs   .agents says "the Codex CLI's",  .claude says "the claude CLI's"   (2 lines)
    run-matrix   .agents says  Codex -p "Reply READY."                              (1 line)
    add-game     .agents is 87 lines, .claude is 126 — .claude is a strict SUPERSET

So the intent was a Codex-flavoured copy, and it has since gone stale. `add-game` there is
missing 39 lines of content that exists only in the Claude copy, and nothing detected that,
because no mechanism compares them.

This is a **second source of truth with no sync and no drift check** — the exact failure this
project records for documentation, in the one place nobody looks.

WHY IT MATTERS

`.agents/` is the cross-tool convention directory. An agent that is not Claude Code, reading this
repository, finds the stale copy and follows it: an `add-game` procedure missing 39 lines, and a
`run-matrix` that tells it to shell out to a CLI that may not be what is actually running here.
The repository is MIT and public, so that reader is not hypothetical.

It is priority 2 rather than 1 because no measurement currently depends on it — but a skill is
how a procedure survives, and a silently stale one is worse than an absent one.

THE QUESTION THAT IS NOT DERIVABLE FROM THE ARTIFACTS

**Is a Codex-run sibling of this project actually being maintained?** The artifacts cannot say.
There IS a second attempt at this research question at `~/Documents/heavenstudio/game-research-gpt`
(see task 11), which makes a maintained Codex path plausible rather than merely possible. Settle
that first — it decides everything below.

WHAT SHOULD BE DONE

If **no Codex sibling is maintained**: delete `.agents/skills/`, record in `AGENTS.md` that
`.claude/skills/` is the sole authoritative path, and say in the commit why the copy existed —
so the next person who wants cross-tool support knows it was considered, not overlooked.

If **it is maintained**: keep it, but the copies must not be able to drift silently. Add a check
to `eval/tools/docstat.py` sweep that fails when a skill exists in both paths and differs by
anything other than the known tool-name substitution. Bring `add-game` back into sync first — it
is 39 lines behind. A check added while the copies already disagree will just be disabled.

Either way `AGENTS.md` must name which path wins, because right now it names one and the
repository contains two.

WHAT NOT TO CONCLUDE

Do not treat "identical today" as safe. Three of six are identical right now and that is exactly
what the other three looked like before they drifted. The deliverable is a mechanism or a
deletion — not a one-time reconciliation, which buys one day.

Do not resolve this by symlinking without checking the substitution: the Codex copies deliberately
differ, so a symlink would silently revert an intentional edit, which is the same class of defect
in the other direction.
