---
name: evaluate-run
description: "Grade a completed matrix and decide whether its results mean anything: the three tiers, the validation gates in order, adjudicating every failure against source, and the rules for reporting a null."
when_to_use: "A build has finished; re-grading stored trials offline; running the specialist judges; asked whether a stack comparison shows a real difference or whether a result is reportable. Trigger phrases: evaluate the run, grade the submissions, run the judges, does this show a difference, is this a real result."
argument-hint: [run-dir]
---

# Evaluating a run

Authoritative references: `eval/judge/RUBRIC.md` (the contract), `eval/judge/JUDGING.md`
(the subjective layer), `eval/RUNS.md` (what may be compared with what). **If this file
disagrees with them, they win and this file is the bug.**

## 0. Before anything grades

```
cd eval
python3 judge/bot_mutants.py       # UNPIPED, read its own exit code
python3 judge/audio_selftest.py    # UNPIPED
python3 judge/verify_blind.py      # UNPIPED
```

A criterion that cannot fail is worse than absent, because it looks like success. Do not
grade with a red or unrun self-test.

## 1. Deterministic tiers

```
python3 wholegame.py evaluate --run-dir runs/<name> --eval-parallel 1
```

Serial. Concurrent renders produce flaky captures, which is the false-negative class that
has already cost this project three criteria and two evaluation passes.

Weights: **programmatic = a GATE, not scored / play-bot 1.00 / judge 0.00.** `overall` is the
play-bot tier; the tier-1 verdict is reported beside it as `gate: PASS` or `FAIL` with the
failing criterion ids. A stored `overall` from before 2026-08-23 is on the old
`0.31*prog + 0.69*bot` scale — **do not average across that boundary** (`eval/RUNS.md`).

## 2. Adjudicate every failure against source — this is not optional

**Across three matrices, every single criterion failure has been a grader defect, not a
submission defect.** Do not report a failure you have not traced to the submission's code.

For each: read the criterion's evidence string, then the submission's source. Ask whether
the criterion measures the property in its own name, or something incidental — where a
piece happens to sit, what angle a ball happens to serve at, whether a previous process
happened to exit.

Two distinct defects, and a mutant suite only catches the first:

- **Cannot fail** — caught by mutants.
- **Passes for the wrong reason** — invisible to mutants, because the mutant breaks the
  right reason and the criterion was never testing it. Found only by reading the evidence
  text of a *passing* criterion. This class produced this project's withdrawn ranking.

## 3. The subjective layer, gates in order

**Read `RUBRIC.md`'s aspect table before choosing `--aspects`, and `JUDGING.md` before
reporting any of them.** Which aspects exist, which task class each is asked of, which is a
control and which may not be ranked across stacks are stated there; this file does not
restate them, because a second copy is the one nobody edits (#38). The tools refuse what the
table forbids — `--aspects feel` is rejected, a scene aspect asked of a game is refused
before a round starts, and `field_ranks.py` prints each bar with the per-stack means.

Verify the judges **actually executed and produced non-empty packs per aspect**. A green
exit is not evidence — making the legacy judge opt-in once silently removed the source
pack two aspects read.

Then, in order, and none may be skipped:

1. **Ceiling** — no judge may grade everything the same. Watch the *mode*, not just the
   top score: a judge putting seven of eight at the bottom reads as healthy otherwise.
2. **Independence** — if aspects produce the same ranking there is one judge with many
   names. Report how many pairs were actually comparable; a tau over three pairs must not
   be read like one over twenty-eight.
3. **Order-invariance** — reshuffle presentation order; a ranking that moves is an
   artifact.
4. **Adjudication** — spot-check firings against the underlying evidence. Consistency is
   not correctness; three stack-specific instrument defects here were each perfectly
   consistent.

Sequential sampling per `JUDGING.md`: resolve per **pair** with a Wilson interval, stop
early per pair, report the N each decision required. `TIED_EXACT` and `UNRESOLVED` are
different verdicts and must never be reported as the same thing. At affordable N the
instrument can detect an ordering but **cannot statistically prove a tie** (~96 rounds).

## 4. Reporting

- **Partition by `terminal_reason`** before computing anything. Report `n` per group.
- **Never pool across a regime boundary** — task change, allowlist change, limit change.
  `RUNS.md` lists which runs are comparable.
- **A stack-correlated result is not reportable without a named causal chain in the
  code.** Four for four here have been harness defects. Do not invent a mechanism to fill
  the gap; where none is found, record the split as unresolved.
- **If within-cell variance is comparable to between-stack variance, there is no ranking**
  — say exactly that.

**A null is a result.** Three suites of increasing difficulty have failed to separate
these four templates, and every deviation has been a grader defect. Lead with it plainly.
Do not manufacture a separation from a small spread because money was spent.
