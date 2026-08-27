---
id: 186
title: Two harnesses record trial wall-clock under two names, and the one nothing reads holds 4.4 hours of it
status: in_review
priority: 3
refs: eval/runner.py,eval/wholegame.py,eval/RUNS.md,eval/judge/capability.py
done_when: 'The two names are reconciled - one quantity, one name, or an explicit statement in `eval/RUNS.md` that they are the same measurement recorded by two harnesses with the conversion written down. If `duration_ms` is kept, something must read it or the register must say why it is captured and not read; if it is dropped, the 47 stored records that carry it are evidence and the entry must say where that reading now lives. State which of the two the whole-game and spec-change suites each use after the change, and whether any published wall-clock figure moves - the expected answer is none, because nothing reads the one being changed, and that expectation should be checked rather than assumed. A null result closes this: if the two quantities turn out NOT to be the same measurement - different start points, different inclusions - say so with the two definitions side by side, because that is a sharper answer than renaming them.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/63
---

Found by the cleanup pass of 2026-08-27, the first to open `eval/runner.py`.

Both harnesses time a trial, under different field names, and only one of the two is ever read:

| written by | field | stored in | consumers outside its own module |
|---|---|---|---|
| `wholegame.py:450` | `wall_s` | whole-game trials | **6+** - `eval/judge/RUBRIC.md`, `capability.py`, `bot_mutants.py`, `BAKEOFF.md`, two findings files |
| `runner.py:726` | `duration_ms` | spec-change trials | **0, anywhere in the repository** |

Measured over the stored tree: `agent.duration_ms` is present and positive in **47 of 55** non-whole-game trial records and **0 of 84** whole-game ones. Its distribution is min 36s, median 332s, max 659s, totalling **4.4 hours of recorded agent wall-clock that nothing has ever read**. (`ci_minutes.py` mentions `run_duration_ms`, which is GitHub Actions' field for a workflow run and unrelated - checked.)

**Why this is more than a tidiness item.** `eval/RUNS.md` treats wall clock as a COMPARISON METRIC, and `wholegame.py` says so in a comment at line 459. A comparison that spans the two harnesses has to know the two names are the same quantity, and nothing says so - not the field names, not the docs, and not a producer. That is the shape #83 records: **an audit trail of what a mechanism did is worth more than the confidence you had when you built it, because the question it will be asked is not the one it was built for.** The judge's file-open log was captured for one reason and bounded a serious defect two weeks later; this capture has been sitting unread since 2026-08-12.

It is also live rather than historical: a second harness was added on 2026-08-25 as a recorded arm dimension, and any wall-clock comparison across harnesses or across the two suites meets this immediately.

## note 2026-08-27

## Reconciled 2026-08-27 — and the premise was wrong, which is the sharper answer

**Both harnesses record `wall_s`, and it is read.** `runner.py:719` and `wholegame.py:450`
both write it; `tools/runstat.py:156` and `runner.py:970` read it. The ticket's table put
`wall_s` against `duration_ms` as two harnesses' names for one field, and that is not what
they are.

`duration_ms` is a **third quantity held by a different party** — the agent CLI's report of
its own internal run, nested inside the harness's stopwatch — and it is the one nothing read.

| producer | field | stopwatch held by | interval | clock |
|---|---|---|---|---|
| `wholegame.py:450` | `wall_s` | the harness, around its own `run_agent()` | spawn, the CLI's whole life, reading and parsing its stdout | `time.monotonic()` |
| `runner.py:719` | `wall_s` | the harness, around the same call | the same span | `datetime.now()` — **not monotonic** |
| `runner.py:726` | `agent.duration_ms` | the `claude` CLI | its internal run alone | the CLI's own |
| `wholegame.py:481` | `artifacts/<tid>/agent_result.json` -> `duration_ms` | the same | the same | the same |

**The conversion, over 157 paired observations:** `wall_s - duration_ms/1000` is min 0.9s,
p25 1.0s, median 1.1s, p75 1.3s, max 6.5s, **negative on none of them**. The self-report is
97.4-99.9% of the harness figure; the rest is spawn-and-parse overhead. Producer:
`python3 eval/tools/wallclock.py` (needs the main checkout — `eval/runs/` is gitignored).

### The ticket's census was a shallow-glob undercount, and it is #126/#127's shape again

**71 of 71 spec-change records, not 47 of 55. 7.36 h, not 4.4 h.** `eval/AGENTS.md` names this
by file and by number: *"a `runs/*/trials/*.json` pattern misses 24 records and reports 47"*.
Reproduced both ways in one script — shallow 47, depth-independent 71 — and `census.py` agrees
at 71. The defect was not in any shipped tool; all three walkers are depth-independent. It was
in a one-off script at a shell prompt, which is the population no gate covers. **Handed to the
orchestrator as a finding needing a number; not allocated here.**

**And the self-report is NOT absent from the live harness.** `wholegame.py` stores the CLI's
whole result object and lifts no duration out of it, so the field sits in
`artifacts/<tid>/agent_result.json` and is present in **86 of 91** whole-game records. A sweep
of `trials/*.json` alone finds it in 0 and concludes the live arm never captured it.

The **6** records with no self-report are 6 explained records, not a gap: 4 are
`archive-arena2d-wg-audio48`'s wedged arena trials (`agent_result.json` is `{}`), 1 is the
prime-agent probe (that CLI reports no such field), 1 is the scene trial, killed before any
result object was written. **Every trial whose agent process terminated and reported carries
both clocks.**

### What was built, and the decision not to touch the live harness

- `eval/tools/wallclock.py` — the producer. **No walker of its own**: it takes
  `census.load_records`, so archive wrappers are found by construction. It takes **both**
  addresses and reports which one each record used, and **exits non-zero on a negative delta**.
  That assertion is not vacuous: `runner.py` brackets with a non-monotonic `datetime.now()`, so
  an NTP step or a DST change is a real hazard on that arm and a negative delta is what it
  would look like.
- `eval/tools/wallclock_mutants.py` — 12 mutants, all caught with a named failure, control
  green. `artifact_never_read` reproduces the ticket's own wrong answer (0 paired whole-game
  records) and reddens 11 selftest rows.
- `eval/RUNS.md` — the definitions side by side, the conversion, the two addresses.
  **Not a comparability break**; no stored run changed.
- Both `--selftest` and the mutant sweep are wired into `gates.yml`; the corpus-reading half is
  RECORDED in the register's `left out | why` table.

**`ClaudeHarness.normalise` deliberately does NOT gain a `duration_ms` field.** It would give
future runs one address instead of two, but nothing is being lost today — the figure is in the
artifact on 86 of 91 records — and lifting a field into the trial record on the only live
harness is a change to the thing being measured for a benefit the measurement does not support.
`runner.py:726` is kept: it is the only address for 71 stored records.

**Both suites use `wall_s` after this, exactly as before, and no published wall-clock figure
moves.** Checked, not assumed: `grep -rn duration_ms` outside `eval/runs/` returns
`eval/runner.py:726` as the sole non-documentation hit. `ci_minutes.py`'s `run_duration_ms` is
GitHub Actions' field for a workflow run and is unrelated.

### Known-good rows, if this is ever re-derived

| row | `wall_s` | self-report | delta | address |
|---|---|---|---|---|
| `wg-arena3d-2026-08-15T12-46-30/g3_arena__rust__t0` | 7100.1 | 7093.59 | 6.5 (the max) | artifact; absent from the record |
| `bakeoff-rust-2026-08-10T12-38-17/t1_rally__rust_bevy__t0` | 351.6 | 350.557 | 1.0 (the p25) | record; no artifact exists |

## note 2026-08-27

## Correction to the note above — the "97.4-99.9%" figure is wrong

Self-caught before the review. **Do not use the percentage in the note above.** It was
measured over the 71 spec-change records and then written as a statement about all 157 —
rule 5 (quoting a value not just read) and rule 4 (a range over a population never
established homogeneous).

**Over all 157 the ratio `duration_ms/1000` / `wall_s` runs 0.2347 to 0.9998.** The 5 lowest
are all `wg-g4b-2026-08-17T19-50-43`, the run `eval/RUNS.md` records as a null: the API refused
its 8 trials in under 2 seconds each, so ~1.2 s of constant overhead is most of a 1.6 s trial.

**The overhead is a CONSTANT, not a fraction.** ~1 s on a 1.6 s trial and ~1 s on a 4961 s one;
the 6.5 s maximum belongs to the longest trial in the corpus rather than to a proportion. The
ratio measures trial LENGTH and says nothing about the two clocks. **Quote the difference in
seconds** — min 0.9 s, median 1.1 s, max 6.5 s over 157 — and never the fraction.

`eval/RUNS.md` and `eval/tools/wallclock.py`'s docstring both say so now. **No measured figure
moved:** the tool has always reported the delta and reports no ratio; the defect was prose.
