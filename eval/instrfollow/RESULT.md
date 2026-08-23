# Result: compliance did not fall between 1 and 16 instructions

**Task 39. Run `eval/instrfollow/runs/main`, 2026-08-23, 104 trials, $9.06 measured.**
`DESIGN.md` was written and committed before any trial ran. Reproduce with
`python3 eval/instrfollow/run.py analyse --run-dir eval/instrfollow/runs/main` — it reads
stored trials and spends nothing.

## The answer

**320 of 320 instruction-instances complied. Every arm scored 1.000.** No decline with
instruction count, none with prompt length, none with position in the block.

| arm | k | obs | pass | rate | Wilson 95% |
|---|---|---|---|---|---|
| `k1` | 1 | 32 | 32 | 1.000 | [0.893, 1.000] |
| `k2` | 2 | 32 | 32 | 1.000 | [0.893, 1.000] |
| `k4` | 4 | 32 | 32 | 1.000 | [0.893, 1.000] |
| `k8` | 8 | 64 | 64 | 1.000 | [0.943, 1.000] |
| `k16` | 16 | 128 | 128 | 1.000 | [0.971, 1.000] |
| `k1pad` | 1 | 32 | 32 | 1.000 | [0.893, 1.000] |

104 trials, **every one `terminal_reason: success`**; 0 wrote no artifact, 0 produced an
unusable one. Turn use: median 2, max 15 against a ceiling of 40 — **the ceiling never
bound**, so this is not a truncated result.

### The effect is bounded, which is what makes the null a result

A sign test bounds nothing here: with 16 tied pairs it returns p=1.0000 whether the design
could have caught a 40-point drop or a 2-point one. The interval is the answer.

- Over all 16 instructions: `k16 − k1 = +0.0000`, Newcombe 95% CI **[−0.0291, +0.1072]**.
- **Over the 14 instructions the not-given control shows are doing work: `k16 − k1 =
  +0.0000`, 95% CI [−0.0332, +0.1206] — the largest decline consistent with this data is
  3.3 percentage points.** Quote this one.

The 14-instruction figure is the honest one because two instructions (`F5` no tabs, `B10`
no stdout) were satisfied by agents that were never given them. Their observations tighten
the interval while carrying no information about whether an instruction was followed —
keeping them buys a narrower bound out of rows that could not have moved.

## The controls that make the null mean something

A null is only worth reading if the instrument could have seen an effect. Four say it could.

### 1. The instructions demonstrably drive behaviour — 14 of 16 measurably

Every artifact was re-checked against **all 16** checkers, including the ones its trial was
never given. If compliance were mostly accidental, a rate of 1.000 would say nothing.

| effect (given − not given) | instructions |
|---|---|
| **1.000** | F1, F2, F3, F6, B2, B3, B4, B5, B7, B8, B9 — 11 of them, never once satisfied by an agent that was not asked |
| 0.500 | B6 (loud exit on a missing directory) |
| 0.250 | B1 (no error-swallowing `except`) |
| 0.060 | F4 (≤88 columns) |
| **0.000** | F5 (no tabs), B10 (silent stdout) — satisfied by default |

So the checkers can distinguish compliance from coincidence on 14 of 16, and the null is a
null about **instructions that were being followed**, not about checks that see nothing.

### 2. Length is not hiding a count effect, and nothing drifted

`k1pad` — one instruction, in a prompt padded to `k16` length with non-normative prose from
this project's own docs — scored **32/32, identical to `k1`**. Prompt length alone did not
move compliance.

`k1pad` also ran **last**, after every `k16` trial, so its agreement with `k1` bounds drift
over the run. Arms ran sequentially, so arm order is time order; this is what limits that
confound rather than eliminating it.

### 3. Position in the block did nothing

Order was randomised per trial and recorded, so this was free. Across the `k16` arm by
quartile of block position: **32/32, 32/32, 32/32, 32/32**. No U-shape, no tail-off. That is
a null on arXiv:2307.03172's effect for this pool at this length, not a refutation of it.

### 4. The apparatus is pinned in both directions, offline

`python3 eval/instrfollow/run.py gates` — census, pool, padding and statistics selftests in
one command, exit 1 on any failure. Green as of 2026-08-23. The pool half is: gold 16/16;
sixteen mutants each flipping **exactly one** checker; a legitimately different variant
16/16; an unparseable artifact 0/16.

## What this does NOT establish

Stated as plainly as the result, because the number is what will get quoted.

- **It does not test this repository's actual instruction count.** The always-loaded set
  holds **108–151** instructions depending on definition (`AGENTS.md` alone 43–66), read on
  2026-08-23 from `python3 eval/tools/instruction_census.py`. This experiment reached **16**.
  It read *73–113* when this result was written and the tool has not changed since — the
  always-loaded documents grew, which is what a count with a producer is supposed to reveal.
  The claim *"instruction count does not degrade compliance in this repository"* is
  **untested** — everything above stops at roughly a seventh of the real load.
- **It does not refute arXiv:2509.21051.** That paper's benchmarks reach 10 (text) and 6
  (code); at k≤16 on one task with one model, this is consistent with an effect that only
  bites higher, on harder instructions, or under conflict.
- **16 of 16 instructions saturated.** The pre-registered saturation outcome fired: at
  1.000 everywhere there is no variance for a count term to act on. Per rule 16 that is a
  question about the quantity, not the parameter — and the quantity's answer is the bound.
- **One model, one task, one shape of instruction.** Sonnet, a ~40-line single-file Python
  script, deterministic checkable constraints. Nothing here transfers to the folder-scoped
  or starter files without measuring them.
- **The padding cannot be proved instruction-free**, only free of anything the census scores
  as an instruction, anything opening as an imperative, and anything restating a pool
  instruction. Residual instructions would inflate `k1pad`'s effective count — conservative
  for a count claim, liberal for a length one. Since `k1pad` matched `k1` exactly, this does
  not bite here.

## What would actually test the open question

The gap is between 16 and whatever `instruction_census.py` reports today — 108–151 as of
2026-08-23, and growing — and closing it needs instructions, not trials. Sketch,
costed from what this run measured:

- **Grow the pool past 32.** The binding constraint is writing checkable, mutually
  non-conflicting, non-default instructions — this run's own not-given control shows 2 of 16
  were already dead on arrival, so a pool of 100 nominal instructions is perhaps 85 live.
- **Cost scales with k, steeply.** Measured per trial: k1 $0.056, k4 $0.089, k8 $0.152,
  k16 $0.273. Extrapolating past k16 is exactly the boundary `eval/AGENTS.md` forbids
  crossing without measuring — price a k32 pilot before sizing anything.
- **Interleave arms** rather than running them in blocks, which removes the time confound
  instead of merely bounding it.
- **Test conflict separately.** arXiv:2510.14842 puts the mechanism in conflict between
  instructions, and this pool was built conflict-free on purpose. Two contradictions already
  exist in the always-loaded set (tasks 77 and 79) and are a cheaper subject than count.

## Cost

$9.06 over 104 trials. **Per arm, never pooled** — the spread is 5×, so a single mean would
misprice every arm:

| arm | n | total | mean | min | max |
|---|---|---|---|---|---|
| `k1` | 32 | $1.80 | $0.0563 | $0.0477 | $0.0754 |
| `k2` | 16 | $1.04 | $0.0647 | $0.0516 | $0.0922 |
| `k4` | 8 | $0.71 | $0.0892 | $0.0557 | $0.1209 |
| `k8` | 8 | $1.22 | $0.1522 | $0.0736 | $0.2111 |
| `k16` | 8 | $2.18 | $0.2728 | $0.2177 | $0.3632 |
| `k1pad` | 32 | $2.11 | $0.0659 | $0.0533 | $0.0935 |

Plus $0.83 for the 8-trial pilot, which changed the apparatus twice — see `DESIGN.md`.
