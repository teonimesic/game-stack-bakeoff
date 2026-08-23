---
id: 103
title: 'The code-content half of the directory leak: a feasible rewrite was declined because its redaction density is stack-correlated 0/43/228/265'
status: in_progress
priority: 3
refs: eval/judge/blind_dir_selftest.py arm_exclusive_dirs, eval/judge/field.py blind_changed_txt, DECISIONS.md 2026-08-23, tasks/95
done_when: either a rewrite whose per-arm rewrite count is measured and comparable across all four arms lands, blind-only and pinned by a mutant AND a variant proving a non-blind pack is byte-unchanged; or the channel is closed as unrepairable with the per-arm density table and the reason recorded in DECISIONS.md. A per-arm count is mandatory either way - a single total is what made task 95 nearly choose the wrong repair
---

Task 95 repaired CHANGED.txt and measured the code half rather than guessing at it. 149 of the 1,379 arm-naming tokens in the code content of the 8 stored architecture packs are real path segments; the other 1,230 are the same words doing something else - 1,129 public are the C# access modifier, 16 of 17 ProjectSettings are ProjectSettings.globalize_path(), Assets is ResMut<Assets<Image>> in Rust packs. The ticket for 95 guessed that a directory vocabulary probably cannot be audited against the starters mechanically. IT CAN: whole-segment and path-adjacent, read from git ls-files over the four starters, it finds 536 hits across all 84 stored packs with exactly 1 in an arm the segment does not name - and the one false positive is scripts/demo.json inside a Rust pack, which removes a word rather than adding a leak. Feasibility is not what disqualified it. The redaction it produces is stack-correlated by construction because only some starters have arm-exclusive directories: godot 0, rust 43, unity 228, ts 265. A judge shown three packs with redacted paths and one without has been handed the partition by the instrument, which is FINDINGS 62's shape. Two alternatives that were measured and are also not clean: mapping code content through the manifest the way CHANGED.txt now is covers 166 occurrences over 77 of 199 origins and is stack-correlated too - Rust is 0 of 43 because it references modules as crate::sim::world and never as a path; and rewriting EVERY path segment would destroy the bucket labels sim/ view/ tests/ that the judge's own brief instructs it to cite. Whoever picks this up should start from the per-arm table, not from a total.

## What was established while closing this, so the next agent does not re-derive it

**Closed as unrepairable.** Four candidates were measured, not two. The census is
**part 6 of `eval/judge/blind_dir_selftest.py`**, run with `--runs-root <main>/eval/runs`,
so the decision has a producer rather than a remembered table.

**The ticket's per-arm table reproduces to the digit — but only with `bin` excluded, and
the ticket does not say so.** The shipped `arm_exclusive_dirs()` returns 19 segments
including `bin`; swept with all 19 the code half reads **9/50/265/238 = 562**, not
0/43/265/228 = 536. The whole 26-hit gap is `bin`, and **19 of those 26 are
`#!/usr/bin/env` shebang lines** — 9 in Godot packs, 10 in Unity, 0 of Rust's 7. So `bin`
is the one arm-exclusive segment that fires in all four arms, and it does it through a
word that is not the Rust starter's `src/bin/` at all. Two consequences the next reader
needs: the ticket's *"exactly 1 hit in an arm the segment does not name"* is true only of
the 18-segment vocabulary (with `bin` it is 19), and `CHANGED.txt`'s detector keeps `bin`
correctly, because every row there **is** a path and no shebang can appear in one.
`code-half-bin-is-excluded-for-a-measured-reason` pins that, so the exclusion cannot be
inherited without its reason.

**THE MAIN RESULT IS THAT THE TICKET'S OWN CRITERION WAS THE WRONG QUANTITY.** The
done-when, and the `DECISIONS.md` reversal row, asked for a rewrite whose **per-arm
redaction count is comparable across all four arms**. That is satisfiable, and satisfying
it does not close the channel:

| candidate | godot | rust | ts | unity | per-arm density | isolates an arm |
|---|---|---|---|---|---|---|
| C1 arm-exclusive vocabulary (the declined one) | 0 | 43 | 265 | 228 | infinite | 6 of 9 fields |
| C2 every starter directory, shared included | 271 | 102 | 830 | 273 | 8.9x | 9 of 9 |
| C3 vocabulary-free: every path component | 831 | 927 | 1701 | 668 | 2.8x | 9 of 9 |
| C4 C3 minus the four bucket labels | 428 | 690 | 1021 | 668 | 2.1x | 9 of 9 |

*Isolates* = a **strict** threshold on ONE pack's redaction count separates a whole arm
from the other six, measured per field over the 9 independent stored fields, against
**7.1%** by chance. C4 gets the per-arm aggregate to 2.1x with **no arm at zero** —
passing the old criterion outright — and is **worse** on the statistic that matters, 9 of
9 against 6 of 9, at a cost of 2,807 redactions against 536. A per-arm total is an
aggregate over the corpus; a judge is shown eight packs and how redacted each one looks.
**Optimising a proxy the protected party never observes is a fix that measures nothing.**
The reversal row now names the per-field statistic.

**A tie is not a separation, and the first version of this measurement got it wrong.**
Sorting a field by redaction count and counting contiguous arm blocks reported *"godot is
the lowest pair in 10 of 10 fields"* — but three `wg-matrix` fields have four packs at
zero, and the ordering among them was `sorted`'s tie-breaking, not a signal. The shipped
statistic is strict inequality on both sides for that reason.

**`wg-g4c-capgate/uncapped` is not an independent field** and produced byte-identical
per-arm counts to `wg-g4c-2026-08-21T02-26-46` (rule 9). It shares **176 of 199 pack file
blobs** with it under different labels, so no digest of a pack catches it. The census
collapses fields on **shared content**, never on a run name — a name list would not
survive the next re-pack. `capped` is genuinely different: 94 of 199.

**The per-arm table for the manifest-mapping candidate, which the record never published.**
Over the 199 origins of the re-packed `wg-g4c` run: godot 33 of 56 origins hit / 71
occurrences, rust **0 of 43** / 0, ts 26 of 43 / 63, unity 14 of 57 / 18 — total 73 of 199
origins and 152 occurrences, against the recorded *"166 over 77 of 199"*. Rust is zero
because it names modules `crate::sim::world` and never as a path. Stack-correlated, and
more sharply than C1.

**Signal against collateral, over the 84 stored packs.** C1 redacts 536 segments, every
one an arm-exclusive starter directory. C4 redacts 2,807 to remove 428 of the same signal
— **5.6:1 collateral overall, 35:1 in Rust, and in Godot it removes 428 tokens carrying
zero arm signal.** The useful work stays stack-correlated under every candidate; only the
visible mark count moves.

**Three reds, established before the greens (rule 1, rule 14).** Patching `field.py`'s
sibling in place rather than symlinking, per task 95's trap: putting `bin` back into the
published vocabulary turns `code-half-published-table-reproduces` red with the exact
9/50/265/238; pointing `--runs-root` at one run instead of the corpus turns
`code-half-population` red (rule 12); both also fire `code-half-decision-may-be-stale`,
which is the reversal trigger and therefore proven able to fire. The **variant** the
done-when asks for holds by construction and is not merely asserted: the `field.py` diff
is comment-only, so no packing code changed, and parts 1-5 of the selftest — including the
byte-identical non-blind `CHANGED.txt` check — stay green.

**A citation repaired on the way.** `field.py` and `blind_dir_selftest.py` both said *"the
measurement that declined it is in tasks/96"*. Task 96 is the task-87 finding-numbering
ticket and holds no such measurement; it is this ticket. The reference resolved, which is
why nothing saw it.

**Left alone deliberately.** No starter or template file was touched, so `verify_blind`,
`starter_parity` and a `eval/RUNS.md` regime note are not required. No stored round is
repaired by any of this: every `architecture` round on disk read unredacted code content,
and that was already true and already recorded.

**A FINDING IS OWED AND NO NUMBER WAS ALLOCATED** (peer worktrees hold concurrent work).
The claim: *a reversal condition that names an aggregate the protected party never observes
can be satisfied while making the protected property worse.* Measured here — C4 drives
per-arm density from infinite to 2.1x, removes the zero arm entirely, and moves per-field
arm isolation from 6 of 9 to 9 of 9. This is rule 16's shape one level up: rule 16 says an
inert parameter is a question about the quantity; this says **a live parameter can be the
wrong quantity, and moving it looks exactly like progress.**

**Gates, unpiped:** `blind_dir_selftest --runs-root` 0, `blind_ext_selftest` 0,
`pack_selftest` 0, `anonymise_selftest` 0, `aspects_selftest` 0, `gate_selftest` 0,
`dead_private_control` 0, `withdrawn_control` 0, `field.py packcheck --run <wg-g4c path>`
0, `docstat.py --sweep` 0, `tasks.py check` 0 with 112 tasks well-formed. `ruff check` on
the changed file drops from 4 findings to 3 — the duplicated `git ls-files` call was
folded into one `starter_dirs_by_arm()`, so the exclusive and shared vocabularies cannot
be computed against different trees (rule 12). That refactor moved C2's row from
278/123/839/275 to the 271/102/830/273 above, because C2 now inherits the shipped
`SKIP_DIRS` rule; both tables were rewritten from the run, not from memory.
