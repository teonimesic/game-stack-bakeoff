---
id: 210
title: capability.py's gate docstring names stack_cannot as failure mode 3, but no check fails on a stack_cannot every arm marks
status: done
priority: 5
refs: eval/judge/capability.py
done_when: code and docstring agree about stack_cannot, one way or the other - EITHER no_stack_correlated_gap reports any `stack_cannot` reason it sees anywhere (one added check; the constant's own comment already says "GATE FAILURE"), OR the docstring's way 3 is narrowed to say a stack_cannot is caught only through the per-field asymmetry path and a uniform one is out of its sight; capability_selftest.py gains a fixture that marks stack_cannot on ALL arms of one (run, class) cell with the expected verdict stated in the expectation, and exits 0 unpiped after, with python3 eval/judge/capability.py --runs <main checkout>/eval/runs still exit 0.
established_by: 'PR #89 squash c44b31d; verified at b9121211 in the agent worktree unpiped: selftest exit 0 all-controls-hold with the uniform stack_cannot fixture red 8-of-8 (all four arms, field and reason named) and the scene variant 2-of-2; asymmetry path pinned still firing beside the new reason scan; branch code on the stored corpus exit 0, 0 stack_cannot, census 64/69 unchanged; agent measured the fixture RED 4 expectations against the unfixed module first; CI gates+controls green at merge; findings: none, executes task 210'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/89
---

`eval/judge/capability.py`'s gate says one thing about `stack_cannot` and does another.

- `STACK_CANNOT = "stack_cannot"  # this arm has no mechanism. GATE FAILURE.` (the
  contract section).
- `no_stack_correlated_gap`'s docstring, "Four ways to fail", item 3: a null marked
  `stack_cannot` "should be unreachable. If it appears, the contract is wrong and this is
  how you find out."

The code: `stack_cannot` appears in no predicate. The per-field loop (implementation of
docstring ways 3-4) skips any field nobody populated in the cell
(`if not any(populated.values()): continue`), and its problem path fires on the
ABSENCE-asymmetry, not on the reason string - a `stack_cannot` is reported only when it
sits beside a populated arm in the same (run, task class) cell. So:

| who marks stack_cannot | gate verdict |
|---|---|
| one arm, others populate the field | reported (asymmetry path) |
| every arm of one cell | **exit 0, silent** |

The every-arm case is the loudest contract break possible - all four arms lacking the
mechanism the contract says is measured identically everywhere - and it is the one the
gate cannot see. This is the #38 class: a document naming a check that does not exist,
except here the document is a docstring and the check half-exists.

**Measured 2026-08-29:** 0 `stack_cannot` reasons in the 69 stored records, so nothing
live is miscounted and the corpus pins and census reproduce (64 of 69 at default, 3
varied, 2 absent - re-run same day). Latent only; that is why p5.

**What NOT to conclude:** the asymmetry path IS real and IS exercised by its pins; this
ticket does not claim the gate is blind, only that its third listed failure mode is
partially implemented. Pick one side - make the code fire on any `stack_cannot`, or make
the docstring say what the code does - and pin it with a fixture whose answer is stated
in advance. Do not widen `FIELDS`, do not touch the DECLINED register, do not write into
`eval/runs/`.
