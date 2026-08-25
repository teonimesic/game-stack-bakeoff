---
id: 147
title: 'The CI register narrates its own history: run ids, past timings and variance history in a document that states what runs'
status: done
priority: 3
refs: ''
done_when: every dated timing, run id and change-history sentence in .github/workflows/README.md either states a standing instruction with its producer command beside it, or has moved to eval/findings/ or eval/RUNS.md; the register's own job - what runs in which tier and every gate deliberately left out with the reason - is intact and still names every workflow step; and docstat.py --sweep and linkcheck.py are green
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/25
established_by: 'PR #25 squash-merged as d3484a7. Verified independently: diffing the set of backticked names in the register before and after, the whole diff removes exactly two - the commit sha d087994 and ''18 mutants died, 5 variants passed'' - both dated history, and no workflow or gate name was lost, which is the ticket''s ''register''s job intact'' clause. The corpus repair is real and confirmed on main: the register is now in reference_docs() and github_docs() returns it. It remains outside project_docs() and outside the backticked-flag half, because that half is gated file-wide on a harness name and this file names tools - that exclusion is deliberate, measured (widening the trigger costs 25 candidate rows with 0 adjudicated genuine) and recorded in three places. My own plant still exits 0 there, which is the documented state rather than a defect.'
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

## note 2026-08-24

## What the next agent should not re-derive

### The register's prose is done; the interesting half was underneath it

Every run id, commit sha and how-the-number-moved sentence is gone from
`.github/workflows/README.md`, each replaced by the standing instruction with its producer
beside it. The check that the register's *job* survived is mechanical rather than asserted:
diffing the set of backticked names before and after, **the only name the whole diff removes
is the commit sha `d087994`**. Re-run that diff before believing any future claim that this
file "still names every step".

### `--sweep` and `linkcheck` were green on a file neither of them opened

`glob("**")` does not descend into a name beginning with a dot, so `.github/` was outside
`docstat.py`'s corpus exactly as `.claude/` was before task 44. The register is the file
`AGENTS.md` sends every session to read before adding a gate. This is **#170**, allocated by
the orchestrator against `main` while this was in flight — do not allocate another.

`github_docs()` now feeds `reference_docs()`. It does **not** widen `project_docs()`, and that
is deliberate: `project_docs()` feeds the bare-trial-id ratchet, which is pinned to an exact
count that a larger corpus would move in the **passing** direction.

### The mechanism that `tasks/149` and #170's second paragraph were built on is wrong

**The flag census does not read `project_docs()`.** In `cmd_sweep()` both flag halves are
inside `for p in refs:` where `refs = reference_docs()`; the only `for p in docs:` loop is the
bare-trial-id ratchet, scoped to `findings/`. What actually gates the backticked half is
file-wide, 40 lines into that loop:

    harness = re.search(r"(wholegame|runner|judge/|evaluate|regrade)\.py", text)

The two hypotheses agree on `DECISIONS.md` and on the register, and **disagree on skills** —
which are in `reference_docs()` and not in `project_docs()`. Planting the identical backticked
token in all 10 settles it: `add-game`, `audit-docs`, `evaluate-run`, `run-matrix` name a
harness and come back **exit 1**; the other 6 do not and come back exit 0; `any SKILL.md in
project_docs()` is `False`. Under the corpus hypothesis all 10 would be exit 0. Written into
`tasks/149`; the orchestrator has since corrected #170.

**Do not widen that trigger without re-measuring.** The obvious closed-class replacement,
`_our_script_names()`, admits 168 documents instead of 43 and adds 25 candidate rows,
adjudicated 2026-08-24 as **0 genuine** — `gh`, `git`, Godot and Chrome flags and tokens task
files name as deliberately fake. 9 of the 25 are in skills, which is where coverage is wanted.
`python3 eval/tools/docstat.py --selftest` is the producer and recounts it live; the rows print
as **candidates**, because the census applies only the exclusions the check applies and
classifies nothing beyond them.

### Traps this task walked into, in the order they cost time

1. **`skill_layout_control.py` plants into the real working tree.** A 2-minute Bash timeout
   killed it at exit 143 and left `.claude/skills` a real directory of copies; the next four
   gate runs were red with 11 rows blaming the skills, for a reason unrelated to the change.
   Repair: `rm -rf .claude/skills` then restore the symlink from the index. Filed as
   **`tasks/150`**. Give it 5+ minutes or do not start it.
2. **`_DELIBERATELY_FAKE` matches `phantom`, `plant*`, `does not exist`.** A control token
   named `--zzq-real-phantom` exempted its own line, and the census read 25 → 25 —
   indistinguishable from a census that had stopped looking. Use a neutral token:
   `--zzq-unresolved-tok` works.
3. **A plant's SHAPE decides which half sees it.** Bare-on-a-fenced-command-line and
   backticked-inline are different checks with different triggers. A single plant shape
   measures one half and tells you nothing about the other — which is how one observation
   became a wrong mechanism twice.
4. **`is_vendored` tests substrings, and 3 of the 5 `VENDORED` entries carry separators.**
   `is_vendored("target")` is `False`; `is_vendored(".../target/x.md")` is `True`. Any oracle
   filtering bare directory names disagrees with any subject filtering full paths.
   **`_all_skill_files()` still has this** — harmless today because neither `.claude/` nor
   `.agents/` holds a vendored directory, and not fixed here because it is not this ticket.

### Left deliberately

- **`linkcheck.py`'s `LIVE_DOCS` is unchanged.** The register carries no relative markdown link
  after this change, so widening the corpus would gate nothing. Check it explicitly with
  `python3 eval/tools/linkcheck.py .github/workflows/README.md`.
- **`tasks/148`** holds `ci_minutes.py` printing `(PRIVATE -- these minutes are metered)`.
  `DECISIONS.md` is already repaired here; the tool needs the visibility *read*, not a
  hardcoded `PUBLIC`, which is the same defect one value later.
