---
name: prune
description: A cleanup exploration pass. Explore one area of the repository for things that no longer earn their space — stale prose, history a future run does not need, duplicated documents, refactorable code, sections that could say the same thing in fewer tokens — record what you looked at, and file tasks for what you found.
when_to_use: The six-hourly cleanup monitor fired; or the repository feels heavier than it should; or you have just finished work and want to know what it made obsolete.
argument-hint: "[area to explore, e.g. 'eval/judge' or 'the starter docs']"
---

# The cleanup pass

**Authoritative files: `AGENTS.md` (the pruning principle and the archive exception) and
`CLEANUP-LOG.md` (what has already been explored).** If this skill and either of those
disagree, they win and this skill is the bug.

## What this is for

Everything in this repository costs the next session attention. `AGENTS.md` already says it:

> Prune. Every rule that does not earn its place makes the ones that do harder to find. A
> document nobody finishes reading protects nothing. When a rule is superseded, replace it —
> do not annotate it.

The goal is **less to read for the same understanding.** Not tidiness, and not deletion for
its own sake.

## This is exploration, not a script

There is a helper — `python3 eval/tools/prune_scan.py` — and it is an *aid*, not the
definition of the job. It finds six mechanical shapes. It cannot notice that a whole document
describes a subsystem that was replaced, that two rules say the same thing in different words,
or that a 3000-token section could be a table.

**Go and read things.** Open files. Follow references. Ask of each piece of text: *if a fresh
agent read only this, would it be better off?* The scanner tells you where to start looking on
a slow day; your own reading is what actually finds things.

What it can tell you, and how to read each one:

| category | what it means, and what it does NOT mean |
|---|---|
| `hotspot` | **churn × complexity.** Complicated code people keep having to touch — the difficulty is being paid for repeatedly. Neither number alone says this: complexity alone flags code that is hard but settled, churn alone flags code that is simply under active development. High churn on something being actively built is expected. |
| `complexity` | cyclomatic complexity above 20 per function. A prompt to look. A 30-branch dispatch table scores badly and reads fine. |
| `longfn` | functions over 90 lines. Same caveat. |
| `lint` | `ruff`, pinned to **correctness** rules, not style — blind excepts, `subprocess.run` without `check=`, swallowed exceptions. Deliberately not run over `eval/starters/*/` or `eval/judge/fixtures/`, which are the product or stand-ins for it. **Totals only; `python3 eval/tools/lint.py` gives the file and line of every site.** |
| `dup` | the same paragraph in more than one file, grouped per file-pair. Two copies drift and the reader who finds the stale one cannot tell. |
| `fat` / `history` / `dead` / `todo` | long sections, prose describing a former state, uncalled functions, markers. |

**A high score is a question, never a verdict.** The scanner cannot tell a hotspot from a file
that is simply where the work is this week.

> **Churn is a cost, not an output — and that applies to fixing lint too.** The unpinned ruff
> default reported 491 issues here, 132 of them percent-formatting. Mass-fixing those spends
> review attention to move text and buries the handful that map onto real recorded failures.
> Triage; do not sweep.

The `PLW1510` and `BLE001` counts are a **triaged baseline** as of 2026-08-23 (#105), so a hit
from either is a site nobody has considered. The rest of the lint output is a standing backlog
and its total is not a verdict — `DECISIONS.md` says which is which.

## Do this, in order

### 1. Read `CLEANUP-LOG.md` first

It records every previous pass: what area, what was looked for, what was found, and — just as
important — **what was looked at and judged fine.**

Without that, every pass re-explores the same ground and re-files the same tasks. A negative
result is a result: *"read all six skills, found nothing worth changing"* saves the next pass
an hour, and only exists if someone wrote it down.

### 2. Check the queue before filing anything

```bash
python3 eval/tools/tasks.py                 # what is already open
grep -rl "<the thing you found>" tasks/     # has someone already filed this?
```

**A duplicate task is worse than no task** — it splits the work and both copies get half-done.
If an open task already covers it, add your evidence to that file instead.

### 3. Pick ONE area not covered recently

One area, explored properly, beats six skimmed.

**A recorded pointer is a claim, not a decision.** The previous entry's "next pass should
take X" was written by a reader as fallible as you, and has twice named a file an earlier
pass had already read (pass 13's alternate; pass 17's pointer). Verify before following:

```bash
grep "^## " CLEANUP-LOG.md | grep "<candidate path>"
```

A hit means it is a prior pass's *subject* — the pointer is void, pick your own area, and
record the voiding in your entry. The check reads the headings, not prose: alternates and
pin sites name files that were never read. This is step 1 applied to the pointer itself,
and it costs one grep. The heading match is format-agnostic on purpose: passes 1-12 headed
their entries `## 2026-08-DD (nth pass) — …`, passes 13+ use `## Pass N — …`, and a grep
keyed to one format silently stops covering the other — which pass 19 caught in this very
repair one pass after it was written.

Candidates, but do not feel bound by them:

| area | what tends to accumulate |
|---|---|
| the root docs | `README.md`, `DECISIONS.md`, `AGENTS.md` — superseded state annotated rather than replaced |
| `eval/judge/` | criteria and gates kept "just in case" after being disproved; long functions |
| the starter/template docs | duplicated stack notes that drift between copies |
| `eval/tools/` | scripts written for one investigation and never used again |
| the skills | procedures that restate a doc instead of pointing at it |
| `tasks/` | closed tasks whose evidence has been superseded; open ones nobody will ever do |
| `IMPROVEMENTS.md` (root and `eval/`) | hypotheses left open that were settled elsewhere |

### 4. Explore, and judge

For each candidate, the question is **what would be lost.** Three outcomes:

- **Cut it** — it says nothing a future run needs. Small and obvious: just do it.
- **Replace it** — it is superseded state. Rewrite to say what is true now, do not annotate.
- **Keep it** — it is load-bearing. Say so in the log so nobody re-examines it next month.

### 5. File tasks for anything you are not doing now

Use the `tasks` skill's standard — a ticket a stranger could pick up. Do the small obvious
things directly; file the rest. **Do not start a large refactor from a cleanup pass** — a
refactor entangled with a cleanup is one nobody can review or revert.

### 6. Write the log entry. This is not optional

Append to `CLEANUP-LOG.md`. An entry that records only what you changed is half an entry —
the value is in what you *looked at*, including what you cleared.

## What must never be pruned

This is the part that makes cleanup dangerous here, and it is the reason this skill exists
rather than a one-line instruction to "tidy up".

| Never | Why |
|---|---|
| `eval/findings/` and `eval/FINDINGS.md` | A findings log. A number published and later proven wrong **stays**, marked, because someone may have acted on it. Retractions are the most valuable text in the repository. |
| Regime boundaries in `eval/RUNS.md` | They say which runs may be compared with which. A boundary that reads as obsolete history is exactly what makes an old number safe to use. |
| The *reasoning* in `DECISIONS.md` | A decision without its why gets re-litigated. Supersede the decision; keep why the old one was made. |
| The evidence a rule was bought with | `AGENTS.md`'s rules cite the incidents that produced them. A rule stripped to its imperative is one the next reader talks themselves out of. |

> **The test: would removing this make a future wrong conclusion possible?** If yes, it is
> evidence, not clutter — no matter how old it looks.

The scanner excludes the archive by default for this reason. `--include-archive` exists, and
what it returns is a question, never a to-do list.

## What a good pass looks like

Not "deleted 400 lines". A good pass is: *one area read properly, two or three things
genuinely cut or replaced, a couple of tasks filed with evidence, and an honest record of
what was checked and found sound.* Several passes will legitimately find almost nothing —
write that down and stop, rather than manufacturing changes to justify the run.

**Churn is a cost, not an output.** A cleanup pass that rewrites text without making it easier
to act on has spent tokens and review attention to move words around.
