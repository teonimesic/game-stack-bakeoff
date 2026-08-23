---
established_by: judge/capture_selftest.py 39/39 after, 9/17 with 7 of 9 tests unrunnable before (rule 14). Variant on the unfixed function: 10 KB stderr plus one stdout line lost the line, reverse kept it. Positive control, one wg-g4c submission per stack, gate run once and rendered under both policies - godot 3263/0 yes-yes, rust 16/8638 NO-yes, ts 670/213 yes-yes, unity 201/0 yes-yes. End to end: full collect on godot 9/9, 51/51 tests parsed, capability.py reads all nine fields. Commit 9a0345f on task-45-command-capture; FINDINGS #103; runner.py instance filed as task 50.
id: 45
title: Repair the tier-1 command capture so a gate's own completion line survives truncation
status: done
priority: 3
refs: eval/FINDINGS.md #99, eval/judge/static.py, eval/IMPROVEMENTS.md axis 2 candidate 1
done_when: a selftest pins both directions - a command that floods stderr keeps its one stdout line, and the reverse - and a fresh collect over one submission per stack records which of the four stored tails hold the verify recipe's completion line; if any arm still loses it, report that arm and the reason rather than closing
---

## What this thing is

Tier 1 is the programmatic layer of the evaluator: nine criteria (fourteen when the game has
audio) answered by running commands inside a submission and reading the result. It is implemented
in `eval/judge/static.py`. For every command it runs — `just check`, `just verify`, `just lint`,
`just test`, `just film` — it stores a `Cmd` record holding the argv, the exit code, the wall
seconds, and a `tail`: the captured output, truncated.

That stored `tail` is the whole audit trail. It is what a human reads when adjudicating a
criterion, what the per-criterion `evidence` string is cut from, and the only thing any future
check could inspect about what a command actually printed.

## What is wrong, and how we know

`Cmd.to_dict` stores `self.tail[-4000:]` (`static.py:64`), and the buffer it truncates is
assembled as `bufs["out"] + bufs["err"]` (`static.py:163`) — **the whole of stdout, then the whole
of stderr, then keep the last 4000 characters.** When a command writes a lot to stderr, its stdout
is discarded entirely.

All four starters end their `verify` recipe with the same line, `@echo "✅ verify passed"`
(`eval/starters/godot/justfile:35`, `rust/justfile:36`, `ts/justfile:38`, `unity/justfile:30`),
and `just` sends it to stdout.

Measured 2026-08-23 across the 68 stored `eval/runs/**/programmatic.json` records — 62 of them
have `just verify` exiting 0:

| | godot | rust | ts | unity |
|---|---|---|---|---|
| `verify` exit 0 | 15 | 16 | 16 | 15 |
| stored tail contains `verify passed` | 13 | **1** | 16 | 15 |

The 17 misses are **exactly** the 17 records whose tail hit the 4000-character cap. Eighteen hit
the cap; the eighteenth holds the token at offset 3986. `cargo-nextest` writes its progress and
its `Summary` line to stderr, which is why the Rust arm loses stdout in 15 of 16 cases and the
other arms almost never do.

This is `eval/FINDINGS.md` #99. No score is wrong — the exit code is read from the process, not
from the text — so nothing published needs marking.

## Why it matters

Two reasons, and the second is the one that blocks work.

1. The stored justification for one criterion differs in kind by stack. On godot and unity,
   `verify.green`'s evidence ends with the gate's own verdict; on rust it ends mid-test-listing.

2. **It blocks `eval/IMPROVEMENTS.md` axis 2 candidate 1.** The natural strengthening of #98
   (`build.compiles` and `verify.green` are exit codes and nothing else) is to require the recipe
   to emit a token it could only print by having finished — which is what `game-research-gpt`'s
   verify manifest does with `expected_stdout_contains`. Installed against today's capture that
   check would be **structurally unable to fire on the Rust arm**, which is the one-arm shape this
   project keeps a findings file for. Fix the capture first; the token check is a separate
   decision afterwards.

## What should be done

In `eval/judge/static.py`, stop truncating a concatenation. Options, in the order they were
considered — pick on evidence, not on taste:

- keep stdout and stderr as separate fields, each truncated independently;
- keep both ends of the combined buffer (head + elision marker + tail);
- raise the cap.

The third alone is not a fix: it moves the boundary without changing the rule that stdout is
sacrificed first, so it will fail again on a noisier test runner.

Prefer the first. It also makes the stream a command wrote to an observable fact rather than an
inference, which is what the `AGENTS.md` capture rule asks for.

**This is an evaluator change, not a starter change — no regime boundary.** Stored records cannot
be repaired: the discarded stdout was never written down. The change affects future runs only, and
that is fine; say so rather than backfilling.

### How to know it worked

Two directions, both required (rule 15).

- **Positive control.** Run `judge/static.py`'s collect path against one submission per stack in a
  scratch copy and assert the completion line is present in all four stored tails. Choose a Rust
  submission whose stderr exceeds 4000 characters — most do; `wg-matrix-2026-08-13T14-02-50`
  `g1_pong__rust__t1` is one.
- **Variant, not merely a mutant.** A mutant that deletes the truncation cannot manufacture the
  input that produces this defect. Feed the capture a command that writes 10 KB to stderr and one
  short line to stdout, and assert the stdout line survives. Then feed it the reverse. Run both
  against the unfixed function first and record how many expectations it fails — the shape
  `judge/pack_selftest.py` uses.

### What not to conclude

Not that the 17 affected submissions failed `verify`; all 62 exited 0. Not that #98 has recurred.
And not that the two godot misses share the Rust cause — those are the engine's resource-leak
lines at exit, a different instance of the same mechanism.
