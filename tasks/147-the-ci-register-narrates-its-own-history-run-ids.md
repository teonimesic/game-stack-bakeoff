---
id: 147
title: 'The CI register narrates its own history: run ids, past timings and variance history in a document that states what runs'
status: in_review
priority: 3
refs: ''
done_when: every dated timing, run id and change-history sentence in .github/workflows/README.md either states a standing instruction with its producer command beside it, or has moved to eval/findings/ or eval/RUNS.md; the register's own job - what runs in which tier and every gate deliberately left out with the reason - is intact and still names every workflow step; and docstat.py --sweep and linkcheck.py are green
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/25
---

CodeRabbit flagged .github/workflows/README.md lines 19-32 and 41-42 on PR #23 (task 140) under the .coderabbit.yaml rule that a live document states the choices in force and is not a log of what happened. The finding is valid and was declined THERE rather than acted on, because git log -L 19,32 and -L 41,42 both name c29429a (task 135, PR #22), which landed on main while #23 was open - editing a section another task had just landed, inside an unrelated pull request, is what .agents/skills/work/SKILL.md section 4 forbids. The content at issue: a floor timing dated 2026-08-24 with per-tool step times, a named CI run id, and a sentence recording that two selftests became gated. What a reader needs is what runs in which tier and how to re-derive the timings (ci_minutes.py), not the history of how the numbers moved.

## note 2026-08-24

## note 2026-08-24 (orchestrator) — the corpus fix is HALF a fix, measured

Verified the dot-directory discovery independently on `main`, with one plant plus a positive
control, because an all-green result and a broken probe look identical:

| plant `` `--zzqwerty-nonexistent` `` in | `--sweep` on `main` |
|---|---|
| `.github/workflows/README.md` | **exit 0** — invisible |
| `DECISIONS.md` | exit 1 — caught |

So the discovery is real and the register was never read. **But the fix as pushed does not close
it for the flag check.** The same plant, on this branch:

| plant in `.github/workflows/README.md` on the branch | `--sweep` |
|---|---|
| after `dot_dir_docs()` feeds `reference_docs()` | **still exit 0** |

The reason is visible in `cmd_sweep()`: it holds **two** corpora — `docs = project_docs()` and
`refs = reference_docs()` — and the flag census iterates the first. `reference_docs()` gained the
register (212 docs, 1 `.github` entry); `project_docs()` did not (201, 0). So **unresolved
references are now checked there and phantom flags still are not.**

Not widening `project_docs()` was a stated and sound choice — its exact-count ratchet would move
in the passing direction. That reasoning stands; what it leaves is a gap that must be **recorded
rather than implied**, and CodeRabbit reached the same place from the other side on
`docstat.py:3631`: the corpus pins still pass if `dot_dir_docs()` returns only the one file it
currently returns.

**What this ticket needs is not necessarily the wider fix.** Its `done_when` asks for the history
removed and the two gates green, and that is met. Deciding which checks should cover `.github/`
is a bigger question than a p3 documentation ticket. Either close that gap here with a control
that would fail if the corpus shrank to one file, or say in `.github/workflows/README.md` and in
`docstat.py` exactly which checks read that file and which do not — an exclusion recorded is fine;
one silently absent is what this whole ticket is about.
